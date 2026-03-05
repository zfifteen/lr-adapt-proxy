from __future__ import annotations

from typing import Protocol

from experiments.adaptation.types import AdaptationContext, AdaptationStep


class AdaptationPolicy(Protocol):
    def step(self, context: AdaptationContext) -> AdaptationStep:
        ...
