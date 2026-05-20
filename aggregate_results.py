from pathlib import Path
import pandas as pd

clients_list = [1, 2, 5, 10, 15, 20, 30, 40, 50, 75, 100, 150, 200]

summary_rows = []
gas_rows = []

for n in clients_list:
    d = Path(f"results_anvil_mnist_full_N{n}_12r")
    summary_path = d / "contract_mvp_summary.csv"
    receipts_path = d / "contract_anvil_receipts.csv"
    store_dir = d / "artifact_store"

    if not summary_path.exists() or not receipts_path.exists():
        print(f"Skipping N={n}: missing outputs")
        continue

    s = pd.read_csv(summary_path).iloc[0].to_dict()
    r = pd.read_csv(receipts_path)

    rounds = int(s["rounds"])
    expected_app_txs = 1 + rounds * (2*n + 2) + n
    expected_total_txs = expected_app_txs + 1  # includes contract deployment

    artifact_sizes = []
    total_offchain_bytes = 0
    if store_dir.exists():
        for p in store_dir.iterdir():
            if p.is_file():
                size = p.stat().st_size
                artifact_sizes.append(size)
                total_offchain_bytes += size

    measured_artifacts = len(artifact_sizes)
    expected_artifacts = 1 + rounds * (n + 1)
    expected_gets = rounds * n

    # local identifier format: sha256:<64 hex chars> = 71 ASCII bytes
    identifier_bytes = measured_artifacts * 71

    total_gas = int(s["total_gas_used_model_or_estimate"])
    measured_txs = int(s["tx_count"])

    summary_rows.append({
        "clients": n,
        "rounds": rounds,
        "dataset": s["dataset"],
        "n_total": int(s.get("n_total", 70000)),

        "plain_acc": float(s["plain_final_test_acc"]),
        "auditfl_acc": float(s["final_test_acc"]),
        "accuracy_gap": float(s["accuracy_gap_vs_plain"]),
        "mean_included": float(s["mean_included"]),

        "measured_txs": measured_txs,
        "expected_total_txs": expected_total_txs,
        "tx_match": measured_txs == expected_total_txs,

        "total_gas_used": total_gas,
        "gas_per_round": total_gas / rounds,
        "gas_per_client_round": total_gas / (n * rounds),

        "store_puts": int(s["store_puts"]),
        "expected_artifacts": expected_artifacts,
        "measured_artifacts": measured_artifacts,
        "artifact_count_match": measured_artifacts == expected_artifacts,

        "store_gets": int(s["store_gets"]),
        "expected_gets": expected_gets,
        "store_get_failures": int(s["store_get_failures"]),

        "total_offchain_bytes": total_offchain_bytes,
        "total_offchain_mib": total_offchain_bytes / (1024 * 1024),
        "avg_artifact_bytes": total_offchain_bytes / measured_artifacts if measured_artifacts else 0,
        "identifier_bytes": identifier_bytes,
        "identifier_mib": identifier_bytes / (1024 * 1024),
        "offchain_to_identifier_ratio": total_offchain_bytes / identifier_bytes if identifier_bytes else 0,
        "offchain_bytes_per_client_round": total_offchain_bytes / (n * rounds),
    })

    g = r.groupby("event")["gas_used"].agg(["count", "mean", "sum"]).reset_index()
    g.insert(0, "clients", n)
    gas_rows.append(g)

summary = pd.DataFrame(summary_rows)
gas = pd.concat(gas_rows, ignore_index=True) if gas_rows else pd.DataFrame()

summary.to_csv("auditfl_scaling_full_mnist_summary_N1_to_N200.csv", index=False)
gas.to_csv("auditfl_scaling_full_mnist_gas_by_operation_N1_to_N200.csv", index=False)

print("\n=== AuditFL full-MNIST scaling summary N=1..200 ===")
print(summary.to_string(index=False))

print("\n=== Gas by operation N=1..200 ===")
print(gas.to_string(index=False))

