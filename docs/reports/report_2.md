# Novelty Assessment Report: lr-adapt-proxy

**Report Date**: March 5, 2026  
**Repository**: github.com/zfifteen/lr-adapt-proxy  
**Run Analyzed**: 20260305T085129Z-cac939ce (high-rigor)  
**Author**: Big D' (Dionisio Alberto Lopez III)

***

## Executive Summary

This assessment evaluates the novelty of the `lr-adapt-proxy` implementation against the published LRA-CMA-ES algorithm by Nomura, Akimoto, and Ono (GECCO 2023, ACM TELO 2024). The repository implements a transparent, repository-local proxy adaptation mechanism for CMA-ES sigma control that draws inspiration from LRA-CMA-ES's signal-to-noise ratio philosophy but deliberately diverges in implementation details, scope, and architectural approach.

**Key Novelty Finding**: While the core SNR-based adaptation concept originates from Nomura et al., the lr-adapt-proxy implementation introduces novel contributions in four areas: (1) external policy-adapter architecture, (2) empirical discovery of function-specific failure modes not documented in LRA literature, (3) dimension-dependent performance scaling patterns, and (4) transparent proxy design as a pedagogical and research tool.

***

## 1. Conceptual Lineage and Attribution

### 1.1 Source Material

The repository correctly attributes conceptual inspiration to:
- Nomura, M., Akimoto, Y., & Ono, I. (2023). "CMA-ES with Learning Rate Adaptation: Can CMA-ES with Default Population Size Solve Multimodal and Noisy Problems?" GECCO'23 (arXiv:2304.03473)
- Extended version: "CMA-ES with Learning Rate Adaptation" (arXiv:2401.15876, ACM TELO 2024)

### 1.2 Claimed Scope

The README explicitly states boundary conditions:

> "lr_adapt_proxy is a transparent repository-local proxy algorithm. It is not claimed as an exact reproduction of Nomura et al. or any external LR-Adapt implementation."

This framing positions the work as an educational proxy and experimental platform rather than a faithful reproduction, which is methodologically sound given the architectural differences.

***

## 2. Core Algorithm Comparison

### 2.1 LRA-CMA-ES (Nomura et al.)

The published algorithm adapts **both mean learning rate** (η_m) and **sigma learning rate** (η_Σ) based on SNR estimates:

**Mean SNR**:
```
SNR_mean = (||E_mean||² - (β_m / (2 - β_m)) * V_mean) / 
           (V_mean - ||E_mean||²)
```

**Sigma SNR**:
```
SNR_sigma = (||E_sigma||² - (β_Σ / (2 - β_Σ)) * V_Sigma) / 
            (V_Sigma - ||E_sigma||²)
```

**Learning Rate Adaptation**:
```
relative_SNR = clip((SNR / (α * η)) - 1, -1, 1)
η_next = η * exp(relative_SNR * (β / α))
```

Where:
- E_mean, E_sigma: Expected update directions
- V_mean, V_Sigma: Variance of update directions
- β_m, β_Σ: Cumulation constants
- α: Target SNR (typically 1.5)

### 2.2 lr-adapt-proxy Implementation

The proxy implementation adapts **only sigma** (step size) using a simplified SNR metric:

**Signal**:
```
signal = max(best_so_far - current_best, 0)
```

**Noise** (robust MAD-based spread):
```
noise = 1.4826 * MAD(fitness) + eps
```

**SNR**:
```
snr = signal / noise
```

**EMA Smoothing**:
```
ema_snr = alpha * snr + (1 - alpha) * ema_snr_prev
```

**Sigma Factor** (thresholded multiplicative):
```
if ema_snr < tau_down: factor = k_down
elif ema_snr > tau_up: factor = k_up
else: factor = 1.0
```

**Clamped Update**:
```
sigma_next = clip(sigma_current * factor, sigma0 * r_min, sigma0 * r_max)
```

### 2.3 Comparison Analysis

