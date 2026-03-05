from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.io import ensure_dir, load_json, parse_analyze_args, save_csv, save_json
from experiments.plots import plot_method_delta_bars, plot_method_winrate_bars, plot_qvalue_counts
from experiments.stats import compute_cell_stats, compute_method_aggregate


def analyze_runs(
    runs_csv: str | Path,
    outdir: str | Path,
    figdir: str | Path | None = None,
    phase: str = "eval",
    manifest_json: str | Path | None = None,
) -> dict[str, str]:
    runs_path = Path(runs_csv)
    out_path = ensure_dir(outdir)
    fig_path = ensure_dir(figdir if figdir is not None else out_path)

    manifest: dict[str, Any] | None = load_json(manifest_json) if manifest_json else None

    runs_df = pd.read_csv(runs_path)
    cell_stats = compute_cell_stats(runs_df, phase=phase)
    method_agg = compute_method_aggregate(cell_stats)

    cell_stats_path = out_path / "cell_stats.csv"
    method_agg_path = out_path / "method_aggregate.csv"
    analysis_manifest_path = out_path / "analysis_manifest.json"

    save_csv(cell_stats_path, cell_stats)
    save_csv(method_agg_path, method_agg)

    fig_delta = fig_path / "method_median_delta_bar.png"
    fig_win = fig_path / "method_win_rate_bar.png"
    fig_q = fig_path / "method_q_lt_005_count_bar.png"

    plot_method_delta_bars(method_agg, fig_delta)
    plot_method_winrate_bars(method_agg, fig_win)
    plot_qvalue_counts(cell_stats, fig_q)

    analysis_manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_csv": str(runs_path),
        "phase_filter": phase,
        "run_id": manifest.get("run_id") if manifest else None,
        "manifest_json": str(manifest_json) if manifest_json else None,
        "files": {
            "cell_stats_csv": str(cell_stats_path),
            "method_aggregate_csv": str(method_agg_path),
            "figure_method_delta": str(fig_delta),
            "figure_method_win_rate": str(fig_win),
            "figure_method_q_count": str(fig_q),
        },
        "summary": {
            "n_cell_rows": int(len(cell_stats)),
            "n_methods": int(method_agg["method"].nunique()) if not method_agg.empty else 0,
            "n_significant_q_lt_005": int((cell_stats["bh_fdr_q_value"] < 0.05).sum()) if not cell_stats.empty else 0,
        },
    }
    save_json(analysis_manifest_path, analysis_manifest)

    return {
        "cell_stats_csv": str(cell_stats_path),
        "method_aggregate_csv": str(method_agg_path),
        "analysis_manifest_json": str(analysis_manifest_path),
        "figure_method_delta": str(fig_delta),
        "figure_method_win_rate": str(fig_win),
        "figure_method_q_count": str(fig_q),
    }


def main() -> None:
    args = parse_analyze_args()
    outputs = analyze_runs(args.runs, args.outdir, args.figdir, args.phase, args.manifest_json)
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
