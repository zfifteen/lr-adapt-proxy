from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

from experiments.awf_utils import projected_awf, projected_n_floor
from experiments.io import ensure_dir, parse_awf_analysis_args, save_csv, save_json


TARGET_P1 = {
    ("sphere", 10),
    ("sphere", 20),
    ("rosenbrock", 10),
    ("rosenbrock", 20),
}


def _load_proxy_eval_rows(runs_df: pd.DataFrame) -> pd.DataFrame:
    mask = (
        (runs_df["phase"] == "eval")
        & (runs_df["status"] == "ok")
        & (runs_df["method"] == "lr_adapt_proxy")
    )
    return runs_df.loc[mask].copy()


def _variant_metadata(summary_df: pd.DataFrame, proxy_df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "variant_id",
        "variant_group",
        "lr_sigma_down_factor",
        "lr_sigma_min_ratio",
        "planned_generations",
        "n_floor_projected",
        "awf_projected",
    ]
    from_summary = [c for c in cols if c in summary_df.columns]
    meta = summary_df[from_summary].drop_duplicates().copy()
    if meta.empty and not proxy_df.empty:
        from_runs = [c for c in cols if c in proxy_df.columns]
        meta = proxy_df[from_runs].drop_duplicates().copy()
    if meta.empty:
        return meta

    if "planned_generations" not in meta.columns:
        if "planned_generations" in proxy_df.columns:
            planned = float(proxy_df["planned_generations"].dropna().median())
        elif "generations" in proxy_df.columns:
            planned = float(proxy_df["generations"].dropna().median())
        else:
            planned = np.nan
        meta["planned_generations"] = planned

    if "n_floor_projected" not in meta.columns:
        if {"lr_sigma_min_ratio", "lr_sigma_down_factor"}.issubset(meta.columns):
            meta["n_floor_projected"] = meta.apply(
                lambda r: projected_n_floor(
                    sigma_min_ratio=float(r["lr_sigma_min_ratio"]),
                    sigma_down_factor=float(r["lr_sigma_down_factor"]),
                ),
                axis=1,
            )
        else:
            meta["n_floor_projected"] = np.nan

    if "awf_projected" not in meta.columns:
        if {
            "lr_sigma_min_ratio",
            "lr_sigma_down_factor",
            "planned_generations",
        }.issubset(meta.columns):
            meta["awf_projected"] = meta.apply(
                lambda r: projected_awf(
                    sigma_min_ratio=float(r["lr_sigma_min_ratio"]),
                    sigma_down_factor=float(r["lr_sigma_down_factor"]),
                    planned_generations=int(r["planned_generations"]) if np.isfinite(r["planned_generations"]) else 0,
                ),
                axis=1,
            )
        else:
            meta["awf_projected"] = np.nan

    wanted_order = [
        "variant_id",
        "variant_group",
        "lr_sigma_down_factor",
        "lr_sigma_min_ratio",
        "planned_generations",
        "n_floor_projected",
        "awf_projected",
    ]
    present = [c for c in wanted_order if c in meta.columns]
    others = [c for c in meta.columns if c not in present]
    return meta[present + others].sort_values(["variant_group", "variant_id"]).reset_index(drop=True)


def _floor_summary(proxy_df: pd.DataFrame) -> pd.DataFrame:
    if proxy_df.empty:
        return pd.DataFrame()

    metric_cols = [
        "proxy_time_to_first_floor_gen",
        "proxy_fraction_at_floor",
        "proxy_n_floor_entries",
        "proxy_n_floor_exits",
        "proxy_n_down_steps",
        "proxy_n_up_steps",
        "proxy_n_neutral_steps",
        "proxy_sigma_min_seen",
        "proxy_sigma_max_seen",
    ]

    rows: list[dict[str, Any]] = []

    overall = proxy_df.groupby(["variant_id", "variant_group"], as_index=False)
    for (variant_id, variant_group), group in overall:
        row: dict[str, Any] = {
            "slice_level": "overall",
            "variant_id": variant_id,
            "variant_group": variant_group,
            "function": np.nan,
            "dimension": np.nan,
            "n_runs": int(len(group)),
        }
        for col in metric_cols:
            if col in group:
                row[f"mean_{col}"] = float(group[col].mean())
                row[f"median_{col}"] = float(group[col].median())
        rows.append(row)

    by_fd = proxy_df.groupby(["variant_id", "variant_group", "function", "dimension"], as_index=False)
    for (variant_id, variant_group, function_name, dimension), group in by_fd:
        row = {
            "slice_level": "function_dimension",
            "variant_id": variant_id,
            "variant_group": variant_group,
            "function": function_name,
            "dimension": int(dimension),
            "n_runs": int(len(group)),
        }
        for col in metric_cols:
            if col in group:
                row[f"mean_{col}"] = float(group[col].mean())
                row[f"median_{col}"] = float(group[col].median())
        rows.append(row)

    return pd.DataFrame(rows).sort_values(["slice_level", "variant_id", "function", "dimension"]).reset_index(drop=True)


