# lr-adapt-proxy

Extracted from `gaussian-hill-surface` to preserve `lr_adapt_proxy` and its benchmark pipeline with parity-first structure.

This repository intentionally keeps the existing pipeline layout (`experiments/`, `scripts/`, run artifacts) to maintain command and schema compatibility during migration.

Primary docs:
- `docs/analysis/lr_adapt_proxy_technical_spec.md`
- `docs/analysis/rerun_protocol.md`

Active wrappers:
- `scripts/run_high_rigor_pipeline.sh`
- `scripts/run_eval_only_lr_vs_vanilla.sh`
- `scripts/run_lr_proxy_sensitivity.sh`
- `scripts/run_smoke_pipeline.sh`

Active configs:
- `experiments/config/high_rigor.yaml`
- `experiments/config/eval_only_lr_vs_vanilla.yaml`
- `experiments/config/lr_proxy_sensitivity.yaml`
- `experiments/config/smoke.yaml`

Migration/archive note:
- `docs/archive/MIGRATION_PLAN.md`
