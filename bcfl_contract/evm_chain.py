from __future__ import annotations

from pathlib import Path
import json
import os


class EVMUnavailable(RuntimeError):
    pass


class EVMCoordinator:
    """Thin wrapper for deploying and using BCFLCoordinator on an Ethereum-compatible RPC.

    Requires:
      pip install -r requirements-evm.txt
      anvil --host 127.0.0.1 --port 8545
    """
    def __init__(self, rpc_url: str = "http://127.0.0.1:8545", contract_path: str | None = None):
        try:
            from web3 import Web3
            from solcx import compile_standard, install_solc, set_solc_version
        except Exception as e:
            raise EVMUnavailable("Install EVM deps with: pip install -r requirements-evm.txt") from e
        self.Web3 = Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise EVMUnavailable(f"Cannot connect to RPC {rpc_url}. Start Anvil first.")
        self.accounts = self.w3.eth.accounts
        if not self.accounts:
            raise EVMUnavailable("RPC has no unlocked accounts")
        contract_path = contract_path or str(Path(__file__).resolve().parents[1] / "contracts" / "BCFLCoordinator.sol")
        source = Path(contract_path).read_text()
        version = "0.8.24"
        try:
            set_solc_version(version)
        except Exception:
            install_solc(version)
            set_solc_version(version)
        compiled = compile_standard({
            "language": "Solidity",
            "sources": {"BCFLCoordinator.sol": {"content": source}},
            "settings": {
                # The coordinator has array-heavy round-finalization logic.
                # viaIR + optimizer avoids Solidity's "stack too deep" codegen limit.
                "optimizer": {"enabled": True, "runs": 200},
                "viaIR": True,
                "outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}},
            },
        })
        c = compiled["contracts"]["BCFLCoordinator.sol"]["BCFLCoordinator"]
        self.abi = c["abi"]
        self.bytecode = c["evm"]["bytecode"]["object"]
        Contract = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        tx_hash = Contract.constructor().transact({"from": self.accounts[0]})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.address = receipt.contractAddress
        self.contract = self.w3.eth.contract(address=self.address, abi=self.abi)
        self.receipts = [{"tx": receipt.transactionHash.hex(), "gas_used": receipt.gasUsed, "event": "Deploy"}]

    @staticmethod
    def _b32(hex_or_text: str) -> bytes:
        if hex_or_text.startswith("0x") and len(hex_or_text) == 66:
            return bytes.fromhex(hex_or_text[2:])
        import hashlib
        return hashlib.sha256(hex_or_text.encode()).digest()

    def _tx(self, fn, sender: str, value: int = 0):
        tx_hash = fn.transact({"from": sender, "value": value})
        r = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        name = getattr(fn, "fn_name", None) or getattr(fn, "function_identifier", None) or "tx"
        self.receipts.append({"tx": r.transactionHash.hex(), "gas_used": int(r.gasUsed), "event": name})
        return r

    def create_listing(self, sender: str, model_id: str, init_cid: str, rules_hash: str, deposit_wei: int):
        return self._tx(self.contract.functions.createListing(self._b32(model_id), init_cid, self._b32(rules_hash), deposit_wei), sender)

    def fund_round(self, sender: str, model_id: str, amount_wei: int):
        return self._tx(self.contract.functions.fundRound(self._b32(model_id)), sender, amount_wei)

    def reserve_ticket(self, sender: str, model_id: str, round_index: int, deposit_wei: int):
        before = self.contract.functions.getModel(self._b32(model_id)).call()[6]
        r = self._tx(self.contract.functions.reserveTicket(self._b32(model_id), round_index), sender, deposit_wei)
        return int(before), r

    def publish_update(self, sender: str, model_id: str, round_index: int, ticket_id: int, update_cid: str, metrics_hash: str):
        return self._tx(self.contract.functions.publishUpdate(self._b32(model_id), round_index, ticket_id, update_cid, self._b32(metrics_hash)), sender)

    def finalize_round(self, sender: str, model_id: str, round_index: int, global_cid: str, included: list[int], refunds: list[int], scores_hash: str):
        return self._tx(self.contract.functions.finalizeRound(self._b32(model_id), round_index, global_cid, included, refunds, self._b32(scores_hash)), sender)

    def claim(self, sender: str, model_id: str):
        return self._tx(self.contract.functions.claim(self._b32(model_id)), sender)

    def current_round(self, model_id: str) -> int:
        return int(self.contract.functions.getModel(self._b32(model_id)).call()[3])

    def global_cid(self, model_id: str) -> str:
        return self.contract.functions.getModel(self._b32(model_id)).call()[1]
