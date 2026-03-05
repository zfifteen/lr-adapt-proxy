# LR-Proxy Sensitivity Findings

- Run ID: `20260305T060340Z-1a889aa0`
- Output root: `artifacts/runs/lr-proxy-sensitivity/20260305T060340Z-1a889aa0/results`

## Headline
- Best variant: `sigma_clamp_0.05_20.0` with median_of_cell_median_delta=`-42.053864412274585` and cells_q_lt_0_05=`30`.
- Worst variant: `sigma_clamp_0.2_5.0` with median_of_cell_median_delta=`5.806193522986625` and cells_q_lt_0_05=`31`.
- Baseline variant: median_of_cell_median_delta=`-18.87208878679077`, cells_q_lt_0_05=`35`.

## Top Variants
- `sigma_clamp_0.05_20.0` (sigma_clamp): median_delta=`-42.053864412274585`, win_rate=`0.6116666666666666`, q<0.05 cells=`30`
- `ema_alpha_0.4` (ema_alpha): median_delta=`-20.696409056762793`, win_rate=`0.5219444444444443`, q<0.05 cells=`32`
- `sigma_factors_0.85_1.05` (sigma_factors): median_delta=`-19.43905436166877`, win_rate=`0.48444444444444446`, q<0.05 cells=`33`
- `baseline` (baseline): median_delta=`-18.87208878679077`, win_rate=`0.505`, q<0.05 cells=`35`
- `thresholds_0.12_0.3` (snr_thresholds): median_delta=`-18.141109603508557`, win_rate=`0.5216666666666668`, q<0.05 cells=`36`

## Bottom Variants
- `thresholds_0.12_0.3` (snr_thresholds): median_delta=`-18.141109603508557`, win_rate=`0.5216666666666668`, q<0.05 cells=`36`
- `ema_alpha_0.1` (ema_alpha): median_delta=`-15.146783226973717`, win_rate=`0.49027777777777776`, q<0.05 cells=`30`
- `thresholds_0.05_0.2` (snr_thresholds): median_delta=`-7.010586499624814`, win_rate=`0.4888888888888888`, q<0.05 cells=`33`
- `sigma_factors_0.95_1.02` (sigma_factors): median_delta=`-2.744581747774073`, win_rate=`0.4952777777777777`, q<0.05 cells=`33`
- `sigma_clamp_0.2_5.0` (sigma_clamp): median_delta=`5.806193522986625`, win_rate=`0.2986111111111111`, q<0.05 cells=`31`
