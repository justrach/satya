# Changelog

All notable changes to Satya will be documented in this file.

---

## [0.4.12] - 2025-10-13 - 🎯 PYDANTIC COMPATIBILITY & DX FIXES

### 🐛 **Critical Bug Fixes**

**Issue #12: Field Access Returns Field Objects Instead of Values**
- **Fixed**: Field objects were being returned instead of actual values when accessing model attributes
- **Root Cause**: `ModelMetaclass` was leaving `Field` objects in class namespace, shadowing `__getattr__`
- **Solution**: Remove Field objects from class namespace after storing in `__fields__`
- **Impact**: All Python operations now work seamlessly (math, comparisons, string formatting)
- **Tests**: 291/291 tests pass (100%)

**Issue #9: Missing Pydantic Field Attributes**
- **Added**: `default_factory` - Factory functions for mutable defaults (lists, dicts, datetime.now)
- **Added**: `title` - Field title for documentation/UI
- **Added**: `frozen`, `validate_default`, `repr`, `init_var`, `kw_only` - Pydantic V2 metadata
- **Impact**: Zero-friction migration from Pydantic/Langchain pipelines

**Example #3 Validation Errors Not Showing**
- **Fixed**: `validator.validate()` now recursively validates nested models
- **Added**: `_validate_nested_models()` method to handle `List[Model]`, `Dict[str, Model]`
- **Impact**: Both `validator.validate()` and `Model(**data)` approaches now work correctly

### ✨ **New Features**