| Aspect | LRA-CMA-ES | lr-adapt-proxy | Novelty Assessment |
|--------|------------|----------------|-------------------|
| **Adapted variables** | Both η_m and η_Σ (mean + sigma learning rates) | Only sigma (step size) directly | **Different scope** - proxy is narrower |
| **SNR computation** | Uses expected update direction E and variance V from CMA-ES internals | Uses generation-level best-improvement signal and MAD noise | **Novel simplification** - avoids CMA-ES internal state |
| **Update mechanism** | Continuous exponential adaptation via relative SNR | Discrete thresholded multiplicative factors | **Novel design** - simpler control logic |
| **Smoothing** | Implicit in cumulation constants β | Explicit EMA on SNR statistic | **Novel approach** - transparent smoothing |
| **Integration** | Modifies CMA-ES internal update equations | External post-tell mutation of es.sigma | **Novel architecture** - non-invasive overlay |

**Conclusion**: The proxy is conceptually inspired by LRA-CMA-ES but implements a fundamentally different adaptation mechanism with novel architectural properties.

***

## 3. Novel Contributions

### 3.1 Architectural Innovation: Policy-Adapter Pattern

The repository introduces a clean separation between decision logic and optimizer state mutation:

**Policy Layer** (`experiments/adaptation/policies/lr_proxy.py`):
```python
class LRProxyPolicy:
    def step(self, context: AdaptationContext) -> AdaptationStep:
        # Pure decision logic - no optimizer mutation
        # Returns action with diagnostics
```

**Adapter Layer** (`experiments/adaptation/clients/pycma_sigma.py`):
```python
def apply_sigma_action(es: cma.CMAEvolutionStrategy, action: AdaptationAction):
    # Mutates optimizer state
    es.sigma = action.next_value
```

**Novelty**: This architecture is not present in Nomura et al.'s reference implementation, which modifies CMA-ES internals directly. The pattern enables:
- Reusable policy logic across optimizer implementations
- Transparent audit trail of adaptation decisions
- Easy A/B testing of policies without optimizer coupling

### 3.2 Empirical Discovery: Function-Specific Failure Modes

The high-rigor run data reveals three distinct performance regimes not documented in LRA-CMA-ES literature:

#### Sphere Function Catastrophic Failure
- **Observation**: At d=10, noise_sigma=0.0, median delta = +0.018, win rate = 0%
- **Pattern**: Adapter performs worse than baseline on unimodal, symmetric functions
- **Hypothesis**: Uniform gradient structure creates pathological resonance with thresholded sigma updates

#### Rosenbrock Valley Trap
- **Observation**: At d=10-20, median delta = +1.97 to +28.99, loss rates 74-76%
- **Pattern**: Consistent severe losses on curved valley landscapes
- **Hypothesis**: Narrow valley requires tight sigma control; thresholded jumps overshoot

#### Ellipsoid Dominance
- **Observation**: At d=40, median delta = -620,317, win rate = 99%
- **Pattern**: Massive improvement on ill-conditioned quadratic functions
- **Hypothesis**: Noise-aware sigma control exploits elongated valley structure

**Novelty**: Nomura et al. report LRA-CMA-ES improving performance on sphere, rosenbrock, and ellipsoid uniformly. The proxy's function-specific failure modes represent a distinct behavioral signature not present in the source algorithm, suggesting the simplified SNR mechanism and thresholded updates interact differently with landscape geometry.

### 3.3 Dimension-Dependent Scaling Discovery

Cell breakdown analysis reveals performance scales with dimension:

| Dimension | Median Delta | Win Rate | Q<0.05 Cells |
|-----------|--------------|----------|--------------|
| d=10 | -1.66 | 37.75% | 12/12 |
| d=20 | -15.49 | 51.83% | 12/12 |
| d=40 | -55.56 | 61.92% | 11/12 |

**Observation**: Adapter advantage increases super-linearly with dimension, suggesting benefits compound in high-dimensional search spaces while failures are concentrated in low dimensions.

