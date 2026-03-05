# AWF Mechanism Sweep Interpretation Memo (March 5, 2026)

## Plain-Language Takeaway
We ran the full mechanism-proof experiment to test whether `lr_adapt_proxy` wins or loses mainly because it gets trapped at the step-size floor too early. The short answer is: that floor dynamic is real, measurable, and important, but it is not the whole story.

The new telemetry confirms that some variants spend a very large part of the run clamped at the floor, while others stay adaptive much longer. That shift changes outcomes in predictable ways for some problem families, especially low-dimensional Sphere and Rosenbrock. But high projected AWF by itself is not a guaranteed improvement rule. Some high-AWF variants were excellent, and some were clearly bad.

So the mechanism claim has moved from "plausible" to "partially proven": the primary switch is floor depth, and occupancy metrics are the downstream readout of that switch.

## Executive Summary
1. The experiment executed successfully at full scale: **108,000/108,000 runs completed with status `ok`**.
2. Hybrid telemetry worked exactly as designed: **21,600 traced proxy runs** (about **2.16M generation rows**) and complete run-level floor metrics for all proxy runs.
3. Pre-registered checks came out mixed but informative:
   - **P1: not supported globally**.
   - **P2: supported** (and not falsified under the defined check).
   - **P3: supported strongly**.
4. The strongest practical pattern was not "increase AWF at all costs." It was "avoid aggressive floor regime (`r_min=0.20`), and prefer low floor (`r_min=0.05`) with moderate down-step (`k_down` roughly 0.90 to 0.95)."
5. This materially changes next-step design: we should treat **floor depth as the mechanism lever** and **regime occupancy metrics as the measurement layer**, not rely on projected AWF alone.

## 1) What Was Run
- Sweep config: `awf_mechanism_proof.yaml`.
- Comparator methods: `vanilla_cma`, `lr_adapt_proxy`.
- Variants: **15 total**.
  - Geometry arm: 12 variants (`k_down x r_min`).
  - Threshold-control arm: 3 variants (`snr_down/snr_up`) at baseline geometry.
- Matrix: 4 functions x 3 dimensions x 3 noise levels.
- Seeds: 100 eval seeds.
- Total jobs: `15 x 36 x 100 x 2 = 108,000`.

## 2) Data Integrity and Telemetry Validation
### 2.1 Run health
- Total rows in `sensitivity_runs_long.csv`: **108,000**.
- Status distribution: **108,000 `ok`**, zero failures.
- Method split: **54,000 proxy**, **54,000 vanilla**.

### 2.2 Hybrid trace sampling contract
Trace policy was: trace all proxy runs in target function/dimension pairs `{sphere 10/20, rosenbrock 10/20}` OR any proxy run with `seed % 10 == 0`.

Observed:
- Traced proxy runs: **21,600**.
- Target-pair traced runs: **18,000**.
- Non-target, seed-sampled traced runs: **3,600**.
- Unexpected traces: **0**.
- Missed target traces: **0**.

### 2.3 Backward-compatible endpoint diagnostics retained
For baseline geometry variant `geom_k090_r010`, endpoint diagnostics match prior findings:
- `proxy_sigma_factor_last` counts: `0.90: 2795`, `1.00: 664`, `1.03: 141`.
- `proxy_ema_snr_last` quantiles: median `0.0174`, p75 `0.0723`, p90 `0.1606`.

This confirms continuity with earlier evidence while adding richer floor telemetry.

## 3) Primary Findings
### 3.1 Hypothesis checks (pre-registered)
From `awf_hypothesis_checks.json`:

| Check | Outcome | Interpretation |
|---|---:|---|
| P1 | Not supported | High-AWF geometry variants did not all satisfy the 9/12 target-cell improvement rule. |
| P2 | Supported | In high-AWF geometry variants, ellipsoid d40 cells moved in the expected "less-negative" direction versus baseline. |
| P3 | Supported | Adding floor-time features improved predictive fit beyond endpoint SNR-only features. |

