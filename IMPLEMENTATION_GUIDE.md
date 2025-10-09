# 🏗️ Satya Implementation Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Key Components](#key-components)
4. [Performance Features](#performance-features)
5. [Advanced Usage](#advanced-usage)
6. [Extending Satya](#extending-satya)

---

## Quick Start

### Installation
```bash
pip install satya
```

### Basic Usage (30 seconds to production!)

```python
from satya import BaseModel, Field

# Define your model (just like Pydantic!)
class User(BaseModel):
    id: int
    name: str
    email: str = Field(email=True)
    age: int = Field(ge=0, le=150)

# Single validation
user = User(id=1, name="Alice", email="alice@example.com", age=30)
print(user)  # User(id=1, name='Alice', email='alice@example.com', age=30)

# Batch validation (5× faster!)
data = [
    {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30},
    {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25}
]
users = User.validate_many(data)
print(f"Validated {len(users)} users")  # Validated 2 users
```

**That's it!** You're now using the **FASTEST Python validation library**! 🚀

---

## Architecture Overview

Satya's architecture is built on three pillars:

```
┌─────────────────────────────────────────────────────────────┐
│                     Python API Layer                         │
│  (BaseModel, Field, validators - Pydantic-like interface)   │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  PyO3 Bridge Layer                           │
│     (Type conversion, GIL management, memory safety)        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                 Rust Validation Core                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  BLAZE Compiler  │  Parallel Engine  │  Shape Cache │   │
│  └─────────────────────────────────────────────────────┘   │
│     ▪ Schema compilation    ▪ Rayon workers   ▪ Hidden     │
│     ▪ Instruction reorder   ▪ GIL-free batch  ▪ classes    │
│     ▪ Loop unrolling        ▪ 100K threshold  ▪ Interned   │
└─────────────────────────────────────────────────────────────┘
```

### Design Philosophy

1. **Zero Learning Curve**: If you know Pydantic, you know Satya
2. **Performance by Default**: Fast paths are automatic, no configuration needed
3. **Rust Where It Matters**: 95%+ of validation logic runs in Rust
4. **Smart Parallelism**: Automatic serial/parallel switching based on batch size

---

## Key Components

### 1. BaseModel - Your Starting Point

**File**: `src/satya/model.py`

The `BaseModel` is your entry point. It provides:
- Pydantic-compatible API
- Automatic schema compilation
- Three validation modes: single, batch, fast

```python
from satya import BaseModel, Field

class Product(BaseModel):
    name: str
    price: float = Field(gt=0)
    quantity: int = Field(ge=0)

# 🐌 Regular: 600K ops/sec
product = Product(name="Widget", price=9.99, quantity=100)

# ⚡ Fast: 1.2M ops/sec (model_validate_fast)
product = Product.model_validate_fast({"name": "Widget", "price": 9.99, "quantity": 100})

# 🚀 Batch: 4.4M ops/sec (validate_many)
products = Product.validate_many([{...}, {...}, ...])
```

### 2. UltraFastModel - The Secret Sauce

**File**: `src/fast_model.rs`

This is where the magic happens! Key innovations:

#### Hidden Classes (V8/PyPy Inspired)
```rust
struct SchemaShape {
    id: u64,
    field_names: Vec<Py<PyString>>,  // Interned for O(1) comparison!
    num_fields: usize,
}

// Global registry - shared across all instances
static SHAPE_REGISTRY: Lazy<Mutex<HashMap<u64, Arc<SchemaShape>>>> = ...;
```

#### Pointer-Based Field Access
```rust
fn __getattribute__(name: &Bound<'_, PyString>) -> PyResult<Py<PyAny>> {
    let name_ptr = name.as_ptr();
    for (idx, field_name) in self.shape.field_names.iter().enumerate() {
        if field_name.as_ptr() == name_ptr {  // Pointer equality = O(1)!
            return Ok(self.slots[idx].clone_ref(py));
        }
    }
}
```

**Why This is Fast:**
- No Python dict lookups (zero hash table overhead)
- Pointer comparison instead of string comparison
- Shared shapes = no per-instance metadata allocation
- Direct slot access = cache-friendly memory layout

### 3. Scalar Validators - Building Blocks

**File**: `src/satya/scalar_validators.py`

Fast validation for primitive types:

```python
from satya import StringValidator, IntValidator, NumberValidator

# Email validator (1M+ validations/sec)
email_validator = StringValidator(email=True)
result = email_validator.validate("user@example.com")

# Integer with bounds (500K+ validations/sec)
age_validator = IntValidator(ge=0, le=150)
result = age_validator.validate(30)

# Float with precision
price_validator = NumberValidator(ge=0.0, le=1000000.0)
result = price_validator.validate(99.99)
```

**Smart Reuse**: These validators use `StreamValidatorCore` internally - no duplicate Rust code!

### 4. JSON Schema Compiler

**File**: `src/satya/json_schema_compiler.py`

Drop-in replacement for fastjsonschema:

```python
from satya import compile_json_schema

# Any JSON Schema document
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "age": {"type": "integer", "minimum": 0}
    },
    "required": ["name", "age"]
}

validator = compile_json_schema(schema)
result = validator.validate({"name": "Alice", "age": 30})
```

**Performance**: 5-10× faster than fastjsonschema, 80× faster than jsonschema!

---

## Performance Features

### 1. Adaptive Serial/Parallel Switching

**File**: `src/fast_model.rs:hydrate_batch_ultra_fast_parallel`

```rust
// Smart threshold: serial for <100K, parallel for ≥100K
if len < 100_000 {
    return hydrate_batch_ultra_fast(py, schema_name, field_names, validated_dicts);
}

// Parallel path with optimal chunking
let results = py.detach(|| {
    dicts.par_chunks(1000)
        .map(|chunk| validate_chunk(chunk))
        .collect()
});
```

**Why 100K?**: Benchmark-driven threshold where parallel overhead < parallel gains

### 2. BLAZE Compilation

**File**: `src/compiled_validator.rs`

Schema compilation pipeline:
1. **Parse** schema into field descriptors
2. **Reorder** checks (fast first: type, then constraints)
3. **Unroll** loops for small schemas (≤5 fields)
4. **Inline** primitive type checks

```rust
// Before: Interpreted validation
for field in schema.fields {
    check_type(field)
    check_constraints(field)
}

// After: Compiled instruction sequence
LOAD_INT, CHECK_RANGE, STORE_SLOT_0,
LOAD_STR, CHECK_LENGTH, STORE_SLOT_1,
...
```

### 3. Shape-Based Caching

**File**: `src/fast_model.rs:get_or_create_shape`

```rust
fn get_or_create_shape(py: Python<'_>, field_names: &[String]) -> Arc<SchemaShape> {
    // Hash field names to create shape ID
    let shape_id = compute_hash(field_names);
    
    // Try to reuse existing shape
    let mut registry = SHAPE_REGISTRY.lock().unwrap();
    if let Some(shape) = registry.get(&shape_id) {
        return shape.clone();  // Arc clone = cheap!
    }
    
    // Create new shape with interned strings
    let interned_names: Vec<Py<PyString>> = field_names
        .iter()
        .map(|name| PyString::intern(py, name).unbind())
        .collect();
    
    let shape = Arc::new(SchemaShape { ... });
    registry.insert(shape_id, shape.clone());
    shape
}
```

**Impact**: Zero per-instance allocation for field name metadata!

---

## Advanced Usage

### 1. Hybrid Validation (MAXIMUM Performance)

```python
from satya import BaseModel

class DataRecord(BaseModel):
    id: int
    value: float
    label: str

validator = DataRecord.validator()

# 🔥 FASTEST: Direct hybrid validation (4.2M items/sec!)
results = validator._validator.validate_batch_hybrid(data)
```

### 2. Stream Processing for Large Datasets

```python
# Memory-efficient processing
validator = DataRecord.validator()
validator.set_batch_size(10000)

for valid_record in validator.validate_stream(huge_dataset):
    process(valid_record)  # Constant memory usage!
```

### 3. Custom Validation Logic

```python
from satya import BaseModel, Field, field_validator

class User(BaseModel):
    username: str
    age: int
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username too short')
        return v.lower()  # Normalize

user = User(username="ALICE", age=30)
print(user.username)  # "alice" (normalized)
```

### 4. Nested Models

```python
class Address(BaseModel):
    street: str
    city: str
    country: str

class User(BaseModel):
    name: str
    address: Address  # Nested validation!

user = User(
    name="Alice",
    address={"street": "123 Main St", "city": "NYC", "country": "USA"}
)
```

---

## Extending Satya

### Adding Custom Validators

```python
from satya import StringValidator

class CustomValidator:
    def __init__(self, **constraints):
        self.validator = StringValidator(**constraints)
    
    def validate(self, value):
        result = self.validator.validate(value)
        if result.is_valid:
            # Add custom logic here
            return self.custom_transform(result.value)
        return result
    
    def custom_transform(self, value):
        # Your custom logic
        return value.upper()
```

### Performance Monitoring

```python
import time
from satya import BaseModel

class User(BaseModel):
    name: str
    age: int

# Benchmark your validation
data = [{"name": f"User{i}", "age": i} for i in range(50000)]

start = time.perf_counter()
users = User.validate_many(data)
elapsed = time.perf_counter() - start

print(f"Validated {len(users):,} in {elapsed:.3f}s")
print(f"Throughput: {len(users)/elapsed:,.0f} ops/sec")
```

---

## File Structure Reference

```
satya/
├── src/
│   ├── satya/                    # Python API
│   │   ├── __init__.py          # Main exports
│   │   ├── model.py             # BaseModel, Field
│   │   ├── validator.py         # StreamValidator
│   │   ├── scalar_validators.py # Primitive validators
│   │   └── json_schema_compiler.py  # JSON Schema support
│   │
│   ├── lib.rs                   # Rust FFI entry point
│   ├── fast_model.rs            # UltraFastModel + Shape cache
│   ├── compiled_validator.rs   # BLAZE compiler
│   └── native_model.rs          # NativeModel (alternate impl)
│
├── examples/                     # Working examples
│   ├── ultra_fast_showcase.py   # Performance demo
│   ├── scalar_validation_example.py  # Scalar validators
│   └── json_schema_example.py   # JSON Schema compiler
│
├── tests/                        # Comprehensive test suite
│   ├── test_basic.py
│   ├── test_performance.py
│   └── test_turboapi_features.py
│
├── benchmarks/                   # Performance benchmarks
│   └── ultra_fast_showcase.py   # Latest benchmarks
│
├── README.md                     # Main documentation
├── IMPLEMENTATION_GUIDE.md       # This file!
├── SUMMARY_IMPROVEMENTS.md       # Technical deep dive
└── changelog.md                  # Version history
```

---

## Performance Checklist

✅ **For Maximum Throughput:**
1. Use `validate_many()` for batches
2. Set batch size to 1,000-10,000
3. Use `model_validate_fast()` for single objects
4. Avoid email/regex validation in hot paths (use simple string validation)
5. Enable streaming for large datasets

✅ **For Minimum Latency:**
1. Use `model_validate_fast()` (1.2M ops/sec)
2. Pre-compile schemas once, reuse validators
3. Use scalar validators for primitives
4. Keep schemas simple (<10 fields for optimal unrolling)

✅ **For Memory Efficiency:**
1. Use streaming validation (`validate_stream`)
2. Process in batches of 1,000-10,000
3. Avoid holding large result lists in memory

---

## Common Patterns

### Pattern 1: High-Throughput API

```python
from fastapi import FastAPI
from satya import BaseModel

app = FastAPI()

class Request(BaseModel):
    user_id: int
    action: str

@app.post("/api/action")
async def handle_action(data: dict):
    # Fast validation (1.2M ops/sec)
    request = Request.model_validate_fast(data)
    return process(request)
```

### Pattern 2: ETL Pipeline

```python
from satya import BaseModel

class Record(BaseModel):
    id: int
    value: float

# Stream large dataset
validator = Record.validator()
validator.set_batch_size(10000)

processed = 0
for valid_record in validator.validate_stream(huge_csv_data):
    db.insert(valid_record)
    processed += 1
    if processed % 100000 == 0:
        print(f"Processed {processed:,} records")
```

### Pattern 3: Configuration Validation

```python
from satya import BaseModel, Field
from typing import Optional

class Config(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)
    timeout: float = Field(gt=0, default=30.0)
    ssl_enabled: bool = Field(default=True)

# Load and validate config
import json
with open('config.json') as f:
    config = Config.model_validate_fast(json.load(f))

print(f"Connecting to {config.host}:{config.port}")
```

---

## Next Steps

1. **Read the Performance Story**: See `SUMMARY_IMPROVEMENTS.md` for the complete optimization journey
2. **Run Examples**: Try `examples/ultra_fast_showcase.py` to see performance in action
3. **Explore Benchmarks**: Check `benchmarks/` for comparative performance analysis
4. **Check Changelog**: See `changelog.md` for version history and features

---

## Questions?

- **GitHub Issues**: [github.com/justrach/satya/issues](https://github.com/justrach/satya/issues)
- **Documentation**: See `README.md` for full API reference
- **Performance**: See `SUMMARY_IMPROVEMENTS.md` for technical details

**Satya is production-ready and the FASTEST Python validation library!** 🚀
