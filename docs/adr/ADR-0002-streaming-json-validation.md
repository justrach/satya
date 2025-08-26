# ADR-0002: Streaming JSON validation via serde_json Deserializer and custom Visitors

- Status: Accepted
- Date: 2025-08-26

## Context

We needed to validate large JSON payloads efficiently without building full `serde_json::Value` trees. Goals:

- Lower memory footprint via streaming parsing/validation.
- High throughput on large datasets and `ndjson` streams.
- Stay within the `serde_json` ecosystem (no `orjson`).
- Provide Python ergonomics: a single API that toggles streaming.

Constraints:

- Maintain existing schema/type system and constraints in `satya`.
- Support modes: single object, top-level array of objects, and NDJSON.

## Decision

- Implement streaming validation in Rust using `serde_json::Deserializer` with custom `Visitor`s that validate on-the-fly without allocating full `Value`s.
- Add methods in the Rust core (`src/lib.rs`):
  - `validate_json_bytes_streaming(&self, py, data) -> bool`
  - `validate_json_array_bytes_streaming(&self, py, data) -> Vec[bool]` (per-element)
  - `validate_ndjson_bytes_streaming(&self, py, data) -> bool`
- Keep non-streaming counterparts that parse into `serde_json::Value` for feature parity.
- Expose a unified Python API in `src/satya/validator.py`:
  - `StreamValidator.validate_json(data: bytes, mode: {'object','array','ndjson'}, streaming: bool = False)`
- Error handling in streaming mode favors boolean results and avoids expensive error objects. Wrong top-level types raise `ValueError` for clarity.

## Implementation Notes

- Visitors validate fields inline against `FieldValidator` and `FieldConstraints`.
- Top-level array streaming returns a vector of booleans and does not abort on first failure.
- NDJSON is parsed record-by-record from bytes with minimal buffering.
- Some limitations remain: nested custom types within objects are not supported in streaming mode due to deserializer reuse complexity; these cases return a controlled error.
- Added benchmarks to compare dict-path vs JSON-bytes (streaming and non-streaming) across modes:
  - `benchmarks/streaming_validation_benchmark.py` (new): CLI `--items`, `--batch`, `--mode`, `--no-plot`; saves JSON summaries and optional plots.
  - Reused ideas from `benchmarks/simplified_validation_benchmark.py` with lazy plotting (matplotlib imported inside plotting function).

## Consequences

- Significantly lower memory use for large inputs; improved throughput (especially for `array` and `ndjson` modes).
- Simpler Python ergonomics: one method toggles streaming via a flag.
- Streaming path returns booleans for speed; less detailed error reporting compared to non-streaming paths.
- Additional maintenance in Rust for visitor-based validators; some lints pending cleanup.

## Alternatives Considered

- Use `orjson`: fast but adds dependency and diverges from current stack; not adopted.
- Parse full `serde_json::Value` then validate: simpler but higher memory and lower throughput.
- Adopt `simd-json` backend now: promising, but deferred behind an optional Cargo feature for later evaluation.

## References

- Core files:
  - `src/lib.rs` (streaming visitors and methods)
  - `src/satya/validator.py` (`validate_json` streaming flag and mode selection)
- Benchmarks:
  - `benchmarks/streaming_validation_benchmark.py` (new)
  - `benchmarks/simplified_validation_benchmark.py` (lazy plotting; `--no-plot`)
- Tests:
  - `tests/` and repo root tests (`test_simple.py`, `test_basic.py`, etc.)
- Build and DX:
  - Built via `maturin develop --release`
  - Benchmarks import the installed package (no `sys.path` manipulation)

## Status and Next Steps

- Implemented and benchmarked; tests passing.
- TODO: optional `simd-json` feature flag; richer error reporting in streaming mode; lint cleanup in `src/lib.rs`.