P3 quantitative details:
- `delta_aic = 1872.75`
- `delta_bic = 1837.16`
- `proxy_fraction_at_floor p-value = 2.92e-92`
- modeled rows: `54,000`

Interpretation: floor dynamics carry substantial predictive signal that endpoint SNR alone misses.

### 3.2 Performance shape across variants
Top and bottom variants by `median_of_cell_median_delta`:

| Rank slice | Variant | Group | Median cell delta | Mean win rate |
|---|---|---|---:|---:|
| Best | `geom_k093_r005` | geometry | `-44.341` | `0.603` |
| 2 | `geom_k095_r005` | geometry | `-42.236` | `0.589` |
| 3 | `geom_k090_r005` | geometry | `-42.054` | `0.612` |
| Baseline geometry | `geom_k090_r010` | geometry | `-18.872` | `0.505` |
| Worst | `geom_k090_r020` | geometry | `+5.806` | `0.299` |

Interpretation:
- Dropping floor ratio from `0.10` to `0.05` was the strongest positive move in this sweep.
- Raising floor ratio to `0.20` was consistently damaging.

### 3.3 Why significance count alone is misleading
`cells_q_lt_0_05` stayed high even in poor variants. Example:
- `geom_k090_r020` has **31 significant cells**, but sign split is **6 better / 25 worse**.
- `geom_k093_r005` has **29 significant cells**, sign split **21 better / 8 worse**.

Interpretation: with 100 seeds per cell, many differences become significant in either direction. You must inspect sign and effect direction, not only q-count.

### 3.4 Floor telemetry behavior by variant
Selected overall floor metrics:

| Variant | Mean time to first floor (gen) | Mean fraction at floor | Mean down-steps | Mean up-steps |
|---|---:|---:|---:|---:|
| `geom_k090_r010` (baseline) | 55.31 | 0.402 | 45.66 | 11.68 |
| `geom_k093_r005` (best overall) | 76.86 | 0.209 | 35.94 | 13.96 |
| `geom_k095_r005` | 80.80 | 0.176 | 38.15 | 12.75 |
| `geom_k097_r020` (bad) | 49.32 | 0.477 | 63.20 | 6.84 |
| `thctl_012_030` | 48.19 | 0.481 | 57.28 | 9.00 |
| `thctl_016_035` | 43.18 | 0.536 | 65.59 | 6.94 |

Interpretation:
- Better-performing geometry variants in this run generally delayed floor arrival and reduced floor occupancy.
- Threshold-only controls could still drive heavy floor occupancy despite unchanged projected geometry, showing that realized dynamics depend on policy firing behavior, not just projected AWF constants.

### 3.5 Geometry proxy (projected AWF) versus realized floor dynamics
Across geometry variants:
- Correlation(`awf_projected`, mean time-to-first-floor) was strongly positive (`rho ≈ +0.697`, `p ≈ 0.0118`).
- Correlation(`awf_projected`, mean fraction-at-floor) was strongly negative (`rho ≈ -0.697`, `p ≈ 0.0118`).

But projected AWF had weak relationship to aggregate performance by itself:
- Correlation with median aggregate delta was weak/non-significant in this sweep.

Interpretation: projected AWF is a good design-time predictor for floor timing/occupancy, but not a complete predictor of net performance.

### 3.6 Target-cell behavior (P1 details)
For high-AWF geometry variants (`awf_projected >= 0.45`), P1 improvement counts vs baseline (`sphere d10/d20`, `rosenbrock d10/d20`, all noise levels):

| Variant | AWF | Improved target cells | Pass (>=9/12) |
|---|---:|---:|---:|
| `geom_k095_r005` | 0.59 | 12/12 | Yes |
| `geom_k097_r005` | 0.99 | 12/12 | Yes |
| `geom_k097_r010` | 0.76 | 7/12 | No |
| `geom_k095_r010` | 0.45 | 5/12 | No |
| `geom_k097_r020` | 0.53 | 0/12 | No |

