# Generalize `lr_adapt_proxy` Into a Framework-Level Adaptation Module (PyCMA Demo Client, Exact Parity)

## Summary
Build a reusable adaptation framework inside this repo, then prove it with one client integration (pycma) that reproduces current `lr_adapt_proxy` behavior exactly under deterministic conditions (`workers=1`).
This remains a decision-complete implementation spec for external peer review.

Round-2 precision updates:
1. Removed redundant `initial_value` from `AdaptationContext`.
2. Converted multi-worker soft-gate parity from qualitative wording to measurable criteria.
3. Split test phases so deterministic parity tests land before runner rewiring.
4. Explicitly defined `direction="maximize"` behavior and hard-gate trace keys.
5. Clarified `was_clamped` surfacing as internal-only in v1.

Round-3 strict polish updates:
1. Pinned soft-gate baseline to a specific run ID and manifest commit.
2. Pinned soft-gate metric provenance to specific artifact file and row filters.
3. Added explicit types for `fitness`, `current_value`, and `AdaptationAction` fields in plan prose.
4. Explicitly documented that pipeline-level parity is intentionally `workers>=1` (not `workers=1`).

Locked decisions for v1:
1. Use repo-relative references only (no absolute local filesystem links).
2. Use a tiered parity contract: deterministic exact parity for `workers=1`; measurable consistency checks for multi-worker runs.
3. No rollback/feature-flag path in v1.

## Scope
1. In scope: internal architecture refactor from hardcoded proxy logic to a generic policy interface with one production client.
2. In scope: preserve current CLI/config behavior and output schemas.
3. In scope: preserve current method names (`vanilla_cma`, `lr_adapt_proxy`, `pop4x`).
4. Out of scope: adding a second optimizer client, changing benchmark matrix, changing inferential methodology, retuning hyperparameters, or revising scientific claims.
5. Out of scope: fallback toggles or dual-path runtime switches for the legacy implementation.

