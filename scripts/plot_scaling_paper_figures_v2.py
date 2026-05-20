from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

summary_path = Path("auditfl_scaling_full_mnist_summary_N1_to_N200.csv")
gas_path = Path("auditfl_scaling_full_mnist_gas_by_operation_N1_to_N200.csv")

out_dir = Path("paper_figures")
out_dir.mkdir(exist_ok=True)

summary = pd.read_csv(summary_path).sort_values("clients")
gas = pd.read_csv(gas_path).sort_values(["clients", "event"])

clients = summary["clients"].to_numpy()

# Color-blind friendly palette.
COL = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "sky": "#56B4E9",
    "yellow": "#F0E442",
    "gray": "#666666",
    "lightgray": "#EEEEEE",
}

plt.rcParams.update({
    "font.size": 7,
    "axes.titlesize": 8,
    "axes.labelsize": 7,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
    "figure.titlesize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

def fmt_millions(x, pos):
    return f"{x/1e6:.0f}M"

def fmt_thousands(x, pos):
    return f"{x/1e3:.0f}k"

def fmt_mib(x, pos):
    return f"{x:.0f}"

def annotate_last(ax, x, y, text, color):
    ax.scatter([x], [y], s=18, color=color, zorder=5)
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(5, 2),
        textcoords="offset points",
        fontsize=6,
        color=color,
        ha="left",
        va="bottom",
    )

# ------------------------------------------------------------
# Prepare gas operation groups
# ------------------------------------------------------------
dominant = {"publishUpdate", "reserveTicket", "finalizeRound"}
gas2 = gas.copy()
gas2["event_group"] = gas2["event"].where(gas2["event"].isin(dominant), "other")

gas_pivot = (
    gas2.groupby(["clients", "event_group"])["sum"]
    .sum()
    .unstack(fill_value=0)
    .reindex(summary["clients"])
)

ordered_cols = [c for c in ["reserveTicket", "publishUpdate", "finalizeRound", "other"] if c in gas_pivot.columns]
gas_pivot = gas_pivot[ordered_cols]

gas_colors = {
    "reserveTicket": COL["blue"],
    "publishUpdate": COL["orange"],
    "finalizeRound": COL["green"],
    "other": COL["gray"],
}

# ------------------------------------------------------------
# Figure 1: Control-plane scaling
# ------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(7.15, 4.35), constrained_layout=True)

# (a) transaction model
ax = axes[0, 0]
ax.plot(
    clients,
    summary["expected_total_txs"],
    linestyle="--",
    linewidth=1.7,
    color=COL["gray"],
    label="analytical",
)
ax.plot(
    clients,
    summary["measured_txs"],
    marker="o",
    markersize=3.4,
    linewidth=1.3,
    color=COL["blue"],
    label="measured",
)
ax.set_title("(a) Transactions follow the model")
ax.set_xlabel("clients")
ax.set_ylabel("transactions")
ax.grid(True, linewidth=0.35, alpha=0.45)
ax.yaxis.set_major_formatter(FuncFormatter(fmt_thousands))
ax.legend(frameon=False, loc="upper left")
ax.text(
    0.97,
    0.06,
    r"$1+R(2N+2)+N+1$",
    transform=ax.transAxes,
    fontsize=6.5,
    ha="right",
    va="bottom",
    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=COL["lightgray"]),
)
annotate_last(
    ax,
    clients[-1],
    summary["measured_txs"].iloc[-1],
    f"{int(summary['measured_txs'].iloc[-1])} tx",
    COL["blue"],
)

# (b) total gas used
ax = axes[0, 1]
ax.plot(
    clients,
    summary["total_gas_used"],
    marker="o",
    markersize=3.4,
    linewidth=1.5,
    color=COL["red"],
)
ax.fill_between(clients, summary["total_gas_used"], color=COL["red"], alpha=0.08)
ax.set_title("(b) Total smart-contract gas")
ax.set_xlabel("clients")
ax.set_ylabel("gas used")
ax.grid(True, linewidth=0.35, alpha=0.45)
ax.yaxis.set_major_formatter(FuncFormatter(fmt_millions))
annotate_last(
    ax,
    clients[-1],
    summary["total_gas_used"].iloc[-1],
    f"{summary['total_gas_used'].iloc[-1]/1e6:.0f}M",
    COL["red"],
)

# (c) stacked gas by operation
ax = axes[1, 0]
bottom = np.zeros(len(gas_pivot))
for col in gas_pivot.columns:
    vals = gas_pivot[col].to_numpy()
    ax.fill_between(
        clients,
        bottom,
        bottom + vals,
        alpha=0.85,
        color=gas_colors.get(col, COL["gray"]),
        label=col,
        linewidth=0,
    )
    bottom += vals
ax.set_title("(c) Gas dominated by per-client calls")
ax.set_xlabel("clients")
ax.set_ylabel("gas used")
ax.grid(True, linewidth=0.35, alpha=0.45)
ax.yaxis.set_major_formatter(FuncFormatter(fmt_millions))
ax.legend(frameon=False, loc="upper left", ncol=1)

# Add share note at largest N
last_n = clients[-1]
last_total = summary["total_gas_used"].iloc[-1]
last_gas = gas_pivot.loc[last_n]
per_client_share = 100 * (
    last_gas.get("publishUpdate", 0) + last_gas.get("reserveTicket", 0)
) / last_total
ax.text(
    0.97,
    0.08,
    f"reserve+publish ≈ {per_client_share:.1f}% at N={last_n}",
    transform=ax.transAxes,
    fontsize=6.2,
    ha="right",
    va="bottom",
    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=COL["lightgray"]),
)

