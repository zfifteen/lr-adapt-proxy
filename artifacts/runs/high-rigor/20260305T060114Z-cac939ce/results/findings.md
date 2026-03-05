# Run Findings

## Run Identity
- Run ID: `20260305T060114Z-cac939ce`
- Scope: `high_rigor_rerun_pipeline`
- Created (UTC): `2026-03-05T06:02:29.479093+00:00`
- Config: `experiments/config/high_rigor.yaml`
- Config Hash: `cac939ced1decbce009884f348425b5725eccf6d35277e9e9e392df139dfc9bb`
- Manifest: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/results/manifest.json`
- Analysis Manifest: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/results/analysis_manifest.json`

## Execution Integrity
- Total runs: `10800`
- OK runs: `10800`
- Failed runs: `0`
- Status by phase:
  - `eval` / `ok`: `10800`

## Tuning Outcomes

## Statistical Findings
- Cell rows: `72`
- Methods in aggregate: `2`
- Rows with BH-FDR q < 0.05: `71`
- Method ranking (lower median delta is better):
  - `lr_adapt_proxy`: median delta `-18.87208878679076`, mean win-rate `0.505`, q<0.05 cells `35`
  - `pop4x`: median delta `58.69544875079048`, mean win-rate `0.0797222222222222`, q<0.05 cells `36`

## Caveats
- LR-Adapt comparator is a transparent proxy implementation, not exact Nomura reproduction.
- Findings are run-scoped; treat smoke runs as pipeline-validation evidence, not final inferential evidence.

## Artifact Links
- `analysis_manifest_json`: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/results/analysis_manifest.json`
- `cell_stats_csv`: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/results/cell_stats.csv`
- `figure_method_delta`: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/figures/method_median_delta_bar.png`
- `figure_method_q_count`: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/figures/method_q_lt_005_count_bar.png`
- `figure_method_win_rate`: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/figures/method_win_rate_bar.png`
- `manifest_json`: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/results/manifest.json`
- `method_aggregate_csv`: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/results/method_aggregate.csv`
- `runs_long_csv`: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/results/runs_long.csv`
- `selected_params_json`: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/results/selected_params.json`
- `tuning_summary_csv`: `artifacts/runs/high-rigor/20260305T060114Z-cac939ce/results/tuning_summary.csv`
