# Run Findings

## Run Identity
- Run ID: `20260305T040341Z-321d79b1-repro`
- Scope: `phasewall_additive_ablation_pwlr_vs_lr`
- Created (UTC): `2026-03-05T04:07:29.841778+00:00`
- Config: `experiments/config/ablation_pwlr_vs_lr.yaml`
- Config Hash: `321d79b14146d30a7b265a00d539d0c73c08299d30b9f7ce11ce501c792ec425`
- Manifest: `artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/results/manifest.json`
- Analysis Manifest: `artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/results/analysis_manifest.json`

## Execution Integrity
- Total runs: `7200`
- OK runs: `7200`
- Failed runs: `0`
- Status by phase:
  - `eval` / `ok`: `7200`

## Tuning Outcomes
- `lr_adapt_proxy` selected strength: `0.0`
- `phasewall_plus_lr_tuned` selected strength: `0.1`

## Statistical Findings
- Cell rows: `0`
- Methods in aggregate: `0`
- Rows with BH-FDR q < 0.05: `0`
- Method ranking (lower median delta is better):

## Caveats
- No cell-level comparisons passed BH-FDR q < 0.05 in this run.
- LR-Adapt comparator is a transparent proxy implementation, not exact Nomura reproduction.
- Findings are run-scoped; treat smoke runs as pipeline-validation evidence, not final inferential evidence.
- Optional figure artifact missing for this run mode: artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/figures/method_median_delta_bar.png
- Optional figure artifact missing for this run mode: artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/figures/method_win_rate_bar.png
- Optional figure artifact missing for this run mode: artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/figures/method_q_lt_005_count_bar.png

## Artifact Links
- `analysis_manifest_json`: `artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/results/analysis_manifest.json`
- `cell_stats_csv`: `artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/results/cell_stats.csv`
- `manifest_json`: `artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/results/manifest.json`
- `method_aggregate_csv`: `artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/results/method_aggregate.csv`
- `runs_long_csv`: `artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/results/runs_long.csv`
- `selected_params_json`: `artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/results/selected_params.json`
- `tuning_summary_csv`: `artifacts/runs/phasewall-ablation/20260305T040341Z-321d79b1-repro/results/tuning_summary.csv`
