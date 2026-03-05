from __future__ import annotations

import json
from pathlib import Path

from experiments.analyze import analyze_runs
from experiments.findings import generate_findings
from experiments.io import parse_smoke_args, save_json
from experiments.run import execute_pipeline


def main() -> None:
    args = parse_smoke_args()

    run_outputs = execute_pipeline(args.config, args.results_dir, args.workers, explicit_run_id=None)
    analysis_outputs = analyze_runs(
        runs_csv=run_outputs["runs_long_csv"],
        outdir=args.results_dir,
        figdir=args.figdir,
        phase="eval",
        manifest_json=run_outputs["manifest_json"],
    )
    findings_outputs = generate_findings(
        results_dir=args.results_dir,
        figdir=args.figdir,
        allow_legacy_run_id=False,
    )

    summary = {
        "run_outputs": run_outputs,
        "analysis_outputs": analysis_outputs,
        "findings_outputs": findings_outputs,
    }
    summary_path = Path(args.results_dir) / "smoke_summary.json"
    save_json(summary_path, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
