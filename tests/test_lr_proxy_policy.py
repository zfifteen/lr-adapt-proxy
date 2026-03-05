from __future__ import annotations

import inspect
import unittest

import numpy as np

from experiments.adaptation.policies.lr_proxy import LRProxyParams, LRProxyPolicy
from experiments.adaptation.types import AdaptationContext
from experiments.lr_adapt_proxy import LRProxyState, apply_lr_adapt_proxy


DEFAULT_PARAMS = {
    "enabled": True,
    "ema_alpha": 0.2,
    "snr_up_threshold": 0.25,
    "snr_down_threshold": 0.08,
    "sigma_up_factor": 1.03,
    "sigma_down_factor": 0.90,
    "sigma_min_ratio": 0.10,
    "sigma_max_ratio": 10.0,
}


class DummyES:
    def __init__(self, sigma: float) -> None:
        self.sigma = float(sigma)


def legacy_step(
    sigma: float,
    fitness: np.ndarray,
    state: dict[str, float | None],
    params: dict,
) -> tuple[dict[str, float], float, dict[str, float | None]]:
    current_best = float(np.min(fitness))
    prev_best = current_best if state["best_so_far"] is None else float(state["best_so_far"])
    signal = max(prev_best - current_best, 0.0)

    med = np.median(fitness)
    mad = np.median(np.abs(fitness - med))
    noise = float(1.4826 * mad + 1e-12)
    snr = signal / noise

    alpha = float(params["ema_alpha"])
    ema_snr = alpha * snr + (1.0 - alpha) * float(state["ema_snr"])

    factor = 1.0
    if ema_snr < float(params["snr_down_threshold"]):
        factor = float(params["sigma_down_factor"])
    elif ema_snr > float(params["snr_up_threshold"]):
        factor = float(params["sigma_up_factor"])

    sigma_min = float(state["initial_sigma"]) * float(params["sigma_min_ratio"])
    sigma_max = float(state["initial_sigma"]) * float(params["sigma_max_ratio"])
    next_sigma = float(np.clip(sigma * factor, sigma_min, sigma_max))

    next_state: dict[str, float | None] = {
        "initial_sigma": float(state["initial_sigma"]),
        "ema_snr": ema_snr,
        "best_so_far": min(prev_best, current_best),
    }
    diagnostics = {
        "proxy_signal": signal,
        "proxy_noise": noise,
        "proxy_snr": snr,
        "proxy_ema_snr": ema_snr,
        "proxy_sigma_factor": factor,
        "proxy_sigma": next_sigma,
    }
    return diagnostics, next_sigma, next_state


class LRProxyPolicyTests(unittest.TestCase):
    def test_policy_matches_legacy_sequence_exactly(self) -> None:
        params = LRProxyParams.from_dict(DEFAULT_PARAMS)
        policy = LRProxyPolicy(params=params, initial_sigma=2.0)

        legacy_state: dict[str, float | None] = {
            "initial_sigma": 2.0,
            "ema_snr": 0.0,
            "best_so_far": None,
        }
        sigma = 2.0

        fitness_series = [
            np.array([10.0, 11.0, 9.0, 10.5], dtype=float),
            np.array([8.0, 8.5, 9.2, 8.1], dtype=float),
            np.array([8.2, 8.4, 8.3, 8.1], dtype=float),
            np.array([7.9, 7.8, 8.0, 8.1], dtype=float),
        ]

        for idx, fitness in enumerate(fitness_series):
            expected_diag, expected_sigma, legacy_state = legacy_step(
                sigma=sigma,
                fitness=fitness,
                state=legacy_state,
                params=DEFAULT_PARAMS,
            )

            step = policy.step(
                AdaptationContext(
                    fitness=fitness,
                    generation_index=idx,
                    current_value=sigma,
                    direction="minimize",
                )
            )

            for key, expected in expected_diag.items():
                self.assertEqual(step.diagnostics[key], expected)
            self.assertEqual(step.action.next_value, expected_sigma)
            self.assertEqual(step.action.factor, expected_diag["proxy_sigma_factor"])

            sigma = step.action.next_value

    def test_maximize_direction_fails_fast(self) -> None:
        params = LRProxyParams.from_dict(DEFAULT_PARAMS)
        policy = LRProxyPolicy(params=params, initial_sigma=2.0)

        with self.assertRaises(NotImplementedError):
            policy.step(
                AdaptationContext(
                    fitness=np.array([1.0, 2.0, 3.0], dtype=float),
                    generation_index=0,
                    current_value=2.0,
                    direction="maximize",
                )
            )

    def test_was_clamped_is_internal_and_not_in_diagnostics(self) -> None:
        params = LRProxyParams.from_dict(DEFAULT_PARAMS)
        policy = LRProxyPolicy(params=params, initial_sigma=2.0)

        # Force a down-factor and clamp to sigma_min.
        step = policy.step(
            AdaptationContext(
                fitness=np.array([4.0, 4.0, 4.0, 4.0], dtype=float),
                generation_index=0,
                current_value=0.05,
                direction="minimize",
            )
        )

        self.assertTrue(step.action.was_clamped)
        self.assertNotIn("was_clamped", step.diagnostics)
        self.assertSetEqual(
            set(step.diagnostics.keys()),
            {
                "proxy_signal",
                "proxy_noise",
                "proxy_snr",
                "proxy_ema_snr",
                "proxy_sigma_factor",
                "proxy_sigma",
            },
        )

    def test_policy_signature_takes_context_only(self) -> None:
        signature = inspect.signature(LRProxyPolicy.step)
        self.assertEqual(list(signature.parameters.keys()), ["self", "context"])

    def test_legacy_shim_delegates_and_preserves_state(self) -> None:
        params = dict(DEFAULT_PARAMS)
        state = LRProxyState(initial_sigma=2.0)
        es = DummyES(sigma=2.0)

        policy = LRProxyPolicy(
            params=LRProxyParams.from_dict(params),
            initial_sigma=2.0,
        )

        fitness_1 = np.array([10.0, 9.0, 11.0, 10.5], dtype=float)
        diag_1 = apply_lr_adapt_proxy(es=es, fitness=fitness_1, state=state, params=params)
        step_1 = policy.step(
            AdaptationContext(
                fitness=fitness_1,
                generation_index=0,
                current_value=2.0,
                direction="minimize",
            )
        )
        self.assertDictEqual(diag_1, step_1.diagnostics)
        self.assertEqual(es.sigma, step_1.action.next_value)
        self.assertEqual(state.ema_snr, policy.ema_snr)
        self.assertEqual(state.best_so_far, policy.best_so_far)

        fitness_2 = np.array([8.1, 8.3, 8.2, 8.0], dtype=float)
        prev_sigma = es.sigma
        diag_2 = apply_lr_adapt_proxy(es=es, fitness=fitness_2, state=state, params=params)
        step_2 = policy.step(
            AdaptationContext(
                fitness=fitness_2,
                generation_index=1,
                current_value=prev_sigma,
                direction="minimize",
            )
        )
        self.assertDictEqual(diag_2, step_2.diagnostics)
        self.assertEqual(es.sigma, step_2.action.next_value)
        self.assertEqual(state.ema_snr, policy.ema_snr)
        self.assertEqual(state.best_so_far, policy.best_so_far)


if __name__ == "__main__":
    unittest.main()
