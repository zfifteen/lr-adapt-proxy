from __future__ import annotations

import math
import unittest

from experiments.methods import run_experiment_job


LR_PARAMS = {
    "enabled": True,
    "ema_alpha": 0.2,
    "snr_up_threshold": 0.25,
    "snr_down_threshold": 0.08,
    "sigma_up_factor": 1.03,
    "sigma_down_factor": 0.90,
    "sigma_min_ratio": 0.10,
    "sigma_max_ratio": 10.0,
}


class MethodsIntegrationTests(unittest.TestCase):
    def _base_job(self, method_name: str) -> dict:
        return {
            "phase": "eval",
            "method_name": method_name,
            "function": "sphere",
            "dimension": 2,
            "noise_sigma": 0.0,
            "seed": 123,
            "eval_budget": 32,
            "initial_sigma": 2.0,
            "base_popsize": 4,
            "cma_verbose": -9,
            "lr_proxy_params": dict(LR_PARAMS),
        }

    def test_lr_adapt_proxy_job_runs_and_emits_proxy_fields(self) -> None:
        result = run_experiment_job(self._base_job("lr_adapt_proxy"))
        self.assertEqual(result["status"], "ok")
        self.assertGreaterEqual(result["generations"], 1)
        self.assertIn("proxy_sigma_factor_last", result)
        self.assertIn("proxy_ema_snr_last", result)
        self.assertIn("proxy_time_to_first_floor_gen", result)
        self.assertIn("proxy_fraction_at_floor", result)
        self.assertIn("proxy_n_down_steps", result)
        self.assertIn("proxy_trace_written", result)
        self.assertFalse(math.isnan(result["proxy_fraction_at_floor"]))

    def test_vanilla_job_keeps_default_proxy_summary_fields(self) -> None:
        result = run_experiment_job(self._base_job("vanilla_cma"))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["proxy_sigma_factor_last"], 1.0)
        self.assertEqual(result["proxy_ema_snr_last"], 0.0)
        self.assertTrue(math.isnan(result["proxy_fraction_at_floor"]))
        self.assertTrue(math.isnan(result["proxy_time_to_first_floor_gen"]))

    def test_pop4x_budget_divisibility_and_status(self) -> None:
        result = run_experiment_job(self._base_job("pop4x"))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["n_evals"], 32)


if __name__ == "__main__":
    unittest.main()