def _geometry_baseline(meta_df: pd.DataFrame) -> str:
    candidates = meta_df[
        (meta_df["variant_group"] == "geometry")
        & np.isclose(meta_df["lr_sigma_down_factor"], 0.90)
        & np.isclose(meta_df["lr_sigma_min_ratio"], 0.10)
    ]
    if not candidates.empty:
        return str(candidates.iloc[0]["variant_id"])
    fallback = meta_df[meta_df["variant_id"] == "baseline"]
    if not fallback.empty:
        return str(fallback.iloc[0]["variant_id"])
    raise ValueError("Could not identify geometry baseline variant")


def _target_delta_table(cell_df: pd.DataFrame, baseline_variant: str) -> pd.DataFrame:
    proxy_cells = cell_df[cell_df["method"] == "lr_adapt_proxy"].copy()
    baseline = proxy_cells[proxy_cells["variant_id"] == baseline_variant][
        ["function", "dimension", "noise_sigma", "median_delta_vs_vanilla"]
    ].rename(columns={"median_delta_vs_vanilla": "baseline_delta"})

    merged = proxy_cells.merge(
        baseline,
        on=["function", "dimension", "noise_sigma"],
        how="left",
    )
    merged["variant_delta"] = merged["median_delta_vs_vanilla"]
    merged["delta_change_vs_baseline"] = merged["variant_delta"] - merged["baseline_delta"]
    merged["is_p1_target"] = merged.apply(
        lambda r: (str(r["function"]), int(r["dimension"])) in TARGET_P1, axis=1
    )
    merged["is_p2_check"] = merged.apply(
        lambda r: str(r["function"]) == "ellipsoid_cond1e6" and int(r["dimension"]) == 40,
        axis=1,
    )
    merged["p1_improved"] = merged["delta_change_vs_baseline"] < 0.0
    merged["p2_less_negative"] = merged["variant_delta"] > merged["baseline_delta"]

    keep_cols = [
        "variant_id",
        "variant_group",
        "function",
        "dimension",
        "noise_sigma",
        "baseline_delta",
        "variant_delta",
        "delta_change_vs_baseline",
        "is_p1_target",
        "is_p2_check",
        "p1_improved",
        "p2_less_negative",
    ]
    return merged[keep_cols].sort_values(
        ["variant_id", "function", "dimension", "noise_sigma"]
    ).reset_index(drop=True)


def _p1_p2_checks(
    target_df: pd.DataFrame,
    meta_df: pd.DataFrame,
) -> dict[str, Any]:
    high_awf = meta_df[
        (meta_df["variant_group"] == "geometry") & (meta_df["awf_projected"] >= 0.45)
    ]["variant_id"].astype(str).tolist()

    p1_variant_results = []
    p2_variant_results = []

    for variant_id in high_awf:
        v_rows = target_df[target_df["variant_id"] == variant_id]
        p1_rows = v_rows[v_rows["is_p1_target"]]
        p1_improved = int(p1_rows["p1_improved"].sum())
        p1_variant_results.append(
            {
                "variant_id": variant_id,
                "improved_cells": p1_improved,
                "total_cells": int(len(p1_rows)),
                "passes": p1_improved >= 9,
            }
        )

        p2_rows = v_rows[v_rows["is_p2_check"]]
        p2_less_negative = int(p2_rows["p2_less_negative"].sum())
        p2_variant_results.append(
            {
                "variant_id": variant_id,
                "less_negative_cells": p2_less_negative,
                "total_cells": int(len(p2_rows)),
                "passes": p2_less_negative >= 2,
                "falsified": p2_less_negative <= 1,
            }
        )

    p1_supported = bool(high_awf) and all(r["passes"] for r in p1_variant_results)
    p2_supported = bool(high_awf) and all(r["passes"] for r in p2_variant_results)
    p2_falsified = bool(high_awf) and all(r["falsified"] for r in p2_variant_results)

    return {
        "high_awf_variants": high_awf,
        "p1": {
            "criterion": ">=9/12 target cells improved vs geometry baseline for each high-AWF geometry variant",
            "supported": p1_supported,
            "by_variant": p1_variant_results,
        },
        "p2": {
            "criterion": ">=2/3 ellipsoid d40 cells less-negative vs geometry baseline for each high-AWF geometry variant",
            "supported": p2_supported,
            "falsified": p2_falsified,
            "by_variant": p2_variant_results,
        },
    }


