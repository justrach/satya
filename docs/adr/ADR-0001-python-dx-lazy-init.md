# ADR-0001: Python DX refactor for satya imports and lazy initialization

- Status: Accepted
- Date: 2025-08-26

## Context

We observed friction and fragility in Python import/time-to-first-use due to eager initialization of the PyO3 module and duplication of symbols in `satya/__init__.py`. Issues included:

- Eager importing the Rust extension on `import satya`, causing unnecessary startup work and potential failures before users actually need validation.
- A duplicate `StreamValidator` symbol defined/imported in `__init__.py`, increasing coupling and risk of circular imports.
- Minor DX issues: missing `__version__`, `ValidationError.__str__` formatting, and a schema registration call bug.

This also informed our benchmarking scripts: we want benchmarks to load the installed package (built via `maturin develop`) and not accidentally import from `src/`.

## Decision

- Refactor `src/satya/__init__.py` to:
  - Provide lazy, attribute-level exposure of the primary API via `__getattr__`, notably `StreamValidator` and `StreamValidatorCore`.
  - Remove duplicate `StreamValidator` implementation from `__init__.py`.
  - Provide `__version__` via `importlib.metadata`.
  - Update `Model.validator()` to lazily import `StreamValidator`.
- Fix `ValidationError.__str__` and correct schema registration calls.
- Ensure benchmarks avoid injecting `src/` into `sys.path`; scripts should use the installed package (editable install via `maturin develop`).

## Consequences

- Faster and more reliable `import satya`; Rust extension loads only when actually used.
- Reduced risk of circular imports and symbol duplication.
- Clearer import surface and better package semantics.
- Benchmarks call into the same code users run after installing the package.

## Alternatives Considered

- Keep eager initialization: simpler but worse import-time performance, more failure modes.
- Export everything directly from `__init__`: convenient but increases coupling and circular import risk.

## Notes and References

- Files touched:
  - `src/satya/__init__.py` (lazy `__getattr__`, `__version__`)
  - `src/satya/validator.py` (Python wrapper, primary user API)
- Related memories: "Refactored satya/__init__.py to avoid eager initialization..." (lazy import, version, fixes).
