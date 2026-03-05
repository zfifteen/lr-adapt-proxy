from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


plt.switch_backend("Agg")


def plot_method_delta_bars(method_agg: pd.DataFrame, out_path: str | Path) -> None:
    if method_agg.empty:
        return
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(
        method_agg["method"],
        method_agg["median_of_cell_median_delta"],
        color=["#2e86de" if v >= 0 else "#27ae60" for v in method_agg["median_of_cell_median_delta"]],
    )
    ax.axhline(0.0, color="black", linewidth=1)
    ax.set_title("Median Cell Delta vs Vanilla (negative is better)")
    ax.set_ylabel("Median delta")
    ax.set_xlabel("Method")
    ax.tick_params(axis="x", rotation=20)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height, f"{height:.3g}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_method_winrate_bars(method_agg: pd.DataFrame, out_path: str | Path) -> None:
    if method_agg.empty:
        return
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(method_agg["method"], method_agg["mean_win_rate"], color="#16a085")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Mean Paired Win-Rate vs Vanilla")
    ax.set_ylabel("Win-rate")
    ax.set_xlabel("Method")
    ax.tick_params(axis="x", rotation=20)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height, f"{height:.2f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_qvalue_counts(cell_stats: pd.DataFrame, out_path: str | Path) -> None:
    if cell_stats.empty:
        return
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    summary = (
        cell_stats.groupby("method", as_index=False)["bh_fdr_q_value"]
        .apply(lambda s: (s < 0.05).sum())
        .rename(columns={"bh_fdr_q_value": "cells_q_lt_0_05"})
    )

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(summary["method"], summary["cells_q_lt_0_05"], color="#8e44ad")
    ax.set_title("Cells with BH-FDR q < 0.05")
    ax.set_ylabel("Count")
    ax.set_xlabel("Method")
    ax.tick_params(axis="x", rotation=20)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height, f"{int(height)}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
