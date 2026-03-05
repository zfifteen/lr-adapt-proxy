from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CellSpec:
    function: str
    dimension: int
    noise_sigma: float


def objective_value(name: str, x: np.ndarray) -> float:
    d = x.shape[0]
    if name == "sphere":
        return float(np.sum(x**2))
    if name == "rosenbrock":
        return float(np.sum(100.0 * (x[1:] - x[:-1] ** 2) ** 2 + (1.0 - x[:-1]) ** 2))
    if name == "rastrigin":
        return float(10.0 * d + np.sum(x**2 - 10.0 * np.cos(2.0 * np.pi * x)))
    if name == "ellipsoid_cond1e6":
        if d == 1:
            weights = np.array([1.0])
        else:
            exponents = np.arange(d) / float(d - 1)
            weights = (10.0 ** 6) ** exponents
        return float(np.sum(weights * (x**2)))
    raise ValueError(f"Unknown function: {name}")


def noisy_objective(name: str, x: np.ndarray, noise_sigma: float, rng: np.random.Generator) -> float:
    base = objective_value(name, x)
    if noise_sigma <= 0.0:
        return base
    return float(base + rng.normal(0.0, noise_sigma))
