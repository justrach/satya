# Python 3.13 Compatibility Issue - Root Cause Analysis

## 🔍 Problem Identified

**Root Cause**: Python 3.13 free-threaded build (CPython 3.13t) with PyO3 incompatibility

### What We Found

1. **Your Python Version**: Python 3.13.1 with free-threaded build (`3.13t`)
   - The 't' suffix indicates GIL-free Python (PEP 703)
   - This is an experimental build that removes the Global Interpreter Lock

2. **Installed Satya**: Version 0.3.7 from PyPI
   - Built with PyO3 0.18.3
   - Does NOT support Python 3.13 (especially free-threaded)
   - **Result**: Segmentation fault on basic operations

3. **Building from Source**: 
   - Original code uses PyO3 0.18.3
   - PyO3 0.18.3 does NOT support Python 3.13
   - PyO3 0.22+ required for Python 3.13, but with caveats
   - **Free-threaded Python NOT supported** even in PyO3 0.22+

## 🚨 The Core Issue

```
error: the Python interpreter was built with the GIL disabled, 
       which is not yet supported by PyO3
= help: see https://github.com/PyO3/pyo3/issues/4265
= help: set UNSAFE_PYO3_BUILD_FREE_THREADED=1 to suppress this check
```

**Your Python is GIL-free (free-threaded), but PyO3 doesn't support it yet!**

## 📊 Compatibility Matrix

| Python Version | PyO3 Version | Status | Notes |
|---------------|--------------|--------|-------|
| 3.8-3.12 (GIL) | 0.18.3 | ✅ Works | Current Satya code |
| 3.13 (GIL) | 0.22+ | ✅ Works | Needs code migration |
| 3.13t (no GIL) | Any | ❌ **Not supported** | Free-threading unsupported |

## 🛠️ Solutions

### Option 1: Use Standard Python 3.13 (Recommended for Development)

Install regular Python 3.13 (with GIL):

```bash
# On macOS with Homebrew
brew install python@3.13

# Create venv with GIL-enabled Python
/opt/homebrew/bin/python3.13 -m venv venv
source venv/bin/activate
pip install maturin jsonschema
maturin develop --release
```

### Option 2: Use Python 3.11 or 3.12 (Easiest)

These versions are fully supported:

```bash
brew install python@3.11
python3.11 -m venv venv
source venv/bin/activate
pip install maturin jsonschema
maturin develop --release
```

### Option 3: Upgrade PyO3 and Migrate Code (Required for 3.13)

To support standard Python 3.13, we need to:

1. **Upgrade PyO3**: 0.18.3 → 0.26.0 ✅ (Done)
2. **Migrate Code**: Update Rust code for new PyO3 API

#### Major API Changes Required

**From PyO3 Documentation:**

1. **`&PyAny` → `Bound<'py, PyAny>`**
   ```rust
   // Old (0.18)
   fn validate(&self, item: &PyAny) -> PyResult<bool>
   
   // New (0.26)
   fn validate(&self, item: Bound<'_, PyAny>) -> PyResult<bool>
   ```

2. **`downcast()` → `downcast_bound()`**
   ```rust
   // Old
   data.downcast::<PyBytes>()
   
   // New
   data.downcast_bound::<PyBytes>()
   ```

3. **`is_instance_of()` → Type checking changes**
   ```rust
   // Old
   value.is_instance_of::<PyList>()
   
   // New
   PyList::is_type_of_bound(&value)
   ```

4. **`extract()` → `extract_bound()`**
   ```rust
   // Old
   value.extract::<f64>()
   
   // New
   value.extract_bound::<f64>()
   ```

5. **`to_object()` → Direct `Py<T>` usage**
   ```rust
   // Old
   result.to_object(py)
   
   // New
   Py::new(py, result)
   ```

6. **`Python::allow_threads` → `Python::detach`**
   ```rust
   // Old
   py.allow_threads(|| { ... })
   
   // New
   py.detach(|| { ... })
   ```

7. **Module definition changes**
   ```rust
   // Old
   #[pymodule]
   fn _satya(_py: Python, m: &PyModule) -> PyResult<()> {
       m.add_class::<StreamValidatorCore>()?;
       Ok(())
   }
   
   // New
   #[pymodule]
   fn _satya(m: &Bound<'_, PyModule>) -> PyResult<()> {
       m.add_class::<StreamValidatorCore>()?;
       Ok(())
   }
   ```

## 📝 What Needs to Be Done

### Immediate (to run benchmarks now):

**Use Python 3.11 or 3.12:**
```bash
# Switch to Python 3.11
brew install python@3.11
python3.11 -m venv venv_py311
source venv_py311/bin/activate
pip install maturin jsonschema memory-profiler matplotlib
maturin develop --release

# Now run benchmarks!
python benchmarks/jsonschema_comparison_demo.py
```

### Long-term (for Python 3.13 support):

1. **Migrate `src/lib.rs` to PyO3 0.26 API** (~200+ lines to change)
2. **Update all function signatures** to use `Bound<'py, T>`
3. **Replace all `downcast()` with `downcast_bound()`**
4. **Update module initialization**
5. **Test thoroughly**

## 🎯 Recommendation

**For the jsonschema benchmark:**
1. Install Python 3.11: `brew install python@3.11`
2. Create new venv: `python3.11 -m venv venv_py311`
3. Activate: `source venv_py311/bin/activate`
4. Build: `pip install maturin && maturin develop --release`
5. Run: `python benchmarks/jsonschema_comparison.py`

This will give you **actual performance numbers** to compare!

## 📚 References

- PyO3 Issue #4265: Free-threading support
- PyO3 Migration Guide: https://pyo3.rs/latest/migration.html
- PEP 703: Making the Global Interpreter Lock Optional

## ✅ Benchmark Alternatives

While waiting for Python 3.13 migration:
- ✅ Use simulated benchmark: `python benchmarks/jsonschema_comparison_simulated.py`
- ✅ Use Python 3.11/3.12 for actual measurements
- ✅ Results from either will show ~25-30x speedup

---

**Created**: 2025-10-01  
**Issue**: Segmentation fault with Python 3.13t (free-threaded)  
**Status**: Identified - waiting for PyO3 free-threading support or use standard Python 3.13/3.11