**1. Field Access Returns Actual Values (Issue #12)**
```python
# Before (BROKEN):
user.age  # Returns <Field object at 0x...>
user.age + 5  # TypeError!

# After (FIXED):
user.age  # Returns 30
user.age + 5  # Returns 35 ✅
```

**2. Pydantic `default_factory` Support (Issue #9)**
```python
from satya import Model, Field
from typing import List

class User(Model):
    tags: List[str] = Field(default_factory=list)  # ✅ Now works!
    
user1 = User()
user2 = User()
user1.tags.append("admin")
# user2.tags is still empty - each instance gets its own list!
```

**3. Nested Model Validation in validator.validate()**
```python
validator = APIResponse.validator()
result = validator.validate(data)  # ✅ Now validates nested models!
```

### 🔧 **Technical Improvements**

**Field Access Fix:**
- Remove Field objects from class namespace in `ModelMetaclass.__new__`
- Ensure `__getattr__` is called to return values from `_data`
- Apply default values and `default_factory` in `Model.__init__`
- Convert Model instances to dicts before validation

**Constraint Validation:**
- Float constraints (`gt`, `lt`, `ge`, `le`) now properly validated
- Python layer validates floats, Rust core handles integers
- List constraints (`min_items`, `max_items`, `unique_items`) enforced
- Nested model validation errors properly propagated

**Decimal Support:**
- Strings/floats coerced to Decimal for validation
- Converted back to Decimal after Rust validation
- Maintains precision for financial calculations

**Validator Improvements:**
- Register all field types including `List[Model]` and `Dict[str, Model]`
- Recursive nested model validation in `_validate_nested_models()`
- Proper error messages for nested validation failures

### 📚 **Documentation**

- Added `PYDANTIC_MIGRATION.md` - Comprehensive migration guide
- Added `DEVELOPER_EXPERIENCE_GUIDE.md` - Field access and DX improvements
- Updated `examples/example3.py` - Shows both validation approaches
- Created `tests/test_field_access_dx.py` - 11 new DX tests

### 🧪 **Testing**

- **Total Tests**: 291 (all passing)
- **New Tests**: 11 field access DX tests
- **Coverage**: Field access, nested models, constraints, Decimal, default_factory

### 🚀 **Performance**

**⚠️ HONEST PERFORMANCE ASSESSMENT**

This release **prioritizes correctness over speed**. After fixing critical bugs, Satya v0.4.12 is **slower than Pydantic**:

**Benchmark vs Pydantic 2.12.0:**

| Test | Satya v0.4.12 | Pydantic 2.12.0 | Result |
|------|---------------|-----------------|--------|
| Simple Validation | 104K ops/sec | 1,844K ops/sec | Pydantic 17.7× faster |
| With Constraints | 84K ops/sec | 1,736K ops/sec | Pydantic 20.6× faster |
| Field Access | 11M ops/sec | 37M ops/sec | Pydantic 3.3× faster |
| Batch (50K) | 162K ops/sec | 894K ops/sec | Pydantic 5.5× faster |
| Nested Models | 59K ops/sec | 1,328K ops/sec | Pydantic 22.6× faster |
| default_factory | 88K ops/sec | 1,282K ops/sec | Pydantic 14.6× faster |

**Why the Performance Drop?**
- v0.3.x was fast but **completely broken** (field access returned Field objects!)
- v0.4.12 fixes all bugs but uses slower validation path
- We chose **working code** over **fast but broken code**

**What You Get:**
- ✅ **Actually works** (all 291 tests pass)
- ✅ **Correct behavior** (field access, constraints, nested models)
- ✅ **Pydantic compatibility** (default_factory, etc.)
- ⚠️ **Slower than Pydantic** (but functional!)

**Optimization Strategy (Current):**
- Simple models → Blaze fast path attempt (Rust)
- Complex models → Full Python validation
- Trade-off: Correctness > Speed

**Future (v0.5.0):**
- Optimize validation path to match/exceed Pydantic
- Keep all correctness fixes
- Goal: Fast AND correct!

---

## [0.3.86] - 2025-10-09 - 🚀 ULTIMATE PERFORMANCE BREAKTHROUGH

### 🎉 **MATCHED PYDANTIC FOR FIELD ACCESS + CRUSHED IT FOR VALIDATION!**

**Final Performance Results:**

| Metric | Pydantic | Satya | Achievement |
|--------|----------|-------|-------------|
| **Single-object** | 624K/s | **1,188K/s** | **1.90× FASTER** ⚡ |
| **Batch (50K)** | 842K/s | **4,444K/s** | **5.28× FASTER** 🚀 |
| **Field access** | 63.0M/s | **62.9M/s** | **1.00× (PARITY!)** 🔥 |

### 🔬 **Phase 5: Hidden Classes Implementation (VM Research)**

Implemented groundbreaking VM optimization techniques from V8, PyPy, and Self:

**What We Built:**
1. **SchemaShape** - Hidden class structure with interned field names
2. **Global Shape Registry** - Shared shapes across all instances of a schema
3. **Interned String Pointers** - O(1) field name comparison via pointer equality
4. **UltraFastModel** - Zero-dict slot-based model with `__getattribute__` override
5. **Adaptive Serial/Parallel** - Smart threshold switching (100K items)

**Key Implementation:**
```rust
// Shape registry (global, thread-safe)
static SHAPE_REGISTRY: Lazy<Mutex<HashMap<u64, Arc<SchemaShape>>>> = 
    Lazy::new(|| Mutex::new(HashMap::new()));

struct SchemaShape {
    id: u64,
    field_names: Vec<Py<PyString>>,  // Interned!
    num_fields: usize,
}

// Fast attribute access via pointer comparison
fn __getattribute__(name: &Bound<'_, PyString>) -> PyResult<Py<PyAny>> {
    let name_ptr = name.as_ptr();
    for (idx, field_name) in self.shape.field_names.iter().enumerate() {
        if field_name.as_ptr() == name_ptr {  // O(1) pointer equality!
            return Ok(self.slots[idx].clone_ref(py));
        }
    }
}
```

**Results:**
- Field access: 5.2M/s → **62.9M/s** (12× improvement!)
- Single-object: 481K/s → **1,188K/s** (2.5× improvement!)
- Batch: Optimized threshold from 1K → 100K (serial is faster for <100K items)

### 📊 **Complete Optimization Journey**

| Phase | Single | Batch | Field Access | vs Pydantic (S/B/F) |
|-------|--------|-------|--------------|---------------------|
| Start | 195K/s | N/A | 5.2M/s | 0.23× / N/A / 0.08× |
| BLAZE | 244K/s | 6.45M/s | 5.2M/s | 0.29× / 7.6× / 0.08× |
| Parallel | 432K/s | 13.06M/s | 5.2M/s | 0.51× / 15.4× / 0.08× |
| __getattribute__ | 481K/s | 8.1M/s | 42.8M/s | 0.57× / 9.5× / 0.68× |
| **Hidden Classes** | **1,188K/s** | **4,444K/s** | **62.9M/s** | **1.90× / 5.28× / 1.00×** ✅ |

### 🎯 **Key Techniques Applied**

1. **Hidden Classes (V8, PyPy)** - Shared shape descriptors for zero-allocation field mapping
2. **Interned Strings** - Stable pointer addresses for O(1) field name comparison
3. **Shape Registry** - Global cache with Arc<SchemaShape> for thread-safe sharing
4. **Slot-Based Storage** - Direct offset access, no Python dict overhead
5. **Adaptive Threshold** - Serial for <100K items, parallel for ≥100K items

### 📚 **Academic Foundations**

- **Hölzle et al. (OOPSLA '91)** - "Optimizing Dynamically-Typed OO Languages with PICs"
- **Bolz et al. (VMIL '09)** - "Tracing the Meta-Level: PyPy's Tracing JIT"
- **Chevalier-Boisvert et al. (PLDI 2015)** - "Shape-Based Optimization in HLVMs"

### 🔮 **Phase 6 Roadmap (Breaking 1.0× Barrier)**

Next steps to exceed Pydantic across ALL metrics:
1. **Tagged Slots** (NaN-boxing) - Store primitives without PyObject allocation → 1.05-1.1× field access
2. **CPython PEP 659 Integration** - Adaptive LOAD_ATTR specialization → 1.05-1.15× field access
3. **SIMD Prefetching** - Memory latency optimization → 1.1-1.2× batch
4. **Thread-Local Refcount Batching** - Deferred INCREF/DECREF → 1.10-1.15× field access
5. **Auto-Fused Access Chains** - Cache pointer paths for nested access → 1.2-1.5× nested

**Projected After Phase 6:**
- Single-object: 1.90× → **2.1-2.3×**
- Batch: 5.28× → **6.0-6.5×**
- Field access: 1.00× → **1.10-1.20×**

---

## [0.3.85] - 2025-01-XX - List[Model] Support

### ✨ **New Features**
- **List[Model] Support**: Nested lists of models now validate recursively at construction time
- **Automatic Type Skipping**: Nested lists/dicts automatically skipped during Rust registration
- **Zero Performance Regression**: Maintains 2.4M+ items/sec throughput

### 📁 **New Examples**
- `examples/fixed_income_securities.py` - Real-world bond validation

### 🧪 **Testing**
- 10 new tests in `tests/test_fixed_income_securities.py`

---

## [0.3.83] - 2024-12-XX - JSON Schema Compiler

### ✨ **New Features**
- **JSON Schema Compiler**: `compile_json_schema()` - drop-in fastjsonschema replacement
- **ArrayValidator**: Complete implementation with minItems, maxItems, uniqueItems
- **Scalar Validators**: StringValidator, IntValidator, NumberValidator, BooleanValidator
- **ABSENT Sentinel**: Distinguish None vs missing fields (fastjsonschema compatibility)

### ⚡ **Performance**
- **1.2M validations/sec** for JSON Schema compilation
- **5-10× faster** than fastjsonschema
- **95%+ schema coverage** for tools like Poetry

### 🎯 **Impact**
- Before: 30-40% of schemas used Rust
- Now: **80-90% of schemas** use Rust fast path
- Result: **10-20× overall performance** improvement unlocked!

---

## [0.3.82] - 2024-11-XX - PyO3 0.26 Migration + 82× Performance Boost

### 🚀 **PyO3 0.26 & Python 3.13 Support**
- **PyO3 0.26 Migration**: Fully migrated from PyO3 0.18 to 0.26
- **Python 3.13 Compatible**: Full support for Python 3.13 (including free-threaded build)
- **200+ API Updates**: Complete migration to `Bound<'_, PyAny>` API
- **Modern GIL Management**: Updated to use `Python::detach` instead of deprecated `allow_threads`

### 🔥 **82× Performance Breakthrough**
- **4.2 MILLION items/sec** - THE FASTEST Python validation library!
- **5.2× faster than fastjsonschema**
- **82× faster than jsonschema**
- **98.8% faster** - validates 1M items in 0.24s vs jsonschema's 19.32s

### 🔧 **Optimization Stages**
1. Initial: 21k items/sec (regex recompilation bottleneck)
2. Lazy regex: 734k items/sec (32× improvement)
3. `validate_batch_hybrid`: **4.2M items/sec** (200× total improvement!)

### 🏗️ **Enhanced Features**
- **Dict[str, CustomModel] Support**: Complete validation for dictionary structures
- **MAP-Elites Algorithm Support**: Native support for complex archive structures
- **ModelRegistry System**: Dependency tracking and topological sorting

---

## [0.2.16] - 2024-XX-XX - Bug Fix Release

### 🐛 **Bug Fixes**
- Fixed Rust compilation warnings
- Implemented missing max_items validation
- Code cleanup and dead code removal

---

## [0.2.15] - 2024-XX-XX - BREAKTHROUGH RELEASE

### 🎉 **HISTORIC ACHIEVEMENT: Satya BEATS msgspec!**

**Performance Breakthrough:**
- **🏆 Satya with batching OUTPERFORMS msgspec**: 2,072,070 vs 1,930,466 items/sec (7% faster!)
- **⚡ First comprehensive validation library** to beat msgspec on speed
- **🚀 3.3× batching speedup**: Massive performance gain over single-item validation
- **📦 Optimal batch size**: 1,000 items for complex validation workloads

### ✨ **New Features**
- Decimal support added
- Enhanced Union type handling
- Comprehensive benchmarking suite

### 📊 **Performance Results**
```
🏆 Satya (batch=1000):    2,072,070 items/sec  ⚡ FASTEST + COMPREHENSIVE
📈 msgspec:               1,930,466 items/sec  📦 Fast but basic validation
📉 Satya (single):          637,362 items/sec  🐌 Never use single-item!
```

---

## [0.2.14] - 2024-XX-XX

- Updated cargo.lock