def _p3_check(runs_df: pd.DataFrame) -> dict[str, Any]:
    eval_ok = runs_df[(runs_df["phase"] == "eval") & (runs_df["status"] == "ok")].copy()
    proxy = eval_ok[eval_ok["method"] == "lr_adapt_proxy"].copy()
    vanilla = eval_ok[eval_ok["method"] == "vanilla_cma"].copy()

    merge_keys = ["variant_id", "function", "dimension", "noise_sigma", "seed"]
    needed_proxy_cols = [
        "proxy_ema_snr_last",
        "proxy_time_to_first_floor_gen",
        "proxy_fraction_at_floor",
        "proxy_n_floor_entries",
        "proxy_n_floor_exits",
    ]
    if any(col not in proxy.columns for col in needed_proxy_cols):
        return {
            "supported": False,
            "reason": "Missing required proxy telemetry columns for P3",
        }

    merged = proxy.merge(
        vanilla[merge_keys + ["final_best"]],
        on=merge_keys,
        how="inner",
        suffixes=("_proxy", "_vanilla"),
    )
    if merged.empty:
        return {
            "supported": False,
            "reason": "No paired proxy/vanilla rows available for P3",
        }

    merged["win"] = (merged["final_best_proxy"] < merged["final_best_vanilla"]).astype(int)
    model_df = merged[
        [
            "win",
            "proxy_ema_snr_last",
            "proxy_time_to_first_floor_gen",
            "proxy_fraction_at_floor",
            "proxy_n_floor_entries",
            "proxy_n_floor_exits",
        ]
    ].dropna()
    if len(model_df) < 100:
        return {
            "supported": False,
            "reason": f"Insufficient modeled rows for P3: {len(model_df)}",
        }

    y = model_df["win"].astype(float)
    xa = sm.add_constant(model_df[["proxy_ema_snr_last"]], has_constant="add")
    xb = sm.add_constant(
        model_df[
            [
                "proxy_ema_snr_last",
                "proxy_time_to_first_floor_gen",
                "proxy_fraction_at_floor",
                "proxy_n_floor_entries",
                "proxy_n_floor_exits",
            ]
        ],
        has_constant="add",
    )

    try:
        model_a = sm.Logit(y, xa).fit(disp=False)
        model_b = sm.Logit(y, xb).fit(disp=False)
    except Exception as exc:
        return {
            "supported": False,
            "reason": f"Logit fitting failed: {exc}",
        }

    delta_aic = float(model_a.aic - model_b.aic)
    delta_bic = float(model_a.bic - model_b.bic)
    floor_p = float(model_b.pvalues.get("proxy_fraction_at_floor", np.nan))
    supported = bool(delta_aic > 0.0 and delta_bic > 0.0 and np.isfinite(floor_p) and floor_p < 0.05)

    return {
        "criterion": "Model B improves AIC/BIC over Model A and proxy_fraction_at_floor is significant",
        "supported": supported,
        "n_rows_modeled": int(len(model_df)),
        "delta_aic": delta_aic,
        "delta_bic": delta_bic,
        "proxy_fraction_at_floor_pvalue": floor_p,
    }


def analyze_awf(
    runs_csv: str | Path,
    cell_stats_csv: str | Path,
    summary_csv: str | Path,
    outdir: str | Path,
) -> dict[str, str]:
    out_path = ensure_dir(outdir)

    runs_df = pd.read_csv(runs_csv)
    cell_df = pd.read_csv(cell_stats_csv)
    summary_df = pd.read_csv(summary_csv)

    proxy_df = _load_proxy_eval_rows(runs_df)
    meta_df = _variant_metadata(summary_df=summary_df, proxy_df=proxy_df)
    floor_df = _floor_summary(proxy_df=proxy_df)

    baseline_variant = _geometry_baseline(meta_df=meta_df)
    target_df = _target_delta_table(cell_df=cell_df, baseline_variant=baseline_variant)

    p1p2 = _p1_p2_checks(target_df=target_df, meta_df=meta_df)
    p3 = _p3_check(runs_df=runs_df)

    hypothesis = {
        "baseline_variant": baseline_variant,
        "p1": p1p2["p1"],
        "p2": p1p2["p2"],
        "p3": p3,
        "overall": {
            "p1_supported": bool(p1p2["p1"]["supported"]),
            "p2_supported": bool(p1p2["p2"]["supported"]),
            "p2_falsified": bool(p1p2["p2"]["falsified"]),
            "p3_supported": bool(p3.get("supported", False)),
        },
    }

    variant_meta_path = out_path / "awf_variant_metadata.csv"
    floor_path = out_path / "awf_floor_summary.csv"
    target_path = out_path / "awf_target_cell_deltas.csv"
    hypothesis_path = out_path / "awf_hypothesis_checks.json"

    save_csv(variant_meta_path, meta_df)
    save_csv(floor_path, floor_df)
    save_csv(target_path, target_df)
    save_json(hypothesis_path, hypothesis)

    return {
        "awf_variant_metadata_csv": str(variant_meta_path),
        "awf_floor_summary_csv": str(floor_path),
        "awf_target_cell_deltas_csv": str(target_path),
        "awf_hypothesis_checks_json": str(hypothesis_path),
    }


def main() -> None:
    args = parse_awf_analysis_args()
    outputs = analyze_awf(
        runs_csv=args.runs,
        cell_stats_csv=args.cell_stats,
        summary_csv=args.summary,
        outdir=args.outdir,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
