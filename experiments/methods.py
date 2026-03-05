from __future__ import annotations

import csv
import hashlib
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import cma
import numpy as np

from experiments.awf_utils import should_trace_proxy_run, summarize_floor_flags
from experiments.adaptation.clients.pycma_sigma import apply_sigma_action
from experiments.adaptation.policies.lr_proxy import LRProxyParams, LRProxyPolicy
from experiments.adaptation.types import AdaptationContext
from experiments.objectives import noisy_objective


ALL_METHODS = [
    "vanilla_cma",
    "lr_adapt_proxy",
    "pop4x",
]


def method_flags(method_name: str) -> dict[str, Any]:
    if method_name not in ALL_METHODS:
        raise ValueError(f"Unknown method: {method_name}")

    has_adaptation_policy = method_name == "lr_adapt_proxy"
    popsize_multiplier = 4 if method_name == "pop4x" else 1
    return {
        "has_adaptation_policy": has_adaptation_policy,
        "popsize_multiplier": popsize_multiplier,
    }


def _stable_int(seed_text: str) -> int:
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _sanitize_token(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value)


def _trace_file_name(
    *,
    phase: str,
    method: str,
    variant_id: str | None,
    function_name: str,
    dimension: int,
    noise_sigma: float,
    seed: int,
) -> str:
    variant_token = _sanitize_token(variant_id) if variant_id else "na"
    fn_token = _sanitize_token(function_name)
    noise_token = str(noise_sigma).replace(".", "p").replace("-", "m")
    return (
        f"{phase}_{method}_{variant_token}_{fn_token}_d{dimension}_"
        f"n{noise_token}_seed{seed}.csv"
    )


