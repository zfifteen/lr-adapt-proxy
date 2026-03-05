from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.io import ensure_dir, parse_breakdown_args, save_csv


def generate_lr_proxy_breakdown(
    cell_stats_csv: str | Path,
    outdir: str | Path,
    method: str = "lr_adapt_proxy",
) -> dict[str, str]:
    out_path = ensure_dir(outdir)
    cell_stats = pd.read_csv(cell_stats_csv)
    method_df = cell_stats[cell_stats["method"] == method].copy()
    if method_df.empty:
        raise ValueError(f"No rows found for method={method} in {cell_stats_csv}")

    method_df["is_q_significant"] = method_df["bh_fdr_q_value"] < 0.05
    method_df = method_df.sort_values(["function", "dimension", "noise_sigma"]).reset_index(drop=True)

    by_noise = (
        method_df.groupby("noise_sigma", as_index=False)
        .agg(
            n_cells=("method", "size"),
            median_of_cell_median_delta=("median_delta_vs_vanilla", "median"),
            mean_win_rate=("win_rate_vs_vanilla", "mean"),
            cells_q_lt_0_05=("is_q_significant", "sum"),
        )
        .sort_values("noise_sigma")
        .reset_index(drop=True)
    )
    by_noise["cells_q_lt_0_05"] = by_noise["cells_q_lt_0_05"].astype(int)

    by_dimension = (
        method_df.groupby("dimension", as_index=False)
        .agg(
            n_cells=("method", "size"),
            median_of_cell_median_delta=("median_delta_vs_vanilla", "median"),
            mean_win_rate=("win_rate_vs_vanilla", "mean"),
            cells_q_lt_0_05=("is_q_significant", "sum"),
        )
        .sort_values("dimension")
        .reset_index(drop=True)
    )
    by_dimension["cells_q_lt_0_05"] = by_dimension["cells_q_lt_0_05"].astype(int)

    non_sig = method_df[~method_df["is_q_significant"]].copy()
    non_sig = non_sig.sort_values(["function", "dimension", "noise_sigma"]).reset_index(drop=True)

    cell_path = out_path / "lr_proxy_cell_breakdown.csv"
    noise_path = out_path / "lr_proxy_by_noise.csv"
    dim_path = out_path / "lr_proxy_by_dimension.csv"
    non_sig_path = out_path / "lr_proxy_non_significant_cells.csv"

    save_csv(cell_path, method_df)
    save_csv(noise_path, by_noise)
    save_csv(dim_path, by_dimension)
    save_csv(non_sig_path, non_sig)

    return {
        "lr_proxy_cell_breakdown_csv": str(cell_path),
        "lr_proxy_by_noise_csv": str(noise_path),
        "lr_proxy_by_dimension_csv": str(dim_path),
        "lr_proxy_non_significant_cells_csv": str(non_sig_path),
    }


def main() -> None:
    args = parse_breakdown_args()
    outputs = generate_lr_proxy_breakdown(args.cell_stats, args.outdir, args.method)
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
