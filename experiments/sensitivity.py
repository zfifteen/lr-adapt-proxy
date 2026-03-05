from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.io import (
    ensure_dir,
    load_yaml_config,
    make_run_id,
    parse_sensitivity_args,
    save_csv,
    save_json,
    stable_config_hash,
)
from experiments.methods import run_jobs
from experiments.stats import compute_cell_stats, compute_method_aggregate
from experiments.tuning import build_cells


def _variant_signature(params: dict[str, Any]) -> tuple[float, float, float, float, float, float, float]:
    return (
        float(params["ema_alpha"]),
        float(params["snr_down_threshold"]),
        float(params["snr_up_threshold"]),
        float(params["sigma_down_factor"]),
        float(params["sigma_up_factor"]),
        float(params["sigma_min_ratio"]),
        float(params["sigma_max_ratio"]),
    )


def _build_variants(config: dict[str, Any]) -> list[dict[str, Any]]:
    base = dict(config["lr_adapt_proxy"])
    variants: list[dict[str, Any]] = []
    seen: set[tuple[float, float, float, float, float, float]] = set()

    def add_variant(variant_id: str, group: str, params: dict[str, Any]) -> None:
        sig = _variant_signature(params)
        if sig in seen:
            return
        seen.add(sig)
        variants.append(
            {
                "variant_id": variant_id,
                "variant_group": group,
                "lr_params": dict(params),
            }
        )

    add_variant("baseline", "baseline", dict(base))

    for value in config["sweep"]["ema_alpha"]:
        params = dict(base)
        params["ema_alpha"] = float(value)
        add_variant(f"ema_alpha_{value}", "ema_alpha", params)

    for down, up in config["sweep"]["snr_threshold_pairs"]:
        params = dict(base)
        params["snr_down_threshold"] = float(down)
        params["snr_up_threshold"] = float(up)
        add_variant(f"thresholds_{down}_{up}", "snr_thresholds", params)

    for down, up in config["sweep"]["sigma_factor_pairs"]:
        params = dict(base)
        params["sigma_down_factor"] = float(down)
        params["sigma_up_factor"] = float(up)
        add_variant(f"sigma_factors_{down}_{up}", "sigma_factors", params)

    for min_ratio, max_ratio in config["sweep"]["sigma_clamp_pairs"]:
        params = dict(base)
        params["sigma_min_ratio"] = float(min_ratio)
        params["sigma_max_ratio"] = float(max_ratio)
        add_variant(f"sigma_clamp_{min_ratio}_{max_ratio}", "sigma_clamp", params)

    return variants