def run_experiment_job(job: dict[str, Any]) -> dict[str, Any]:
    started = time.time()

    method_name = job["method_name"]
    flags = method_flags(method_name)

    function_name = job["function"]
    dimension = int(job["dimension"])
    noise_sigma = float(job["noise_sigma"])
    seed = int(job["seed"])
    phase = job["phase"]

    eval_budget = int(job["eval_budget"])
    initial_sigma = float(job["initial_sigma"])
    base_popsize = int(job["base_popsize"])
    popsize = int(base_popsize * flags["popsize_multiplier"])
    lr_params = dict(job.get("lr_proxy_params") or {})
    cma_verbose = int(job.get("cma_verbose", -9))
    trace_mode = str(job.get("proxy_trace_mode", "off"))
    trace_root_raw = job.get("proxy_trace_root")
    trace_root = Path(trace_root_raw) if trace_root_raw else None
    variant_id = str(job.get("variant_id", "")) or None

    if eval_budget % popsize != 0:
        raise ValueError(
            f"eval_budget ({eval_budget}) must be divisible by method popsize ({popsize}) for exact budget accounting"
        )

    noise_seed = _stable_int(f"{function_name}|{dimension}|{noise_sigma:.6f}|{seed}")
    rng = np.random.default_rng(noise_seed)

    result_base = {
        "phase": phase,
        "method": method_name,
        "function": function_name,
        "dimension": dimension,
        "noise_sigma": noise_sigma,
        "seed": seed,
        "eval_budget": eval_budget,
        "popsize": popsize,
        "status": "ok",
        "error_message": "",
    }

    try:
        x0 = np.full(dimension, 3.0, dtype=float)
        opts = {
            "seed": seed,
            "popsize": popsize,
            "verbose": cma_verbose,
            "verb_disp": 0,
            "verb_log": 0,
            "maxiter": 10**9,
        }
        es = cma.CMAEvolutionStrategy(x0.tolist(), initial_sigma, opts)

        policy = None
        if flags["has_adaptation_policy"]:
            policy = LRProxyPolicy(
                params=LRProxyParams.from_dict(lr_params),
                initial_sigma=initial_sigma,
            )

        best_so_far = np.inf
        eval_count = 0
        generations = 0

        proxy_sigma_factor_last = 1.0
        proxy_ema_snr_last = 0.0
        proxy_time_to_first_floor_gen = np.nan
        proxy_fraction_at_floor = np.nan
        proxy_n_floor_entries = np.nan
        proxy_n_floor_exits = np.nan
        proxy_n_down_steps = np.nan
        proxy_n_up_steps = np.nan
        proxy_n_neutral_steps = np.nan
        proxy_sigma_min_seen = np.nan
        proxy_sigma_max_seen = np.nan
        proxy_trace_written: bool | float = np.nan
        proxy_trace_relpath: str | float = np.nan

        at_floor_flags: list[bool] = []
        trace_rows: list[dict[str, float | int | bool]] | None = None
        floor_sigma = np.nan
        n_down_steps = 0
        n_up_steps = 0
        n_neutral_steps = 0
        sigma_min_seen = np.inf
        sigma_max_seen = -np.inf

        if policy is not None:
            floor_sigma = initial_sigma * policy.params.sigma_min_ratio
            if should_trace_proxy_run(
                function_name=function_name,
                dimension=dimension,
                seed=seed,
                mode=trace_mode,
            ):
                trace_rows = []

        while eval_count < eval_budget:
            candidates = np.asarray(es.ask(), dtype=float)
            fitness = np.array(
                [
                    noisy_objective(function_name, point, noise_sigma, rng)
                    for point in candidates
                ],
                dtype=float,
            )

            es.tell(candidates.tolist(), fitness.tolist())

            if policy is not None:
                sigma_before = float(es.sigma)
                step = policy.step(
                    AdaptationContext(
                        fitness=fitness,
                        generation_index=generations,
                        current_value=sigma_before,
                        direction="minimize",
                    )
                )
                apply_sigma_action(es, step.action)
                sigma_after = float(es.sigma)
                proxy_sigma_factor_last = float(step.diagnostics["proxy_sigma_factor"])
                proxy_ema_snr_last = float(step.diagnostics["proxy_ema_snr"])

                factor = float(step.action.factor)
                if factor < 1.0:
                    n_down_steps += 1
                elif factor > 1.0:
                    n_up_steps += 1
                else:
                    n_neutral_steps += 1

                at_floor = sigma_after <= float(floor_sigma + 1e-12)
                at_floor_flags.append(at_floor)

                sigma_min_seen = min(sigma_min_seen, sigma_after)
                sigma_max_seen = max(sigma_max_seen, sigma_after)

                if trace_rows is not None:
                    trace_rows.append(
                        {
                            "generation": generations + 1,
                            "sigma_before": sigma_before,
                            "sigma_after": sigma_after,
                            "at_floor": at_floor,
                            "was_clamped": bool(step.action.was_clamped),
                            "proxy_sigma_factor": proxy_sigma_factor_last,
                            "proxy_ema_snr": proxy_ema_snr_last,
                            "proxy_signal": float(step.diagnostics["proxy_signal"]),
                            "proxy_noise": float(step.diagnostics["proxy_noise"]),
                            "proxy_snr": float(step.diagnostics["proxy_snr"]),
                            "proxy_current_best": float(step.diagnostics["proxy_current_best"]),
                            "proxy_best_so_far": float(step.diagnostics["proxy_best_so_far"]),
                        }
                    )

            eval_count += popsize
            generations += 1
            best_so_far = min(best_so_far, float(np.min(fitness)))

        if policy is not None:
            floor_metrics = summarize_floor_flags(at_floor_flags)
            proxy_time_to_first_floor_gen = float(floor_metrics.time_to_first_floor_gen)
            proxy_fraction_at_floor = float(floor_metrics.fraction_at_floor)
            proxy_n_floor_entries = float(floor_metrics.n_floor_entries)
            proxy_n_floor_exits = float(floor_metrics.n_floor_exits)
            proxy_n_down_steps = float(n_down_steps)
            proxy_n_up_steps = float(n_up_steps)
            proxy_n_neutral_steps = float(n_neutral_steps)
            proxy_sigma_min_seen = float(sigma_min_seen if np.isfinite(sigma_min_seen) else np.nan)
            proxy_sigma_max_seen = float(sigma_max_seen if np.isfinite(sigma_max_seen) else np.nan)

            if trace_rows is not None and trace_root is not None:
                trace_root.mkdir(parents=True, exist_ok=True)
                trace_path = trace_root / _trace_file_name(
                    phase=phase,
                    method=method_name,
                    variant_id=variant_id,
                    function_name=function_name,
                    dimension=dimension,
                    noise_sigma=noise_sigma,
                    seed=seed,
                )
                fieldnames = [
                    "generation",
                    "sigma_before",
                    "sigma_after",
                    "at_floor",
                    "was_clamped",
                    "proxy_sigma_factor",
                    "proxy_ema_snr",
                    "proxy_signal",
                    "proxy_noise",
                    "proxy_snr",
                    "proxy_current_best",
                    "proxy_best_so_far",
                ]
                with trace_path.open("w", encoding="utf-8", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(trace_rows)
                proxy_trace_written = True
                proxy_trace_relpath = str(trace_path.relative_to(trace_root.parent))
            elif trace_rows is not None:
                proxy_trace_written = False
                proxy_trace_relpath = ""

        duration_sec = time.time() - started
        return {
            **result_base,
            "n_evals": eval_count,
            "generations": generations,
            "final_best": float(best_so_far),
            "proxy_sigma_factor_last": proxy_sigma_factor_last,
            "proxy_ema_snr_last": proxy_ema_snr_last,
            "proxy_time_to_first_floor_gen": proxy_time_to_first_floor_gen,
            "proxy_fraction_at_floor": proxy_fraction_at_floor,
            "proxy_n_floor_entries": proxy_n_floor_entries,
            "proxy_n_floor_exits": proxy_n_floor_exits,
            "proxy_n_down_steps": proxy_n_down_steps,
            "proxy_n_up_steps": proxy_n_up_steps,
            "proxy_n_neutral_steps": proxy_n_neutral_steps,
            "proxy_sigma_min_seen": proxy_sigma_min_seen,
            "proxy_sigma_max_seen": proxy_sigma_max_seen,
            "proxy_trace_written": proxy_trace_written,
            "proxy_trace_relpath": proxy_trace_relpath,
            "duration_sec": duration_sec,
        }
    except Exception as exc:  # pragma: no cover - defensive path
        duration_sec = time.time() - started
        return {
            **result_base,
            "status": "failed",
            "error_message": str(exc),
            "n_evals": 0,
            "generations": 0,
            "final_best": np.nan,
            "proxy_sigma_factor_last": np.nan,
            "proxy_ema_snr_last": np.nan,
            "proxy_time_to_first_floor_gen": np.nan,
            "proxy_fraction_at_floor": np.nan,
            "proxy_n_floor_entries": np.nan,
            "proxy_n_floor_exits": np.nan,
            "proxy_n_down_steps": np.nan,
            "proxy_n_up_steps": np.nan,
            "proxy_n_neutral_steps": np.nan,
            "proxy_sigma_min_seen": np.nan,
            "proxy_sigma_max_seen": np.nan,
            "proxy_trace_written": np.nan,
            "proxy_trace_relpath": np.nan,
            "duration_sec": duration_sec,
        }


def run_jobs(jobs: list[dict[str, Any]], workers: int) -> list[dict[str, Any]]:
    if workers <= 1:
        return [run_experiment_job(job) for job in jobs]

    ordered_results: list[dict[str, Any]] = [None] * len(jobs)  # type: ignore[assignment]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        future_to_index = {pool.submit(run_experiment_job, job): idx for idx, job in enumerate(jobs)}
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            ordered_results[idx] = future.result()
    return ordered_results
