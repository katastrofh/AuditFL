from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

summary_path = Path("auditfl_scaling_full_mnist_summary_N1_to_N200.csv")
gas_path = Path("auditfl_scaling_full_mnist_gas_by_operation_N1_to_N200.csv")
out_dir = Path("paper_figures")
out_dir.mkdir(exist_ok=True)

summary = pd.read_csv(summary_path)
gas = pd.read_csv(gas_path)

# Make sure rows are ordered by client count.
summary = summary.sort_values("clients")
gas = gas.sort_values(["clients", "event"])

clients = summary["clients"]

def millions(x, pos):
    return f"{x/1e6:.0f}M"

def thousands(x, pos):
    return f"{x/1e3:.0f}k"

# -----------------------------
# Figure 1: Control-plane scaling
# -----------------------------

# Gas by operation. Keep the dominant operations separate and merge small ones.
dominant = {"publishUpdate", "reserveTicket", "finalizeRound"}
gas2 = gas.copy()
gas2["event_group"] = gas2["event"].where(gas2["event"].isin(dominant), "other")

gas_pivot = (
    gas2.groupby(["clients", "event_group"])["sum"]
    .sum()
    .unstack(fill_value=0)
    .reindex(summary["clients"])
)

# Use stable order.
ordered_cols = [c for c in ["reserveTicket", "publishUpdate", "finalizeRound", "other"] if c in gas_pivot.columns]
gas_pivot = gas_pivot[ordered_cols]

fig, axes = plt.subplots(1, 3, figsize=(7.15, 2.45), constrained_layout=True)

# (a) measured vs analytical transaction count
ax = axes[0]
ax.plot(clients, summary["measured_txs"], marker="o", linewidth=1.4, label="measured")
ax.plot(clients, summary["expected_total_txs"], linestyle="--", linewidth=1.4, label="analytical")
ax.set_xlabel("clients")
ax.set_ylabel("transactions")
ax.set_title("(a) transaction model")
ax.grid(True, linewidth=0.3, alpha=0.5)
ax.legend(fontsize=6, frameon=False)
ax.yaxis.set_major_formatter(FuncFormatter(thousands))

# (b) total gas by operation
ax = axes[1]
bottom = None
for col in gas_pivot.columns:
    vals = gas_pivot[col].values
    if bottom is None:
        ax.bar(clients, vals, width=6, label=col)
        bottom = vals.copy()
    else:
        ax.bar(clients, vals, width=6, bottom=bottom, label=col)
        bottom += vals
ax.set_xlabel("clients")
ax.set_ylabel("gas used")
ax.set_title("(b) gas by operation")
ax.grid(True, axis="y", linewidth=0.3, alpha=0.5)
ax.legend(fontsize=5.5, frameon=False, loc="upper left")
ax.yaxis.set_major_formatter(FuncFormatter(millions))

# (c) normalized gas
ax = axes[2]
ax.plot(clients, summary["gas_per_client_round"], marker="o", linewidth=1.4)
ax.set_xlabel("clients")
ax.set_ylabel("gas / client-round")
ax.set_title("(c) normalized gas")
ax.grid(True, linewidth=0.3, alpha=0.5)

fig.savefig(out_dir / "fig_control_plane_scaling.pdf", bbox_inches="tight")
fig.savefig(out_dir / "fig_control_plane_scaling.png", dpi=300, bbox_inches="tight")
plt.close(fig)

# -----------------------------
# Figure 2: Off-chain storage scaling
# -----------------------------

fig, axes = plt.subplots(1, 3, figsize=(7.15, 2.45), constrained_layout=True)

# (a) measured vs analytical artifact count
ax = axes[0]
ax.plot(clients, summary["measured_artifacts"], marker="o", linewidth=1.4, label="measured")
ax.plot(clients, summary["expected_artifacts"], linestyle="--", linewidth=1.4, label="analytical")
ax.set_xlabel("clients")
ax.set_ylabel("artifacts")
ax.set_title("(a) artifact model")
ax.grid(True, linewidth=0.3, alpha=0.5)
ax.legend(fontsize=6, frameon=False)
ax.yaxis.set_major_formatter(FuncFormatter(thousands))

# (b) total off-chain storage
ax = axes[1]
ax.plot(clients, summary["total_offchain_mib"], marker="o", linewidth=1.4)
ax.set_xlabel("clients")
ax.set_ylabel("MiB")
ax.set_title("(b) off-chain bytes")
ax.grid(True, linewidth=0.3, alpha=0.5)

# (c) off-chain tensor bytes vs identifier bytes
ax = axes[2]
ax.plot(clients, summary["total_offchain_mib"], marker="o", linewidth=1.4, label="artifact bytes")
ax.plot(clients, summary["identifier_mib"], marker="s", linestyle="--", linewidth=1.4, label="identifier bytes")
ax.set_xlabel("clients")
ax.set_ylabel("MiB, log scale")
ax.set_yscale("log")
ax.set_title("(c) bytes committed")
ax.grid(True, linewidth=0.3, alpha=0.5)
ax.legend(fontsize=6, frameon=False)

fig.savefig(out_dir / "fig_storage_scaling.pdf", bbox_inches="tight")
fig.savefig(out_dir / "fig_storage_scaling.png", dpi=300, bbox_inches="tight")
plt.close(fig)

print("Wrote:")
print(out_dir / "fig_control_plane_scaling.pdf")
print(out_dir / "fig_control_plane_scaling.png")
print(out_dir / "fig_storage_scaling.pdf")
print(out_dir / "fig_storage_scaling.png")

