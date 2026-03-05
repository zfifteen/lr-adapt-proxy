from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from statsmodels.stats.multitest import multipletests


def _wilcoxon_two_sided(deltas: np.ndarray) -> float:
    if deltas.size == 0:
        return np.nan
    if np.allclose(deltas, 0.0):
        return 1.0
    try:
        return float(wilcoxon(deltas, alternative="two-sided", zero_method="pratt").pvalue)
    except ValueError:
        return 1.0


def compute_cell_stats(runs_df: pd.DataFrame, phase: str = "eval") -> pd.DataFrame:
    out_columns = [
        "function",
        "dimension",
        "noise_sigma",
        "method",
        "n_pairs",
        "vanilla_median",
        "method_median",
        "median_delta_vs_vanilla",
        "win_rate_vs_vanilla",
        "loss_rate_vs_vanilla",
        "wilcoxon_p_two_sided",
        "bh_fdr_q_value",
        "ratio_median_vs_vanilla_non_primary",
    ]

    eval_df = runs_df[(runs_df["phase"] == phase) & (runs_df["status"] == "ok")].copy()
    if eval_df.empty:
        return pd.DataFrame(columns=out_columns)

    cells = (
        eval_df[["function", "dimension", "noise_sigma"]]
        .drop_duplicates()
        .sort_values(["function", "dimension", "noise_sigma"])
    )
    methods = sorted(eval_df["method"].unique())

    rows = []
    for _, cell in cells.iterrows():
        cell_df = eval_df[
            (eval_df["function"] == cell["function"])
            & (eval_df["dimension"] == cell["dimension"])
            & (eval_df["noise_sigma"] == cell["noise_sigma"])
        ]
        pivot = cell_df.pivot_table(index="seed", columns="method", values="final_best", aggfunc="first")
        if "vanilla_cma" not in pivot.columns:
            continue

        for method in methods:
            if method == "vanilla_cma" or method not in pivot.columns:
                continue

            paired = pivot[["vanilla_cma", method]].dropna()
            n_pairs = int(len(paired))
            if n_pairs == 0:
                continue

            deltas = (paired[method] - paired["vanilla_cma"]).to_numpy(dtype=float)
            vanilla_median = float(np.median(paired["vanilla_cma"].to_numpy(dtype=float)))
            method_median = float(np.median(paired[method].to_numpy(dtype=float)))

            rows.append(
                {
                    "function": cell["function"],
                    "dimension": int(cell["dimension"]),
                    "noise_sigma": float(cell["noise_sigma"]),
                    "method": method,
                    "n_pairs": n_pairs,
                    "vanilla_median": vanilla_median,
                    "method_median": method_median,
                    "median_delta_vs_vanilla": float(np.median(deltas)),
                    "win_rate_vs_vanilla": float(np.mean(deltas < 0.0)),
                    "loss_rate_vs_vanilla": float(np.mean(deltas > 0.0)),
                    "wilcoxon_p_two_sided": _wilcoxon_two_sided(deltas),
                    "ratio_median_vs_vanilla_non_primary": (
                        method_median / vanilla_median if abs(vanilla_median) > 1e-16 else np.nan
                    ),
                }
            )

    cell_stats = pd.DataFrame(rows)
    if cell_stats.empty:
        return pd.DataFrame(columns=out_columns)

    pvals = cell_stats["wilcoxon_p_two_sided"].fillna(1.0).to_numpy(dtype=float)
    qvals = multipletests(pvals, method="fdr_bh")[1]
    cell_stats["bh_fdr_q_value"] = qvals

    return cell_stats.sort_values(["function", "dimension", "noise_sigma", "method"]).reset_index(drop=True)


def compute_method_aggregate(cell_stats: pd.DataFrame) -> pd.DataFrame:
    if cell_stats.empty:
        return pd.DataFrame(
            columns=[
                "method",
                "n_cells",
                "median_of_cell_median_delta",
                "mean_win_rate",
                "mean_loss_rate",
                "fraction_cells_median_delta_lt0",
                "cells_q_lt_0_05",
                "best_q_value",
            ]
        )

    grouped = cell_stats.groupby("method", as_index=False)
    rows = []
    for method, g in grouped:
        rows.append(
            {
                "method": method,
                "n_cells": int(len(g)),
                "median_of_cell_median_delta": float(np.median(g["median_delta_vs_vanilla"])),
                "mean_win_rate": float(np.mean(g["win_rate_vs_vanilla"])),
                "mean_loss_rate": float(np.mean(g["loss_rate_vs_vanilla"])),
                "fraction_cells_median_delta_lt0": float(np.mean(g["median_delta_vs_vanilla"] < 0.0)),
                "cells_q_lt_0_05": int(np.sum(g["bh_fdr_q_value"] < 0.05)),
                "best_q_value": float(np.min(g["bh_fdr_q_value"])),
            }
        )

    return pd.DataFrame(rows).sort_values("method").reset_index(drop=True)


def compute_pairwise_cell_stats(
    runs_df: pd.DataFrame,
    method_a: str,
    method_b: str,
    phase: str = "eval",
) -> pd.DataFrame:
    eval_df = runs_df[(runs_df["phase"] == phase) & (runs_df["status"] == "ok")].copy()
    eval_df = eval_df[eval_df["method"].isin([method_a, method_b])]
    if eval_df.empty:
        return pd.DataFrame(
            columns=[
                "function",
                "dimension",
                "noise_sigma",
                "method_a",
                "method_b",
                "n_pairs",
                "median_delta_b_minus_a",
                "win_rate_b_vs_a",
                "loss_rate_b_vs_a",
                "wilcoxon_p_two_sided",
                "bh_fdr_q_value",
            ]
        )

    cells = (
        eval_df[["function", "dimension", "noise_sigma"]]
        .drop_duplicates()
        .sort_values(["function", "dimension", "noise_sigma"])
    )
    rows: list[dict[str, float | int | str]] = []
    for _, cell in cells.iterrows():
        cell_df = eval_df[
            (eval_df["function"] == cell["function"])
            & (eval_df["dimension"] == cell["dimension"])
            & (eval_df["noise_sigma"] == cell["noise_sigma"])
        ]
        pivot = cell_df.pivot_table(index="seed", columns="method", values="final_best", aggfunc="first")
        if method_a not in pivot.columns or method_b not in pivot.columns:
            continue

        paired = pivot[[method_a, method_b]].dropna()
        n_pairs = int(len(paired))
        if n_pairs == 0:
            continue

        deltas = (paired[method_b] - paired[method_a]).to_numpy(dtype=float)
        rows.append(
            {
                "function": str(cell["function"]),
                "dimension": int(cell["dimension"]),
                "noise_sigma": float(cell["noise_sigma"]),
                "method_a": method_a,
                "method_b": method_b,
                "n_pairs": n_pairs,
                "median_delta_b_minus_a": float(np.median(deltas)),
                "win_rate_b_vs_a": float(np.mean(deltas < 0.0)),
                "loss_rate_b_vs_a": float(np.mean(deltas > 0.0)),
                "wilcoxon_p_two_sided": _wilcoxon_two_sided(deltas),
            }
        )

    pairwise = pd.DataFrame(rows)
    if pairwise.empty:
        pairwise["bh_fdr_q_value"] = []
        return pairwise

    pvals = pairwise["wilcoxon_p_two_sided"].fillna(1.0).to_numpy(dtype=float)
    qvals = multipletests(pvals, method="fdr_bh")[1]
    pairwise["bh_fdr_q_value"] = qvals

    return pairwise.sort_values(["function", "dimension", "noise_sigma"]).reset_index(drop=True)
