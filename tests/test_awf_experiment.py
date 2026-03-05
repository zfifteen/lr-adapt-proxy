from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

from experiments.awf_utils import projected_n_floor, should_trace_proxy_run, summarize_floor_flags
from experiments.sensitivity import _build_variants, run_sensitivity_sweep


class AWFExperimentTests(unittest.TestCase):
    def test_n_floor_projected_formula(self) -> None:
        expected = {
            (0.90, 0.05): 29,
            (0.90, 0.10): 22,
            (0.90, 0.20): 16,
            (0.93, 0.05): 42,
            (0.93, 0.10): 32,
            (0.93, 0.20): 23,
            (0.95, 0.05): 59,
            (0.95, 0.10): 45,
            (0.95, 0.20): 32,
            (0.97, 0.05): 99,
            (0.97, 0.10): 76,
            (0.97, 0.20): 53,
        }
        for (k_down, r_min), n_floor in expected.items():
            self.assertEqual(projected_n_floor(sigma_min_ratio=r_min, sigma_down_factor=k_down), float(n_floor))

    def test_floor_metrics_from_sequence(self) -> None:
        metrics = summarize_floor_flags([False, False, True, True, False, True])
        self.assertEqual(metrics.time_to_first_floor_gen, 3)
        self.assertAlmostEqual(metrics.fraction_at_floor, 3.0 / 6.0)
        self.assertEqual(metrics.n_floor_entries, 2)
        self.assertEqual(metrics.n_floor_exits, 1)

        metrics_none = summarize_floor_flags([False, False])
        self.assertEqual(metrics_none.time_to_first_floor_gen, 3)
        self.assertAlmostEqual(metrics_none.fraction_at_floor, 0.0)
        self.assertEqual(metrics_none.n_floor_entries, 0)
        self.assertEqual(metrics_none.n_floor_exits, 0)

    def test_variant_mode_explicit(self) -> None:
        config = {
            "lr_adapt_proxy": {
                "enabled": True,
                "ema_alpha": 0.2,
                "snr_up_threshold": 0.25,
                "snr_down_threshold": 0.08,
                "sigma_up_factor": 1.03,
                "sigma_down_factor": 0.90,
                "sigma_min_ratio": 0.10,
                "sigma_max_ratio": 10.0,
            },
            "variant_mode": "explicit",
            "variants": [
                {
                    "variant_id": "v1",
                    "variant_group": "geometry",
                    "lr_params": {"sigma_down_factor": 0.95, "sigma_min_ratio": 0.05},
                },
                {
                    "variant_id": "v2",
                    "variant_group": "threshold_control",
                    "lr_params": {"snr_down_threshold": 0.12, "snr_up_threshold": 0.30},
                },
            ],
        }
        variants = _build_variants(config)
        self.assertEqual(len(variants), 2)
        self.assertEqual(variants[0]["variant_id"], "v1")
        self.assertEqual(variants[1]["variant_id"], "v2")
        self.assertEqual(variants[0]["lr_params"]["sigma_down_factor"], 0.95)
        self.assertEqual(variants[1]["lr_params"]["sigma_down_factor"], 0.90)
        self.assertEqual(variants[1]["lr_params"]["snr_down_threshold"], 0.12)

    def test_hybrid_trace_selector(self) -> None:
        self.assertTrue(should_trace_proxy_run("sphere", 10, 1001, "hybrid"))
        self.assertTrue(should_trace_proxy_run("rastrigin", 40, 1010, "hybrid"))
        self.assertFalse(should_trace_proxy_run("rastrigin", 40, 1011, "hybrid"))
        self.assertFalse(should_trace_proxy_run("sphere", 10, 1001, "off"))
        self.assertTrue(should_trace_proxy_run("sphere", 10, 1001, "all"))

    def test_sensitivity_smoke_emits_new_columns_and_traces(self) -> None:
        config = {
            "experiment_name": "awf_smoke",
            "matrix": {
                "functions": ["sphere"],
                "dimensions": [2],
                "noise_sigmas": [0.0],
            },
            "methods": ["vanilla_cma", "lr_adapt_proxy"],
            "budget": {"evals_per_run": 16},
            "cma": {
                "initial_sigma": 2.0,
                "base_popsize": 4,
                "verbose": -9,
            },
            "lr_adapt_proxy": {
                "enabled": True,
                "ema_alpha": 0.2,
                "snr_up_threshold": 0.25,
                "snr_down_threshold": 0.08,
                "sigma_up_factor": 1.03,
                "sigma_down_factor": 0.90,
                "sigma_min_ratio": 0.10,
                "sigma_max_ratio": 10.0,
            },
            "variant_mode": "explicit",
            "variants": [
                {
                    "variant_id": "geom_base",
                    "variant_group": "geometry",
                    "lr_params": {
                        "sigma_down_factor": 0.90,
                        "sigma_min_ratio": 0.10,
                    },
                },
                {
                    "variant_id": "geom_hi",
                    "variant_group": "geometry",
                    "lr_params": {
                        "sigma_down_factor": 0.95,
                        "sigma_min_ratio": 0.05,
                    },
                },
            ],
            "telemetry": {"proxy_trace_mode": "hybrid"},
            "seeds": {"eval": [10, 11]},
            "runtime": {"parallel_workers": 1},
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            outdir = tmp_path / "results"
            config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

            outputs = run_sensitivity_sweep(
                config_path=config_path,
                outdir=outdir,
                workers_override=1,
                explicit_run_id="awf-smoke",
            )

            runs_df = pd.read_csv(outputs["sensitivity_runs_long_csv"])
            summary_df = pd.read_csv(outputs["sensitivity_summary_csv"])
            variant_meta_df = pd.read_csv(outputs["awf_variant_metadata_csv"])

            for col in [
                "proxy_time_to_first_floor_gen",
                "proxy_fraction_at_floor",
                "proxy_n_floor_entries",
                "proxy_n_floor_exits",
                "proxy_n_down_steps",
                "proxy_n_up_steps",
                "proxy_n_neutral_steps",
                "proxy_sigma_min_seen",
                "proxy_sigma_max_seen",
                "proxy_trace_written",
                "proxy_trace_relpath",
                "planned_generations",
                "n_floor_projected",
                "awf_projected",
            ]:
                self.assertIn(col, runs_df.columns)

            self.assertIn("awf_projected", summary_df.columns)
            self.assertEqual(len(variant_meta_df), 2)

            traced = runs_df[
                (runs_df["method"] == "lr_adapt_proxy") & (runs_df["proxy_trace_written"] == True)  # noqa: E712
            ]
            self.assertGreaterEqual(len(traced), 1)
            relpath = str(traced.iloc[0]["proxy_trace_relpath"])
            self.assertTrue((outdir / relpath).exists())


if __name__ == "__main__":
    unittest.main()
