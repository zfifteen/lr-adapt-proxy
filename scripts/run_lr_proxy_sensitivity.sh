#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CONFIG_PATH="experiments/config/lr_proxy_sensitivity.yaml"
RUN_ID="${RUN_ID:-}"

if [[ -z "$RUN_ID" ]]; then
  RUN_ID="$(python3 - <<'PY'
import yaml
from experiments.io import make_run_id, stable_config_hash
with open('experiments/config/lr_proxy_sensitivity.yaml', 'r', encoding='utf-8') as fh:
    config = yaml.safe_load(fh)
print(make_run_id(stable_config_hash(config)))
PY
)"
fi

RUN_ROOT="artifacts/runs/lr-proxy-sensitivity/${RUN_ID}"
RESULTS_DIR="${RUN_ROOT}/results"

if [[ -e "$RUN_ROOT" ]]; then
  echo "[lr-proxy-sensitivity] ERROR: run root already exists: $RUN_ROOT" >&2
  exit 1
fi

mkdir -p "$RESULTS_DIR"

python3 -m experiments.sensitivity \
  --config "$CONFIG_PATH" \
  --outdir "$RESULTS_DIR" \
  --run-id "$RUN_ID" \
  "$@"

echo "[lr-proxy-sensitivity] run_id=$RUN_ID"
echo "[lr-proxy-sensitivity] run_root=$RUN_ROOT"
