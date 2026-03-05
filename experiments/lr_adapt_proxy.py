from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from experiments.adaptation.clients.pycma_sigma import apply_sigma_action
from experiments.adaptation.policies.lr_proxy import LRProxyParams, LRProxyPolicy, robust_spread as _core_robust_spread
from experiments.adaptation.types import AdaptationContext


@dataclass
class LRProxyState:
    initial_sigma: float
    ema_snr: float = 0.0
    best_so_far: float | None = None


def robust_spread(values: np.ndarray) -> float:
    return _core_robust_spread(np.asarray(values, dtype=float))


def apply_lr_adapt_proxy(
    es,
    fitness: np.ndarray,
    state: LRProxyState,
    params: dict,
) -> dict[str, float]:
    """Backward-compatible shim for the repository-local LR proxy rule.

    The implementation now delegates to the generalized adaptation policy while
    preserving the legacy function signature and diagnostic keys.
    """

    policy = LRProxyPolicy(
        params=LRProxyParams.from_dict(params),
        initial_sigma=state.initial_sigma,
        ema_snr=state.ema_snr,
        best_so_far=state.best_so_far,
    )

    step = policy.step(
        AdaptationContext(
            fitness=np.asarray(fitness, dtype=float),
            generation_index=0,
            current_value=float(es.sigma),
            direction="minimize",
        )
    )

    apply_sigma_action(es, step.action)

    state.ema_snr = policy.ema_snr
    state.best_so_far = policy.best_so_far

    return step.diagnostics
