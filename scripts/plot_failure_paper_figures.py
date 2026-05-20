from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

AGG = Path("auditfl_failure_sweep_mnist_full_N50_aggregate.csv")
OUT = Path("paper_figures")
OUT.mkdir(exist_ok=True)

df = pd.read_csv(AGG).sort_values(["failure_type", "failure_rate"])

labels = {
    "dropout": "Dropout",
    "invalid": "Invalid updates",
    "storage": "Storage failure",
}

colors = {
    "dropout": "#0072B2",
    "invalid": "#D55E00",
    "storage": "#009E73",
}

plt.rcParams.update({
    "font.size": 7,
    "axes.titlesize": 8,
    "axes.labelsize": 7,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

fig, axes = plt.subplots(1, 2, figsize=(7.15, 2.45), constrained_layout=True)

# Panel A: included updates
ax = axes[0]
for failure_type, g in df.groupby("failure_type"):
    g = g.sort_values("failure_rate")
    x = g["failure_rate"] * 100
    y = g["mean_included_mean"]
    yerr = g["mean_included_std"].fillna(0)
    ax.errorbar(
        x, y, yerr=yerr,
        marker="o", markersize=3.2,
        linewidth=1.4, capsize=2.2,
        color=colors[failure_type],
        label=labels[failure_type],
    )

ax.set_title("(a) Included updates")
ax.set_xlabel("Injected failure rate (%)")
ax.set_ylabel("Mean included updates / round")
ax.grid(True, linewidth=0.3, alpha=0.45)
ax.set_ylim(0, 52)
ax.legend(frameon=False, loc="upper right")

# Panel B: accuracy gap
ax = axes[1]
for failure_type, g in df.groupby("failure_type"):
    g = g.sort_values("failure_rate")
    x = g["failure_rate"] * 100
    y = g["accuracy_gap_vs_plain_mean"] * 100
    yerr = g["accuracy_gap_vs_plain_std"].fillna(0) * 100
    ax.errorbar(
        x, y, yerr=yerr,
        marker="o", markersize=3.2,
        linewidth=1.4, capsize=2.2,
        color=colors[failure_type],
        label=labels[failure_type],
    )

ax.axhline(0, linestyle="--", linewidth=0.8, color="#666666")
ax.set_title("(b) Learning impact")
ax.set_xlabel("Injected failure rate (%)")
ax.set_ylabel("Accuracy gap vs Plain FL (pp)")
ax.grid(True, linewidth=0.3, alpha=0.45)
ax.legend(frameon=False, loc="lower left")

fig.savefig(OUT / "fig_failure_stress_compact.pdf", bbox_inches="tight")
fig.savefig(OUT / "fig_failure_stress_compact.png", dpi=350, bbox_inches="tight")

print("Wrote:")
print(OUT / "fig_failure_stress_compact.pdf")
print(OUT / "fig_failure_stress_compact.png")