# (d) normalized gas
ax = axes[1, 1]
ax.plot(
    clients,
    summary["gas_per_client_round"],
    marker="o",
    markersize=3.4,
    linewidth=1.5,
    color=COL["purple"],
)
ax.set_title("(d) Gas per client-round stabilizes")
ax.set_xlabel("clients")
ax.set_ylabel("gas / client-round")
ax.grid(True, linewidth=0.35, alpha=0.45)
annotate_last(
    ax,
    clients[-1],
    summary["gas_per_client_round"].iloc[-1],
    f"{summary['gas_per_client_round'].iloc[-1]:.0f}",
    COL["purple"],
)

fig.savefig(out_dir / "fig_control_plane_scaling_v2.pdf", bbox_inches="tight")
fig.savefig(out_dir / "fig_control_plane_scaling_v2.png", dpi=350, bbox_inches="tight")
plt.close(fig)

# ------------------------------------------------------------
# Figure 2: Storage scaling
# ------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(7.15, 4.35), constrained_layout=True)

# (a) artifact model
ax = axes[0, 0]
ax.plot(
    clients,
    summary["expected_artifacts"],
    linestyle="--",
    linewidth=1.7,
    color=COL["gray"],
    label="analytical",
)
ax.plot(
    clients,
    summary["measured_artifacts"],
    marker="o",
    markersize=3.4,
    linewidth=1.3,
    color=COL["green"],
    label="measured",
)
ax.set_title("(a) Artifact count follows the model")
ax.set_xlabel("clients")
ax.set_ylabel("artifacts")
ax.grid(True, linewidth=0.35, alpha=0.45)
ax.yaxis.set_major_formatter(FuncFormatter(fmt_thousands))
ax.legend(frameon=False, loc="upper left")
ax.text(
    0.97,
    0.06,
    r"$1+R(N+1)$",
    transform=ax.transAxes,
    fontsize=6.5,
    ha="right",
    va="bottom",
    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=COL["lightgray"]),
)
annotate_last(
    ax,
    clients[-1],
    summary["measured_artifacts"].iloc[-1],
    f"{int(summary['measured_artifacts'].iloc[-1])}",
    COL["green"],
)

# (b) total off-chain MiB
ax = axes[0, 1]
ax.plot(
    clients,
    summary["total_offchain_mib"],
    marker="o",
    markersize=3.4,
    linewidth=1.5,
    color=COL["blue"],
)
ax.fill_between(clients, summary["total_offchain_mib"], color=COL["blue"], alpha=0.08)
ax.set_title("(b) Off-chain tensor storage")
ax.set_xlabel("clients")
ax.set_ylabel("MiB")
ax.grid(True, linewidth=0.35, alpha=0.45)
annotate_last(
    ax,
    clients[-1],
    summary["total_offchain_mib"].iloc[-1],
    f"{summary['total_offchain_mib'].iloc[-1]:.1f} MiB",
    COL["blue"],
)

# (c) off-chain artifact bytes vs identifier bytes
ax = axes[1, 0]
ax.plot(
    clients,
    summary["total_offchain_mib"],
    marker="o",
    markersize=3.4,
    linewidth=1.5,
    color=COL["orange"],
    label="artifact bytes",
)
ax.plot(
    clients,
    summary["identifier_mib"],
    marker="s",
    markersize=3.0,
    linestyle="--",
    linewidth=1.4,
    color=COL["purple"],
    label="identifier bytes",
)
ax.set_yscale("log")
ax.set_title("(c) Tensors dominate identifiers")
ax.set_xlabel("clients")
ax.set_ylabel("MiB, log scale")
ax.grid(True, linewidth=0.35, alpha=0.45)
ax.legend(frameon=False, loc="upper left")

ratio_last = summary["offchain_to_identifier_ratio"].iloc[-1]
ax.text(
    0.97,
    0.08,
    f"artifact bytes ≈ {ratio_last:.0f}× identifiers at N={last_n}",
    transform=ax.transAxes,
    fontsize=6.2,
    ha="right",
    va="bottom",
    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=COL["lightgray"]),
)

# (d) normalized off-chain storage
ax = axes[1, 1]
ax.plot(
    clients,
    summary["offchain_bytes_per_client_round"] / 1024,
    marker="o",
    markersize=3.4,
    linewidth=1.5,
    color=COL["red"],
)
ax.set_title("(d) Storage per client-round")
ax.set_xlabel("clients")
ax.set_ylabel("KiB / client-round")
ax.grid(True, linewidth=0.35, alpha=0.45)
annotate_last(
    ax,
    clients[-1],
    (summary["offchain_bytes_per_client_round"] / 1024).iloc[-1],
    f"{(summary['offchain_bytes_per_client_round'] / 1024).iloc[-1]:.1f}",
    COL["red"],
)

fig.savefig(out_dir / "fig_storage_scaling_v2.pdf", bbox_inches="tight")
fig.savefig(out_dir / "fig_storage_scaling_v2.png", dpi=350, bbox_inches="tight")
plt.close(fig)

print("Wrote:")
print(out_dir / "fig_control_plane_scaling_v2.pdf")
print(out_dir / "fig_control_plane_scaling_v2.png")
print(out_dir / "fig_storage_scaling_v2.pdf")
print(out_dir / "fig_storage_scaling_v2.png")