**Novelty**: LRA-CMA-ES papers test up to d=40 but do not report dimension-stratified performance breakdowns. This scaling pattern is a novel empirical finding specific to the proxy mechanism.

### 3.4 Transparent Proxy as Research Tool

The implementation serves as a minimal viable noise-aware step-size controller:
- **178 lines** of core policy logic vs. LRA-CMA-ES's integration with CMA-ES internals
- **6 tunable parameters** with clear semantic meaning
- **Diagnostic telemetry** (`proxy_signal`, `proxy_noise`, `proxy_snr`, `proxy_ema_snr`, `proxy_sigma_factor`) logged per generation

**Novelty**: This pedagogical approach enables researchers to understand SNR-based adaptation without navigating CMA-ES covariance update mechanics. The proxy serves as a "computational microscope" for studying the signal-to-noise adaptation hypothesis in isolation.

***

## 4. What Is NOT Novel

### 4.1 Core Hypothesis
- **Not Novel**: The idea that step size should adapt to maintain constant SNR originates from Nomura et al.
- **Citation Required**: Any claim about SNR-based adaptation principles must cite arXiv:2304.03473

### 4.2 Noise Estimation via MAD
- **Not Novel**: Robust spread estimation using median absolute deviation is standard practice
- **Prior Art**: Used in outlier detection, robust statistics, and noisy optimization broadly

### 4.3 EMA Smoothing
- **Not Novel**: Exponential moving average for signal smoothing is ubiquitous
- **Note**: LRA-CMA-ES uses cumulation constants; proxy uses explicit EMA. Different implementation of same concept.

### 4.4 Thresholded Multiplicative Updates
- **Potentially Novel**: The discrete three-state (down/neutral/up) sigma control based on EMA_SNR thresholds may be original, but requires literature search to confirm no prior use
- **Similar Concept**: Step-size damping in standard CMA-ES uses continuous updates; proxy's thresholded approach is architecturally different

***

## 5. Reproducibility and Verification Gaps

### 5.1 Missing LRA-CMA-ES Baseline

The repository compares against vanilla CMA-ES but **does not include a faithful LRA-CMA-ES implementation** for head-to-head comparison.

**Impact on Novelty Claims**:
- Cannot determine if observed failure modes (sphere, rosenbrock) are artifacts of the proxy simplification or shared with LRA-CMA-ES
- Cannot verify if dimension-scaling pattern holds for Nomura et al.'s algorithm

**Recommendation**: Implement LRA-CMA-ES via `cmaes` library (`lr_adapt=True`) and add as comparator in pipeline.

### 5.2 Parameter Selection Rationale

The proxy uses:
```python
ema_alpha = 0.3
snr_up_threshold = 0.5
snr_down_threshold = 0.05
sigma_up_factor = 1.2
sigma_down_factor = 0.85
sigma_min_ratio = 0.01
sigma_max_ratio = 100.0
```

**Gap**: No documented justification for these values. Were they tuned? Borrowed from LRA-CMA-ES heuristics? Arbitrary?

**Impact**: Without provenance, unclear if proxy performance represents the best achievable with this architecture or just one configuration point.

***

## 6. Prior Art Search

### 6.1 LRA-CMA-ES Variants

**Found**:
- LRA-CMA-ES (Nomura et al., 2023/2024): Mean + sigma learning rate adaptation
- PSA-CMA-ES (Nishida & Akimoto, 2018): Population size adaptation (related concept, different mechanism)
- RA-CMA-ES (Nomura et al., 2024): Reevaluation adaptation for multiplicative noise

**Assessment**: lr-adapt-proxy's external sigma-only control does not directly overlap with these methods.

### 6.2 Step-Size Adaptation Mechanisms

**Known Approaches**:
- CSA (Cumulative Step-size Adaptation): Uses evolution path length (standard in CMA-ES)
- TPA (Two-Point Adaptation): Uses rank changes
- MSR (Median Success Rule): Uses success rate over generations

