#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.io import derive_legacy_run_id


REQUIRED_RESULTS = [
    "runs_long.csv",
    "tuning_summary.csv",
    "selected_params.json",
    "manifest.json",
    "cell_stats.csv",
    "method_aggregate.csv",
    "analysis_manifest.json",
    "findings.json",
    "findings.md",
]

REQUIRED_FIGURES = [
    "method_median_delta_bar.png",
    "method_win_rate_bar.png",
    "method_q_lt_005_count_bar.png",
]

REQUIRED_FINDINGS_KEYS = {
    "run_id",
    "run_scope",
    "created_at_utc",
    "config_path",
    "config_hash",
    "manifest_json",
    "analysis_manifest_json",
    "execution",
    "tuning",
    "statistics",
    "warnings",
    "artifacts",
}

RUNS_COLS = {
    "phase",
    "method",
    "function",
    "dimension",
    "noise_sigma",
    "seed",
    "eval_budget",
    "status",
    "final_best",
}

PAIRWISE_COLS = {
    "function",
    "dimension",
    "noise_sigma",
    "method_a",
    "method_b",
    "n_pairs",
    "median_delta_b_minus_a",
    "win_rate_b_vs_a",
    "loss_rate_b_vs_a",
    "wilcoxon_p_two_sided",
    "bh_fdr_q_value",
}

CELL_STATS_COLS = {
    "function",
    "dimension",
    "noise_sigma",
    "method",
    "median_delta_vs_vanilla",
    "win_rate_vs_vanilla",
    "loss_rate_vs_vanilla",
    "wilcoxon_p_two_sided",
    "bh_fdr_q_value",
}


