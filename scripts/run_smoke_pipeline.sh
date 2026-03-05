#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

python3 -m experiments.smoke \
  --config experiments/config/smoke.yaml \
  --results-dir artifacts/results/rerun-sample \
  --figdir artifacts/figures/rerun-sample "$@"

python3 scripts/verify_rerun_artifacts.py \
  --results-dir artifacts/results/rerun-sample \
  --figdir artifacts/figures/rerun-sample \
  --config experiments/config/smoke.yaml \
  --require-smoke-summary
