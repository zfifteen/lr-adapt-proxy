# Run Findings

## Run Identity
- Run ID: `20260305T060239Z-2f5b6f1b`
- Scope: `eval_only_lr_vs_vanilla`
- Created (UTC): `2026-03-05T06:03:36.296959+00:00`
- Config: `experiments/config/eval_only_lr_vs_vanilla.yaml`
- Config Hash: `2f5b6f1bee55d4dbebae8fc5b2daca2c5a0d8a220f41b9fa2841f0542ecef6b2`
- Manifest: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/results/manifest.json`
- Analysis Manifest: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/results/analysis_manifest.json`

## Execution Integrity
- Total runs: `7200`
- OK runs: `7200`
- Failed runs: `0`
- Status by phase:
  - `eval` / `ok`: `7200`

## Tuning Outcomes

## Statistical Findings
- Cell rows: `36`
- Methods in aggregate: `1`
- Rows with BH-FDR q < 0.05: `35`
- Method ranking (lower median delta is better):
  - `lr_adapt_proxy`: median delta `-18.87208878679076`, mean win-rate `0.505`, q<0.05 cells `35`

## Caveats
- LR-Adapt comparator is a transparent proxy implementation, not exact Nomura reproduction.
- Findings are run-scoped; treat smoke runs as pipeline-validation evidence, not final inferential evidence.

## Artifact Links
- `analysis_manifest_json`: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/results/analysis_manifest.json`
- `cell_stats_csv`: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/results/cell_stats.csv`
- `figure_method_delta`: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/figures/method_median_delta_bar.png`
- `figure_method_q_count`: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/figures/method_q_lt_005_count_bar.png`
- `figure_method_win_rate`: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/figures/method_win_rate_bar.png`
- `manifest_json`: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/results/manifest.json`
- `method_aggregate_csv`: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/results/method_aggregate.csv`
- `runs_long_csv`: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/results/runs_long.csv`
- `selected_params_json`: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/results/selected_params.json`
- `tuning_summary_csv`: `artifacts/runs/eval-only-lr-vs-vanilla/20260305T060239Z-2f5b6f1b/results/tuning_summary.csv`
