#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


def _save_table(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=True)


def plot_accuracy(root: Path, plots: Path) -> None:
    plain_files = list(root.glob("plain_fl_rounds.csv"))
    bcfl_files = list(root.glob("bcfl_*_rounds.csv"))
    if not (plain_files and bcfl_files):
        return
    plain = pd.read_csv(plain_files[0])
    bcfl = pd.read_csv(bcfl_files[0])

    plt.figure(figsize=(5.2, 3.2))
    plt.plot(plain["round"], plain["test_acc"], marker="o", label="Plain FL")
    plt.plot(bcfl["round"], bcfl["test_acc"], marker="s", label="Contract-backed BC-FL")
    plt.xlabel("Round")
    plt.ylabel("Test accuracy")
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(plots / "fig_accuracy_plain_vs_bcfl.pdf")
    plt.savefig(plots / "fig_accuracy_plain_vs_bcfl.png", dpi=300)
    plt.close()

    plt.figure(figsize=(5.2, 3.2))
    plt.plot(bcfl["round"], bcfl["included"], marker="o", label="Included updates")
    if "refunds" in bcfl:
        plt.plot(bcfl["round"], bcfl["refunds"], marker="s", label="Refunded tickets")
    if "unretrievable" in bcfl:
        plt.plot(bcfl["round"], bcfl["unretrievable"], marker="^", label="Unretrievable")
    plt.xlabel("Round")
    plt.ylabel("Count")
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(plots / "fig_round_inclusion.pdf")
    plt.savefig(plots / "fig_round_inclusion.png", dpi=300)
    plt.close()


def plot_gas(root: Path, plots: Path) -> None:
    receipt_files = list(root.glob("contract_*_receipts.csv"))
    if not receipt_files:
        return
    df = pd.read_csv(receipt_files[0])
    if "gas_used" not in df.columns:
        return
    op_col = "event" if "event" in df.columns else "op" if "op" in df.columns else None
    if op_col is None:
        return
    gas = df.groupby(op_col)["gas_used"].agg(["count", "mean", "sum"]).sort_values("sum", ascending=False)
    _save_table(gas.round(2), plots / "table_gas_by_operation.csv")

    gas_no_deploy = gas.drop(index=["Deploy"], errors="ignore")
    plt.figure(figsize=(5.6, 3.4))
    gas_no_deploy["sum"].sort_values().plot(kind="barh")
    plt.xlabel("Total gas used")
    plt.ylabel("Contract operation")
    plt.tight_layout()
    plt.savefig(plots / "fig_gas_by_operation.pdf")
    plt.savefig(plots / "fig_gas_by_operation.png", dpi=300)
    plt.close()


def plot_sweep(root: Path, plots: Path) -> None:
    sweep = root / "sweep_summary.csv"
    if not sweep.exists():
        return
    df = pd.read_csv(sweep)
    if not {"scenario", "final_test_acc"}.issubset(df.columns):
        return
    plt.figure(figsize=(6.2, 3.4))
    plt.bar(df["scenario"], df["final_test_acc"])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Final test accuracy")
    plt.tight_layout()
    plt.savefig(plots / "fig_sweep_final_accuracy.pdf")
    plt.savefig(plots / "fig_sweep_final_accuracy.png", dpi=300)
    plt.close()


def write_summary(root: Path, plots: Path) -> None:
    summary_files = list(root.glob("contract_mvp_summary.csv"))
    if not summary_files:
        return
    s = pd.read_csv(summary_files[0]).iloc[0].to_dict()
    lines = ["# Plot summary", ""]
    for key in ["backend", "dataset", "n_total", "clients", "rounds", "plain_final_test_acc", "final_test_acc", "accuracy_gap_vs_plain", "tx_count", "total_gas_used_model_or_estimate", "store_puts", "store_gets", "store_get_failures"]:
        if key in s:
            lines.append(f"- {key}: {s[key]}")
    (plots / "plot_summary.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate paper-ready plots and tables for BC-FL contract MVP outputs")
    ap.add_argument("results_dir", help="Result directory, e.g., results_anvil_mnist_20k_12r")
    args = ap.parse_args()
    root = Path(args.results_dir)
    plots = root / "plots"
    plots.mkdir(exist_ok=True)

    plot_accuracy(root, plots)
    plot_gas(root, plots)
    plot_sweep(root, plots)
    write_summary(root, plots)

    print(f"Wrote plots/tables to {plots}")


if __name__ == "__main__":
    main()
