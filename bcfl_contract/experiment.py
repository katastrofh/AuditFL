from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .fl import aggregate, evaluate, init_model, load_dataset_noniid, train_local, validate_update
from .store import ArtifactUnavailable, ContentAddressedStore
from .mock_chain import MockCoordinator, hash_bytes32


@dataclass
class RunConfig:
    backend: str = "mock"
    clients: int = 10
    rounds: int = 12
    local_epochs: int = 2
    lr: float = 0.35
    seed: int = 7
    noniid_alpha: float = 0.4
    dataset: str = "digits"
    max_samples: int | None = None
    dropout_rate: float = 0.0
    storage_fail_rate: float = 0.0
    invalid_rate: float = 0.0
    deposit_wei: int = 10**15
    reward_wei: int = 10**16
    rpc_url: str = "http://127.0.0.1:8545"


def _sha(text: str) -> str:
    return "0x" + hashlib.sha256(text.encode()).hexdigest()


def _accounts(n: int) -> list[str]:
    return [f"acct_{i}" for i in range(n)]


def _make_chain(cfg: RunConfig):
    if cfg.backend == "mock":
        return MockCoordinator(_accounts(cfg.clients + 1), deposit_wei=cfg.deposit_wei), _accounts(cfg.clients + 1)
    if cfg.backend == "anvil":
        from .evm_chain import EVMCoordinator
        chain = EVMCoordinator(rpc_url=cfg.rpc_url)
        if len(chain.accounts) < cfg.clients + 1:
            raise RuntimeError(f"Need at least {cfg.clients + 1} unlocked Anvil accounts")
        return chain, chain.accounts[: cfg.clients + 1]
    raise ValueError(f"unknown backend {cfg.backend}")


def run_plain_fl(cfg: RunConfig) -> pd.DataFrame:
    ds = load_dataset_noniid(cfg.clients, cfg.noniid_alpha, cfg.seed, cfg.dataset, cfg.max_samples)
    model = init_model(ds.n_features, ds.n_classes, cfg.seed)
    rows = []
    for r in range(cfg.rounds):
        updates = []
        for Xc, yc in ds.client_data:
            updates.append(train_local(model, Xc, yc, epochs=cfg.local_epochs, lr=cfg.lr))
        model = aggregate(updates)
        rows.append({"round": r, "mode": "plain", "test_acc": evaluate(model, *ds.test), "val_acc": evaluate(model, *ds.val), "included": len(updates)})
    return pd.DataFrame(rows)