def _make_jobs_for_variant(config: dict[str, Any], variant: dict[str, Any]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    cells = build_cells(config["matrix"])
    eval_seeds = [int(s) for s in config["seeds"]["eval"]]
    methods = list(config["methods"])
    for method_name in methods:
        for cell in cells:
            for seed in eval_seeds:
                jobs.append(
                    {
                        "phase": "eval",
                        "method_name": method_name,
                        "function": cell["function"],
                        "dimension": int(cell["dimension"]),
                        "noise_sigma": float(cell["noise_sigma"]),
                        "seed": int(seed),
                        "eval_budget": int(config["budget"]["evals_per_run"]),
                        "initial_sigma": float(config["cma"]["initial_sigma"]),
                        "base_popsize": int(config["cma"]["base_popsize"]),
                        "cma_verbose": int(config["cma"].get("verbose", -9)),
                        "phasewall_strength": 0.0,
                        "lr_proxy_params": dict(variant["lr_params"]),
                    }
                )
    return jobs


def _build_findings_sensitivity_markdown(summary_df: pd.DataFrame, run_id: str, outdir: Path) -> str:
    lines = [
        "# LR-Proxy Sensitivity Findings",
        "",
        f"- Run ID: `{run_id}`",
        f"- Output root: `{outdir}`",
        "",
    ]
    if summary_df.empty:
        lines.append("No summary rows were produced.")
        return "\n".join(lines) + "\n"

    ranked = summary_df.sort_values("median_of_cell_median_delta", ascending=True).reset_index(drop=True)
    best = ranked.iloc[0]
    worst = ranked.iloc[-1]
    baseline_rows = ranked[ranked["variant_id"] == "baseline"]
    baseline = baseline_rows.iloc[0] if not baseline_rows.empty else None

    lines.extend(
        [
            "## Headline",
            f"- Best variant: `{best['variant_id']}` with median_of_cell_median_delta=`{best['median_of_cell_median_delta']}` "
            f"and cells_q_lt_0_05=`{best['cells_q_lt_0_05']}`.",
            f"- Worst variant: `{worst['variant_id']}` with median_of_cell_median_delta=`{worst['median_of_cell_median_delta']}` "
            f"and cells_q_lt_0_05=`{worst['cells_q_lt_0_05']}`.",
        ]
    )
    if baseline is not None:
        lines.append(
            f"- Baseline variant: median_of_cell_median_delta=`{baseline['median_of_cell_median_delta']}`, "
            f"cells_q_lt_0_05=`{baseline['cells_q_lt_0_05']}`."
        )

    lines.extend(
        [
            "",
            "## Top Variants",
        ]
    )
    for _, row in ranked.head(5).iterrows():
        lines.append(
            f"- `{row['variant_id']}` ({row['variant_group']}): median_delta=`{row['median_of_cell_median_delta']}`, "
            f"win_rate=`{row['mean_win_rate']}`, q<0.05 cells=`{row['cells_q_lt_0_05']}`"
        )

    lines.extend(
        [
            "",
            "## Bottom Variants",
        ]
    )
    for _, row in ranked.tail(5).iterrows():
        lines.append(
            f"- `{row['variant_id']}` ({row['variant_group']}): median_delta=`{row['median_of_cell_median_delta']}`, "
            f"win_rate=`{row['mean_win_rate']}`, q<0.05 cells=`{row['cells_q_lt_0_05']}`"
        )

    return "\n".join(lines) + "\n"


def run_sensitivity_sweep(
    config_path: str | Path,
    outdir: str | Path,
    workers_override: int | None = None,
    explicit_run_id: str | None = None,
) -> dict[str, str]:
    config = load_yaml_config(config_path)
    methods = set(config["methods"])
    if methods != {"vanilla_cma", "lr_adapt_proxy"}:
        raise ValueError("Sensitivity config methods must be exactly ['vanilla_cma', 'lr_adapt_proxy']")

    workers = int(workers_override or config.get("runtime", {}).get("parallel_workers", 1))
    out_path = ensure_dir(outdir)
    created_at = datetime.now(timezone.utc)
    config_hash = stable_config_hash(config)
    run_id = explicit_run_id or make_run_id(config_hash, created_at)

    variants = _build_variants(config)
    all_rows: list[dict[str, Any]] = []
    for variant in variants:
        jobs = _make_jobs_for_variant(config, variant)
        results = run_jobs(jobs, workers)
        for row in results:
            row["variant_id"] = variant["variant_id"]
            row["variant_group"] = variant["variant_group"]
            for key, value in variant["lr_params"].items():
                row[f"lr_{key}"] = value
            all_rows.append(row)

    runs_df = pd.DataFrame(all_rows)
    runs_path = out_path / "sensitivity_runs_long.csv"
    save_csv(runs_path, runs_df)

    cell_frames = []
    summary_rows = []
    for variant in variants:
        v_id = variant["variant_id"]
        sub = runs_df[runs_df["variant_id"] == v_id]
        cell = compute_cell_stats(sub, phase="eval")
        cell["variant_id"] = v_id
        cell["variant_group"] = variant["variant_group"]
        for key, value in variant["lr_params"].items():
            cell[f"lr_{key}"] = value
        cell_frames.append(cell)

        agg = compute_method_aggregate(cell)
        if agg.empty:
            continue
        row = agg.iloc[0].to_dict()
        row["variant_id"] = v_id
        row["variant_group"] = variant["variant_group"]
        for key, value in variant["lr_params"].items():
            row[f"lr_{key}"] = value
        summary_rows.append(row)

    cell_df = pd.concat(cell_frames, ignore_index=True) if cell_frames else pd.DataFrame()
    summary_df = pd.DataFrame(summary_rows)

    cell_path = out_path / "sensitivity_cell_stats.csv"
    summary_path = out_path / "sensitivity_summary.csv"
    save_csv(cell_path, cell_df)
    save_csv(summary_path, summary_df)

    findings_path = out_path / "findings_sensitivity.md"
    findings_path.write_text(_build_findings_sensitivity_markdown(summary_df, run_id, out_path), encoding="utf-8")

    manifest_path = out_path / "sensitivity_manifest.json"
    save_json(
        manifest_path,
        {
            "run_id": run_id,
            "created_at_utc": created_at.isoformat(),
            "config_path": str(Path(config_path)),
            "config_hash": config_hash,
            "workers": workers,
            "n_variants": int(len(variants)),
            "files": {
                "sensitivity_runs_long_csv": str(runs_path),
                "sensitivity_cell_stats_csv": str(cell_path),
                "sensitivity_summary_csv": str(summary_path),
                "findings_sensitivity_md": str(findings_path),
            },
        },
    )

    return {
        "run_id": run_id,
        "sensitivity_runs_long_csv": str(runs_path),
        "sensitivity_cell_stats_csv": str(cell_path),
        "sensitivity_summary_csv": str(summary_path),
        "findings_sensitivity_md": str(findings_path),
        "sensitivity_manifest_json": str(manifest_path),
    }


def main() -> None:
    args = parse_sensitivity_args()
    outputs = run_sensitivity_sweep(args.config, args.outdir, args.workers, args.run_id)
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
