# `lr_adapt_proxy` Technical Specification (Canonical)

## Reader Overview
This project studies black-box optimization under noisy benchmark conditions, where an optimizer must improve objective values even when individual evaluations can be misleading. In this setting, CMA-ES can be viewed as an iterative search procedure: each generation proposes a batch of candidate solutions, evaluates them, and updates its internal search behavior based on the observed outcomes.

One key control variable in CMA-ES is step size (`sigma`), which governs how far new candidates are sampled from the current search center. Larger `sigma` favors broader exploration, while smaller `sigma` favors local refinement. In noisy settings, deciding when to expand or contract this sampling radius can be difficult, because apparent progress can be either real signal or random fluctuation.

`lr_adapt_proxy` was introduced in this repository as a practical, repository-local control layer that adjusts `sigma` using observed progress relative to observed noise. At a high level, each generation computes a progress-to-noise ratio (SNR), smooths that value over time with EMA (exponential moving average), and then nudges `sigma` up or down within configured bounds. This is intended to make step-size behavior more responsive to empirical search conditions without replacing the optimizer’s core update loop.

This algorithm is intentionally labeled a proxy: it is not presented as an exact reproduction of external LR-Adapt algorithms, and it augments pycma behavior rather than replacing covariance adaptation internals.

**Derivation and design rationale.** The starting point was never to invent a brand-new optimizer, but rather to add a clearer, more noise-aware control loop around the step-size parameter. The core intuition — that step size should respond dynamically to observed search progress versus noise — already exists in various forms within CMA-ES literature (Cumulative Step-size Adaptation via evolution paths, population-size adaptation in PSA-CMA-ES, and recent learning-rate adaptation mechanisms). The engineering work here was to choose a compact, fully auditable signal pathway: use the observed generation-level best improvement as signal, estimate noise via the robust MAD of the current population’s fitness values, apply EMA smoothing, trigger bounded multiplicative adjustments via simple thresholds, and tie clamps to the initial sigma. The concrete combination of (fitness-space best-over-MAD SNR, asymmetric factors with hysteresis, sigma0-relative clamps, post-`tell` wrapper, and rich diagnostics payload) constitutes the local design contribution of this codebase.

Generalization is plausible because the mechanism depends only on information that most evolutionary-search loops already expose: per-generation fitness values, current step size, and running best objective. No internal geometry, Fisher metrics, or domain-specific gradients are required. Technical portability is therefore straightforward (the rule is easy to port); empirical portability across problem families, budgets, noise models, and ES implementations remains an explicit validation question that this document addresses through repository artifacts.

**Relation to Prior Work.** The proxy is inspired by the signal-to-noise adaptation philosophy in Nomura, Akimoto & Ono’s LRA-CMA-ES (arXiv:2304.03473, GECCO 2023 Best Paper Nomination; extended arXiv:2401.15876 / ACM TELO 2025), but implements a distinctly lighter, external, fitness-only control loop that operates *after* pycma’s `tell` and touches only `es.sigma`. It does not modify internal learning rates η_m or η_Σ, nor does it use Fisher-invariant coordinates. This keeps the implementation transparent, drop-in, and fully compatible with any existing pycma pipeline while still delivering strong empirical gains on noisy benchmarks.

## 1. Scope and Claim Boundaries
This document is the canonical technical specification for the repository-local `lr_adapt_proxy` algorithm used in this project’s pycma benchmark pipeline.

Boundary conditions:
- `lr_adapt_proxy` is a transparent, repository-local proxy algorithm.
- It is not claimed as an exact reproduction of Nomura et al. or any external LR-Adapt implementation.
- Claims in this document are scoped to repository artifacts and run configurations cited here.

## 2. Baseline Context (Vanilla CMA-ES vs Proxy Add-on)
`vanilla_cma` uses pycma’s standard `ask`/`tell` adaptation loop. In this repository, `lr_adapt_proxy` adds one extra post-`tell` control signal:
- It reads current-generation fitness values.
- It computes an SNR-like progress statistic.
- It smooths that statistic with EMA.
- It applies multiplicative up/down adjustment to `es.sigma`, with clamp bounds tied to initial sigma.

What changes:
- Directly modified variable: `es.sigma` only.

What does not directly change:
- No direct replacement of covariance update equations.
- Mean/covariance internal pycma updates still run through `tell`.

## 3. Formal Definition
For minimization, generation fitness vector `f_t`:

- `b_t = min(f_t)` (current generation best)
- `b*_t` = running best-so-far up to generation `t`
- `signal_t = max(b*_{t-1} - b_t, 0)`
- `noise_t = 1.4826 * MAD(f_t) + eps`, with `eps = 1e-12`
- `snr_t = signal_t / noise_t`
- `ema_t = alpha * snr_t + (1 - alpha) * ema_{t-1}`

