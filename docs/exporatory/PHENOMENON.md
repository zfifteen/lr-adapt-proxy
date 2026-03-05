# When Sigma Hits the Floor Too Early: A Working Explanation for Mixed `lr_adapt_proxy` Results

## Abstract
This paper explains a concrete pattern we observed in the `lr_adapt_proxy` benchmark run: the same controller that produces large improvements on some landscapes also produces consistent losses on others. The central claim is that this is not random instability and not just a threshold-tuning issue. It may be a regime change problem.

In this repository, the proxy modifies only `sigma` after each CMA-ES `tell` step. Under the active high-rigor settings, repeated down-steps can push sigma to its configured lower bound quickly relative to total run length. Once that happens, a large part of the remaining budget is spent in a clamp-dominated state, where behavior is constrained more by bounds than by ongoing adaptation.

The current artifact set strongly supports contraction-prevalent end states and a highly structured win/loss pattern by function family and dimension. It does not yet directly prove early floor-collision timing, because per-generation telemetry is not currently logged in results.

The practical implication is straightforward: we should treat budget-relative adaptive-window length as a first-class tuning variable, alongside SNR thresholds. The paper ends with falsifiable predictions and an experiment design that can confirm or reject this mechanism.

## 1. Why This Paper Exists
The current repository has enough data to motivate a strong mechanism-level hypothesis, but not enough telemetry to declare causality closed. This document is meant to do three things clearly:

1. State what is directly observed in the existing run.
2. Separate inference from measurement.
3. Define a test plan that can disconfirm the hypothesis, not just support it.

The scope here is intentionally bounded to one run family (`20260305T085129Z-cac939ce`) and its associated high-rigor config.

## 2. Background in Plain Language
CMA-ES proposes candidate solutions around a center and updates search behavior each generation. The parameter `sigma` controls search radius. Big `sigma` means broad exploration; small `sigma` means local refinement.

`lr_adapt_proxy` adds an external control loop around this process. It computes a generation-level progress-to-noise score, smooths that score with EMA, and then applies one of three multiplicative actions to `sigma`: down, neutral, or up. The result is clamped between a minimum and maximum ratio relative to initial sigma.

What matters for this paper is that these mechanics can create a practical asymmetry: shrink events accumulate multiplicatively and may hit the lower bound quickly. If that happens early enough, much of the run may become effectively floor-constrained.

## 3. Data Scope and Provenance
All quantitative claims in this document come from the high-rigor artifact set and code/config used to produce it.

- Run ID: `20260305T085129Z-cac939ce`
- Successful runs: `10800 / 10800`
- Methods present: `vanilla_cma`, `lr_adapt_proxy`, `pop4x`
- Matrix: 4 functions x 3 dimensions x 3 noise levels
- Budget: `1000` evals/run, base population `10` (observed run length: `100` generations)

A key limitation of the current artifacts is crucial to keep in mind:

- `runs_long.csv` contains end-of-run proxy fields (`proxy_sigma_factor_last`, `proxy_ema_snr_last`), but not per-generation sigma traces.

That means we can establish endpoint structure very well, but we cannot yet directly measure the exact generation where floor contact first occurs.

## 4. What We Observed
### 4.1 Aggregate picture
For `lr_adapt_proxy` versus `vanilla_cma` in the aggregate summary:

- Median of cell median deltas: `-18.872088786790762`
- Mean win rate: `0.505`
- q-significant cells: `35 / 36`

This is a mixed but strong overall profile, not a uniformly dominant one.

### 4.2 Function-family pattern
The cell-level table shows a stable qualitative split:

- Ellipsoid: large gains across all dimensions/noise levels.
- Rastrigin: consistent gains across all dimensions/noise levels.
- Sphere: losses across all dimensions/noise levels.
- Rosenbrock: losses at d10 and d20, gains at d40.

This split is the main empirical fact that any mechanism must explain.

### 4.3 End-state proxy state is contraction-heavy
Across all proxy runs (`n = 3600`):

- `proxy_sigma_factor_last = 0.90` in `2795` runs
- `proxy_sigma_factor_last = 1.00` in `664` runs
- `proxy_sigma_factor_last = 1.03` in `141` runs

Equivalent proportions:

- Down-state: `77.6%`
- Neutral-state: `18.4%`
- Up-state: `3.9%`

