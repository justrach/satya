# ADR-0003: Validation Performance Optimization

## Status
Accepted

## Context
Satya's validation performance had regressed significantly from the expected ~55M items/s to only ~1M items/s, making it uncompetitive with other validation libraries like Pydantic (~2.4M items/s) and msgspec (~10.8M items/s). The performance bottleneck was identified in the Rust core's `validate_value()` function.

## Problem
The `validate_value()` function in `src/lib.rs` was performing expensive Python C-API operations for every field of every validated item:

```rust
// SLOW: Separate type check + downcast
if !value.is_instance_of::<pyo3::types::PyString>()? {
    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string"));
}
let s = value.downcast::<pyo3::types::PyString>()?.to_str()?;
```

For 100k items × 3 fields = 300k Python object operations, each doing:
1. `is_instance_of()` - expensive type checking
2. `downcast()` - type casting 
3. `to_str()` / `extract()` - value extraction

## Decision
Optimize the hot path by eliminating redundant `is_instance_of()` calls and using direct downcasting with pattern matching:

```rust
// FAST: Direct downcast with error handling
let s = match value.downcast::<pyo3::types::PyString>() {
    Ok(py_str) => py_str.to_str()?,
    Err(_) => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string")),
};
```

Applied to both string and numeric validation paths.

## Results
**Performance improvement (100k items):**
- Before: ~1.1M items/s
- After: ~7.7M items/s  
- **7x performance improvement**

**Competitive positioning (5M items, 10-run average):**
- msgspec: 10.8M items/s (1.7x faster than Satya)
- **Satya: 6.4M items/s** (2.7x faster than Pydantic)
- Pydantic: 2.4M items/s

## Consequences
### Positive
- Satya is now competitive with top-tier validation libraries
- Maintains memory efficiency advantage (streaming uses 0.1MB vs 4.3MB for orjson+dict)
- Preserves all existing functionality and API compatibility
- Rust-level optimization with no Python-side changes required

### Negative
- None identified - pure performance improvement

## Implementation Details
- Modified `validate_value()` in `src/lib.rs` lines 551-616
- Eliminated redundant `is_instance_of()` calls for String and Integer/Float types
- Used pattern matching on `downcast()` results for cleaner error handling
- Built with `maturin develop --release` for optimized compilation

## Future Considerations
- Monitor for additional optimization opportunities in the validation pipeline
- Consider vectorized validation for large batches
- Explore SIMD optimizations for constraint checking