## Current Baseline (to preserve)
1. Current hook is method-specific and runs post-`tell` only for `lr_adapt_proxy` in [experiments/methods.py](experiments/methods.py#L111).
2. Current rule directly mutates `es.sigma` in [experiments/lr_adapt_proxy.py](experiments/lr_adapt_proxy.py#L52).
3. Current diagnostics contract includes `proxy_signal`, `proxy_noise`, `proxy_snr`, `proxy_ema_snr`, `proxy_sigma_factor`, `proxy_sigma` in [experiments/lr_adapt_proxy.py](experiments/lr_adapt_proxy.py#L55).
4. Current run-row contract includes `proxy_sigma_factor_last` and `proxy_ema_snr_last` in [experiments/methods.py](experiments/methods.py#L126).
5. Soft-gate baseline run is pinned to `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/results`.
6. Baseline manifest for that run pins source commit `675b7bd` in `manifest.json`.
7. Baseline config is `experiments/config/high_rigor.yaml`.

## Important API / Interface / Type Changes
1. Add adaptation core package at [experiments/adaptation](experiments/adaptation).
2. Add typed context and action models in [experiments/adaptation/types.py](experiments/adaptation/types.py).
3. Add policy protocol in [experiments/adaptation/protocols.py](experiments/adaptation/protocols.py).
4. Add `LRProxyPolicy` in [experiments/adaptation/policies/lr_proxy.py](experiments/adaptation/policies/lr_proxy.py).
5. Add pycma client adapter in [experiments/adaptation/clients/pycma_sigma.py](experiments/adaptation/clients/pycma_sigma.py).
6. Refactor runner wiring in [experiments/methods.py](experiments/methods.py) to use the policy interface instead of method-specific mutation branches.
7. Keep [experiments/lr_adapt_proxy.py](experiments/lr_adapt_proxy.py) as a backward-compatible shim that delegates to the new policy core while preserving existing function signature and diagnostics keys.

## Parity Definition (Tiered)
1. Step-level parity (`workers=1`, hard gate): generation-by-generation exact equality using Python float `==` on the following keys:
   - `proxy_signal`
   - `proxy_noise`
   - `proxy_snr`
   - `proxy_ema_snr`
   - `proxy_sigma_factor`
   - `proxy_sigma`
2. Run-level parity (`workers=1`, hard gate): exact equality for key run outputs:
   - `final_best`
   - `proxy_sigma_factor_last`
   - `proxy_ema_snr_last`
3. Pipeline-level parity (`workers>=1`, soft gate): measurable consistency checks (byte-identical output is not required). This is intentionally `workers>=1` and not `workers=1`.

CI/review gates:
1. Hard gate: deterministic `workers=1` step-level and run-level parity must pass.
2. Soft gate: multi-worker runs must satisfy all of the following against the pinned baseline:
   - schema is identical for `runs_long.csv`, `cell_stats.csv`, `method_aggregate.csv`, and `findings.json`,
   - sign of `median_of_cell_median_delta` for `lr_adapt_proxy` matches baseline, where value is read from `results/method_aggregate.csv` row `method=lr_adapt_proxy`,
   - `abs(cells_q_lt_0_05_current - cells_q_lt_0_05_baseline) <= 2`, where values are read from `results/method_aggregate.csv` row `method=lr_adapt_proxy`.

## Detailed Interface Spec
1. `LRProxyParams` dataclass in `policies/lr_proxy.py` with existing parameters only: `ema_alpha`, `snr_up_threshold`, `snr_down_threshold`, `sigma_up_factor`, `sigma_down_factor`, `sigma_min_ratio`, `sigma_max_ratio`.
2. `AdaptationContext` dataclass in `types.py` with fields:
   - `fitness: np.ndarray`
   - `generation_index: int` (zero-based, job-scoped)
   - `current_value: float`
   - `direction: Literal["minimize", "maximize"]`
3. `AdaptationAction` dataclass in `types.py` with fields:
   - `next_value: float`
   - `factor: float`
   - `was_clamped: bool`
4. `AdaptationStep` dataclass in `types.py` with fields: `action`, `diagnostics`.
5. `AdaptationPolicy` protocol in `protocols.py` with `step(context: AdaptationContext) -> AdaptationStep`.
6. `LRProxyPolicy` class state fields: `ema_snr`, `best_so_far`, `initial_sigma`.
7. `direction="maximize"` behavior in v1: raise `NotImplementedError` (explicit fail-fast to prevent silent misuse).
8. `initial_value` is intentionally absent from `AdaptationContext`; policy-owned `initial_sigma` is the single source of truth.
9. Diagnostics names returned by `LRProxyPolicy.step` remain exactly: `proxy_signal`, `proxy_noise`, `proxy_snr`, `proxy_ema_snr`, `proxy_sigma_factor`, `proxy_sigma`.
10. Runner output column names remain unchanged, including `proxy_sigma_factor_last` and `proxy_ema_snr_last`.
11. `was_clamped` is internal diagnostic data in v1 and is not persisted to run-level CSV/manifest schema.
12. Strict purity boundary: policy code is pure decision logic and never mutates optimizer internals.

## Data Flow After Refactor
1. Runner builds method descriptor for each `method_name`.
2. For `lr_adapt_proxy`, runner instantiates `LRProxyPolicy(params, initial_sigma)` once per job.
3. Each generation: runner computes fitness via existing objective flow.
4. Runner builds `AdaptationContext` and calls `policy.step(context)` after `es.tell`.
5. Client adapter applies returned action to optimizer state (`es.sigma <- action.next_value`).
6. Runner records last-step diagnostics into existing output fields.
7. Non-adaptive methods (`vanilla_cma`, `pop4x`) bypass policy path and keep current behavior.
8. Boundary rule: policy never receives an optimizer object; only the adapter mutates optimizer state.

## Implementation Phases
1. Phase 1: Add adaptation core types/protocols/policy/client skeletons.
2. Phase 2: Add compatibility shim behavior in [experiments/lr_adapt_proxy.py](experiments/lr_adapt_proxy.py) that forwards to `LRProxyPolicy`.
3. Phase 3a: Add and pass deterministic parity tests (unit + golden trace) against shim path before runner rewiring.
4. Phase 3b: Refactor [experiments/methods.py](experiments/methods.py) to generic policy wiring and remove hardcoded `use_lr` mutation branch.
5. Phase 4: Run post-refactor integration/regression checks (eval-only pipeline checks, verifier checks, schema checks, multi-worker soft-gate checks).
6. Phase 5: Update docs in [docs/analysis/lr_adapt_proxy_technical_spec.md](docs/analysis/lr_adapt_proxy_technical_spec.md), [docs/analysis/lr_adapt_proxy_mechanism.md](docs/analysis/lr_adapt_proxy_mechanism.md), and [README.md](README.md) to reflect finalized architecture and unchanged empirical claims.

## Test Cases and Scenarios
1. Doc-gate check: no absolute local filesystem paths in this plan.
2. Plan lint check: pipeline-level parity line contains `workers>=1` (and not `workers=1`).
3. Baseline pin check: plan contains run ID `20260305T060114Z-cac939ce`, commit `675b7bd`, and config `experiments/config/high_rigor.yaml`.
4. Metric provenance check: soft-gate section names `results/method_aggregate.csv` with row filter `method=lr_adapt_proxy`.
5. Type clarity check: plan explicitly types `fitness`, `current_value`, and `AdaptationAction` fields.
6. Unit: `robust_spread` parity for representative arrays, including near-constant values.
7. Unit: deterministic sequence parity for SNR/EMA/factor/clamp logic across many generations.
8. Unit: first-generation edge case parity (`best_so_far is None` path).
9. Unit: no-improvement path parity (`signal=0`) and clamp-bound saturation behavior.
10. Unit: policy purity guard (no optimizer object passed to policy).
11. Unit: `direction="maximize"` raises `NotImplementedError`.
12. Integration: golden trace parity test (`workers=1`, fixed seed) asserting exact equality for all six trace keys.
13. Integration: single-job run with fixed seed and `workers=1` asserting exact equality for `final_best`, `proxy_sigma_factor_last`, `proxy_ema_snr_last`.
14. Integration: eval-only pipeline on small config to confirm no schema drift in `runs_long.csv`, `cell_stats.csv`, `method_aggregate.csv`, `findings.json`.
15. Integration: verifier pass using existing script [scripts/verify_rerun_artifacts.py](scripts/verify_rerun_artifacts.py).
16. Contract: `was_clamped` available in step diagnostics but absent from persisted run schemas.
17. Regression: ensure `vanilla_cma` and `pop4x` rows are unchanged by adaptation refactor path.
18. Contract: ensure pairwise artifact naming and manifest links remain unchanged.
19. Multi-worker soft gate checks:
   - schema invariance,
   - `median_of_cell_median_delta` sign consistency,
   - `cells_q_lt_0_05` count within ±2 of baseline.

## Acceptance Criteria
1. `PLAN.md` has no unresolved ambiguities identified in round-3 feedback.
2. `PLAN.md` explicitly resolves all round-2 findings:
   - `initial_value` redundancy removed,
   - measurable soft gate added,
   - phase-order contradiction resolved,
   - maximize behavior defined,
   - explicit hard-gate trace keys and `was_clamped` treatment documented.
3. Baseline and metric provenance are explicit enough that implementers cannot choose different references.
4. Type-level expectations for context/action fields are explicit in the plan.
5. Parity section is enforceable and testable (contains numeric/measurable conditions).
6. Existing configs run unchanged, including [experiments/config/high_rigor.yaml](experiments/config/high_rigor.yaml) and [experiments/config/eval_only_lr_vs_vanilla.yaml](experiments/config/eval_only_lr_vs_vanilla.yaml).
7. Output schemas and key names remain identical to baseline.
8. `lr_adapt_proxy` numeric behavior passes deterministic exact parity tests at `workers=1`.
9. Existing wrapper scripts still execute without interface changes.
10. No new scope creep is introduced (still one client, no rollback path).

## Risks and Mitigations
1. Risk: accidental behavior drift while extracting logic.
Mitigation: Phase 3a parity tests are locked and passing before Phase 3b runner refactor; merge is gated on hard parity checks.
2. Risk: over-generalization adds unused abstraction noise.
Mitigation: one concrete protocol, one policy, one client in v1 only.
3. Risk: hidden downstream schema dependency.
Mitigation: run existing verifier and compare key artifact columns/keys as explicit checks in Phase 4.
4. Risk: reviewers assume implied rollback support.
Mitigation: explicit no-fallback stance in v1; failures are fixed in-path rather than via feature flags.
5. Risk: `proxy_*` diagnostic key coupling can be misread as full generality.
Mitigation: treat key naming as intentional v1 compatibility debt; document decoupling as a future generalization step in the architecture note.

## Review Deliverables
1. This plan as review artifact.
2. A short architecture note in repo docs describing policy/context/action model, why pycma is first client, and why `proxy_*` naming remains in v1.
3. A parity matrix table template for reviewers listing each invariant and its test.

## Assumptions and Defaults
1. This revision edits only `PLAN.md` (no code/config changes).
2. Baseline pin uses tracked high-rigor run `20260305T060114Z-cac939ce`, manifest commit `675b7bd`, and config `experiments/config/high_rigor.yaml`.
3. `cells_q_lt_0_05` tolerance default is fixed at ±2 cells for multi-worker soft gate.
4. Soft-gate thresholds are calibrated for the current 36-cell matrix; if matrix size changes, revisit tolerance policy (for example, percentage-based bounds).
5. Default target is exact pycma parity for deterministic `workers=1` runs.
6. Multi-worker parity target is measurable consistency plus schema invariance, not byte-identical outputs.
7. Default API style is pure policy API; mutation remains in client adapter only.
8. Default first client is pycma sigma control only.
9. Default compatibility target is strict for config/CLI/artifact schemas.
10. No fallback/feature-flag path is introduced in v1.
11. v1 intentionally does not implement maximize semantics; fail-fast behavior is preferred over silent behavior.
