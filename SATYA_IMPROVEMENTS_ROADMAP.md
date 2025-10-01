# Satya Improvements for Better JSON Schema Adapter Support

This document outlines improvements that Satya (the library) should implement to better support JSON Schema validation use cases like the Poetry integration.

**Context**: Based on Sourcery AI review feedback from the Poetry PR integration.

---

## Priority 1: High-Performance Validation for Non-Object Schemas

### Current Limitation
The adapter's `_convert_jsonschema_to_satya()` only converts `object` type schemas to Satya Models. This means:
- **Scalar schemas** (e.g., `{"type": "string", "minLength": 5}`) fall back to slow Python validation
- **Array schemas** (e.g., `{"type": "array", "items": {...}}`) fall back to slow Python validation
- **Only object schemas** get the 7.6x performance boost

### What Satya Should Add

#### 1. **First-Class Support for Scalar Validation**
```python
from satya import StringValidator, IntValidator, NumberValidator

# Should be able to create validators for primitives directly
string_validator = StringValidator(min_length=5, max_length=100, pattern=r'^[a-z]+$')
result = string_validator.validate("hello")

int_validator = IntValidator(ge=0, le=100)
result = int_validator.validate(42)
```

**Benefits:**
- String validation (package names, versions, markers) would get Rust performance
- Number validation (port numbers, timeouts) would be faster
- Boolean validation would be optimized

#### 2. **Native Array/List Validation with Item Schemas**
```python
from satya import ArrayValidator, Model, Field

# Should support array validation with item constraints
class PackageDep(Model):
    name: str
    version: str

# Native array validator
deps_validator = ArrayValidator(
    item_type=PackageDep,
    min_items=1,
    max_items=100,
    unique_items=True  # bonus feature
)

# Or simpler for primitive arrays
tags_validator = ArrayValidator(
    item_type=str,
    min_items=0,
    max_items=10
)
```

**Benefits:**
- Poetry dependency arrays would validate at Rust speed
- Extras arrays would be faster
- Large lists of dependencies would see dramatic speedup

#### 3. **Schema Union Types (anyOf/oneOf equivalent)**
```python
from satya import UnionValidator, Model

class StringDep(Model):
    dep: str

class ObjectDep(Model):
    version: str
    extras: list[str] | None = None

# Poetry dependencies can be strings OR objects
dep_validator = UnionValidator([StringDep, ObjectDep])
```

---

## Priority 2: Optional Field Behavior Compatibility

### Current Issue
**Sourcery Feedback**: "Default values for optional fields are auto-injected (e.g. empty strings, zeros), which may differ from fastjsonschema's behavior of leaving missing keys absent."

### What Satya Should Add

#### 1. **Explicit "Absent" vs "None" Distinction**
```python
from satya import Model, Field, ABSENT

class Config(Model):
    # Currently: optional fields get default values (empty string, 0, etc.)
    # This changes the data structure!
    
    # Should support:
    name: str
    version: str | None = None  # Explicitly allows None
    python: str | type[ABSENT] = ABSENT  # Field can be absent (not in dict)
    markers: str | type[ABSENT] = ABSENT
```

**Behavior:**
```python
# Input: {"name": "pkg", "version": "1.0"}
# Current Satya output: {"name": "pkg", "version": "1.0", "python": "", "markers": ""}
# Desired output: {"name": "pkg", "version": "1.0"}  # absent fields stay absent
```

#### 2. **Field-Level Control**
```python
from satya import Model, Field

class Config(Model):
    name: str
    version: str
    # Control whether field appears in output when missing
    python: str = Field(default=ABSENT, omit_if_absent=True)
    markers: str = Field(default="", omit_if_absent=False)  # always include
```

**Benefits:**
- Matches fastjsonschema behavior exactly
- No unexpected data structure changes
- Better compatibility with existing tools

---

## Priority 3: JSON Schema Feature Parity

### Current Limitations
The adapter has to fall back to Python validation for:
- `$ref` references
- `oneOf` / `anyOf` / `allOf` composition
- `patternProperties`
- `additionalProperties` with schemas
- Complex nested schemas

### What Satya Should Add

#### 1. **Schema References**
```python
from satya import Model, Field, SchemaRef

# Define reusable schemas
PackageInfo = Model(...)

class Config(Model):
    dependencies: dict[str, SchemaRef["PackageInfo"]]
    # Or reference by name
    dev_dependencies: dict[str, SchemaRef["PackageInfo"]]
```

#### 2. **Composition Support**
```python
from satya import Model, OneOf, AllOf

# oneOf support
DependencySpec = OneOf[str, DependencyObject]

# allOf support (multiple constraints)
StrictPackage = AllOf[BasicPackage, SecurityRules, LicenseRules]
```

#### 3. **Dynamic Property Names (patternProperties)**
```python
from satya import Model, Field, PatternProperties

class PyProjectDeps(Model):
    # Keys matching pattern must validate against schema
    dependencies: PatternProperties[
        r'^[a-zA-Z0-9-_.]+$',  # pattern
        str | DependencyObject   # value type
    ]
```

