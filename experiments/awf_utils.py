from __future__ import annotations

import math
from dataclasses import dataclass


HYBRID_TRACE_TARGETS = {
    ("sphere", 10),
    ("sphere", 20),
    ("rosenbrock", 10),
    ("rosenbrock", 20),
}


def projected_n_floor(sigma_min_ratio: float, sigma_down_factor: float) -> float:
    if not (0.0 < sigma_min_ratio < 1.0):
        return math.nan
    if not (0.0 < sigma_down_factor < 1.0):
        return math.nan
    return float(math.ceil(math.log(sigma_min_ratio) / math.log(sigma_down_factor)))


def projected_awf(
    sigma_min_ratio: float,
    sigma_down_factor: float,
    planned_generations: int,
) -> float:
    if planned_generations <= 0:
        return math.nan
    n_floor = projected_n_floor(sigma_min_ratio=sigma_min_ratio, sigma_down_factor=sigma_down_factor)
    if math.isnan(n_floor):
        return math.nan
    return float(n_floor / float(planned_generations))


@dataclass(frozen=True)
class FloorMetrics:
    time_to_first_floor_gen: int
    fraction_at_floor: float
    n_floor_entries: int
    n_floor_exits: int


def summarize_floor_flags(at_floor_flags: list[bool]) -> FloorMetrics:
    if not at_floor_flags:
        return FloorMetrics(
            time_to_first_floor_gen=1,
            fraction_at_floor=0.0,
            n_floor_entries=0,
            n_floor_exits=0,
        )

    first_floor_gen: int | None = None
    entries = 0
    exits = 0
    n_at_floor = 0
    prev = False

    for idx, at_floor in enumerate(at_floor_flags, start=1):
        if at_floor:
            n_at_floor += 1
            if first_floor_gen is None:
                first_floor_gen = idx
        if at_floor and not prev:
            entries += 1
        if prev and not at_floor:
            exits += 1
        prev = at_floor

    if first_floor_gen is None:
        first_floor_gen = len(at_floor_flags) + 1

    return FloorMetrics(
        time_to_first_floor_gen=first_floor_gen,
        fraction_at_floor=float(n_at_floor / float(len(at_floor_flags))),
        n_floor_entries=entries,
        n_floor_exits=exits,
    )


def should_trace_proxy_run(
    function_name: str,
    dimension: int,
    seed: int,
    mode: str,
) -> bool:
    mode_norm = str(mode or "off").strip().lower()
    if mode_norm in {"off", "none", "false", "0"}:
        return False
    if mode_norm in {"all", "full"}:
        return True
    if mode_norm == "hybrid":
        if (str(function_name), int(dimension)) in HYBRID_TRACE_TARGETS:
            return True
        return int(seed) % 10 == 0
    raise ValueError(f"Unsupported proxy trace mode: {mode}")