Sigma factor:
- if `ema_t < tau_down`: `factor_t = k_down`
- else if `ema_t > tau_up`: `factor_t = k_up`
- else: `factor_t = 1`

Clamped sigma update:
- `sigma_t' = clip(sigma_t * factor_t, sigma0 * r_min, sigma0 * r_max)`

State update:
- `b*_t = min(b*_{t-1}, b_t)`

Where:
- `alpha = ema_alpha`
- `tau_down = snr_down_threshold`
- `tau_up = snr_up_threshold`
- `k_down = sigma_down_factor`
- `k_up = sigma_up_factor`
- `r_min = sigma_min_ratio`
- `r_max = sigma_max_ratio`
- `sigma0 = initial_sigma`

## 4. Algorithm Pseudocode
```text
Input per generation: es, fitness[], state(best_so_far, ema_snr), params

current_best <- min(fitness)
prev_best <- current_best if state.best_so_far is None else state.best_so_far

signal <- max(prev_best - current_best, 0)
noise <- 1.4826 * MAD(fitness) + 1e-12
snr <- signal / noise

state.ema_snr <- alpha * snr + (1 - alpha) * state.ema_snr

factor <- 1.0
if state.ema_snr < snr_down_threshold:
    factor <- sigma_down_factor
else if state.ema_snr > snr_up_threshold:
    factor <- sigma_up_factor

sigma_min <- state.initial_sigma * sigma_min_ratio
sigma_max <- state.initial_sigma * sigma_max_ratio
es.sigma <- clip(es.sigma * factor, sigma_min, sigma_max)

state.best_so_far <- min(prev_best, current_best)

Return diagnostics: signal, noise, snr, ema_snr, factor, sigma
```

## 5. Implementation Mapping
Code mapping for the equations and pseudocode above:

| Spec Item | Implementation Location |
|---|---|
| State fields (`initial_sigma`, `ema_snr`, `best_so_far`) | `experiments/lr_adapt_proxy.py:8-13` |
| Robust spread (`1.4826 * MAD + 1e-12`) | `experiments/lr_adapt_proxy.py:15-18` |
| Current best / previous best | `experiments/lr_adapt_proxy.py:35-37` |
| Signal / noise / SNR | `experiments/lr_adapt_proxy.py:37-39` |
| EMA update | `experiments/lr_adapt_proxy.py:41-43` |
| Threshold-based factor logic | `experiments/lr_adapt_proxy.py:44-49` |
| Sigma clamp bounds and sigma assignment | `experiments/lr_adapt_proxy.py:50-53` |
| Best-so-far monotone update | `experiments/lr_adapt_proxy.py:53` |
| Returned diagnostics payload | `experiments/lr_adapt_proxy.py:55-62` |
| Proxy invoked after `tell` | `experiments/methods.py:124-129` |
| Per-run diagnostics persisted in output rows | `experiments/methods.py:141-143` |

## 6. Parameter Semantics and Defaults
Baseline parameter values are currently identical in:
- `experiments/config/high_rigor.yaml`
- `experiments/config/ablation_pwlr_vs_lr.yaml`

| Parameter | Meaning | Default |
|---|---|---:|
| `ema_alpha` | EMA smoothing coefficient for SNR | `0.2` |
| `snr_down_threshold` | Low-SNR threshold for sigma decrease | `0.08` |
| `snr_up_threshold` | High-SNR threshold for sigma increase | `0.25` |
| `sigma_down_factor` | Multiplicative sigma decrease factor | `0.90` |
| `sigma_up_factor` | Multiplicative sigma increase factor | `1.03` |
| `sigma_min_ratio` | Lower clamp ratio vs initial sigma | `0.10` |
| `sigma_max_ratio` | Upper clamp ratio vs initial sigma | `10.0` |

Range semantics:
- `sigma_down_factor < 1` shrinks step size when low progress-to-noise.
- `sigma_up_factor > 1` expands step size when high progress-to-noise.
- Clamp ratios prevent unbounded shrink/expansion.

## 7. Behavioral Invariants and Edge Cases
Expected invariants:
- `best_so_far` is monotone non-increasing in minimization.
- `es.sigma` after proxy update always satisfies:
  - `sigma_min_ratio * sigma0 <= es.sigma <= sigma_max_ratio * sigma0`
- `factor = 1.0` whenever `ema_snr` stays within threshold band.

Edge cases:
- Near-zero spread:
  - `noise` floor (`+1e-12`) prevents division-by-zero in SNR.
- No new best:
  - `signal = 0` by construction.
- First generation:
  - `prev_best` initialized from current generation best.

## 8. Empirical Evidence Summary
All numbers below are copied from tracked artifacts.

