from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def hash_bytes32(text: str) -> str:
    return "0x" + hashlib.sha256(text.encode()).hexdigest()


@dataclass
class Receipt:
    tx: str
    gas_used: int
    status: int = 1
    event: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Ticket:
    owner: str
    round: int
    deposit: int
    revealed: bool = False
    settled: bool = False
    update_cid: str = ""
    metrics_hash: str = ""


class MockCoordinator:
    """Same public API as the Solidity coordinator, but deterministic and dependency-free."""
    def __init__(self, accounts: list[str], deposit_wei: int = 10**15):
        self.accounts = accounts
        self.deposit_wei = deposit_wei
        self.models: dict[str, dict] = {}
        self.tickets: dict[tuple[str, int], Ticket] = {}
        self.entitlements: dict[tuple[str, str], int] = {}
        self.receipts: list[Receipt] = []
        self._tx_nonce = 0

    def _receipt(self, event: str, gas: int, data: dict[str, Any]) -> Receipt:
        self._tx_nonce += 1
        payload = json.dumps(data, sort_keys=True, default=str)
        tx = "0x" + hashlib.sha256(f"{self._tx_nonce}:{event}:{payload}".encode()).hexdigest()
        r = Receipt(tx=tx, gas_used=gas, event=event, data=data)
        self.receipts.append(r)
        return r

    def create_listing(self, sender: str, model_id: str, init_cid: str, rules_hash: str, deposit_wei: int | None = None) -> Receipt:
        if model_id in self.models:
            raise ValueError("model exists")
        self.models[model_id] = {
            "lister": sender,
            "global_cid": init_cid,
            "rules_hash": rules_hash,
            "current_round": 0,
            "deposit_wei": deposit_wei or self.deposit_wei,
            "pool_wei": 0,
            "next_ticket_id": 1,
        }
        return self._receipt("ListingCreated", 145_000, {"model_id": model_id, "init_cid": init_cid})

    def fund_round(self, sender: str, model_id: str, amount_wei: int) -> Receipt:
        m = self.models[model_id]
        m["pool_wei"] += amount_wei
        return self._receipt("RoundFunded", 52_000, {"model_id": model_id, "amount_wei": amount_wei})

    def reserve_ticket(self, sender: str, model_id: str, round_index: int, deposit_wei: int | None = None) -> tuple[int, Receipt]:
        m = self.models[model_id]
        if round_index != m["current_round"]:
            raise ValueError("wrong round")
        if deposit_wei is not None and deposit_wei != m["deposit_wei"]:
            raise ValueError("bad deposit")
        tid = m["next_ticket_id"]
        m["next_ticket_id"] += 1
        self.tickets[(model_id, tid)] = Ticket(sender, round_index, m["deposit_wei"])
        return tid, self._receipt("TicketReserved", 86_000, {"model_id": model_id, "round": round_index, "ticket_id": tid, "owner": sender})

    def publish_update(self, sender: str, model_id: str, round_index: int, ticket_id: int, update_cid: str, metrics_hash: str) -> Receipt:
        m = self.models[model_id]
        t = self.tickets[(model_id, ticket_id)]
        if round_index != m["current_round"] or t.round != round_index:
            raise ValueError("wrong round")
        if t.owner != sender:
            raise ValueError("not owner")
        if t.revealed:
            raise ValueError("already revealed")
        t.revealed = True
        t.update_cid = update_cid
        t.metrics_hash = metrics_hash
        return self._receipt("UpdatePublished", 93_000, {"model_id": model_id, "round": round_index, "ticket_id": ticket_id, "cid": update_cid})

    def finalize_round(self, sender: str, model_id: str, round_index: int, global_cid: str, included: list[int], refunds: list[int], scores_hash: str) -> Receipt:
        m = self.models[model_id]
        if sender != m["lister"]:
            raise ValueError("only lister")
        if round_index != m["current_round"]:
            raise ValueError("wrong round")
        for tid in refunds:
            t = self.tickets[(model_id, tid)]
            if not t.revealed or t.round != round_index or t.settled:
                raise ValueError("bad refund ticket")
            t.settled = True
            key = (model_id, t.owner)
            self.entitlements[key] = self.entitlements.get(key, 0) + t.deposit
        reward = m["pool_wei"] // len(included) if included and m["pool_wei"] > 0 else 0
        paid = 0
        for tid in included:
            t = self.tickets[(model_id, tid)]
            if not t.revealed or t.round != round_index:
                raise ValueError("bad included ticket")
            key = (model_id, t.owner)
            self.entitlements[key] = self.entitlements.get(key, 0) + reward
            paid += reward
        m["pool_wei"] -= paid
        m["global_cid"] = global_cid
        m["current_round"] += 1
        return self._receipt("RoundFinalized", 125_000 + 10_000 * (len(included) + len(refunds)), {"model_id": model_id, "round": round_index, "included": len(included), "refunds": len(refunds)})

    def claim(self, sender: str, model_id: str) -> Receipt:
        amount = self.entitlements.get((model_id, sender), 0)
        if amount <= 0:
            raise ValueError("nothing to claim")
        self.entitlements[(model_id, sender)] = 0
        return self._receipt("Claimed", 38_000, {"model_id": model_id, "account": sender, "amount_wei": amount})

    def current_round(self, model_id: str) -> int:
        return int(self.models[model_id]["current_round"])

    def global_cid(self, model_id: str) -> str:
        return str(self.models[model_id]["global_cid"])
