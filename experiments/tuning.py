from __future__ import annotations

from typing import Any

import pandas as pd


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


def run_tuning(
    config: dict[str, Any],
    workers: int,
) -> tuple[dict[str, float], pd.DataFrame, list[dict[str, Any]]]:
    _ = (config, workers)

    tuning_summary = pd.DataFrame(
        columns=[
            "method",
            "n_pairs",
            "median_delta_vs_vanilla",
            "win_rate_vs_vanilla",
            "loss_rate_vs_vanilla",
            "selected",
            "note",
        ]
    )
    return {}, tuning_summary, []
