#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.findings import generate_findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill findings artifacts for an existing run directory.")
    parser.add_argument("--results-dir", default="artifacts/results/rerun-sample")
    parser.add_argument("--figdir", default="artifacts/figures/rerun-sample")
    args = parser.parse_args()

    outputs = generate_findings(
        results_dir=args.results_dir,
        figdir=args.figdir,
        allow_legacy_run_id=True,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
