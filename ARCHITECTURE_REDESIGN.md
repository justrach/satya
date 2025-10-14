# Satya v2.0 - Pure Rust Architecture Design

## Current Architecture (v0.4.12)

```
Python Model Class
    ↓ (creates)
Python Dict
    ↓ (passes to)
Rust Validator (via FFI)
    ↓ (validates)
Python Dict (mutated)
    ↓ (wraps in)
Python Model Instance
```

**Bottlenecks:**
- Python dict creation/access (slow)
- FFI boundary crossings (expensive)
- Type conversions Python ↔ Rust (overhead)
- Python object protocol (not optimized)

---

## Proposed Architecture (v2.0) - Pydantic-style

```
Python Model Class (thin wrapper)
    ↓ (compiles to)
Rust Schema (compiled once)
    ↓ (validates directly to)
Rust Struct (native memory)
    ↓ (exposed as)
Python Object (via PyO3 #[pyclass])
```

**Advantages:**
- Zero dict overhead
- Single FFI crossing
- Native Rust memory layout
- Direct field access
- JIT-like compilation

---

## Implementation Plan

### 1. Rust-Native Model Storage

```rust
// Instead of storing in Python dict, store in Rust struct
#[pyclass]
pub struct SatyaModelInstance {
    // Fields stored as Rust types (zero overhead!)
    fields: Vec<FieldValue>,
    schema: Arc<CompiledSchema>,
}

#[derive(Clone)]
pub enum FieldValue {
    Int(i64),
    Float(f64),
    String(String),
    Bool(bool),
    List(Vec<FieldValue>),
    Dict(HashMap<String, FieldValue>),
    Model(Box<SatyaModelInstance>),
    None,
}
```

### 2. Schema Compilation (JIT-style)

```rust
pub struct CompiledSchema {
    name: String,
    fields: Vec<CompiledField>,
    // Pre-computed validation function (like JIT)
    validator: Box<dyn Fn(&[FieldValue]) -> Result<(), ValidationError>>,
    // Semi-perfect hash for O(1) field lookup
    field_map: HashMap<String, usize>,
}

impl CompiledSchema {
    pub fn compile(model_class: &PyType) -> Self {
        // 1. Extract field definitions
        // 2. Build optimized validator function
        // 3. Generate specialized code path
        // 4. Return compiled schema
    }
}
```

### 3. Zero-Copy Validation

```rust
impl SatyaModelInstance {
    // Validate directly from input dict to Rust struct
    // NO intermediate Python dict!
    pub fn from_dict(py: Python<'_>, schema: &CompiledSchema, data: &PyDict) -> PyResult<Self> {
        let mut fields = Vec::with_capacity(schema.fields.len());
        
        // Extract directly to Rust types
        for field in &schema.fields {
            let value = match data.get_item(&field.name)? {
                Some(v) => extract_and_validate(field, v)?,
                None if field.required => return Err(...),
                None => FieldValue::None,
            };
            fields.push(value);
        }
        
        // Validate in Rust (zero FFI overhead)
        (schema.validator)(&fields)?;
        
        Ok(Self { fields, schema: schema.clone() })
    }
}
```

### 4. Direct Field Access (Python Protocol)

```rust
#[pymethods]
impl SatyaModelInstance {
    // Implement Python descriptor protocol
    fn __getattribute__(&self, py: Python<'_>, name: &str) -> PyResult<PyObject> {
        // O(1) lookup via semi-perfect hash
        if let Some(&idx) = self.schema.field_map.get(name) {
            // Direct access to Rust field (fast!)
            return self.fields[idx].to_python(py);
        }
        // Fallback to Python attributes
        Err(PyAttributeError::new_err(format!("no attribute '{}'", name)))
    }
    
    fn __setattr__(&mut self, name: &str, value: PyObject) -> PyResult<()> {
        // Validate and set field
        if let Some(&idx) = self.schema.field_map.get(name) {
            let field = &self.schema.fields[idx];
            let validated = extract_and_validate(field, value)?;
            self.fields[idx] = validated;
            return Ok(());
        }
        Err(PyAttributeError::new_err(format!("no attribute '{}'", name)))
    }
}
```

### 5. Optimized Batch Validation

```rust
impl CompiledSchema {
    pub fn validate_batch(&self, py: Python<'_>, data: &PyList) -> PyResult<Vec<SatyaModelInstance>> {
        let len = data.len();
        
        if len < 1000 {
            // Small batch - sequential
            data.iter()
                .map(|item| {
                    let dict = item.downcast::<PyDict>()?;
                    SatyaModelInstance::from_dict(py, self, dict)
                })
                .collect()
        } else {
            // Large batch - parallel with Rayon
            let dicts: Vec<_> = data.iter()
                .map(|item| item.downcast::<PyDict>().unwrap().clone().unbind())
                .collect();
            
            py.detach(|| {
                dicts.par_iter()
                    .map(|dict| {
                        Python::with_gil(|py| {
                            SatyaModelInstance::from_dict(py, self, dict.bind(py))
                        })
                    })
                    .collect()
            })
        }
    }
}
```

