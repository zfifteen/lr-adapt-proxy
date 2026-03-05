# LR-Adapt Proxy Performance Breakdown (High-Rigor Run)

Run analyzed: `20260305T002116Z-6ae43213`

Artifacts:
- `artifacts/runs/high-rigor/20260305T002116Z-6ae43213/results/lr_proxy_cell_breakdown.csv`
- `artifacts/runs/high-rigor/20260305T002116Z-6ae43213/results/lr_proxy_by_noise.csv`
- `artifacts/runs/high-rigor/20260305T002116Z-6ae43213/results/lr_proxy_by_dimension.csv`
- `artifacts/runs/high-rigor/20260305T002116Z-6ae43213/results/lr_proxy_non_significant_cells.csv`

## By Noise Level
`lr_adapt_proxy` remains favorable across all three noise slices:

| noise_sigma | n_cells | median_of_cell_median_delta | mean_win_rate | cells_q_lt_0_05 |
|---:|---:|---:|---:|---:|
| 0.0 | 12 | -22.661261 | 0.501667 | 11 |
| 0.1 | 12 | -18.292153 | 0.502500 | 11 |
| 0.2 | 12 | -18.165979 | 0.510833 | 12 |

Interpretation: the effect is not limited to the noisy settings; the strongest median cell-level deltas appear at `noise_sigma=0.0` in this run.

## By Dimension (Including 40D)

| dimension | n_cells | median_of_cell_median_delta | mean_win_rate | cells_q_lt_0_05 |
|---:|---:|---:|---:|---:|
| 10 | 12 | -1.659981 | 0.377500 | 12 |
| 20 | 12 | -15.492065 | 0.518333 | 12 |
| 40 | 12 | -55.557329 | 0.619167 | 10 |

40D behavior is strong in magnitude (`median_of_cell_median_delta = -55.557329`), with 10/12 cells passing BH-FDR `q < 0.05`.

## Non-Significant Cells (2/36)
The only non-significant cells for `lr_adapt_proxy` are:

| function | dimension | noise_sigma | median_delta_vs_vanilla | bh_fdr_q_value |
|---|---:|---:|---:|---:|
| rosenbrock | 40 | 0.0 | -62.479059 | 0.073867 |
| rosenbrock | 40 | 0.1 | -67.620092 | 0.050528 |

Both are still directionally favorable (negative median delta), but miss q-threshold after multiplicity correction.

## Function/Dimension/Noise Drivers
The largest cell-level gains and losses are concentrated in `ellipsoid_cond1e6` high-dimension regimes (large-magnitude objective scales), with broad favorable directionality elsewhere. This supports treating aggregate effects with scale awareness and reading alongside per-cell tables.
