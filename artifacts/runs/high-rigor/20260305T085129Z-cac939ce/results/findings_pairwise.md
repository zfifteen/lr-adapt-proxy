# Pairwise Findings

## Run Identity
- Run ID: `20260305T085129Z-cac939ce`
- Created (UTC): `2026-03-05T08:52:37.485528+00:00`
- Phase: `eval`
- Method A: `vanilla_cma`
- Method B: `lr_adapt_proxy`

## Pairwise Summary
- Cell rows: `36`
- Cells with BH-FDR q < 0.05: `35`
- Cells with uncorrected p < 0.05: `35`
- Cells where B beats A (median delta < 0): `21`
- Cells where A beats B (median delta > 0): `15`
- Median of cell medians (B-A): `-18.872088786790762`

## Interpretation
- `median_delta_b_minus_a < 0` means method B is better in that cell.
- Pairwise significance is two-sided Wilcoxon with BH-FDR correction across cells.

## Top Cells (B Better)
- `ellipsoid_cond1e6` d=40 noise=0.1: median(B-A)=-620317.4553029037, p=4.266322730718234e-18, q=2.1941088329408057e-17
- `ellipsoid_cond1e6` d=40 noise=0.0: median(B-A)=-620317.3470573493, p=4.266322730718234e-18, q=2.1941088329408057e-17
- `ellipsoid_cond1e6` d=40 noise=0.2: median(B-A)=-620317.0468367639, p=4.266322730718234e-18, q=2.1941088329408057e-17
- `ellipsoid_cond1e6` d=20 noise=0.1: median(B-A)=-37674.74856099834, p=3.4412810293497968e-15, q=8.849008361185191e-15
- `ellipsoid_cond1e6` d=20 noise=0.2: median(B-A)=-37674.65207957549, p=3.1686412518635367e-15, q=8.77469885131441e-15

## Top Cells (A Better)
- `rosenbrock` d=20 noise=0.0: median(B-A)=28.988317206678627, p=4.0973322370456585e-05, q=5.9001584213457484e-05
- `rosenbrock` d=20 noise=0.2: median(B-A)=28.174663946019255, p=2.172993678852733e-05, q=3.401207497334713e-05
- `rosenbrock` d=20 noise=0.1: median(B-A)=27.940058249224588, p=1.2418346489695002e-05, q=2.032093061950091e-05
- `rosenbrock` d=10 noise=0.0: median(B-A)=2.1667428996053584, p=2.8586825773647623e-05, q=4.2880238660471434e-05
- `rosenbrock` d=10 noise=0.1: median(B-A)=2.0156707156372624, p=0.00015334083624479915, q=0.00020445444832639886

## Artifact Links
- `pairwise_csv`: `artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/pairwise_lr_vs_vanilla.csv`
- `pairwise_json`: `artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/pairwise_lr_vs_vanilla.json`
