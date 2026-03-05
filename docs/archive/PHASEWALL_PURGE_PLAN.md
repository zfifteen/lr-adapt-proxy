# Zero-`phasewall` Purge Plan (`lr-adapt-proxy`)

## Summary
Yes, this is achievable for the **current checked-out repository state** (files + paths), and I recommend doing it as a clean-breaking purge.

Your stated constraint is strict: the string `phasewall` must not appear anywhere in this repo.  
Given current state, that requires:

1. removing legacy code/config/scripts tied to PhaseWall,
2. deleting contaminated historical artifacts (they embed `phasewall` in CSV/JSON/paths),
3. regenerating clean artifacts with updated schemas and method sets,
4. validating with repo-wide string/path scans.

Per your instruction, this plan is for later execution and should be placed in the repo root as a plan file before implementation.

## Important Changes / Interfaces
This is a **breaking cleanup** of interfaces.

### Removed components
1. Script: `scripts/run_phasewall_ablation_pipeline.sh`
2. Module: `experiments/phasewall.py`
3. Config: `experiments/config/ablation_pwlr_vs_lr.yaml`
4. Run family directory: `artifacts/runs/phasewall-ablation/`

### Method set changes
1. Remove methods:
   - `phasewall_tuned`
   - `phasewall_plus_lr_tuned`
2. Keep methods:
   - `vanilla_cma`
   - `lr_adapt_proxy`
   - `pop4x` (default retained)

### Schema changes (remove `phasewall` tokens from outputs)
In all generated run tables/manifests:
1. Remove `phasewall_strength`
2. Remove `phasewall_mean_scale_last`
3. Remove notes/keys containing `phasewall_*`
4. Replace pairwise artifact naming from legacy `pairwise_pwlr_vs_lr*` to neutral:
   - `pairwise_lr_vs_vanilla.csv`
   - `pairwise_lr_vs_vanilla.json`
   - matching keys in `analysis_manifest.json`

## Implementation Plan

## Phase 0 — Plan file only (no code execution yet)
1. Add a root plan file:
   - `PHASEWALL_PURGE_PLAN.md`
2. Copy this full plan into that file.
3. Stop (execution deferred).

## Phase 1 — Purge contaminated tracked artifacts
Reason: current artifacts contain `phasewall` in both paths and content.

1. Delete all contaminated run directories:
   - `artifacts/runs/phasewall-ablation/`
   - `artifacts/runs/high-rigor/` (all existing runs are contaminated by method names/columns)
   - `artifacts/runs/lr-proxy-sensitivity/` (current schema includes `phasewall_*` columns)
2. Recreate empty run roots as needed later by wrappers.

## Phase 2 — Remove legacy code paths
1. Delete `experiments/phasewall.py`
2. Update `experiments/__init__.py` to remove `phasewall` export.
3. Update `experiments/methods.py`:
   - remove PhaseWall import and logic branches,
   - remove PhaseWall methods from `ALL_METHODS`,
   - remove all output/job fields containing `phasewall`.
4. Update `experiments/tuning.py`:
   - remove PhaseWall-specific tuned method constants,
   - make tuning generic/optional or empty when no tuned methods configured,
   - remove `phasewall_strength` field names.
5. Update `experiments/run.py`, `experiments/run_eval_only.py`, `experiments/sensitivity.py`:
   - remove all `phasewall` config and job field references,
   - ensure manifests/notes are clean of the term.
6. Update `scripts/verify_rerun_artifacts.py`:
   - remove hardcoded PhaseWall checks (`config["phasewall"]`, tuned method names),
   - validate new neutral pairwise artifact keys when required.

## Phase 3 — Update scripts/configs/docs
1. Delete `scripts/run_phasewall_ablation_pipeline.sh`
2. Update `scripts/run_high_rigor_pipeline.sh`:
   - pairwise becomes `vanilla_cma` vs `lr_adapt_proxy`,
   - output prefix `pairwise_lr_vs_vanilla`.
3. Update `experiments/config/high_rigor.yaml`:
   - remove PhaseWall methods and `phasewall:` block.
4. Update `experiments/config/smoke.yaml`:
   - same removal as high-rigor.
5. Remove `experiments/config/ablation_pwlr_vs_lr.yaml`
6. Update docs to remove all PhaseWall references:
   - `docs/analysis/rerun_protocol.md`
   - `docs/analysis/lr_adapt_proxy_technical_spec.md`
   - `MIGRATION_PLAN.md` (or replace with updated migration note)

## Phase 4 — Regenerate clean artifacts
1. Run high-rigor pipeline (clean config, no PhaseWall constructs).
2. Run sensitivity pipeline (clean schema).
3. Optional smoke run.
4. Run verifier on produced runs.

## Phase 5 — Final purity gate
Must pass both:
1. Content scan:
```bash
rg -n -i --hidden --glob '!.git' 'phasewall'
```
Expected: no output.
2. Path scan:
```bash
rg --files --hidden --glob '!.git' | rg -i 'phasewall'
```
Expected: no output.

## Test Cases and Scenarios

1. Code-path removal:
   - `python3 -m experiments.run --help` works
   - `python3 -m experiments.sensitivity --help` works
   - no missing imports after deleting `experiments/phasewall.py`
2. Pipeline integrity:
   - high-rigor run completes and verifier passes
   - sensitivity run completes and outputs expected row counts
3. Schema integrity:
   - no output CSV/JSON field names include `phasewall`
4. Purity guarantee:
   - both repo-wide scans return zero matches
5. Regression sanity:
   - pairwise artifacts still generated under neutral names where enabled

## Assumptions and Defaults
1. Scope is **current repo state only** (no git history rewrite).
2. This is a deliberate breaking cleanup for contamination removal.
3. `pop4x` is retained unless explicitly removed later.
4. Historical PhaseWall artifacts are not kept in-repo.
5. Execution is deferred; this turn only defines the plan and plan-file requirement.