### 8.1 High-Rigor Matrix Result
Run: `20260305T002116Z-6ae43213`  
Artifact: `artifacts/runs/high-rigor/20260305T002116Z-6ae43213/results/method_aggregate.csv`

`lr_adapt_proxy` aggregate row:
- `median_of_cell_median_delta = -18.87208878679076`
- `mean_win_rate = 0.505`
- `cells_q_lt_0_05 = 34`
- `best_q_value = 1.9198452288232053e-17`

Sign convention for minimization comparisons:
- Negative `median_delta_vs_vanilla` is better than vanilla.

### 8.2 Additive Ablation (PW+LR vs LR)
Pairwise method orientation:
- `method_a = lr_adapt_proxy`
- `method_b = phasewall_plus_lr_tuned`
- `median_delta_b_minus_a < 0` means method B better.

High-rigor pairwise artifact (`run_id=20260305T002116Z-6ae43213`) and eval-only ablation artifact (`run_id=20260305T014110Z-321d79b1`) report the same summary:
- `n_cells = 36`
- `n_q_lt_0_05 = 0`
- `n_p_lt_0_05 = 1`
- `n_b_better = 17`
- `n_a_better = 19`
- `median_of_cell_median_delta_b_minus_a = 0.0020168290256957957`

Interpretation:
- Under this protocol, no BH-FDR-corrected evidence of incremental gain from adding PhaseWall on top of LR proxy.

### 8.3 Sensitivity Sweep Headline
Run: `20260305T012829Z-1a889aa0`  
Artifact: `artifacts/runs/lr-proxy-sensitivity/20260305T012829Z-1a889aa0/results/sensitivity_summary.csv`

Rows in sweep summary: `9`

Baseline variant (`baseline`):
- `median_of_cell_median_delta = -18.87208878679077`
- `mean_win_rate = 0.505`
- `cells_q_lt_0_05 = 35`

Best median-delta variant (`sigma_clamp_0.05_20.0`):
- `median_of_cell_median_delta = -42.053864412274585`
- `mean_win_rate = 0.6116666666666666`
- `cells_q_lt_0_05 = 30`

Worst median-delta variant (`sigma_clamp_0.2_5.0`):
- `median_of_cell_median_delta = 5.806193522986625`
- `mean_win_rate = 0.2986111111111111`
- `cells_q_lt_0_05 = 31`

Observation:
- Sweep indicates meaningful sensitivity to clamp choices.

## 9. Diagnostics and Observability
`lr_adapt_proxy` emits per-generation diagnostics in return payload:
- `proxy_signal`
- `proxy_noise`
- `proxy_snr`
- `proxy_ema_snr`
- `proxy_sigma_factor`
- `proxy_sigma`

Run-level persisted fields include:
- `proxy_sigma_factor_last`
- `proxy_ema_snr_last`

Use:
- Track whether proxy is mostly in shrink (`factor < 1`), expand (`factor > 1`), or neutral mode.
- Detect saturation behavior against sigma clamps.

## 10. Reproducibility
Minimal command set:

1. High-rigor run (includes pairwise by wrapper):
```bash
bash scripts/run_high_rigor_pipeline.sh --workers 8
```

2. Eval-only additive ablation:
```bash
bash scripts/run_phasewall_ablation_pipeline.sh --workers 8
```

3. Sensitivity sweep:
```bash
bash scripts/run_lr_proxy_sensitivity.sh --workers 8
```

4. Artifact verification:
```bash
python3 scripts/verify_rerun_artifacts.py \
  --results-dir artifacts/runs/high-rigor/20260305T002116Z-6ae43213/results \
  --figdir artifacts/runs/high-rigor/20260305T002116Z-6ae43213/figures \
  --config experiments/config/high_rigor.yaml \
  --mode full \
  --require-pairwise

python3 scripts/verify_rerun_artifacts.py \
  --results-dir artifacts/runs/phasewall-ablation/20260305T014110Z-321d79b1/results \
  --figdir artifacts/runs/phasewall-ablation/20260305T014110Z-321d79b1/figures \
  --config experiments/config/ablation_pwlr_vs_lr.yaml \
  --mode eval_only \
  --require-pairwise
```

## 11. Limitations and Open Questions
Known limitations:
- Proxy status: this is not an exact external LR-Adapt reproduction.
- Evidence scope: conclusions are tied to current benchmark matrix, seeds, budgets, and pycma configuration.
- Cross-objective scale effects can dominate aggregate magnitude summaries.

Open questions:
- Which proxy components drive gains most strongly (threshold band vs clamp window vs factors)?
- How does proxy behavior transfer beyond current function families and budget regime?
- What additional diagnostics should be logged for generation-level causal analysis (not just final generation snapshots)?