Final EMA-SNR distribution:

- median: `0.017413983708`
- p75: `0.072334577771`
- p90: `0.160600232511`

This does not prove early floor collision, but it is consistent with a contraction-prevalent regime at run end.

### 4.4 Dimension trend and a caution
Raw median deltas by dimension become more negative as dimension increases:

- d10: `-1.659980919799537`
- d20: `-15.492064825446974`
- d40: `-55.55732862291053`

This trend is real in the reported metric, but raw deltas are objective-scale dependent across function families, so they should not be interpreted as directly comparable effect sizes without normalization.

## 5. Mechanism Reconstruction from Code and Config
The active high-rigor proxy parameters are:

- `ema_alpha = 0.2`
- `snr_up_threshold = 0.25`
- `snr_down_threshold = 0.08`
- `sigma_up_factor = 1.03`
- `sigma_down_factor = 0.90`
- `sigma_min_ratio = 0.10`
- `sigma_max_ratio = 10.0`

Given this configuration, a simple geometric calculation gives the shrink events needed to hit the floor ratio:

\[
N_{floor} = \left\lceil \frac{\log(r_{min})}{\log(k_{down})} \right\rceil
= \left\lceil \frac{\log(0.10)}{\log(0.90)} \right\rceil = 22
\]

With observed run length `100` generations, define:

\[
AWF = \frac{N_{floor}}{G} = \frac{22}{100} = 0.22
\]

Interpretation:

- `AWF = 0.22` means floor contact is reachable after roughly one-fifth of the run under repeated down updates.
- This does not say floor contact always happens at generation 22.
- It says the configuration makes early floor arrival feasible on any trajectory that spends many steps in down mode.

## 6. Working Hypothesis
**Hypothesis:** the mixed benchmark behavior is partly explained by a short adaptive window before floor dominance.

In this view, the key variable is not just whether SNR is high or low at the end. The key variable is how much of the run remains unconstrained by the minimum sigma clamp.

If this hypothesis is right, it explains why a single controller can produce opposite outcomes:

- On some landscapes, early aggressive contraction helps quickly enter useful local scales.
- On others, early floor pressure suppresses necessary exploration or anisotropic adaptation time.

## 7. Competing Explanations
A good mechanism must beat alternatives, not just sound plausible.

### A. Threshold mismatch only
Maybe losses are mainly because `tau_up`/`tau_down` are wrong for certain landscapes.

- Prediction: threshold-only retunes should fix target loss cells even if floor geometry is unchanged.

### B. SNR estimator pathology only
Maybe the generation-level signal/noise estimator is fundamentally misaligned for specific landscape classes.

- Prediction: changing estimator form should fix losses even when clamp geometry is unchanged.

### C. Clamp-window dominance (focus)
Maybe budget-relative floor geometry is a primary control variable.

- Prediction: changing only `k_down` and `r_min` (thus AWF), while keeping estimator form fixed, should move outcomes in a structured way.

These explanations are not mutually exclusive. The immediate goal is to identify which one accounts for the largest share of behavior in this pipeline.

## 8. Adversarial Self-Critique
### Objection 1: "This is just step-size saturation"
Fair objection. If true, there is no new mechanism.

Response: the claim here is narrower. It is not "saturation exists." It is that a budget-relative floor-window metric can predict cross-cell outcome direction better than endpoint SNR alone. That is testable.

### Objection 2: "Early floor can be good, so this is not useful"
Also fair. The current data already shows this mixed effect.

Response: usefulness does not require universal harm. It requires a decision boundary that tells us when to preserve contraction versus delay it.

### Objection 3: "Even if true, nothing changes operationally"
If no decision changes, the finding is not worth publishing.

Response: the finding implies a concrete policy gate before runs are launched: reject or modify configurations with projected floor-window below a threshold relative to budget.

## 9. Falsifiable Predictions and Decision Rule
### Prediction 1
If AWF is increased (delaying feasible floor arrival), then sphere d10/d20 and Rosenbrock d10/d20 should improve versus vanilla in median delta and win-rate terms.

### Prediction 2
The same AWF increase should reduce at least part of the extreme ellipsoid d40 advantage.

### Prediction 3
Per-run floor-time features (time-to-first-floor, fraction-at-floor) should explain outcome variance beyond endpoint `proxy_ema_snr_last`.

