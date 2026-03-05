from __future__ import annotations

import hashlib
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

import cma
import numpy as np

from experiments.lr_adapt_proxy import LRProxyState, apply_lr_adapt_proxy
from experiments.objectives import noisy_objective
from experiments.phasewall import damp_candidates_with_phasewall


ALL_METHODS = [
    "vanilla_cma",
    "lr_adapt_proxy",
    "pop4x",
    "phasewall_tuned",
    "phasewall_plus_lr_tuned",
]


def method_flags(method_name: str) -> dict[str, Any]:
    if method_name not in ALL_METHODS:
        raise ValueError(f"Unknown method: {method_name}")

    use_phasewall = method_name in {"phasewall_tuned", "phasewall_plus_lr_tuned"}
    use_lr = method_name in {"lr_adapt_proxy", "phasewall_plus_lr_tuned"}
    popsize_multiplier = 4 if method_name == "pop4x" else 1
    return {
        "use_phasewall": use_phasewall,
        "use_lr": use_lr,
        "popsize_multiplier": popsize_multiplier,
    }


def _stable_int(seed_text: str) -> int:
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


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
    phasewall_strength = float(job.get("phasewall_strength") or 0.0)
    lr_params = dict(job.get("lr_proxy_params") or {})
    cma_verbose = int(job.get("cma_verbose", -9))

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
        "phasewall_strength": phasewall_strength,
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

        lr_state = LRProxyState(initial_sigma=initial_sigma)
        best_so_far = np.inf
        eval_count = 0
        generations = 0

        proxy_sigma_factor_last = 1.0
        proxy_ema_snr_last = 0.0
        phasewall_mean_scale = 1.0

        while eval_count < eval_budget:
            candidates = np.asarray(es.ask(), dtype=float)

            if flags["use_phasewall"] and phasewall_strength > 0.0:
                eval_points, _, scales = damp_candidates_with_phasewall(es, candidates, phasewall_strength)
                phasewall_mean_scale = float(np.mean(scales))
            else:
                eval_points = candidates

            fitness = np.array(
                [
                    noisy_objective(function_name, point, noise_sigma, rng)
                    for point in eval_points
                ],
                dtype=float,
            )

            es.tell(candidates.tolist(), fitness.tolist())

            if flags["use_lr"]:
                lr_diag = apply_lr_adapt_proxy(es, fitness, lr_state, lr_params)
                proxy_sigma_factor_last = float(lr_diag["proxy_sigma_factor"])
                proxy_ema_snr_last = float(lr_diag["proxy_ema_snr"])

            eval_count += popsize
            generations += 1
            best_so_far = min(best_so_far, float(np.min(fitness)))

        duration_sec = time.time() - started
        return {
            **result_base,
            "n_evals": eval_count,
            "generations": generations,
            "final_best": float(best_so_far),
            "proxy_sigma_factor_last": proxy_sigma_factor_last,
            "proxy_ema_snr_last": proxy_ema_snr_last,
            "phasewall_mean_scale_last": phasewall_mean_scale,
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
            "phasewall_mean_scale_last": np.nan,
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
