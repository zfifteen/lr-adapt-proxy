from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from experiments.adaptation.types import AdaptationAction, AdaptationContext, AdaptationStep


@dataclass(frozen=True)
class LRProxyParams:
    ema_alpha: float
    snr_up_threshold: float
    snr_down_threshold: float
    sigma_up_factor: float
    sigma_down_factor: float
    sigma_min_ratio: float
    sigma_max_ratio: float

    @classmethod
    def from_dict(cls, values: dict) -> "LRProxyParams":
        return cls(
            ema_alpha=float(values["ema_alpha"]),
            snr_up_threshold=float(values["snr_up_threshold"]),
            snr_down_threshold=float(values["snr_down_threshold"]),
            sigma_up_factor=float(values["sigma_up_factor"]),
            sigma_down_factor=float(values["sigma_down_factor"]),
            sigma_min_ratio=float(values["sigma_min_ratio"]),
            sigma_max_ratio=float(values["sigma_max_ratio"]),
        )


def robust_spread(values: np.ndarray) -> float:
    med = np.median(values)
    mad = np.median(np.abs(values - med))
    return float(1.4826 * mad + 1e-12)


class LRProxyPolicy:
    """Pure decision policy for repository-local LR proxy adaptation."""

    def __init__(
        self,
        params: LRProxyParams,
        initial_sigma: float,
        *,
        ema_snr: float = 0.0,
        best_so_far: float | None = None,
    ) -> None:
        self.params = params
        self.initial_sigma = float(initial_sigma)
        self.ema_snr = float(ema_snr)
        self.best_so_far = best_so_far

    def step(self, context: AdaptationContext) -> AdaptationStep:
        if context.direction == "maximize":
            raise NotImplementedError("LRProxyPolicy currently supports minimization only")
        if context.direction != "minimize":
            raise ValueError(f"Unsupported direction: {context.direction}")

        fitness = np.asarray(context.fitness, dtype=float)
        current_best = float(np.min(fitness))
        prev_best = current_best if self.best_so_far is None else float(self.best_so_far)

        signal = max(prev_best - current_best, 0.0)
        noise = robust_spread(fitness)
        snr = signal / noise

        alpha = self.params.ema_alpha
        self.ema_snr = alpha * snr + (1.0 - alpha) * self.ema_snr

        factor = 1.0
        if self.ema_snr < self.params.snr_down_threshold:
            factor = self.params.sigma_down_factor
        elif self.ema_snr > self.params.snr_up_threshold:
            factor = self.params.sigma_up_factor

        sigma_min = self.initial_sigma * self.params.sigma_min_ratio
        sigma_max = self.initial_sigma * self.params.sigma_max_ratio

        unclamped_next = float(context.current_value) * factor
        next_value = float(np.clip(unclamped_next, sigma_min, sigma_max))
        was_clamped = unclamped_next < sigma_min or unclamped_next > sigma_max

        self.best_so_far = min(prev_best, current_best)

        diagnostics = {
            "proxy_signal": signal,
            "proxy_noise": noise,
            "proxy_snr": snr,
            "proxy_ema_snr": self.ema_snr,
            "proxy_sigma_factor": factor,
            "proxy_sigma": next_value,
            "proxy_current_best": current_best,
            "proxy_best_so_far": prev_best,
        }
        return AdaptationStep(
            action=AdaptationAction(
                next_value=next_value,
                factor=factor,
                was_clamped=was_clamped,
            ),
            diagnostics=diagnostics,
        )
