# AWF Mechanism One-Pager (March 5, 2026)

## What we tested
We ran a high-rigor mechanism-proof sweep to answer one question: is `lr_adapt_proxy` mostly winning or losing based on how quickly it falls into a sigma-floor regime?

Experiment scope:
- Run root: `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results`
- Total runs: `108000` (`54000` proxy + `54000` vanilla)
- Variants: `15` (`12` geometry + `3` threshold-control)
- Matrix: 4 functions x 3 dimensions x 3 noise levels
- Budget: `1000` evals/run (`100` generations)

## Why this run matters
Earlier analysis suggested early floor dominance was plausible, but telemetry was too thin to prove timing effects. This run added the missing pieces:
- run-level floor metrics for every proxy run
- deterministic hybrid per-generation traces

Trace capture worked exactly as intended:
- traced proxy runs: `21600`
- target cells fully traced: sphere d10/d20 and rosenbrock d10/d20
- extra seed-based sample traces: `seed % 10 == 0`
- no missing target traces, no unexpected traces

## What we found
### 1) The floor mechanism is real and measurable
Floor-time features were strongly predictive of outcomes, even after including endpoint SNR.

P3 check outcome:
- supported
- `delta_aic = 1872.75`
- `delta_bic = 1837.16`
- `proxy_fraction_at_floor p = 2.92e-92`

This is the strongest signal in the run: endpoint SNR alone is not enough to explain proxy behavior.

### 2) “More AWF” is not a complete rule
Pre-registered P1 asked whether every high-AWF geometry variant would improve target loss cells (`sphere d10/d20`, `rosenbrock d10/d20`). It did not hold globally.

P1 outcome:
- not supported globally

High-AWF split was decisive:
- Pass (`12/12` improved): `geom_k095_r005`, `geom_k097_r005`
- Fail (`5/12`, `7/12`, `0/12`): `geom_k095_r010`, `geom_k097_r010`, `geom_k097_r020`

Implication: AWF helps explain regime shifts, but AWF alone does not determine success.

### 3) The worst practical setting in this sweep was high floor ratio
Across geometry variants, `r_min = 0.20` was consistently harmful.

Example:
- `geom_k090_r020`: median cell delta `+5.806` (worse), mean win rate `0.299`

By contrast, low floor ratio variants (`r_min = 0.05`) produced the strongest aggregate outcomes:
- `geom_k093_r005`: median cell delta `-44.341`, mean win rate `0.603`
- `geom_k095_r005`: median cell delta `-42.236`, mean win rate `0.589`
- `geom_k090_r005`: median cell delta `-42.054`, mean win rate `0.612`

### 4) Ellipsoid tradeoff prediction behaved as expected
P2 check asked whether high-AWF geometry settings would soften at least part of extreme ellipsoid d40 advantage.

P2 outcome:
- supported
- not falsified under the pre-registered criterion

This reinforces that geometry changes shift the win/loss balance by family, rather than producing universal gains.

## What changed in our model
Old working story:
- “short adaptive window might be the problem.”

Updated model after this sweep:
- the key control variable is **realized floor-occupancy regime**
- projected geometry (AWF) is useful, but only as a prior
- true behavior depends on interaction among `k_down`, `r_min`, thresholds, and resulting down/up/neutral firing balance

In plain terms: we should tune for how long and how often runs are floor-dominated, not only for endpoint SNR or static threshold values.

## Immediate implications for CMA-ES proxy tuning
1. Treat floor occupancy metrics as first-class diagnostics:
   - `time_to_first_floor`
   - `fraction_at_floor`
   - floor entry/exit counts
2. Avoid `r_min = 0.20` in this benchmark regime unless a narrow, cell-specific reason is demonstrated.
3. Focus next search near:
   - `r_min` around `0.05`
   - `k_down` around `0.90` to `0.95`
4. Keep threshold controls in the loop, but do not use them as a substitute for geometry control.

## Bottom line
This is not noise and not just accidental overfitting. The experiment shows a real, testable, decision-relevant mechanism.

The correction is subtle but important:
- not “maximize AWF”
- but “manage the floor-occupancy regime using geometry plus firing dynamics.”

That is the actionable interpretation to carry into the next CMA-ES experiment phase.

## Evidence paths
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/sensitivity_runs_long.csv`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/sensitivity_cell_stats.csv`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/sensitivity_summary.csv`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/awf_floor_summary.csv`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/awf_hypothesis_checks.json`
- `artifacts/runs/awf-mechanism/20260305T111933Z-awf-mechanism/results/awf_target_cell_deltas.csv`
