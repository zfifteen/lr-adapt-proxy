#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CONFIG_PATH="experiments/config/high_rigor.yaml"
RUN_ID="${RUN_ID:-}"

if [[ -z "$RUN_ID" ]]; then
  RUN_ID="$(python3 - <<'PY'
import yaml
from experiments.io import make_run_id, stable_config_hash
with open('experiments/config/high_rigor.yaml', 'r', encoding='utf-8') as fh:
    config = yaml.safe_load(fh)
print(make_run_id(stable_config_hash(config)))
PY
)"
fi

RUN_ROOT="artifacts/runs/high-rigor/${RUN_ID}"
RESULTS_DIR="${RUN_ROOT}/results"
FIG_DIR="${RUN_ROOT}/figures"

if [[ -e "$RUN_ROOT" ]]; then
  echo "[high-rigor] ERROR: run root already exists: $RUN_ROOT" >&2
  exit 1
fi

mkdir -p "$RESULTS_DIR" "$FIG_DIR"

python3 -m experiments.run \
  --config "$CONFIG_PATH" \
  --outdir "$RESULTS_DIR" \
  --run-id "$RUN_ID" \
  "$@"

python3 -m experiments.analyze \
  --runs "$RESULTS_DIR/runs_long.csv" \
  --outdir "$RESULTS_DIR" \
  --figdir "$FIG_DIR" \
  --phase eval \
  --manifest-json "$RESULTS_DIR/manifest.json"

python3 -m experiments.findings \
  --results-dir "$RESULTS_DIR" \
  --figdir "$FIG_DIR"

python3 -m experiments.pairwise \
  --runs "$RESULTS_DIR/runs_long.csv" \
  --method-a vanilla_cma \
  --method-b lr_adapt_proxy \
  --outdir "$RESULTS_DIR" \
  --output-prefix pairwise_lr_vs_vanilla \
  --phase eval \
  --analysis-manifest "$RESULTS_DIR/analysis_manifest.json" \
  --manifest-json "$RESULTS_DIR/manifest.json"

python3 scripts/verify_rerun_artifacts.py \
  --results-dir "$RESULTS_DIR" \
  --figdir "$FIG_DIR" \
  --config "$CONFIG_PATH" \
  --mode full \
  --require-pairwise

echo "[high-rigor] run_id=$RUN_ID"
echo "[high-rigor] run_root=$RUN_ROOT"
