# PyO3 0.26 Migration Changelog

## Date: 2025-10-01

### Major Changes

#### PyO3 Version Upgrade
- **From**: PyO3 0.18.3
- **To**: PyO3 0.26.0
- **Impact**: Full Python 3.13 support (including free-threaded build)

### API Migrations (200+ changes)

#### 1. Type System Changes
- **`&PyAny` → `Bound<'_, PyAny>`**: All Python object references now use the new `Bound` smart pointer
- **`PyObject` → `Py<PyAny>`**: Replaced deprecated type alias with explicit `Py<PyAny>`
- **Vec Parameters**: Function signatures changed from `Vec<&PyAny>` to `Vec<Bound<'_, PyAny>>`

#### 2. Method Replacements
- **`Python::allow_threads` → `Python::detach`**: GIL release mechanism updated
- **`downcast()`**: Updated to work with `Bound` types
- **`is_instance_of()` → type checking via `downcast().is_ok()`**: Simplified type checking pattern
- **`dict.get_item()`**: Now returns `PyResult<Option<Bound<PyAny>>>` instead of `Option<&PyAny>`

#### 3. Python Object Creation
- **Boolean**: `PyBool::new(py, value).to_owned().unbind().into()`
- **Integer**: `PyInt::new(py, value).to_owned().unbind().into()`
- **Float**: `PyFloat::new(py, value).to_owned().unbind().into()`
- **String**: `PyString::new(py, value).to_owned().unbind().into()`
- **List**: `PyList::empty(py)` (unchanged)
- **Dict**: `PyDict::new(py)` (unchanged)

#### 4. Module Definition
```rust
// Old (PyO3 0.18)
#[pymodule]
fn _satya(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<StreamValidatorCore>()?;
    Ok(())
}

// New (PyO3 0.26)
#[pymodule]
fn _satya(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<StreamValidatorCore>()?;
    Ok(())
}
```

#### 5. Helper Function Updates
- **`extract_bytes()`**: Changed from returning `&[u8]` to `Vec<u8>` due to lifetime constraints
- **`json_value_to_py()`**: Complete rewrite to use `Bound` API and proper type conversions

### Files Modified

1. **`Cargo.toml`**
   - Updated PyO3 dependency: `0.18.3` → `0.26.0`

2. **`src/lib.rs`** (Major changes)
   - All function signatures updated to use `Bound<'_, PyAny>`
   - GIL management updated to use `Python::detach`
   - Python object creation updated to new API
   - Module definition updated
   - Type checking patterns updated

### Build Instructions

#### For Development (Python 3.13 free-threaded)
```bash
# Set environment variable to allow free-threaded build
export UNSAFE_PYO3_BUILD_FREE_THREADED=1

# Build with maturin
maturin develop --release
```

#### For Standard Python 3.13
```bash
# No special flags needed
maturin develop --release
```

#### For Production (wheels)
```bash
# Build wheels for multiple Python versions
maturin build --release --out dist/
```

### Testing

All existing tests pass with the new PyO3 0.26:
- ✅ Model validation
- ✅ Batch processing
- ✅ Stream validation
- ✅ Nested models
- ✅ Custom types

### Python 3.13 Notes

#### Free-Threaded Build (3.13t)
- PyO3 0.26 supports Python 3.13's free-threaded build with `UNSAFE_PYO3_BUILD_FREE_THREADED=1`
- The GIL is automatically enabled when loading the module (expected behavior)
- Performance is maintained; GIL-free support will come in future PyO3 releases

#### Standard Build (3.13)
- Works out of the box with no special configuration
- Full compatibility with all Satya features

### Performance Impact

**No performance regression** - all optimizations preserved:
- Batch processing remains efficient
- Memory usage unchanged
- Validation speed maintained

### Breaking Changes

**None for Python users** - This is an internal Rust API migration. Python API remains unchanged.

### Migration for Contributors

If you're working on Satya's Rust code:

1. **Update imports**: Add `use pyo3::types::{PyBool, PyFloat, PyInt, PyString};` where needed
2. **Change function signatures**: Replace `&PyAny` with `Bound<'_, PyAny>`
3. **Update GIL operations**: Replace `py.allow_threads()` with `py.detach()`
4. **Fix type conversions**: Use `.to_owned().unbind().into()` pattern for Python object creation
5. **Update dict operations**: Handle `PyResult<Option<Bound<PyAny>>>` from `get_item()`

### References

- [PyO3 0.26 Release Notes](https://pyo3.rs/v0.26.0/)
- [PyO3 Migration Guide](https://pyo3.rs/v0.26.0/migration.html)
- [Python 3.13 Free-Threading PEP 703](https://peps.python.org/pep-0703/)

### Credits

Migration completed by @justrach with assistance from Cascade AI on 2025-10-01.
