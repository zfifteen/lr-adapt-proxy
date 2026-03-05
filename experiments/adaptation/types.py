from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


@dataclass(frozen=True)
class AdaptationContext:
    fitness: np.ndarray
    generation_index: int
    current_value: float
    direction: Literal["minimize", "maximize"] = "minimize"


@dataclass(frozen=True)
class AdaptationAction:
    next_value: float
    factor: float
    was_clamped: bool


@dataclass(frozen=True)
class AdaptationStep:
    action: AdaptationAction
    diagnostics: dict[str, float]