**Assessment**: Proxy's SNR-based thresholded adaptation is distinct from these mechanisms.

### 6.3 Noise-Aware Optimization

**Broad Field**: Uncertainty handling in black-box optimization includes:
- Resampling / averaging strategies
- Robust ranking methods
- Variance-aware selection

**Specific to CMA-ES**: LRA-CMA-ES is the most closely related noise-aware step-size work.

**Assessment**: Proxy's generation-level SNR + MAD noise estimate is a simplified variant of LRA-CMA-ES approach.

***

## 7. Novelty Classification

| Component | Novelty Level | Justification |
|-----------|---------------|---------------|
| **SNR-based adaptation concept** | **Not Novel** | Core idea from Nomura et al. Must cite. |
| **External policy-adapter architecture** | **Novel** | Not present in LRA-CMA-ES reference code or papers |
| **Sigma-only adaptation (vs. η_m + η_Σ)** | **Novel simplification** | Narrower scope, different trade-offs |
| **Generation-level SNR (signal/noise via MAD)** | **Novel operationalization** | Avoids CMA-ES internals; simpler but less precise |
| **Thresholded 3-state factor updates** | **Likely novel** | Discrete control vs. continuous exponential; no prior art found |
| **Sphere/Rosenbrock failure modes** | **Novel empirical finding** | Not reported in LRA-CMA-ES papers |
| **Dimension-dependent scaling pattern** | **Novel empirical finding** | Not stratified in LRA-CMA-ES results |
| **Transparent proxy research tool** | **Novel contribution** | Pedagogical value + empirical research platform |

***

## 8. Publication Viability Assessment

### 8.1 Strengths
1. **Clean architectural contribution**: Policy-adapter pattern is reusable
2. **Empirical rigor**: 10,800 runs with statistical testing (BH-FDR correction)
3. **Failure mode analysis**: Sphere/rosenbrock losses are scientifically interesting
4. **Dimension scaling**: Super-linear benefit scaling is a novel observation

### 8.2 Weaknesses
1. **No LRA-CMA-ES head-to-head**: Cannot claim superiority, only difference
2. **Parameter tuning unclear**: Were proxy params optimized or arbitrary?
3. **Limited function suite**: 4 functions × 3 noise levels × 3 dimensions = 36 cells
4. **No real-world validation**: All results on synthetic benchmarks

### 8.3 Positioning Options

**Option A: Methods Paper**
- **Title**: "lr-adapt-proxy: An External Step-Size Adaptation Layer for CMA-ES in Noisy Optimization"
- **Venue**: GECCO Workshop, IEEE CEC
- **Angle**: Architectural contribution + empirical characterization
- **Required additions**:
    - LRA-CMA-ES baseline
    - Ablation studies on parameter sensitivity
    - Computational cost analysis

**Option B: Empirical Study**
- **Title**: "Function-Specific Failure Modes in SNR-Based Step-Size Adaptation for CMA-ES"
- **Venue**: Foundations track (GECCO, FOGA)
- **Angle**: Why sphere/rosenbrock fail under simplified SNR control
- **Required additions**:
    - Theoretical analysis of thresholded updates on quadratic functions
    - Visualization of sigma trajectories on failure cases
    - Proposed fixes or hybrid approaches

**Option C: Tool Paper**
- **Title**: "A Transparent Proxy Framework for Studying Noise-Aware Adaptation in Evolution Strategies"
- **Venue**: JMLR-MLOSS, ACM TOMS
- **Angle**: Research tool for community
- **Required additions**:
    - API documentation
    - Tutorial notebooks
    - Extensibility examples (other policies, other optimizers)

***

## 9. Attribution Recommendations

### 9.1 Mandatory Citations

