# LR-Adapt Proxy Mechanism (Repository-Local)

## Scope
This document describes the repository-local `lr_adapt_proxy` mechanism used in the pycma rerun pipeline. It is intentionally labeled a proxy and is not claimed as an exact reimplementation of external LR-Adapt variants.

Primary implementation references:
- `experiments/lr_adapt_proxy.py` (update rule)
- `experiments/methods.py` (post-`tell` wiring)
- `docs/analysis/rerun_protocol.md` (protocol caveat and evaluation context)

## What Vanilla CMA-ES Does vs What the Proxy Adds
Vanilla CMA-ES (`vanilla_cma`) uses pycma's internal adaptation path in `tell` (mean/covariance/step-size adaptation).

`lr_adapt_proxy` keeps that path intact and adds one explicit post-`tell` adjustment to `es.sigma` each generation:
1. Compute a robust SNR-like signal from current generation fitness.
2. Smooth with EMA.
3. Apply multiplicative sigma up/down factor based on thresholds.
4. Clamp sigma to configured bounds relative to initial sigma.

No direct covariance-matrix equation is replaced by this proxy. The direct write is to `es.sigma`; covariance effects are indirect via subsequent sampling.

## Update Rule
For generation fitness values `f` (minimization):

1. `current_best = min(f)`
2. `signal = max(previous_best - current_best, 0)`
3. `noise = 1.4826 * MAD(f) + 1e-12`
4. `snr = signal / noise`
5. `ema_snr = alpha * snr + (1 - alpha) * ema_snr_prev`
6. Sigma factor selection:
  - if `ema_snr < snr_down_threshold`: `factor = sigma_down_factor`
  - else if `ema_snr > snr_up_threshold`: `factor = sigma_up_factor`
  - else: `factor = 1.0`
7. Apply and clamp:
  - `sigma <- clip(sigma * factor, sigma_min_ratio * sigma0, sigma_max_ratio * sigma0)`

`previous_best` is then updated to `min(previous_best, current_best)`.

## Active Baseline Parameters (High-Rigor / Ablation)
From `experiments/config/high_rigor.yaml` and `experiments/config/ablation_pwlr_vs_lr.yaml`:

| Parameter | Value |
|---|---:|
| `ema_alpha` | `0.2` |
| `snr_down_threshold` | `0.08` |
| `snr_up_threshold` | `0.25` |
| `sigma_down_factor` | `0.90` |
| `sigma_up_factor` | `1.03` |
| `sigma_min_ratio` | `0.10` |
| `sigma_max_ratio` | `10.0` |

These values were carried as explicit config parameters and used as the baseline in the sensitivity sweep.

## Interaction with pycma Internals
- pycma sampling and adaptation (`ask`/`tell`) remain standard.
- Proxy hook executes after `tell` in `experiments/methods.py`, updating only `es.sigma`.
- This means:
  - direct intervention target: step-size scalar
  - indirect downstream effect: altered candidate distribution and therefore future covariance updates

## Auditability Notes
- Each run stores `lr_proxy_params` in job inputs and emits proxy diagnostics in run rows (`proxy_sigma_factor_last`, `proxy_ema_snr_last`).
- All public tables and docs keep the `proxy` label to avoid overclaiming.
