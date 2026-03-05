## `lr_adapt_proxy` Extraction Plan (Reviewed and Rewritten)

### Summary
This rewrite aligns with your constraints:
- same pipeline capability as current repo,
- no scope expansion,
- no new tests added,
- no execution now.

The draft had major scope and compatibility gaps (noted below). This plan preserves current behavior by minimizing refactors and carrying the pipeline as-is into the new repo.

### Draft Corrections (Critical)
1. The draft renamed core module/layout (`experiments/*` to `lr_adapt_proxy/*`), which introduces avoidable refactor risk and breaks “same pipeline” parity.
2. The draft omitted required pipeline dependencies and files (`experiments/io.py`, `experiments/findings.py`, `experiments/plots.py`, `experiments/pairwise.py`, `experiments/run_eval_only.py`, `experiments/sensitivity.py`, script wrappers, verifier, configs).
3. The draft dependency list was incomplete (`requirements.txt` with only `cma/numpy/scipy`), but current pipeline requires `pandas`, `matplotlib`, `statsmodels`, `PyYAML`.
4. The draft proposed adding new tests/docs/examples and DOI/release work. That violates the “no scope change / no additional tests” instruction.
5. The draft proposed leaving `phasewall.py` behind. Current high-rigor pipeline depends on PhaseWall comparators, so leaving it behind breaks parity.
6. The draft included updating the source repo. Out of scope for extraction phase.

### Important Interfaces / Contracts to Preserve
1. Preserve CLI/module entrypoints exactly:
- `python3 -m experiments.run`
- `python3 -m experiments.run_eval_only`
- `python3 -m experiments.analyze`
- `python3 -m experiments.findings`
- `python3 -m experiments.pairwise`
- `python3 -m experiments.sensitivity`
- `python3 -m experiments.lr_proxy_breakdown`
- `python3 -m experiments.smoke`
2. Preserve script entrypoints exactly:
- `scripts/run_high_rigor_pipeline.sh`
- `scripts/run_phasewall_ablation_pipeline.sh`
- `scripts/run_lr_proxy_sensitivity.sh`
- `scripts/run_smoke_pipeline.sh`
- `scripts/verify_rerun_artifacts.py`
3. Preserve artifact schema expectations currently enforced by verifier and manifests:
- `manifest.json`, `analysis_manifest.json`, `findings.json`, `findings.md`
- pairwise artifacts
- run-scoped CSV layouts.

### Decision-Complete Migration Plan

#### Phase A (Now): Plan review only
1. Approve this rewritten migration plan.
2. Do not execute extraction.

#### Phase B (After approval): Create repo and copy plan, then stop
1. Create new repo named `lr-adapt-proxy`.
2. Add one file to the new repo root: `MIGRATION_PLAN.md` containing this approved plan.
3. Stop. No code/file migration yet.

#### Phase C (Future execution, not now): Extraction with parity-first strategy
1. Copy pipeline code without structural refactor:
- copy `experiments/` directory in full.
- copy required scripts in full (`run_*` wrappers + verifier + backfill helper).
- copy `requirements-experiments.txt` unchanged.
2. Copy configs in full:
- `experiments/config/high_rigor.yaml`
- `experiments/config/ablation_pwlr_vs_lr.yaml`
- `experiments/config/lr_proxy_sensitivity.yaml`
- `experiments/config/smoke.yaml`
3. Copy analysis docs needed for algorithm context and pipeline usage:
- `docs/analysis/lr_adapt_proxy_technical_spec.md`
- `docs/analysis/lr_adapt_proxy_mechanism.md`
- `docs/analysis/lr_adapt_proxy_breakdown.md`
- `docs/analysis/rerun_protocol.md`
4. Copy reference evidence run directories exactly (including `results/` and `figures/` where present):
- `artifacts/runs/high-rigor/20260305T002116Z-6ae43213/`
- `artifacts/runs/phasewall-ablation/20260305T014110Z-321d79b1/`
- `artifacts/runs/lr-proxy-sensitivity/20260305T012829Z-1a889aa0/`
5. Add a minimal root `README.md` that explains this repo is extracted from `gaussian-hill-surface` and preserves pipeline parity.
6. Do not add any new tests, quickstart scripts, DOI metadata, packaging refactors, or API renames in this migration phase.

### Test Cases and Scenarios (for future execution phase)
1. Dependency parity:
- install from `requirements-experiments.txt` succeeds.
2. CLI parity:
- each preserved `python3 -m experiments.* --help` command runs.
3. Wrapper parity:
- `bash scripts/run_phasewall_ablation_pipeline.sh --workers 8` completes and verifier passes.
- `bash scripts/run_lr_proxy_sensitivity.sh --workers 8` completes and emits expected files.
- optional heavy parity: `bash scripts/run_high_rigor_pipeline.sh --workers 8`.
4. Schema parity:
- `scripts/verify_rerun_artifacts.py` passes in both modes:
  - `--mode full --require-pairwise`
  - `--mode eval_only --require-pairwise`
5. Evidence continuity:
- copied reference artifacts exist at expected paths and are readable by docs/manifests.

### Assumptions and Defaults
1. Repo name default: `lr-adapt-proxy`.
2. Migration strategy default: preserve current file/module layout (`experiments/`, `scripts/`) to avoid scope creep.
3. “Same pipeline” means existing commands, configs, and verifier behavior continue to work without semantic changes.
4. No new tests means no additional test files or test frameworks are introduced in migration.
5. DOI/CITATION/release automation is explicitly deferred to a later phase.
