# Run Findings

## Run Identity
- Run ID: `20260305T040341Z-6ae43213-repro`
- Scope: `high_rigor_rerun_pipeline`
- Created (UTC): `2026-03-05T04:06:27.910815+00:00`
- Config: `experiments/config/high_rigor.yaml`
- Config Hash: `6ae43213b9af9bf0cbfb11ff0e17d6ada8f813f080ab58e10a0a48b242d93ddc`
- Manifest: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/manifest.json`
- Analysis Manifest: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/analysis_manifest.json`

## Execution Integrity
- Total runs: `21520`
- OK runs: `21520`
- Failed runs: `0`
- Status by phase:
  - `eval` / `ok`: `18000`
  - `tune_baseline` / `ok`: `320`
  - `tune_candidate` / `ok`: `3200`

## Tuning Outcomes
- `phasewall_plus_lr_tuned` selected strength: `0.1`
- `phasewall_tuned` selected strength: `0.4`

## Statistical Findings
- Cell rows: `144`
- Methods in aggregate: `4`
- Rows with BH-FDR q < 0.05: `105`
- Method ranking (lower median delta is better):
  - `lr_adapt_proxy`: median delta `-18.87208878679076`, mean win-rate `0.505`, q<0.05 cells `34`
  - `phasewall_plus_lr_tuned`: median delta `-18.836873235099056`, mean win-rate `0.5077777777777777`, q<0.05 cells `33`
  - `phasewall_tuned`: median delta `-0.0783689937377419`, mean win-rate `0.5061111111111111`, q<0.05 cells `2`
  - `pop4x`: median delta `58.69544875079048`, mean win-rate `0.0797222222222222`, q<0.05 cells `36`

## Caveats
- LR-Adapt comparator is a transparent proxy implementation, not exact Nomura reproduction.
- Findings are run-scoped; treat smoke runs as pipeline-validation evidence, not final inferential evidence.

## Artifact Links
- `analysis_manifest_json`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/analysis_manifest.json`
- `cell_stats_csv`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/cell_stats.csv`
- `figure_method_delta`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/figures/method_median_delta_bar.png`
- `figure_method_q_count`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/figures/method_q_lt_005_count_bar.png`
- `figure_method_win_rate`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/figures/method_win_rate_bar.png`
- `manifest_json`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/manifest.json`
- `method_aggregate_csv`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/method_aggregate.csv`
- `runs_long_csv`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/runs_long.csv`
- `selected_params_json`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/selected_params.json`
- `tuning_summary_csv`: `artifacts/runs/high-rigor/20260305T040341Z-6ae43213-repro/results/tuning_summary.csv`
