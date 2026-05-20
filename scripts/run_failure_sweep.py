#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bcfl_contract.experiment import RunConfig, run_experiment_suite


def main() -> None:
    ap = argparse.ArgumentParser(description="Run dropout/storage/invalid sweeps for the BC-FL contract MVP")
    ap.add_argument("--backend", choices=["mock", "anvil"], default="mock")
    ap.add_argument("--out", default="results_contract_sweep")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--dataset", choices=["digits", "mnist", "fashion_mnist"], default="digits")
    ap.add_argument("--max-samples", type=int, default=0)
    ap.add_argument("--rpc-url", default="http://127.0.0.1:8545")
    args = ap.parse_args()
    root = Path(args.out); root.mkdir(parents=True, exist_ok=True)
    rounds = 4 if args.quick else 12
    cases = []
    for rate in ([0.0, 0.3] if args.quick else [0.0, 0.1, 0.2, 0.4]):
        cases.append((f"storage_{rate}", {"storage_fail_rate": rate}))
    for rate in ([0.0, 0.3] if args.quick else [0.0, 0.2, 0.4]):
        cases.append((f"dropout_{rate}", {"dropout_rate": rate}))
        cases.append((f"invalid_{rate}", {"invalid_rate": rate}))
    summaries = []
    for name, params in cases:
        cfg = RunConfig(backend=args.backend, rounds=rounds, rpc_url=args.rpc_url, seed=13, dataset=args.dataset, max_samples=(args.max_samples or None), **params)
        out = root / name
        outputs = run_experiment_suite(cfg, out)
        s = pd.read_csv(outputs["summary"])
        s.insert(0, "scenario", name)
        summaries.append(s)
    table = pd.concat(summaries, ignore_index=True)
    table.to_csv(root / "sweep_summary.csv", index=False)
    print(table.to_string(index=False))

if __name__ == "__main__":
    main()
