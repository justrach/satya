# ADR-0004: Dynamic Batch Sizing with Heuristics and MAP-Elites

- Status: Accepted
- Date: 2025-08-27
- Owners: Satya Team

## Context

Satya’s throughput and memory usage are strongly affected by batch (buffer) sizing in the Rust validator. Historically, we used static defaults and manual tuning. We want to:

- Increase throughput while decreasing memory usage.
- Adapt to input data characteristics (field count, string sizes, constraint complexity, etc.).
- Avoid brittle per-release hand tuning.

We started with simple heuristics and are introducing a quality-diversity optimization approach (MAP‑Elites) to auto-discover good batch configurations across a diverse set of profiles and reuse these as defaults or hints at runtime.

## Decision

1. Heuristic defaulting remains, but we augment it with offline MAP‑Elites search to learn high-performing batch configurations over representative profiles.
2. We persist results to JSON and add CI tests to ensure tuned configs are never worse than defaults on small samples and remain within a reasonable factor of a baseline (`msgspec`) when available.
3. We provide CLIs to run optimization and to monitor progress and resume from archives.

## Rationale

- MAP‑Elites promotes exploration and maintains a diverse archive of elite (near‑Pareto) solutions across feature dimensions (e.g., field count, avg string length, constraint complexity). This helps avoid overfitting to a single dataset and captures a menu of good batch sizes for different regimes.
- Heuristics bootstrap acceptable performance; MAP‑Elites produces targeted improvements and keeps improving as we run it periodically on wider data.
- Tests protect against regressions and guide safe thresholds in noisy CI environments.

## Scope and Artifacts

- `benchmarks/map_elites_optimizer.py`
  - CLI flags: `--generations`, `--test-size`, `--save-every`, `--archive`, `--results`, `--verbose`, `--seed`, `--no-msgspec`.
  - Progress indicators with ETA at `--verbose 2`.
  - Periodic saving and resumability from `--archive`.
- `tests/test_batch_tuning.py`
  - Regression guard: tuned ≥ default throughput on small samples (median-of-3, 2% tolerance by default; `SATYA_TUNING_STRICT=1` to enforce no-regression).
  - Optional ratio vs msgspec (`SATYA_RATIO_FLOOR`, default 0.001). Skips if `msgspec` not installed.
  - Smoke test: best configs run without errors.
- `pytest.ini`
  - Registers `slow` marker; uses quiet output.

## How It Works

- Profiles: Synthetic profile descriptors (field count, avg string length, constraint complexity, object size) define data generators and validator shapes.
- Individuals: Tunables include `batch_size` and `micro_batch_size` used by the Rust validator API (`validate_batch`).
- Fitness: Items per second (IPS) measured with consistent micro-batching; higher is better. Optional auxiliary baselines (e.g., `msgspec`) for reference.
- Archive: MAP‑Elites grid keyed by profile features maintains best‑known configurations per cell.

## Risks and Mitigations

- Performance variance: Use median-of-3 runs in tests; progress outputs and seeds for reproducibility.
- Overfitting: Maintain diverse profiles; periodically expand dataset profiles; keep heuristic fallback.
- CI instability: 2% tolerance, configurable env flags to tighten/loosen as needed.
- Non-determinism: `--seed` used for reproducible sampling when desired; archive-based resumability.

## Operational Guidance

- Quick smoke (progress + saving):
  ```bash
  python3 benchmarks/map_elites_optimizer.py \
    --generations 2 --test-size 5000 --save-every 1 \
    --verbose 2 --no-msgspec --seed 42 \
    --archive benchmarks/map_elites_archive.json \
    --results benchmarks/map_elites_results.json
  ```

- Long run (self-improvement):
  ```bash
  python3 benchmarks/map_elites_optimizer.py \
    --generations 50 --test-size 100000 --save-every 1 \
    --verbose 2 --seed 123 \
    --archive benchmarks/map_elites_archive.json \
    --results benchmarks/map_elites_results.json
  ```
  Notes:
  - Use `--archive` to resume; the optimizer will load it if present.
  - Increase `--generations` for deeper search; adjust `--test-size` for realism vs runtime.
  - Set `--no-msgspec` if you want to avoid comparing against msgspec during fitness.

- Validating improvements locally:
  ```bash
  pytest -q tests/test_batch_tuning.py
  # Strict mode (no 2% tolerance)
  SATYA_TUNING_STRICT=1 pytest -q tests/test_batch_tuning.py::test_tuned_not_worse_than_default
  # Stronger msgspec floor (if desired)
  SATYA_RATIO_FLOOR=0.05 pytest -q -m slow tests/test_batch_tuning.py::test_ratio_vs_msgspec_optional
  ```

## Future Work

- Online adaptation: Use profile detection at runtime to select batch sizes from the archive (or interpolate), falling back to heuristics.
- Expand features: Include memory pressure and latency as explicit objectives or constraints.
- Real-world corpora: Feed anonymized, representative workloads to better match production distributions.
- Multi-objective: Extend fitness to jointly optimize throughput and memory footprint.

## Consequences

- We now have a principled, extensible path to continuously improve batch sizing.
- CI gains regression protection aligned with realistic variance.
- Engineers can run long MAP‑Elites sessions periodically; artifacts are versioned and testable.
