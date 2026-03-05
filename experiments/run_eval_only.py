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
    parse_run_eval_only_args,
    save_csv,
    save_json,
    stable_config_hash,
)
from experiments.methods import ALL_METHODS, run_jobs
from experiments.run import _git_commit_short
from experiments.tuning import build_cells


def _validate_config(config: dict[str, Any]) -> None:
    methods = list(config["methods"])
    unknown = [m for m in methods if m not in ALL_METHODS]
    if unknown:
        raise ValueError(f"Unknown methods in config: {unknown}")
    if not methods:
        raise ValueError("Config methods must not be empty")

    eval_seeds = list(config["seeds"]["eval"])
    if not eval_seeds:
        raise ValueError("Config seeds.eval must not be empty")


def _make_eval_jobs(config: dict[str, Any]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    cells = build_cells(config["matrix"])
    eval_seeds = [int(s) for s in config["seeds"]["eval"]]

    for method_name in config["methods"]:
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
                        "lr_proxy_params": dict(config["lr_adapt_proxy"]),
                    }
                )
    return jobs


def execute_eval_only_pipeline(
    config_path: str | Path,
    outdir: str | Path,
    workers_override: int | None = None,
    explicit_run_id: str | None = None,
) -> dict[str, str]:
    config = load_yaml_config(config_path)
    _validate_config(config)

    workers = int(workers_override or config.get("runtime", {}).get("parallel_workers", 1))
    out_path = ensure_dir(outdir)
    created_at = datetime.now(timezone.utc)
    config_hash = stable_config_hash(config)
    run_id = explicit_run_id or make_run_id(config_hash, created_at)
    run_scope = str(config.get("experiment_name", "unknown"))

    eval_jobs = _make_eval_jobs(config)
    eval_runs = run_jobs(eval_jobs, workers)

    runs_df = pd.DataFrame(eval_runs)
    runs_df.insert(0, "run_index", range(1, len(runs_df) + 1))

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
    selected_params: dict[str, float] = {}

    runs_path = out_path / "runs_long.csv"
    tuning_path = out_path / "tuning_summary.csv"
    selected_path = out_path / "selected_params.json"
    manifest_path = out_path / "manifest.json"

    save_csv(runs_path, runs_df)
    save_csv(tuning_path, tuning_summary)
    save_json(selected_path, selected_params)

    status_counts = (
        runs_df.groupby(["phase", "status"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .to_dict(orient="records")
    )
    manifest = {
        "run_id": run_id,
        "run_scope": run_scope,
        "run_root": str(out_path),
        "pipeline_mode": "eval_only",
        "created_at_utc": created_at.isoformat(),
        "config_path": str(Path(config_path)),
        "config_hash": config_hash,
        "git_commit": _git_commit_short(),
        "workers": workers,
        "selected_params": selected_params,
        "files": {
            "runs_long_csv": str(runs_path),
            "tuning_summary_csv": str(tuning_path),
            "selected_params_json": str(selected_path),
            "manifest_json": str(manifest_path),
        },
        "counts": {
            "total_runs": int(len(runs_df)),
            "status_by_phase": status_counts,
            "methods": list(config["methods"]),
        },
        "notes": {
            "eval_only": "No tuning stage executed in eval-only mode.",
            "lr_adapt_proxy": "Proxy implementation for transparency; not exact Nomura reproduction.",
        },
    }
    save_json(manifest_path, manifest)

    return {
        "run_id": run_id,
        "runs_long_csv": str(runs_path),
        "tuning_summary_csv": str(tuning_path),
        "selected_params_json": str(selected_path),
        "manifest_json": str(manifest_path),
    }


def main() -> None:
    args = parse_run_eval_only_args()
    outputs = execute_eval_only_pipeline(args.config, args.outdir, args.workers, args.run_id)
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
