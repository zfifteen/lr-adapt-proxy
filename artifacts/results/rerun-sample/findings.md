# Run Findings

## Run Identity
- Run ID: `20260305T085008Z-b47c25f9`
- Scope: `smoke_rerun_pipeline`
- Created (UTC): `2026-03-05T08:50:12.247438+00:00`
- Config: `experiments/config/smoke.yaml`
- Config Hash: `b47c25f9944f2d02fc86ab77b6038e0f43216e2173add68f66cf34384a57dcdc`
- Manifest: `artifacts/results/rerun-sample/manifest.json`
- Analysis Manifest: `artifacts/results/rerun-sample/analysis_manifest.json`

## Execution Integrity
- Total runs: `1080`
- OK runs: `1080`
- Failed runs: `0`
- Status by phase:
  - `eval` / `ok`: `1080`

## Tuning Outcomes

## Statistical Findings
- Cell rows: `72`
- Methods in aggregate: `2`
- Rows with BH-FDR q < 0.05: `29`
- Method ranking (lower median delta is better):
  - `lr_adapt_proxy`: median delta `-44.34559581418432`, mean win-rate `0.5305555555555557`, q<0.05 cells `2`
  - `pop4x`: median delta `1403.2623011332582`, mean win-rate `0.1166666666666666`, q<0.05 cells `27`

## Caveats
- LR-Adapt comparator is a transparent proxy implementation, not exact Nomura reproduction.
- Findings are run-scoped; treat smoke runs as pipeline-validation evidence, not final inferential evidence.

## Artifact Links
- `analysis_manifest_json`: `artifacts/results/rerun-sample/analysis_manifest.json`
- `cell_stats_csv`: `artifacts/results/rerun-sample/cell_stats.csv`
- `figure_method_delta`: `artifacts/figures/rerun-sample/method_median_delta_bar.png`
- `figure_method_q_count`: `artifacts/figures/rerun-sample/method_q_lt_005_count_bar.png`
- `figure_method_win_rate`: `artifacts/figures/rerun-sample/method_win_rate_bar.png`
- `manifest_json`: `artifacts/results/rerun-sample/manifest.json`
- `method_aggregate_csv`: `artifacts/results/rerun-sample/method_aggregate.csv`
- `runs_long_csv`: `artifacts/results/rerun-sample/runs_long.csv`
- `selected_params_json`: `artifacts/results/rerun-sample/selected_params.json`
- `tuning_summary_csv`: `artifacts/results/rerun-sample/tuning_summary.csv`
