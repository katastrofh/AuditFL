#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bcfl_contract.experiment import RunConfig, run_experiment_suite


def main() -> None:
    ap = argparse.ArgumentParser(description="Run contract-backed BC-FL MVP experiments")
    ap.add_argument("--backend", choices=["mock", "anvil"], default="mock", help="mock is dependency-free; anvil deploys the Solidity contract to a local EVM RPC")
    ap.add_argument("--out", default="results_contract_mvp")
    ap.add_argument("--clients", type=int, default=10)
    ap.add_argument("--dataset", choices=["digits", "mnist", "fashion_mnist"], default="digits", help="digits is built in; mnist/fashion_mnist download from OpenML on first run")
    ap.add_argument("--max-samples", type=int, default=0, help="optional stratified cap; use 0 for the full dataset")
    ap.add_argument("--rounds", type=int, default=12)
    ap.add_argument("--quick", action="store_true", help="short smoke run")
    ap.add_argument("--storage-fail-rate", type=float, default=0.0)
    ap.add_argument("--dropout-rate", type=float, default=0.0)
    ap.add_argument("--invalid-rate", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--rpc-url", default="http://127.0.0.1:8545")
    args = ap.parse_args()
    rounds = 4 if args.quick else args.rounds
    cfg = RunConfig(
        backend=args.backend,
        clients=args.clients,
        rounds=rounds,
        seed=args.seed,
        dataset=args.dataset,
        max_samples=(args.max_samples or None),
        storage_fail_rate=args.storage_fail_rate,
        dropout_rate=args.dropout_rate,
        invalid_rate=args.invalid_rate,
        rpc_url=args.rpc_url,
    )
    outputs = run_experiment_suite(cfg, Path(args.out))
    print("Wrote outputs:")
    for k, p in outputs.items():
        print(f"  {k}: {p}")
    import pandas as pd
    print(pd.read_csv(outputs["summary"]).to_string(index=False))


if __name__ == "__main__":
    main()
