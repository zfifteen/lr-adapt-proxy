from __future__ import annotations

from experiments.adaptation.types import AdaptationAction


def apply_sigma_action(es, action: AdaptationAction) -> float:
    es.sigma = float(action.next_value)
    return float(es.sigma)