All publications must cite:
```bibtex
@inproceedings{nomura2023cma,
  author = {Nomura, Masahiro and Akimoto, Youhei and Ono, Isao},
  title = {CMA-ES with Learning Rate Adaptation},
  booktitle = {GECCO '23},
  year = {2023},
  doi = {10.1145/3583131.3590358}
}

@article{nomura2024cma,
  title = {CMA-ES with Learning Rate Adaptation},
  author = {Nomura, Masahiro and Akimoto, Youhei and Ono, Isao},
  journal = {ACM Transactions on Evolutionary Learning},
  year = {2024}
}
```

### 9.2 Framing Language

**Recommended**:
> "Inspired by the signal-to-noise ratio adaptation principle introduced by Nomura et al. [citation], we develop a simplified, external proxy mechanism..."

**Avoid**:
> "We propose a novel SNR-based adaptation method..." (implies core concept is original)

***

## 10. Open Questions for Further Investigation

1. **Why does sphere fail catastrophically?** Hypothesis: symmetric gradients + thresholded updates create oscillation. Needs sigma trajectory analysis.

2. **Can hybrid mechanisms rescue rosenbrock?** Potential: combine SNR-based sigma with valley-aware anisotropic scaling.

3. **Is dimension-scaling universal?** Test on d=80, 160 to see if trend continues or saturates.

4. **What is the best achievable proxy configuration?** Current params lack provenance. Grid search or Bayesian optimization needed.

5. **Does gen-20 utilization metric predict final outcomes?** Implement early stopping predictor from previous analysis discussion.

***

## 11. Conclusion

**Novelty Verdict**: The lr-adapt-proxy repository contains **incremental novel contributions** in architecture, empirical characterization, and pedagogical value, built upon the **substantial foundational work** of Nomura et al.'s LRA-CMA-ES.

**Core Contributions**:
1. External policy-adapter architecture for adaptation research
2. Empirical discovery of function-specific failure modes (sphere, rosenbrock)
3. Dimension-dependent performance scaling pattern
4. Transparent proxy tool for studying SNR-based adaptation

**Required Next Steps for Publication**:
1. Add LRA-CMA-ES baseline comparison
2. Document parameter selection rationale or perform tuning study
3. Theoretical analysis of failure modes
4. Expand benchmark suite (more functions, dimensions, noise types)

**Attribution Status**: Repository correctly frames scope and cites Nomura et al. No plagiarism or misattribution detected. Publication-ready from attribution perspective, pending technical expansions above.

***

## Citations

1. [Nomura et al. GECCO'23 arXiv:2304.03473](https://arxiv.org/abs/2304.03473)
2. [Nomura et al. ACM TELO arXiv:2401.15876](https://arxiv.org/abs/2401.15876)
3. [LRA-CMA-ES reference implementation](https://github.com/nomuramasahir0/cma-learning-rate-adaptation)
4. [cmaes library documentation](https://github.com/CyberAgentAILab/cmaes)
5. [lr-adapt-proxy README](https://github.com/zfifteen/lr-adapt-proxy/blob/2e539d1313af1fffd02477a3dc5e3e81ee1f3b8c/README.md)
6. [Cell breakdown analysis](https://github.com/zfifteen/lr-adapt-proxy/blob/2e539d1313af1fffd02477a3dc5e3e81ee1f3b8c/artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/lr_proxy_cell_breakdown.csv)
7. [Dimension stratification](https://github.com/zfifteen/lr-adapt-proxy/blob/2e539d1313af1fffd02477a3dc5e3e81ee1f3b8c/artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/lr_proxy_by_dimension.csv)
8. [Policy implementation](https://github.com/zfifteen/lr-adapt-proxy/blob/2e539d1313af1fffd02477a3dc5e3e81ee1f3b8c/experiments/adaptation/policies/lr_proxy.py)
9. [Run findings](https://github.com/zfifteen/lr-adapt-proxy/blob/2e539d1313af1fffd02477a3dc5e3e81ee1f3b8c/artifacts/runs/high-rigor/20260305T085129Z-cac939ce/results/findings.md)