### Disconfirmation criteria
This mechanism is weakened if any of the following holds under controlled sweeps:

1. Target loss cells do not improve when AWF is increased.
2. Floor-time features provide no explanatory gain over endpoint SNR-only models.
3. Outcome direction is insensitive to AWF changes when estimator form and thresholds are held fixed.

### Decision rule (operational)
Before running large sweeps, compute projected floor-window from config:

- If projected `N_floor / G < 0.33`, switch to gentler contraction (`k_down` closer to 1) and/or lower floor pressure (smaller `r_min`) before evaluation.

This is intentionally a provisional gate, not a universal theorem.

## 10. Dedicated Experiment Design
### 10.1 Objective
Test whether adaptive-window geometry is a primary driver of outcome class.

### 10.2 Required telemetry additions
Add per-generation logging to results:

- `sigma_t`
- `factor_t`
- `was_clamped_t`
- `ema_snr_t`
- `signal_t`
- `noise_t`
- `best_so_far_t`
- `current_best_t`

Without this, timing claims remain indirect.

### 10.3 Factorial sweep
Keep matrix, budget, and seed protocol fixed. Sweep geometry parameters:

- `k_down in {0.90, 0.93, 0.95, 0.97}`
- `r_min in {0.05, 0.10, 0.20}`

Optionally include a threshold-only control sweep to separate geometry effects from threshold effects.

### 10.4 Comparators
- `vanilla_cma`
- `lr_adapt_proxy`
- true LRA comparator (if implementation-compatible in the same pipeline)

### 10.5 Metrics and analysis
Primary metrics:

- time-to-first-floor
- fraction of generations at floor
- floor-exit/recovery events
- per-cell median delta vs vanilla
- per-cell win/loss rates
- BH-FDR-corrected q-values

Modeling:

- cell-wise paired tests for pairwise performance
- regression/ANOVA with interactions: function, dimension, noise, AWF-derived features
- compare SNR-only models vs SNR+floor-time models

### 10.6 Success criteria
- Predicted directional changes appear in predefined target cells.
- Results replicate on at least two independent seed sets.
- Floor-time features add explanatory power over endpoint SNR-only summaries.

## 11. What This Changes in Practice
If this mechanism holds, tuning strategy in this repository should change from:

- "find better SNR thresholds"

to:

- "control the fraction of budget that remains unconstrained by sigma floor, then tune thresholds within that regime."

That is a meaningful workflow change for both experimentation and publication framing.

## 12. Limits and Non-Claims
- This document does not claim SNR-based adaptation is novel.
- This document does not claim universal superiority of `lr_adapt_proxy`.
- This document is scoped to the high-rigor matrix used here.
- Causality for early floor timing remains unproven until per-generation telemetry is added.

## Source Notes (Repo-relative)
R1. `experiments/config/high_rigor.yaml`

R2. `experiments/adaptation/policies/lr_proxy.py`

R3. `artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/findings.md`

R4. `artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/method_aggregate.csv`

R5. `artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/lr_proxy_by_dimension.csv`

R6. `artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/lr_proxy_cell_breakdown.csv`

R7. `artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/runs_long.csv`

R8. `README.md`

## Appendix A: Reproducibility Commands
Run from repository root.

```bash
# Check policy file and params
wc -l experiments/adaptation/policies/lr_proxy.py
sed -n '1,220p' experiments/config/high_rigor.yaml

# Aggregate and cell tables
sed -n '1,80p' artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/method_aggregate.csv
sed -n '1,80p' artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/lr_proxy_by_dimension.csv
sed -n '1,120p' artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/lr_proxy_cell_breakdown.csv

# End-state proxy diagnostics summary
python3 - <<'PY'
import pandas as pd
runs = pd.read_csv('artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/runs_long.csv')
proxy = runs[runs.method == 'lr_adapt_proxy']
print(proxy['proxy_sigma_factor_last'].value_counts().sort_index())
print(proxy['proxy_ema_snr_last'].quantile([0.5, 0.75, 0.9]))
PY

# Floor-window calculation from config values
python3 - <<'PY'
import math
r_min = 0.10
k_down = 0.90
G = 100
N_floor = math.ceil(math.log(r_min) / math.log(k_down))
print('N_floor', N_floor)
print('AWF', N_floor / G)
PY
```
