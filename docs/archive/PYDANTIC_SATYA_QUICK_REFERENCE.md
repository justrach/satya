# Pydantic vs Satya - Quick Reference Guide

## ✅ What Satya Already Supports (Well)

### Core Types
- ✅ `str`, `int`, `float`, `bool`
- ✅ `bytes`, `Decimal`, `datetime`, `date`
- ✅ `List[T]`, `Dict[K, V]`
- ✅ `Union[A, B]`, `Optional[T]`
- ✅ `Any`

### Constraints
- ✅ String: `min_length`, `max_length`, `pattern`
- ✅ String transformations: `strip_whitespace`, `to_lower`, `to_upper` (NEW!)
- ✅ Email validation: `Field(email=True)`
- ✅ URL validation: `Field(url=True)`
- ✅ Integer: `ge`, `le`, `gt`, `lt`, `multiple_of` (NEW!)
- ✅ Float: `ge`, `le`, `gt`, `lt`, `min_value`, `max_value`, `multiple_of` (NEW!)
- ✅ Decimal: `max_digits`, `decimal_places` (NEW!)
- ✅ List: `min_items`, `max_items`, `unique_items`

### Model Features
- ✅ `BaseModel` equivalent (`satya.Model`)
- ✅ `Field()` for field configuration
- ✅ `model_validate()` and `model_validate_json()`
- ✅ `model_dump()` and `model_dump_json()`
- ✅ `model_json_schema()` / `schema()`
- ✅ `model_construct()` (skip validation)
- ✅ `model_config` with `extra='allow'/'forbid'/'ignore'`
- ✅ Nested models
- ✅ `ValidationError` with error details

### Performance Advantages
- ✅ **10.1x faster** than Pydantic for batch processing
- ✅ **5-7x faster** than Pydantic with constraints
- ✅ **12.2M ops/sec** for numeric validation (peak)
- ✅ **5.2x faster** than fastjsonschema
- ✅ **82x faster** than jsonschema
- ✅ Rust-backed validation
- ✅ **2.66x faster** than Pydantic on average

---

## ⚠️ What Satya Partially Supports

### Types
- ⚠️ `tuple`, `set`, `frozenset` (basic support, no constraints)
- ⚠️ `UUID` (basic support, no version-specific validation)
- ⚠️ `time`, `timedelta` (basic support)
- ⚠️ URL types (basic validation, not comprehensive)
- ⚠️ Generic types (basic support)

### Features
- ⚠️ Strict mode (can implement via Field)
- ⚠️ Aliases (basic support, not comprehensive)
- ⚠️ Include/exclude in serialization (basic)

---

## ❌ What Satya is Missing (Priority Order)

### 🔴 Critical (Blocks Real-World Use)

**Validation System**:
- ✅ `@field_validator` decorator (IMPLEMENTED!)
- ✅ `@model_validator` decorator (IMPLEMENTED!)
- ❌ Functional validators (Before/After/Plain/Wrap)

**Numeric Constraints**:
- ✅ `multiple_of` for int/float/decimal (IMPLEMENTED!)
- ✅ `max_digits` and `decimal_places` for Decimal (IMPLEMENTED!)
- ❌ `allow_inf_nan` / `FiniteFloat`

**Date/Time Constraints**:
- ❌ `PastDate`, `FutureDate`, `PastDatetime`, `FutureDatetime`
- ❌ `AwareDatetime`, `NaiveDatetime`
- ❌ Date range constraints (gt, ge, lt, le)

### 🟠 High Priority (Common Use Cases)

**Serialization**:
- ❌ `@field_serializer` decorator
- ❌ `@model_serializer` decorator
- ❌ Conditional serialization

**Network Types**:
- ❌ IP address types (IPv4/IPv6 Address/Network/Interface)
- ❌ Database DSN types (PostgreSQL, MySQL, Redis, etc.)
- ❌ Comprehensive URL types (FTP, WebSocket, etc.)

**File Types**:
- ❌ `FilePath`, `DirectoryPath`, `NewPath`

**Computed Fields**:
- ❌ `@computed_field` decorator

### 🟡 Medium Priority (Nice to Have)

**Configuration**:
- ❌ `alias_generator`
- ❌ `frozen` models (immutability)
- ❌ `validation_alias` and `serialization_alias`
- ❌ `AliasPath` and `AliasChoices`
- ✅ String transformations (`to_upper`, `to_lower`, `strip_whitespace`) (IMPLEMENTED!)

**Collection Types**:
- ❌ Set/FrozenSet with constraints
- ❌ `Deque`, `OrderedDict`, `DefaultDict`, `Counter`
- ❌ `NamedTuple`

**Special Types**:
- ❌ `SecretStr`, `SecretBytes`
- ❌ UUID version-specific (UUID1-UUID8)
- ❌ Base64 encoding types
- ❌ `ByteSize`

### 🟢 Low Priority (Advanced/Rare)

**Advanced Features**:
- ❌ Discriminated unions
- ❌ `Callable` types
- ❌ Generic type specialization
- ❌ `model_rebuild()` for forward refs
- ❌ `model_copy()` with updates
- ❌ `PrivateAttr()`

**Extra Types** (moved to pydantic-extra-types):
- ❌ `Color`
- ❌ `PaymentCardNumber`

