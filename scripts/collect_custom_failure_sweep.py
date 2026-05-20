from pathlib import Path
import pandas as pd
import re

CLIENTS = 50
ROUNDS = 12

base = Path(".")
rows = []

pattern = re.compile(
    rf"results_mock_mnist_full_N{CLIENTS}_R{ROUNDS}_seed(\d+)_(storage|dropout|invalid)_([0-9]+p[0-9]+)$"
)

for d in sorted(base.glob(f"results_mock_mnist_full_N{CLIENTS}_R{ROUNDS}_seed*")):
    if not d.is_dir():
        continue

    m = pattern.match(d.name)
    if not m:
        print(f"Skipping unrecognized folder: {d.name}")
        continue

    seed = int(m.group(1))
    failure_type = m.group(2)
    rate_label = m.group(3)
    failure_rate = float(rate_label.replace("p", "."))

    summary_path = d / "contract_mvp_summary.csv"
    if not summary_path.exists():
        print(f"Skipping incomplete folder: {d.name}")
        continue

    s = pd.read_csv(summary_path).iloc[0].to_dict()

    rows.append({
        "seed": seed,
        "failure_type": failure_type,
        "failure_rate": failure_rate,
        "scenario": f"{failure_type}_{failure_rate:.2f}",
        "backend": s.get("backend"),
        "dataset": s.get("dataset"),
        "n_total": int(s.get("n_total", 70000)),
        "clients": int(s.get("clients")),
        "rounds": int(s.get("rounds")),
        "plain_final_test_acc": float(s.get("plain_final_test_acc")),
        "auditfl_final_test_acc": float(s.get("final_test_acc")),
        "accuracy_gap_vs_plain": float(s.get("accuracy_gap_vs_plain")),
        "mean_included": float(s.get("mean_included")),
        "mean_refunds": float(s.get("mean_refunds")),
        "mean_unretrievable": float(s.get("mean_unretrievable")),
        "mean_invalid": float(s.get("mean_invalid")),
        "store_puts": int(s.get("store_puts")),
        "store_gets": int(s.get("store_gets")),
        "store_get_failures": int(s.get("store_get_failures")),
        "tx_count_or_estimate": int(s.get("tx_count")),
        "gas_model_or_estimate": int(s.get("total_gas_used_model_or_estimate")),
    })

if not rows:
    raise SystemExit("No completed failure-sweep results found.")

df = pd.DataFrame(rows).sort_values(["failure_type", "failure_rate", "seed"])
df.to_csv("auditfl_failure_sweep_mnist_full_N50_all_runs.csv", index=False)

numeric_cols = [
    "plain_final_test_acc",
    "auditfl_final_test_acc",
    "accuracy_gap_vs_plain",
    "mean_included",
    "mean_refunds",
    "mean_unretrievable",
    "mean_invalid",
    "store_get_failures",
]

agg_parts = []
for col in numeric_cols:
    tmp = (
        df.groupby(["failure_type", "failure_rate"])[col]
        .agg(["mean", "std"])
        .reset_index()
    )
    tmp = tmp.rename(columns={
        "mean": f"{col}_mean",
        "std": f"{col}_std",
    })
    agg_parts.append(tmp)

agg = agg_parts[0]
for tmp in agg_parts[1:]:
    agg = agg.merge(tmp, on=["failure_type", "failure_rate"], how="outer")

agg = agg.sort_values(["failure_type", "failure_rate"])
agg.to_csv("auditfl_failure_sweep_mnist_full_N50_aggregate.csv", index=False)

print("\n=== All runs ===")
print(df.to_string(index=False))

print("\n=== Aggregate ===")
print(agg.to_string(index=False))

print("\nWrote:")
print("auditfl_failure_sweep_mnist_full_N50_all_runs.csv")
print("auditfl_failure_sweep_mnist_full_N50_aggregate.csv")
