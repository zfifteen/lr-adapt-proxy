from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from experiments.methods import run_jobs


TUNED_METHODS = ["phasewall_tuned", "phasewall_plus_lr_tuned"]


def build_cells(matrix_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    cells = []
    for function_name in matrix_cfg["functions"]:
        for dimension in matrix_cfg["dimensions"]:
            for noise_sigma in matrix_cfg["noise_sigmas"]:
                cells.append(
                    {
                        "function": function_name,
                        "dimension": int(dimension),
                        "noise_sigma": float(noise_sigma),
                    }
                )
    return cells


def filter_cells(cells: list[dict[str, Any]], subset_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    function_set = set(subset_cfg["functions"])
    dim_set = {int(d) for d in subset_cfg["dimensions"]}
    noise_set = {float(n) for n in subset_cfg["noise_sigmas"]}
    return [
        c
        for c in cells
        if c["function"] in function_set and c["dimension"] in dim_set and c["noise_sigma"] in noise_set
    ]


def _make_jobs(
    cells: list[dict[str, Any]],
    seeds: list[int],
    method_name: str,
    config: dict[str, Any],
    phase: str,
    phasewall_strength: float,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for cell in cells:
        for seed in seeds:
            jobs.append(
                {
                    "phase": phase,
                    "method_name": method_name,
                    "function": cell["function"],
                    "dimension": int(cell["dimension"]),
                    "noise_sigma": float(cell["noise_sigma"]),
                    "seed": int(seed),
                    "eval_budget": int(config["budget"]["evals_per_run"]),
                    "initial_sigma": float(config["cma"]["initial_sigma"]),
                    "base_popsize": int(config["cma"]["base_popsize"]),
                    "cma_verbose": int(config["cma"].get("verbose", -9)),
                    "phasewall_strength": float(phasewall_strength),
                    "lr_proxy_params": dict(config["lr_adapt_proxy"]),
                }
            )
    return jobs


def _pair_key(row: pd.Series) -> tuple[str, int, float, int]:
    return (
        str(row["function"]),
        int(row["dimension"]),
        float(row["noise_sigma"]),
        int(row["seed"]),
    )


def run_tuning(
    config: dict[str, Any],
    workers: int,
) -> tuple[dict[str, float], pd.DataFrame, list[dict[str, Any]]]:
    full_cells = build_cells(config["matrix"])
    tuning_cells = filter_cells(full_cells, config["tuning"]["task_subset"])
    tuning_seeds = [int(s) for s in config["seeds"]["tune"]]

    baseline_jobs = _make_jobs(
        cells=tuning_cells,
        seeds=tuning_seeds,
        method_name="vanilla_cma",
        config=config,
        phase="tune_baseline",
        phasewall_strength=0.0,
    )
    baseline_results = run_jobs(baseline_jobs, workers)
    baseline_df = pd.DataFrame(baseline_results)
    baseline_ok = baseline_df[baseline_df["status"] == "ok"].copy()
    baseline_map = {_pair_key(row): float(row["final_best"]) for _, row in baseline_ok.iterrows()}

    tuning_rows: list[dict[str, Any]] = []
    all_tuning_runs: list[dict[str, Any]] = list(baseline_results)
    selected_params: dict[str, float] = {}

    candidates = [float(s) for s in config["phasewall"]["s_candidates"]]

    for tuned_method in TUNED_METHODS:
        method_rows = []
        for s in candidates:
            jobs = _make_jobs(
                cells=tuning_cells,
                seeds=tuning_seeds,
                method_name=tuned_method,
                config=config,
                phase="tune_candidate",
                phasewall_strength=s,
            )
            results = run_jobs(jobs, workers)
            all_tuning_runs.extend(results)

            res_df = pd.DataFrame(results)
            ok_df = res_df[res_df["status"] == "ok"].copy()

            deltas: list[float] = []
            for _, row in ok_df.iterrows():
                key = _pair_key(row)
                if key not in baseline_map:
                    continue
                deltas.append(float(row["final_best"]) - baseline_map[key])

            if deltas:
                deltas_arr = np.array(deltas, dtype=float)
                median_delta = float(np.median(deltas_arr))
                win_rate = float(np.mean(deltas_arr < 0.0))
                loss_rate = float(np.mean(deltas_arr > 0.0))
            else:
                median_delta = np.nan
                win_rate = np.nan
                loss_rate = np.nan

            row = {
                "method": tuned_method,
                "phasewall_strength": s,
                "n_pairs": int(len(deltas)),
                "median_delta_vs_vanilla": median_delta,
                "win_rate_vs_vanilla": win_rate,
                "loss_rate_vs_vanilla": loss_rate,
                "selected": False,
            }
            method_rows.append(row)
            tuning_rows.append(row)

        ranked = sorted(
            method_rows,
            key=lambda r: (
                np.inf if np.isnan(r["median_delta_vs_vanilla"]) else r["median_delta_vs_vanilla"],
                -(r["win_rate_vs_vanilla"] if not np.isnan(r["win_rate_vs_vanilla"]) else -1.0),
                r["phasewall_strength"],
            ),
        )
        best = ranked[0]
        selected_params[tuned_method] = float(best["phasewall_strength"])

        for row in tuning_rows:
            if row["method"] == tuned_method and row["phasewall_strength"] == best["phasewall_strength"]:
                row["selected"] = True

    tuning_summary = pd.DataFrame(tuning_rows)
    return selected_params, tuning_summary, all_tuning_runs