def run_bcfl(cfg: RunConfig, out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = random.Random(cfg.seed)
    ds = load_dataset_noniid(cfg.clients, cfg.noniid_alpha, cfg.seed, cfg.dataset, cfg.max_samples)
    store = ContentAddressedStore(out_dir / "artifact_store", fail_rate=cfg.storage_fail_rate, seed=cfg.seed)
    chain, accounts = _make_chain(cfg)
    lister = accounts[0]
    client_accounts = accounts[1: cfg.clients + 1]

    model = init_model(ds.n_features, ds.n_classes, cfg.seed)
    init_cid = store.put_obj(model)
    model_id = f"model_{ds.name}_noniid"
    rules = {"deposit_wei": cfg.deposit_wei, "dataset": ds.name, "n_total": ds.n_total, "noniid_alpha": cfg.noniid_alpha, "local_epochs": cfg.local_epochs, "lr": cfg.lr}
    rules_hash = _sha(json.dumps(rules, sort_keys=True))
    chain.create_listing(lister, model_id, init_cid, rules_hash, cfg.deposit_wei)

    rows = []
    ticket_rows = []
    total_wall = 0.0
    for r in range(cfg.rounds):
        t0 = time.perf_counter()
        chain.fund_round(lister, model_id, cfg.reward_wei)
        ticket_meta = []
        for cid, (acct, (Xc, yc)) in enumerate(zip(client_accounts, ds.client_data)):
            if rng.random() < cfg.dropout_rate:
                ticket_rows.append({"round": r, "client": cid, "ticket_id": None, "status": "dropped"})
                continue
            ticket_id, _ = chain.reserve_ticket(acct, model_id, r, cfg.deposit_wei)
            update = train_local(model, Xc, yc, epochs=cfg.local_epochs, lr=cfg.lr)
            if rng.random() < cfg.invalid_rate:
                update = {"W": update["W"][:-1, :], "b": update["b"], "n": update["n"], "invalid": True}
            update_cid = store.put_obj(update)
            metrics_hash = _sha(json.dumps({"client": cid, "n": int(len(yc)), "round": r}, sort_keys=True))
            chain.publish_update(acct, model_id, r, ticket_id, update_cid, metrics_hash)
            ticket_meta.append((ticket_id, acct, update_cid))
            ticket_rows.append({"round": r, "client": cid, "ticket_id": ticket_id, "status": "published", "update_cid": update_cid})

        included_ids: list[int] = []
        refund_ids: list[int] = []
        included_updates: list[dict] = []
        unretrievable = 0
        invalid = 0
        expected_shape = model["W"].shape
        for ticket_id, acct, update_cid in ticket_meta:
            try:
                upd = store.get_obj(update_cid)
            except ArtifactUnavailable:
                unretrievable += 1
                continue
            refund_ids.append(ticket_id)
            if validate_update(upd, expected_shape, ds.n_classes):
                included_ids.append(ticket_id)
                included_updates.append(upd)
            else:
                invalid += 1
        if included_updates:
            model = aggregate(included_updates)
        global_cid = store.put_obj(model)
        scores_hash = _sha(json.dumps({"included": included_ids, "refunds": refund_ids}, sort_keys=True))
        chain.finalize_round(lister, model_id, r, global_cid, included_ids, refund_ids, scores_hash)
        total_wall += time.perf_counter() - t0
        rows.append({
            "round": r,
            "mode": f"bcfl_{cfg.backend}",
            "test_acc": evaluate(model, *ds.test),
            "val_acc": evaluate(model, *ds.val),
            "included": len(included_ids),
            "refunds": len(refund_ids),
            "published": len(ticket_meta),
            "dropped": cfg.clients - len(ticket_meta),
            "unretrievable": unretrievable,
            "invalid": invalid,
            "store_get_failures": store.get_failures,
            "global_cid": global_cid,
            "wall_seconds_cumulative": total_wall,
        })

    # Claim once at end for accounts with entitlements. Some accounts may have nothing, which is expected.
    claim_errors = 0
    for acct in client_accounts:
        try:
            chain.claim(acct, model_id)
        except Exception:
            claim_errors += 1
    receipt_rows = []
    for rec in getattr(chain, "receipts", []):
        if isinstance(rec, dict):
            receipt_rows.append(rec)
        else:
            receipt_rows.append(asdict(rec))
    receipts = pd.DataFrame(receipt_rows)
    if len(receipts):
        receipts["backend"] = cfg.backend
    metrics = pd.DataFrame(rows)
    tickets = pd.DataFrame(ticket_rows)
    summary = pd.DataFrame([{
        "backend": cfg.backend,
        "dataset": ds.name,
        "n_total": ds.n_total,
        "clients": cfg.clients,
        "rounds": cfg.rounds,
        "final_test_acc": float(metrics["test_acc"].iloc[-1]),
        "mean_included": float(metrics["included"].mean()),
        "mean_refunds": float(metrics["refunds"].mean()),
        "mean_unretrievable": float(metrics["unretrievable"].mean()),
        "mean_invalid": float(metrics["invalid"].mean()),
        "store_puts": store.put_count,
        "store_gets": store.get_count,
        "store_get_failures": store.get_failures,
        "tx_count": int(len(receipts)),
        "total_gas_used_model_or_estimate": int(receipts["gas_used"].sum()) if len(receipts) and "gas_used" in receipts else 0,
        "claim_errors_expected_when_no_entitlement": claim_errors,
    }])
    return metrics, receipts, summary


def run_experiment_suite(cfg: RunConfig, out_dir: Path) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plain = run_plain_fl(cfg)
    bcfl, receipts, summary = run_bcfl(cfg, out_dir)
    plain.to_csv(out_dir / "plain_fl_rounds.csv", index=False)
    bcfl.to_csv(out_dir / f"bcfl_{cfg.backend}_rounds.csv", index=False)
    receipts.to_csv(out_dir / f"contract_{cfg.backend}_receipts.csv", index=False)
    summary["plain_final_test_acc"] = float(plain["test_acc"].iloc[-1])
    summary["accuracy_gap_vs_plain"] = summary["final_test_acc"] - summary["plain_final_test_acc"]
    summary.to_csv(out_dir / "contract_mvp_summary.csv", index=False)
    notes = out_dir / "paper_ready_notes.md"
    s = summary.iloc[0].to_dict()
    notes.write_text(
        f"# Contract-backed BC-FL MVP notes\n\n"
        f"Backend: `{cfg.backend}`\n\n"
        f"Dataset: {s['dataset']} (n={int(s['n_total'])}), non-IID Dirichlet alpha={cfg.noniid_alpha}, clients={cfg.clients}, rounds={cfg.rounds}.\n\n"
        f"Plain FL final test accuracy: {s['plain_final_test_acc']:.4f}.\n\n"
        f"Contract-backed BC-FL final test accuracy: {s['final_test_acc']:.4f}.\n\n"
        f"Accuracy gap: {s['accuracy_gap_vs_plain']:.4f}.\n\n"
        f"Mean included updates per round: {s['mean_included']:.2f}.\n\n"
        f"Stored artifacts: puts={s['store_puts']}, gets={s['store_gets']}, injected/missing get failures={s['store_get_failures']}.\n\n"
        f"Transactions: {s['tx_count']}; total gas used / mock gas estimate: {s['total_gas_used_model_or_estimate']}.\n"
    )
    return {
        "plain": out_dir / "plain_fl_rounds.csv",
        "bcfl": out_dir / f"bcfl_{cfg.backend}_rounds.csv",
        "receipts": out_dir / f"contract_{cfg.backend}_receipts.csv",
        "summary": out_dir / "contract_mvp_summary.csv",
        "notes": notes,
    }