### 6. Python API (Metaclass Magic)

```python
# Python side - looks identical to current API!
from satya import Model, Field

class User(Model):
    id: int = Field(gt=0)
    name: str = Field(min_length=1)
    age: int = Field(ge=0, le=150)
    email: str = Field(email=True)

# Behind the scenes:
# 1. Metaclass compiles schema at class definition time
# 2. Schema stored as Rust CompiledSchema
# 3. __init__ calls Rust validator directly
# 4. Instance is Rust SatyaModelInstance (not Python dict!)
```

---

## Performance Comparison

### Current Architecture (v0.4.12)
```
user = User(**data)
    ↓ Python dict creation (50ns)
    ↓ FFI call to Rust (100ns)
    ↓ Validate in Rust (200ns)
    ↓ FFI return (100ns)
    ↓ Python object wrap (50ns)
Total: ~500ns per validation
```

### Proposed Architecture (v2.0)
```
user = User(**data)
    ↓ FFI call to Rust (100ns)
    ↓ Extract + validate in Rust (150ns)
    ↓ Return Rust object (0ns - already in Rust!)
Total: ~250ns per validation (2× faster!)
```

### Field Access Comparison

**Current:**
```python
value = user.name  # 30ns (Python dict lookup)
```

**Proposed:**
```python
value = user.name  # 10ns (Rust array index)
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (2 weeks)
- [ ] Define `SatyaModelInstance` with Rust field storage
- [ ] Implement `CompiledSchema` with schema compilation
- [ ] Add `FieldValue` enum with all types
- [ ] Implement Python descriptor protocol

### Phase 2: Validation Engine (2 weeks)
- [ ] Port all constraint validation to Rust
- [ ] Implement type coercion in Rust
- [ ] Add error accumulation
- [ ] Optimize validation order

### Phase 3: Python Integration (1 week)
- [ ] Create metaclass for schema compilation
- [ ] Implement `__init__` that calls Rust
- [ ] Add `dict()`, `json()` methods
- [ ] Ensure API compatibility

### Phase 4: Optimization (1 week)
- [ ] Add semi-perfect hashing
- [ ] Implement parallel batch validation
- [ ] Optimize memory layout
- [ ] Add SIMD for constraint checks

### Phase 5: Testing & Benchmarking (1 week)
- [ ] Port all 291 tests
- [ ] Add performance benchmarks
- [ ] Profile and optimize hotspots
- [ ] Compare with Pydantic

---

## Expected Performance Gains

| Metric | Current (v0.4.12) | Proposed (v2.0) | Improvement |
|--------|-------------------|-----------------|-------------|
| Simple Model | 159K ops/sec | **800K ops/sec** | **5× faster** |
| With Constraints | 154K ops/sec | **700K ops/sec** | **4.5× faster** |
| Batch (50K) | 323K ops/sec | **1.2M ops/sec** | **3.7× faster** |
| Field Access | 10.4M ops/sec | **40M ops/sec** | **3.8× faster** |

**Target: Match or exceed Pydantic's performance!**

---

## Code Example: Before vs After

### Current Architecture (v0.4.12)

```python
# Python dict-based
class User(Model):
    id: int
    name: str

user = User(id=1, name="Alice")
# Internally: {'id': 1, 'name': 'Alice'} (Python dict)
print(user.name)  # Dict lookup
```

### Proposed Architecture (v2.0)

```python
# Rust struct-based (same API!)
class User(Model):
    id: int
    name: str

user = User(id=1, name="Alice")
# Internally: Rust struct with [Int(1), String("Alice")]
print(user.name)  # Direct Rust field access (fast!)
```

**Same API, 5× faster!**

---

## Migration Path

### Backward Compatibility

```python
# v0.4.12 code works unchanged in v2.0
class User(Model):
    id: int
    name: str = Field(min_length=1)

user = User(id=1, name="Alice")
user.dict()  # Still works!
user.json()  # Still works!
```

### Opt-in to v2.0 Features

```python
# Enable Rust-native mode (default in v2.0)
class User(Model):
    __satya_native__ = True  # Use Rust storage
    
    id: int
    name: str

# Or globally
import satya
satya.config.native_mode = True
```

---

## Conclusion

**To match Pydantic's performance, we need:**

1. ✅ **Rust-native field storage** (no Python dict)
2. ✅ **Schema compilation** (JIT-like optimization)
3. ✅ **Direct field access** (Python descriptor protocol)
4. ✅ **Zero-copy validation** (single FFI crossing)
5. ✅ **Optimized memory layout** (cache-friendly)

**Estimated effort:** 6-7 weeks for full implementation

**Expected result:** 4-5× performance improvement, matching Pydantic!

**Current status:** We've implemented all optimizations possible with the dict-based architecture. To go further requires this fundamental redesign.