def fail(msg: str) -> None:
    print(f"[verify-rerun] FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _resolve_run_id(manifest: dict[str, Any]) -> str:
    run_id = manifest.get("run_id")
    if run_id:
        return str(run_id)
    created_at = str(manifest.get("created_at_utc", ""))
    config_hash = str(manifest.get("config_hash", ""))
    if not created_at or not config_hash:
        fail("Manifest missing run_id and insufficient fields for legacy run_id derivation")
    return derive_legacy_run_id(created_at, config_hash)


def _to_existing_path(path_text: str, repo_root: Path) -> Path:
    candidate = Path(path_text)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate


def _status_rows_from_runs(runs: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        runs.groupby(["phase", "status"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["phase", "status"])
    )
    return grouped.to_dict(orient="records")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--figdir", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--require-smoke-summary", action="store_true")
    parser.add_argument("--require-pairwise", action="store_true")
    parser.add_argument("--mode", choices=["full", "eval_only"], default="full")
    args = parser.parse_args()

    repo_root = Path.cwd()
    results_dir = Path(args.results_dir)
    figdir = Path(args.figdir)

    for rel in REQUIRED_RESULTS:
        path = results_dir / rel
        if not path.is_file():
            fail(f"Missing result artifact: {path}")

    if args.require_smoke_summary:
        smoke_summary = results_dir / "smoke_summary.json"
        if not smoke_summary.is_file():
            fail(f"Missing smoke_summary.json: {smoke_summary}")

    if args.mode == "full":
        for rel in REQUIRED_FIGURES:
            path = figdir / rel
            if not path.is_file():
                fail(f"Missing figure artifact: {path}")

    runs = pd.read_csv(results_dir / "runs_long.csv")
    missing_runs_cols = RUNS_COLS.difference(runs.columns)
    if missing_runs_cols:
        fail(f"runs_long.csv missing columns: {sorted(missing_runs_cols)}")

    phase_set = set(runs["phase"].unique())
    if args.mode == "full":
        if not {"tune_baseline", "tune_candidate", "eval"}.issubset(phase_set):
            fail("runs_long.csv must contain tune_baseline, tune_candidate, and eval phases in full mode")
    else:
        if phase_set != {"eval"}:
            fail(f"runs_long.csv must contain only eval phase in eval_only mode; got {sorted(phase_set)}")

    if not set(runs["status"].unique()).issubset({"ok", "failed"}):
        fail("Unexpected status values in runs_long.csv")

    tuning = pd.read_csv(results_dir / "tuning_summary.csv")
    if "selected" not in tuning.columns:
        fail("tuning_summary.csv must include selected column")

    selected = json.loads((results_dir / "selected_params.json").read_text(encoding="utf-8"))
    with open(args.config, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    if args.mode == "full":
        allowed_s = {float(v) for v in config["phasewall"]["s_candidates"]}
        for method in ["phasewall_tuned", "phasewall_plus_lr_tuned"]:
            if method not in selected:
                fail(f"selected_params.json missing method: {method}")
            if float(selected[method]) not in allowed_s:
                fail(f"Selected s for {method} not in configured candidates")
    else:
        for method in config["methods"]:
            if method not in selected:
                fail(f"selected_params.json missing method from config methods: {method}")
            try:
                float(selected[method])
            except Exception as exc:
                fail(f"selected_params.json value for {method} is not numeric: {exc}")

    cell_stats = pd.read_csv(results_dir / "cell_stats.csv")
    missing_cell_cols = CELL_STATS_COLS.difference(cell_stats.columns)
    if missing_cell_cols:
        fail(f"cell_stats.csv missing columns: {sorted(missing_cell_cols)}")

    if args.mode == "full" and cell_stats.empty:
        fail("cell_stats.csv must not be empty in full mode")

    if (cell_stats["bh_fdr_q_value"] < 0).any() or (cell_stats["bh_fdr_q_value"] > 1).any():
        fail("bh_fdr_q_value must be in [0,1]")

    method_agg = pd.read_csv(results_dir / "method_aggregate.csv")
    if args.mode == "full" and method_agg.empty:
        fail("method_aggregate.csv must not be empty in full mode")

    manifest = json.loads((results_dir / "manifest.json").read_text(encoding="utf-8"))
    analysis_manifest = json.loads((results_dir / "analysis_manifest.json").read_text(encoding="utf-8"))
    findings = json.loads((results_dir / "findings.json").read_text(encoding="utf-8"))

    missing_findings = REQUIRED_FINDINGS_KEYS.difference(findings.keys())
    if missing_findings:
        fail(f"findings.json missing keys: {sorted(missing_findings)}")

    resolved_run_id = _resolve_run_id(manifest)
    if str(findings["run_id"]) != resolved_run_id:
        fail(
            "findings.json run_id mismatch: "
            f"expected {resolved_run_id}, got {findings['run_id']}"
        )

    analysis_run_id = analysis_manifest.get("run_id")
    if analysis_run_id is not None and str(analysis_run_id) != resolved_run_id:
        fail(
            "analysis_manifest run_id mismatch: "
            f"expected {resolved_run_id}, got {analysis_run_id}"
        )

    findings_manifest_ref = _to_existing_path(str(findings["manifest_json"]), repo_root)
    if findings_manifest_ref.resolve() != (results_dir / "manifest.json").resolve():
        fail("findings.json manifest_json does not reference results-dir manifest.json")

    findings_analysis_ref = _to_existing_path(str(findings["analysis_manifest_json"]), repo_root)
    if findings_analysis_ref.resolve() != (results_dir / "analysis_manifest.json").resolve():
        fail("findings.json analysis_manifest_json does not reference results-dir analysis_manifest.json")

    artifacts = findings.get("artifacts", {})
    if not isinstance(artifacts, dict):
        fail("findings.json artifacts must be an object")
    for key, value in artifacts.items():
        path = _to_existing_path(str(value), repo_root)
        if not path.exists():
            fail(f"findings artifact path missing ({key}): {path}")

    expected_status = _status_rows_from_runs(runs)
    reported_status = findings["execution"].get("status_by_phase", [])
    if expected_status != reported_status:
        fail("findings execution.status_by_phase mismatch vs runs_long.csv")

    expected_total = int(len(runs))
    expected_ok = int((runs["status"] == "ok").sum())
    expected_failed = int((runs["status"] != "ok").sum())

    if int(findings["execution"].get("total_runs", -1)) != expected_total:
        fail("findings execution.total_runs mismatch")
    if int(findings["execution"].get("ok_runs", -1)) != expected_ok:
        fail("findings execution.ok_runs mismatch")
    if int(findings["execution"].get("failed_runs", -1)) != expected_failed:
        fail("findings execution.failed_runs mismatch")

    if findings.get("tuning", {}).get("selected_params") != selected:
        fail("findings tuning.selected_params mismatch vs selected_params.json")

    if args.require_pairwise:
        pairwise_csv = results_dir / "pairwise_pwlr_vs_lr.csv"
        pairwise_json = results_dir / "pairwise_pwlr_vs_lr.json"
        ablation_md = results_dir / "findings_ablation.md"
        for path in [pairwise_csv, pairwise_json, ablation_md]:
            if not path.is_file():
                fail(f"Missing required pairwise artifact: {path}")

        pairwise_df = pd.read_csv(pairwise_csv)
        missing_pairwise_cols = PAIRWISE_COLS.difference(pairwise_df.columns)
        if missing_pairwise_cols:
            fail(f"pairwise_pwlr_vs_lr.csv missing columns: {sorted(missing_pairwise_cols)}")
        if pairwise_df.empty:
            fail("pairwise_pwlr_vs_lr.csv must not be empty")

        expected_cells = (
            len(config["matrix"]["functions"])
            * len(config["matrix"]["dimensions"])
            * len(config["matrix"]["noise_sigmas"])
        )
        if int(len(pairwise_df)) != int(expected_cells):
            fail(f"pairwise_pwlr_vs_lr.csv row count mismatch: expected {expected_cells}, got {len(pairwise_df)}")

        if (pairwise_df["bh_fdr_q_value"] < 0).any() or (pairwise_df["bh_fdr_q_value"] > 1).any():
            fail("pairwise bh_fdr_q_value must be in [0,1]")

        if (pairwise_df["wilcoxon_p_two_sided"] < 0).any() or (pairwise_df["wilcoxon_p_two_sided"] > 1).any():
            fail("pairwise wilcoxon_p_two_sided must be in [0,1]")

        files = analysis_manifest.get("files", {})
        for key in ["pairwise_pwlr_vs_lr_csv", "pairwise_pwlr_vs_lr_json", "findings_ablation_md"]:
            if key not in files:
                fail(f"analysis_manifest.json missing files.{key}")
            p = _to_existing_path(str(files[key]), repo_root)
            if not p.exists():
                fail(f"analysis_manifest files.{key} points to missing path: {p}")

    print("[verify-rerun] PASS: rerun artifacts, findings linkage, and schemas validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