**Other**:
- ❌ `complex` numbers
- ❌ `ImportString`

---

## 📊 Coverage Summary

| Category | Satya Support | Notes |
|----------|---------------|-------|
| **Core Types** | 80% | Missing: complex, some UUID versions |
| **Numeric Types** | 70% | Missing: multiple_of, decimal precision |
| **String Types** | 85% | Missing: SecretStr, transformations |
| **Date/Time Types** | 50% | Missing: Past/Future, timezone validation |
| **Network Types** | 20% | Missing: Most specialized types |
| **File Types** | 0% | Not implemented |
| **Collection Types** | 60% | Missing: Set constraints, special dicts |
| **Validation System** | 30% | Missing: Decorators, functional validators |
| **Serialization** | 60% | Missing: Custom serializers |
| **Configuration** | 50% | Missing: Advanced config options |
| **Overall** | **55%** | Good foundation, key gaps |

---

## 🎯 Migration Guide: Pydantic → Satya

### ✅ Works Out of the Box

```python
# Pydantic
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=0, le=120)
    email: str = Field(pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')

# Satya - EXACT SAME CODE! ✅
from satya import Model, Field

class User(Model):
    name: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=0, le=120)
    email: str = Field(pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
```

### ⚠️ Requires Workarounds

```python
# Pydantic - Custom validator
from pydantic import field_validator

class User(BaseModel):
    password: str
    
    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password too short')
        return v

# Satya - Manual validation in __init__ ⚠️
class User(Model):
    password: str = Field(min_length=8)  # Use constraints when possible
    
    # Or override __init__ for complex logic
    def __init__(self, **data):
        super().__init__(**data)
        # Custom validation here
```

### ❌ Not Supported Yet

```python
# Pydantic - Computed field
from pydantic import computed_field

class Rectangle(BaseModel):
    width: float
    height: float
    
    @computed_field
    @property
    def area(self) -> float:
        return self.width * self.height

# Satya - Use regular @property (not in schema) ❌
class Rectangle(Model):
    width: float
    height: float
    
    @property
    def area(self) -> float:
        return self.width * self.height
    # Note: area won't be in JSON schema or serialization
```

---

## 🚀 When to Use Satya vs Pydantic

### Use Satya When:
- ✅ **Performance is critical** (5-82x faster)
- ✅ **Simple to moderate validation** (basic types + constraints)
- ✅ **High-throughput APIs** (FastAPI, Starlette)
- ✅ **Data pipelines** with millions of records
- ✅ **JSON Schema validation** (drop-in fastjsonschema replacement)
- ✅ **You want Rust-level performance** with Python ergonomics

### Use Pydantic When:
- ⚠️ **Complex custom validators** are essential
- ⚠️ **Computed fields** in schemas are required
- ⚠️ **Network/File type validation** is needed
- ⚠️ **Discriminated unions** are used heavily
- ⚠️ **Full ecosystem compatibility** is required
- ⚠️ **Serialization customization** is critical

### Consider Hybrid Approach:
- Use **Satya for hot paths** (validation-heavy code)
- Use **Pydantic for complex logic** (custom validators)
- **Migrate incrementally** as Satya adds features

---

## 📈 Roadmap to Pydantic Parity

### Q1 2025 (60% parity)
- ✅ Native CPython optimization (DONE!)
- 🔄 Validation decorators (@field_validator, @model_validator)
- 🔄 Numeric constraints (multiple_of, decimal precision)
- 🔄 Date/time constraints (past/future validation)

### Q2 2025 (85% parity)
- 🔄 Serialization decorators (@field_serializer, @model_serializer)
- 🔄 Computed fields (@computed_field)
- 🔄 Network types (IP addresses, DSNs)
- 🔄 File path validation

### Q3 2025 (95% parity)
- 🔄 Advanced configuration (alias_generator, frozen)
- 🔄 Collection enhancements (Set constraints, special dicts)
- 🔄 Discriminated unions
- 🔄 Advanced alias types

---

## 💡 Quick Tips

### Performance Optimization
```python
# Use native optimization for unconstrained fields
class FastModel(Model):
    name: str  # ← 10x faster (native Python)
    email: str  # ← 10x faster (native Python)
    age: int = Field(ge=0)  # ← Rust validation (still fast)
```

### Batch Processing
```python
# Use batch validation for maximum speed
validator = MyModel.validator()
results = validator.validate_batch(large_dataset)  # 5x faster
```

### JSON Schema Compilation
```python
# Direct JSON Schema validation (fastjsonschema replacement)
from satya import compile_json_schema

schema = {"type": "object", "properties": {"name": {"type": "string"}}}
validate = compile_json_schema(schema)  # 5-10x faster than fastjsonschema
```

---

## 📚 Resources

- **Full Comparison**: See `PYDANTIC_TYPE_SYSTEM_COMPARISON.md`
- **Native Optimization**: See `NATIVE_CPYTHON_OPTIMIZATION_ANALYSIS.md`
- **Performance Benchmarks**: See `PHASE1_2_NATIVE_OPTIMIZATION_SUMMARY.md`
- **Examples**: See `examples/` directory

---

**Last Updated**: 2025-10-09  
**Satya Version**: 0.3.86  
**Pydantic Version Analyzed**: 2.x
