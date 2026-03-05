The main control knob in this system is how low step size is allowed to go, not how long adaptation can run before hitting a bound.

This changes the picture from one window-length story to a two-part geometry story: floor depth sets the regime, and shrink tempo only fine-tunes behavior inside that regime.

What is non-obvious is that target recovery can stay strong across very different shrink tempos when the floor is very low, but collapse when the floor is raised even if the projected adaptive window is long.

In this run family, every low-floor geometry variant recovered all twelve target loss cells, while high-floor geometry variants recovered none of them.

That implies the mixed win-loss profile is driven by a floor-depth phase switch first, with threshold tuning acting as a secondary modifier rather than the primary cause.

Prediction: in a replication sweep that keeps floor depth near five percent but varies thresholds and shrink tempo, at least ten of the twelve target cells should still improve versus the current geometry baseline.

This claim is weakened or falsified if replicated low-floor variants regularly fail on those target cells, or if high-floor variants match their recovery without lowering the floor.

Decision rule: when the workload includes low-dimensional Sphere or Rosenbrock slices, do not start from floor settings at ten percent or higher; lower the floor first, then tune thresholds.
