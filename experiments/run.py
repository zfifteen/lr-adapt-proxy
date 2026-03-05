from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.io import (
    ensure_dir,
    load_yaml_config,
    make_run_id,
    parse_run_args,
    save_csv,
    save_json,
    stable_config_hash,
)
from experiments.methods import ALL_METHODS, run_jobs
from experiments.tuning import build_cells, run_tuning


def _git_commit_short() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _validate_config(config: dict[str, Any]) -> None:
    config_methods = config["methods"]
    unknown = [m for m in config_methods if m not in ALL_METHODS]
    if unknown:
        raise ValueError(f"Unknown methods in config: {unknown}")

    tune_seeds = {int(s) for s in config["seeds"]["tune"]}
    eval_seeds = {int(s) for s in config["seeds"]["eval"]}
    overlap = tune_seeds.intersection(eval_seeds)
    if overlap:
        raise ValueError(f"Tune/Eval seed sets must be disjoint, overlap={sorted(overlap)}")

    full_cells = {
        (f, int(d), float(n))
        for f in config["matrix"]["functions"]
        for d in config["matrix"]["dimensions"]
        for n in config["matrix"]["noise_sigmas"]
    }
    subset = {
        (f, int(d), float(n))
        for f in config["tuning"]["task_subset"]["functions"]
        for d in config["tuning"]["task_subset"]["dimensions"]
        for n in config["tuning"]["task_subset"]["noise_sigmas"]
    }
    if not subset.issubset(full_cells):
        raise ValueError("Tuning task subset must be contained in full matrix")
    if subset == full_cells:
        raise ValueError("Strict two-stage policy requires tuning task subset to be a strict subset of full matrix")


def _make_eval_jobs(config: dict[str, Any], selected_params: dict[str, float]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    cells = build_cells(config["matrix"])
    eval_seeds = [int(s) for s in config["seeds"]["eval"]]

    for method_name in config["methods"]:
        for cell in cells:
            for seed in eval_seeds:
                if method_name in selected_params:
                    strength = float(selected_params[method_name])
                else:
                    strength = 0.0

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
                        "phasewall_strength": strength,
                        "lr_proxy_params": dict(config["lr_adapt_proxy"]),
                    }
                )
    return jobs


def execute_pipeline(
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

    selected_params, tuning_summary, tuning_runs = run_tuning(config=config, workers=workers)

    eval_jobs = _make_eval_jobs(config, selected_params)
    eval_runs = run_jobs(eval_jobs, workers)

    runs_df = pd.DataFrame(tuning_runs + eval_runs)
    runs_df.insert(0, "run_index", range(1, len(runs_df) + 1))

    runs_path = out_path / "runs_long.csv"
    tuning_path = out_path / "tuning_summary.csv"
    selected_path = out_path / "selected_params.json"
    manifest_path = out_path / "manifest.json"

    save_csv(runs_path, runs_df)
    save_csv(tuning_path, tuning_summary)
    save_json(selected_path, {k: float(v) for k, v in selected_params.items()})

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
        "created_at_utc": created_at.isoformat(),
        "config_path": str(Path(config_path)),
        "config_hash": config_hash,
        "git_commit": _git_commit_short(),
        "workers": workers,
        "selected_params": {k: float(v) for k, v in selected_params.items()},
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
            "lr_adapt_proxy": "Proxy implementation for transparency; not exact Nomura reproduction.",
            "phasewall_tune_then_eval": "Tuning uses disjoint task subset and disjoint seed set from evaluation.",
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
    args = parse_run_args()
    outputs = execute_pipeline(args.config, args.outdir, args.workers, args.run_id)
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