---

## Priority 4: Performance & Developer Experience

### 1. **Batch Validation Should Return Detailed Results**
```python
# Current behavior in adapter is unclear about batch results
results = validator.validate_batch(items)
# Should return: list[ValidationResult] with details per item

# Better API:
class ValidationResult:
    is_valid: bool
    errors: list[ValidationError]
    validated_data: Any | None
    
results = validator.validate_batch(items)
for i, result in enumerate(results):
    if not result.is_valid:
        print(f"Item {i} failed: {result.errors[0].message}")
```

### 2. **Better Error Messages for Debugging**
```python
# When Satya Model creation fails, provide details
try:
    model = create_dynamic_model(schema)
except SatyaSchemaError as e:
    # Should tell us WHY it failed
    print(e.unsupported_features)  # ["$ref", "oneOf"]
    print(e.problematic_fields)     # {"dependencies": "$ref not supported"}
```

### 3. **Schema Introspection**
```python
# Useful for adapter to know what Satya supports
from satya import can_convert_schema

if can_convert_schema(json_schema):
    # Use fast path
    validator = satya.create_validator(json_schema)
else:
    # Use fallback
    validator = manual_validator(json_schema)
```

---

## Priority 5: JSON Schema Standard Compliance

### Missing Features for Full Compatibility

1. **String Formats**
   - `"format": "email"` → email validation
   - `"format": "uri"` → URI validation  
   - `"format": "date-time"` → datetime validation
   - `"format": "uuid"` → UUID validation

2. **Numeric Constraints**
   - `multipleOf` → number must be multiple of X
   - Proper `exclusiveMinimum/Maximum` support

3. **Object Constraints**
   - `minProperties` / `maxProperties`
   - `additionalProperties: false` (reject unknown keys)
   - `propertyNames` schema (validate key names)

4. **Conditional Schemas**
   - `if/then/else` logic
   - `dependentSchemas` (some fields require others)

---

## Implementation Priority

### Phase 1 (Critical - Blocking 10x More Performance)
1. ✅ **Scalar validators** (strings, numbers, booleans)
2. ✅ **Array validators** with item schemas
3. ✅ **Optional field behavior** (absent vs default)

### Phase 2 (Important - Better Compatibility)
4. **`oneOf`/`anyOf` support**
5. **`$ref` support** 
6. **Better error messages** and debugging

### Phase 3 (Nice to Have - Full Parity)
7. **`patternProperties`**
8. **String formats** (email, uri, etc.)
9. **Conditional schemas**

---

## Expected Impact

If Satya implements Priority 1 features:
- **Current**: Only 30-40% of Poetry schemas use fast path (objects only)
- **After**: 80-90% of schemas could use fast path
- **Performance**: Could see 10-20x overall improvement instead of 7.6x

If Satya implements Priority 1 + 2:
- **Compatibility**: 100% drop-in replacement for fastjsonschema
- **No behavior changes**: Exact same output
- **Confidence**: Can fully replace fastjsonschema with zero risk

---

## API Design Suggestions

### Clean, Pythonic API
```python
from satya import (
    Model, Field,
    String, Integer, Number, Boolean, Array, Object,
    OneOf, AnyOf, AllOf,
    Pattern, Format,
    ABSENT
)

# Simple scalar validation
name_validator = String(min_length=1, max_length=100)

# Array validation
tags_validator = Array(String(pattern=r'^[a-z]+$'), min_items=1, max_items=5)

# Complex object with composition
class Package(Model):
    name: String(min_length=1)
    version: String(pattern=r'^\d+\.\d+')
    deps: Object[str, OneOf[String, DependencyObject]]
    python: String | type[ABSENT] = ABSENT  # optional, no default injection
```

### JSON Schema Direct Compilation
```python
from satya import compile_json_schema

# Direct JSON Schema → Satya validator
json_schema = {"type": "object", "properties": {...}}

validator = compile_json_schema(json_schema)
# Returns optimized Satya validator where possible
# Transparently falls back for unsupported features

# Query what was optimized
print(validator.optimization_level)  # "full", "partial", "none"
print(validator.unsupported_features)  # ["$ref", "oneOf"]
```

---

## Conclusion

Satya is already **7.6x faster** for object schemas. With these improvements, it could become:
- **10-20x faster** overall (support all schema types)
- **100% compatible** with fastjsonschema (correct optional field behavior)
- **The de-facto standard** for high-performance JSON validation in Python

These improvements would make Satya suitable not just for Poetry, but for any project currently using fastjsonschema, jsonschema, or pydantic for validation.

---

## Related Documents
- [Poetry Integration Guide](./POETRY_INTEGRATION_GUIDE.md)
- [Poetry Quick Action Plan](./POETRY_QUICK_ACTION_PLAN.md)
- [Architecture & Systems](./SYSTEMS.md)
