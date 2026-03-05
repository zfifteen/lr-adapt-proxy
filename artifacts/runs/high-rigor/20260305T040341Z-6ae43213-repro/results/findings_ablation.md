# Pairwise Ablation Findings

## Run Identity
- Run ID: `20260305T040341Z-6ae43213-repro`
- Created (UTC): `2026-03-05T04:06:28.830080+00:00`
- Phase: `eval`
- Method A: `lr_adapt_proxy`
- Method B: `phasewall_plus_lr_tuned`

## Pairwise Summary
- Cell rows: `36`
- Cells with BH-FDR q < 0.05: `0`
- Cells with uncorrected p < 0.05: `1`
- Cells where B beats A (median delta < 0): `17`
- Cells where A beats B (median delta > 0): `19`
- Median of cell medians (B-A): `0.0020168290256957957`

## Interpretation
- `median_delta_b_minus_a < 0` means method B is better in that cell.
- Pairwise significance is two-sided Wilcoxon with BH-FDR correction across cells.

## Top Cells (B Better)
- `rosenbrock` d=40 noise=0.1: median(B-A)=-56.959199689216405, p=0.21706930167208116, q=0.8802716596954202
- `rosenbrock` d=40 noise=0.0: median(B-A)=-48.0982081603718, p=0.21451884959596101, q=0.8802716596954202
- `rosenbrock` d=40 noise=0.2: median(B-A)=-32.08979929494268, p=0.13563807876829767, q=0.8802716596954202
- `rastrigin` d=40 noise=0.2: median(B-A)=-8.214701010008696, p=0.042148596180625435, q=0.8802716596954202
- `rastrigin` d=40 noise=0.0: median(B-A)=-7.7333835530536135, p=0.1810567539013742, q=0.8802716596954202

## Top Cells (A Better)
- `ellipsoid_cond1e6` d=40 noise=0.2: median(B-A)=4688.3552069317375, p=0.6229452589763703, q=0.8802716596954202
- `ellipsoid_cond1e6` d=40 noise=0.0: median(B-A)=4688.255494505895, p=0.6229452589763703, q=0.8802716596954202
- `ellipsoid_cond1e6` d=40 noise=0.1: median(B-A)=4688.11546345416, p=0.6229452589763703, q=0.8802716596954202
- `ellipsoid_cond1e6` d=20 noise=0.0: median(B-A)=3120.8921916747113, p=0.26972230853401546, q=0.8802716596954202
- `ellipsoid_cond1e6` d=20 noise=0.2: median(B-A)=3120.8713760795144, p=0.2579671879817931, q=0.8802716596954202

## Artifact Links
- `pairwise_csv`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/pairwise_pwlr_vs_lr.csv`
- `pairwise_json`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/pairwise_pwlr_vs_lr.json`
