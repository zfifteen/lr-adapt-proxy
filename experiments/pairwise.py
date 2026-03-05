from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.io import ensure_dir, load_json, parse_pairwise_args, save_csv, save_json
from experiments.stats import compute_pairwise_cell_stats


def _quantiles(values: pd.Series) -> dict[str, float]:
    if values.empty:
        return {}
    quantiles = values.quantile([0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0])
    return {f"{k:.2f}": float(v) for k, v in quantiles.items()}


def _top_rows(df: pd.DataFrame, ascending: bool, n: int = 5) -> list[dict[str, Any]]:
    if df.empty:
        return []
    cols = ["function", "dimension", "noise_sigma", "median_delta_b_minus_a", "wilcoxon_p_two_sided", "bh_fdr_q_value"]
    ranked = df.sort_values("median_delta_b_minus_a", ascending=ascending).head(n)
    return ranked[cols].to_dict(orient="records")


def _build_findings_ablation_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Pairwise Ablation Findings",
        "",
        "## Run Identity",
        f"- Run ID: `{summary['run_id']}`",
        f"- Created (UTC): `{summary['created_at_utc']}`",
        f"- Phase: `{summary['phase']}`",
        f"- Method A: `{summary['method_a']}`",
        f"- Method B: `{summary['method_b']}`",
        "",
        "## Pairwise Summary",
        f"- Cell rows: `{summary['n_cells']}`",
        f"- Cells with BH-FDR q < 0.05: `{summary['n_q_lt_0_05']}`",
        f"- Cells with uncorrected p < 0.05: `{summary['n_p_lt_0_05']}`",
        f"- Cells where B beats A (median delta < 0): `{summary['n_b_better']}`",
        f"- Cells where A beats B (median delta > 0): `{summary['n_a_better']}`",
        f"- Median of cell medians (B-A): `{summary['median_of_cell_median_delta_b_minus_a']}`",
        "",
        "## Interpretation",
        "- `median_delta_b_minus_a < 0` means method B is better in that cell.",
        "- Pairwise significance is two-sided Wilcoxon with BH-FDR correction across cells.",
        "",
        "## Top Cells (B Better)",
    ]

    for row in summary["top_b_better_cells"]:
        lines.append(
            f"- `{row['function']}` d={row['dimension']} noise={row['noise_sigma']}: "
            f"median(B-A)={row['median_delta_b_minus_a']}, p={row['wilcoxon_p_two_sided']}, q={row['bh_fdr_q_value']}"
        )

    lines.append("")
    lines.append("## Top Cells (A Better)")
    for row in summary["top_a_better_cells"]:
        lines.append(
            f"- `{row['function']}` d={row['dimension']} noise={row['noise_sigma']}: "
            f"median(B-A)={row['median_delta_b_minus_a']}, p={row['wilcoxon_p_two_sided']}, q={row['bh_fdr_q_value']}"
        )

    lines.append("")
    lines.append("## Artifact Links")
    for key in ["pairwise_csv", "pairwise_json"]:
        lines.append(f"- `{key}`: `{summary[key]}`")
    return "\n".join(lines) + "\n"


def generate_pairwise_artifacts(
    runs_csv: str | Path,
    method_a: str,
    method_b: str,
    outdir: str | Path,
    output_prefix: str = "pairwise_pwlr_vs_lr",
    phase: str = "eval",
    analysis_manifest_path: str | Path | None = None,
    manifest_json_path: str | Path | None = None,
) -> dict[str, str]:
    out_path = ensure_dir(outdir)
    runs_path = Path(runs_csv)
    runs_df = pd.read_csv(runs_path)

    pairwise_df = compute_pairwise_cell_stats(
        runs_df=runs_df,
        method_a=method_a,
        method_b=method_b,
        phase=phase,
    )

    csv_path = out_path / f"{output_prefix}.csv"
    json_path = out_path / f"{output_prefix}.json"
    findings_md_path = out_path / "findings_ablation.md"
    save_csv(csv_path, pairwise_df)

    run_id = "unknown"
    if manifest_json_path:
        manifest = load_json(manifest_json_path)
        run_id = str(manifest.get("run_id", "unknown"))

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "phase": phase,
        "method_a": method_a,
        "method_b": method_b,
        "n_cells": int(len(pairwise_df)),
        "n_q_lt_0_05": int((pairwise_df["bh_fdr_q_value"] < 0.05).sum()) if not pairwise_df.empty else 0,
        "n_p_lt_0_05": int((pairwise_df["wilcoxon_p_two_sided"] < 0.05).sum()) if not pairwise_df.empty else 0,
        "n_b_better": int((pairwise_df["median_delta_b_minus_a"] < 0.0).sum()) if not pairwise_df.empty else 0,
        "n_a_better": int((pairwise_df["median_delta_b_minus_a"] > 0.0).sum()) if not pairwise_df.empty else 0,
        "median_of_cell_median_delta_b_minus_a": (
            float(pairwise_df["median_delta_b_minus_a"].median()) if not pairwise_df.empty else float("nan")
        ),
        "delta_quantiles_b_minus_a": _quantiles(pairwise_df["median_delta_b_minus_a"]) if not pairwise_df.empty else {},
        "top_b_better_cells": _top_rows(pairwise_df, ascending=True),
        "top_a_better_cells": _top_rows(pairwise_df, ascending=False),
        "pairwise_csv": str(csv_path),
        "pairwise_json": str(json_path),
    }
    save_json(json_path, summary)
    findings_md_path.write_text(_build_findings_ablation_markdown(summary), encoding="utf-8")

    if analysis_manifest_path:
        analysis_manifest = load_json(analysis_manifest_path)
        files = dict(analysis_manifest.get("files", {}))
        files[f"{output_prefix}_csv"] = str(csv_path)
        files[f"{output_prefix}_json"] = str(json_path)
        if output_prefix == "pairwise_pwlr_vs_lr":
            files["pairwise_pwlr_vs_lr_csv"] = str(csv_path)
            files["pairwise_pwlr_vs_lr_json"] = str(json_path)
            files["findings_ablation_md"] = str(findings_md_path)
        analysis_manifest["files"] = files
        analysis_manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(analysis_manifest_path, analysis_manifest)

    return {
        "pairwise_csv": str(csv_path),
        "pairwise_json": str(json_path),
        "findings_ablation_md": str(findings_md_path),
    }


def main() -> None:
    args = parse_pairwise_args()
    outputs = generate_pairwise_artifacts(
        runs_csv=args.runs,
        method_a=args.method_a,
        method_b=args.method_b,
        outdir=args.outdir,
        output_prefix=args.output_prefix,
        phase=args.phase,
        analysis_manifest_path=args.analysis_manifest,
        manifest_json_path=args.manifest_json,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
