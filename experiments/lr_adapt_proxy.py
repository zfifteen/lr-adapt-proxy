from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class LRProxyState:
    initial_sigma: float
    ema_snr: float = 0.0
    best_so_far: float | None = None


def robust_spread(values: np.ndarray) -> float:
    med = np.median(values)
    mad = np.median(np.abs(values - med))
    return float(1.4826 * mad + 1e-12)


def apply_lr_adapt_proxy(
    es,
    fitness: np.ndarray,
    state: LRProxyState,
    params: dict,
) -> dict[str, float]:
    """Proxy LR adaptation rule.

    This is a transparent, repository-local approximation and is intentionally
    labeled proxy in all outputs. Sigma is adapted using an EMA of SNR where:
      signal = max(previous_best - current_best, 0)
      noise  = robust MAD-based spread of current generation fitness
      snr    = signal / noise
    """
    current_best = float(np.min(fitness))
    prev_best = current_best if state.best_so_far is None else state.best_so_far
    signal = max(prev_best - current_best, 0.0)
    noise = robust_spread(fitness)
    snr = signal / noise

    alpha = float(params["ema_alpha"])
    state.ema_snr = alpha * snr + (1.0 - alpha) * state.ema_snr

    factor = 1.0
    if state.ema_snr < float(params["snr_down_threshold"]):
        factor = float(params["sigma_down_factor"])
    elif state.ema_snr > float(params["snr_up_threshold"]):
        factor = float(params["sigma_up_factor"])

    sigma_min = state.initial_sigma * float(params["sigma_min_ratio"])
    sigma_max = state.initial_sigma * float(params["sigma_max_ratio"])
    es.sigma = float(np.clip(es.sigma * factor, sigma_min, sigma_max))
    state.best_so_far = min(prev_best, current_best)

    return {
        "proxy_signal": signal,
        "proxy_noise": noise,
        "proxy_snr": snr,
        "proxy_ema_snr": state.ema_snr,
        "proxy_sigma_factor": factor,
        "proxy_sigma": float(es.sigma),
    }