Interpretation: high AWF was not sufficient by itself. Variant structure still matters.

## 4) Human-Readable Interpretation of the Mechanism
The data now supports a refined mechanism statement:

1. **The mechanism is a floor-depth phase transition.**
   - Crossing from low floor depth (`r_min` near `0.05`) to higher floor depth (`r_min` near `0.10` or `0.20`) changes outcome class, not just outcome magnitude.
   - In this run family, low-floor variants can recover target cells across very different shrink tempos, while higher-floor variants fail despite some high projected AWF values.

2. **No, "high AWF" is not a universal good.**
   - Some high-AWF variants improved target cells dramatically.
   - Other high-AWF variants were poor overall.

3. **Regime occupancy is the measurement framework, not the primary mechanism label.**
   - `r_min`, `k_down`, and threshold settings jointly determine how often the policy fires down, up, or neutral.
   - Occupancy metrics (`time_to_first_floor`, `fraction_at_floor`, entries/exits) quantify the downstream state after the phase switch, and they remain critical for diagnosis.

4. **The mechanism discovered through this adapter design is still useful even if discovery was accidental.**
   - This is now an instrumented, testable regime concept, not just a post-hoc story.

## 5) What This Means for CMA-ES Work
For CMA-ES practitioners, this sweep suggests a concrete shift in emphasis:

- Stop treating proxy adaptation quality as mostly an endpoint-SNR problem.
- Treat it as a **phase-switch plus regime-measurement problem** over the full run horizon.
- Optimize for:
  - later and less frequent floor lock-in,
  - controlled down-step pressure,
  - and reversible behavior (ability to leave floor when signal changes).

In this run family, the sweet spot leaned toward lower `r_min` (`0.05`) and moderate `k_down` (`0.90` to `0.95`), not toward the most extreme projected AWF settings.

## 6) Caveats and Threats to Validity
1. The aggregate delta metric is objective-scale dependent, especially visible on Ellipsoid.
2. P3 model support is predictive, not proof of causal sign for each feature coefficient in isolation.
3. High-seed power makes many cells statistically significant; directional interpretation remains essential.
4. This result is scoped to this benchmark matrix and budget (`1000` evals, popsize `10`, 100 generations planned).

## 7) Recommended Next-Step Protocol
1. Run a focused causal follow-up with explicit confound control:
   - Arm A (floor-depth phase test): `r_min in {0.04, 0.05, 0.06, 0.08}` with fixed `k_down = 0.93`.
   - Arm B (threshold test inside low-floor phase): fix `r_min = 0.05` and `k_down = 0.93`, then vary threshold pairs.
2. Add analysis centered on realized occupancy trajectories:
   - first-floor generation distribution,
   - re-entry rates,
   - conditional win rates by occupancy bins.
3. Add a paired-model with variant fixed effects to separate within-variant telemetry effects from between-variant config shifts.
4. Pre-register a hard rejection condition for mechanism claims:
   - if occupancy-controlled models lose predictive advantage over SNR-only models in replicated seed sets, downgrade the mechanism.

## 8) Evidence Sources
All statistics in this memo were computed from the following artifacts:

- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/sensitivity_manifest.json`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/sensitivity_runs_long.csv`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/sensitivity_cell_stats.csv`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/sensitivity_summary.csv`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/awf_variant_metadata.csv`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/awf_floor_summary.csv`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/awf_target_cell_deltas.csv`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/awf_hypothesis_checks.json`

## 9) Bottom Line
This was not garbage noise. The phenomenon is real, measurable, and decision-relevant. The key correction is that the mechanism is **a floor-depth phase transition**, while **regime occupancy is the telemetry framework that reveals it**. That is the actionable model to carry into the next CMA-ES experiment phase.
