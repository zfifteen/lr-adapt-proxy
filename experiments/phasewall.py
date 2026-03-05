from __future__ import annotations

import numpy as np


def phasewall_radius(dimension: int) -> float:
    return float(np.sqrt(max(dimension - 2.0 / 3.0, 1e-12)))


def damp_candidates_with_phasewall(es, candidates: np.ndarray, strength: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Scale candidate displacements according to PhaseWall in whitened space.

    We compute the Mahalanobis radius of each candidate relative to the current
    CMA-ES mean and covariance, then apply scalar radial damping to candidates
    beyond r0. Scaling displacement in phenotype space by this scalar is
    equivalent to scaling z in whitened space.
    """
    if strength <= 0.0:
        radii = np.zeros(candidates.shape[0], dtype=float)
        scales = np.ones(candidates.shape[0], dtype=float)
        return candidates.copy(), radii, scales

    mean = np.asarray(es.mean, dtype=float)
    sigma = float(es.sigma)
    covariance = np.asarray(es.sm.C, dtype=float)

    centered = (candidates - mean) / max(sigma, 1e-16)
    solved = np.linalg.solve(covariance, centered.T).T
    radii = np.sqrt(np.einsum("ij,ij->i", centered, solved))

    r0 = phasewall_radius(candidates.shape[1])
    scales = np.ones_like(radii)
    outside = radii > r0
    if np.any(outside):
        scales[outside] = 1.0 - strength * (1.0 - r0 / radii[outside])
        scales[outside] = np.clip(scales[outside], 0.0, 1.0)

    damped = mean + (candidates - mean) * scales[:, None]
    return damped, radii, scales
