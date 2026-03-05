from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.io import derive_legacy_run_id, load_json, parse_findings_args, save_json


def _status_by_phase(runs_df: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        runs_df.groupby(["phase", "status"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["phase", "status"])
    )
    return grouped.to_dict(orient="records")


def _resolve_run_id(manifest: dict[str, Any], allow_legacy: bool) -> str:
    run_id = manifest.get("run_id")
    if run_id:
        return str(run_id)
    if not allow_legacy:
        raise ValueError("Manifest missing run_id and legacy fallback is disabled")
    created_at = str(manifest.get("created_at_utc", ""))
    config_hash = str(manifest.get("config_hash", ""))
    if not created_at or not config_hash:
        raise ValueError("Cannot derive legacy run_id without created_at_utc and config_hash")
    return derive_legacy_run_id(created_at, config_hash)


def _build_findings_markdown(payload: dict[str, Any]) -> str:
    exec_info = payload["execution"]
    stats = payload["statistics"]
    tuning = payload["tuning"]

    lines = [
        "# Run Findings",
        "",
        "## Run Identity",
        f"- Run ID: `{payload['run_id']}`",
        f"- Scope: `{payload['run_scope']}`",
        f"- Created (UTC): `{payload['created_at_utc']}`",
        f"- Config: `{payload['config_path']}`",
        f"- Config Hash: `{payload['config_hash']}`",
        f"- Manifest: `{payload['manifest_json']}`",
        f"- Analysis Manifest: `{payload['analysis_manifest_json']}`",
        "",
        "## Execution Integrity",
        f"- Total runs: `{exec_info['total_runs']}`",
        f"- OK runs: `{exec_info['ok_runs']}`",
        f"- Failed runs: `{exec_info['failed_runs']}`",
        "- Status by phase:",
    ]

    for row in exec_info["status_by_phase"]:
        lines.append(f"  - `{row['phase']}` / `{row['status']}`: `{row['count']}`")

    lines.extend(
        [
            "",
            "## Tuning Outcomes",
        ]
    )

    for method, value in sorted(tuning["selected_params"].items()):
        lines.append(f"- `{method}` selected strength: `{value}`")

    lines.extend(
        [
            "",
            "## Statistical Findings",
            f"- Cell rows: `{stats['n_cells']}`",
            f"- Methods in aggregate: `{stats['n_methods']}`",
            f"- Rows with BH-FDR q < 0.05: `{stats['n_q_lt_0_05']}`",
            "- Method ranking (lower median delta is better):",
        ]
    )

    for row in stats["method_ranking"]:
        lines.append(
            f"  - `{row['method']}`: median delta `{row['median_of_cell_median_delta']}`, "
            f"mean win-rate `{row['mean_win_rate']}`, q<0.05 cells `{row['cells_q_lt_0_05']}`"
        )

    lines.extend(["", "## Caveats"])
    for warning in payload["warnings"]:
        lines.append(f"- {warning}")

    lines.extend(["", "## Artifact Links"])
    for key, value in sorted(payload["artifacts"].items()):
        lines.append(f"- `{key}`: `{value}`")

    return "\n".join(lines) + "\n"


def generate_findings(results_dir: str | Path, figdir: str | Path, allow_legacy_run_id: bool = False) -> dict[str, str]:
    results_path = Path(results_dir)
    fig_path = Path(figdir)

    manifest_path = results_path / "manifest.json"
    analysis_manifest_path = results_path / "analysis_manifest.json"
    runs_path = results_path / "runs_long.csv"
    cell_stats_path = results_path / "cell_stats.csv"
    method_agg_path = results_path / "method_aggregate.csv"
    selected_path = results_path / "selected_params.json"

    manifest = load_json(manifest_path)
    analysis_manifest = load_json(analysis_manifest_path)

    run_id = _resolve_run_id(manifest, allow_legacy=allow_legacy_run_id)
    run_scope = str(manifest.get("run_scope") or manifest.get("experiment_name") or "unknown")

    runs_df = pd.read_csv(runs_path)
    cell_stats_df = pd.read_csv(cell_stats_path)
    method_agg_df = pd.read_csv(method_agg_path)
    selected = load_json(selected_path)

    total_runs = int(len(runs_df))
    ok_runs = int((runs_df["status"] == "ok").sum())
    failed_runs = int((runs_df["status"] != "ok").sum())

    method_ranking_df = method_agg_df.sort_values("median_of_cell_median_delta", ascending=True)
    method_ranking = method_ranking_df.to_dict(orient="records")

    warnings: list[str] = []
    if failed_runs > 0:
        warnings.append("Some runs failed; inspect runs_long.csv before drawing conclusions.")
    if int((cell_stats_df["bh_fdr_q_value"] < 0.05).sum()) == 0:
        warnings.append("No cell-level comparisons passed BH-FDR q < 0.05 in this run.")
    warnings.append("LR-Adapt comparator is a transparent proxy implementation, not exact Nomura reproduction.")
    warnings.append("Findings are run-scoped; treat smoke runs as pipeline-validation evidence, not final inferential evidence.")

    analysis_run_id = analysis_manifest.get("run_id")
    if analysis_run_id and str(analysis_run_id) != run_id:
        warnings.append(
            f"analysis_manifest run_id ({analysis_run_id}) differs from resolved run_id ({run_id}); verify run linkage."
        )

    artifacts = {
        "runs_long_csv": str(runs_path),
        "tuning_summary_csv": str(results_path / "tuning_summary.csv"),
        "selected_params_json": str(selected_path),
        "manifest_json": str(manifest_path),
        "analysis_manifest_json": str(analysis_manifest_path),
        "cell_stats_csv": str(cell_stats_path),
        "method_aggregate_csv": str(method_agg_path),
    }
    figure_map = {
        "figure_method_delta": fig_path / "method_median_delta_bar.png",
        "figure_method_win_rate": fig_path / "method_win_rate_bar.png",
        "figure_method_q_count": fig_path / "method_q_lt_005_count_bar.png",
    }
    for key, path in figure_map.items():
        if path.is_file():
            artifacts[key] = str(path)
        else:
            warnings.append(f"Optional figure artifact missing for this run mode: {path}")

    findings_payload = {
        "run_id": run_id,
        "run_scope": run_scope,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(manifest.get("config_path", "unknown")),
        "config_hash": str(manifest.get("config_hash", "unknown")),
        "manifest_json": str(manifest_path),
        "analysis_manifest_json": str(analysis_manifest_path),
        "execution": {
            "total_runs": total_runs,
            "ok_runs": ok_runs,
            "failed_runs": failed_runs,
            "status_by_phase": _status_by_phase(runs_df),
        },
        "tuning": {
            "selected_params": selected,
        },
        "statistics": {
            "n_cells": int(len(cell_stats_df)),
            "n_methods": int(method_agg_df["method"].nunique()) if not method_agg_df.empty else 0,
            "n_q_lt_0_05": int((cell_stats_df["bh_fdr_q_value"] < 0.05).sum()),
            "method_ranking": method_ranking,
        },
        "warnings": warnings,
        "artifacts": artifacts,
    }

    findings_json_path = results_path / "findings.json"
    findings_md_path = results_path / "findings.md"

    save_json(findings_json_path, findings_payload)
    findings_md_path.write_text(_build_findings_markdown(findings_payload), encoding="utf-8")

    return {
        "findings_json": str(findings_json_path),
        "findings_md": str(findings_md_path),
    }


def main() -> None:
    args = parse_findings_args()
    outputs = generate_findings(
        results_dir=args.results_dir,
        figdir=args.figdir,
        allow_legacy_run_id=args.allow_legacy_run_id,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
