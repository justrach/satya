# Satya Migration Guide (legacy bindings → v0.3+ Pydantic-like DX)

This guide helps you migrate from the legacy Satya bindings (direct `StreamValidatorCore` usage and manual schema setup) to the new, Pythonic, Pydantic-like developer experience.

- Target version: v0.3+
- Audience: users of pre-v0.3 Satya who interacted directly with `_satya`/`StreamValidatorCore` or manual `StreamValidator`

## TL;DR
- Use `Model` subclasses and `Field(...)` for schema definition
- Instantiate models directly (validation on `__init__`) or call `Model.model_validate(...)`
- For high-throughput pipelines use `Model.validator()` and `StreamValidator.validate_batch/validate_stream`
- Prefer JSON-bytes validators for raw JSON input: `Model.model_validate_json_bytes`, `Model.model_validate_json_array_bytes`, `Model.model_validate_ndjson_bytes`

---

## Old → New: Quick mapping

- Legacy: import core and build schema manually
  - `from satya._satya import StreamValidatorCore`
  - `core.add_field('name', 'str', required=True)`
  - `core.set_field_constraints('email', pattern=..., email=True)`
  - `ok_list = core.validate_batch(items)`

- New: model-first API
  - `from satya import Model, Field`
  - Define class with annotations and optional field constraints
  - Use `User(**data)` or `User.model_validate(data)`
  - Batch/stream via `User.validator().validate_batch(items)` or `validate_stream(...)`

### Type / constraint mapping
- Types: `str|int|float|bool|list|dict|Model` → declare with type hints on `Model` fields
- Constraints:
  - strings: `min_length`, `max_length`, `pattern`, `email`, `url`
  - numbers: `ge`, `le`, `gt`, `lt`, `min_value`, `max_value`
  - arrays: `min_items`, `max_items`, `unique_items`
  - enums (strings): `Field(enum=[...])`
- Extras handling: `model_config = {"extra": "ignore|allow|forbid"}`

---

## Before / After

### 1) Dict-path validation (Python dicts)

Before (legacy manual schema):
```python
from satya._satya import StreamValidatorCore

core = StreamValidatorCore()
core.add_field('id', 'int', True)
core.add_field('name', 'str', True)
core.add_field('email', 'str', True)
core.set_field_constraints('email', email=True)

items = [{"id": 1, "name": "Ada", "email": "ada@example.com"}]
oks = core.validate_batch(items)  # List[bool]
```

After (model-first):
```python
from satya import Model, Field

class User(Model):
    id: int
    name: str
    email: str = Field(email=True)

items = [{"id": 1, "name": "Ada", "email": "ada@example.com"}]
oks = User.validator().validate_batch(items)  # List[bool]
```

### 2) One item with exception-based errors

Before:
```python
ok = core.validate_item_internal({"id": "x"})
# had to catch PyErr or check boolean/result elsewhere
```

After:
```python
from satya import Model, Field, ModelValidationError

class User(Model):
    id: int

try:
    User(id="x")  # validates on init
except ModelValidationError as e:
    print(e.errors)
```

### 3) JSON bytes validation

Before:
```python
ok = core.validate_json_bytes(b'{"id": 1}')
oks = core.validate_json_array_bytes(b'[{"id":1},{"id":2}]')
oks = core.validate_ndjson_bytes(b'{"id":1}\n{"id":2}\n')
# streaming variants existed but required direct core calls
```

After (model-level helpers):
```python
from satya import Model

class User(Model):
    id: int

ok = User.model_validate_json_bytes(b'{"id": 1}', streaming=True)
oks = User.model_validate_json_array_bytes(b'[{"id":1},{"id":2}]', streaming=True)
oks = User.model_validate_ndjson_bytes(b'{"id":1}\n{"id":2}\n', streaming=True)
```

### 4) Nested models and lists

Before (custom types + manual registration):
```python
core.define_custom_type('Address')
core.add_field_to_custom_type('Address', 'city', 'str', True)

core.add_field('user', 'User', True)
core.add_field_to_custom_type('User', 'addresses', 'List[str]', True)
```

After (natural typing):
```python
from typing import List
from satya import Model, Field

class Address(Model):
    city: str

class User(Model):
    addresses: List[Address] = Field(min_items=1)
```

---

## Extras handling (forbid/allow/ignore)
```python
class A(Model):
    x: int
    model_config = {"extra": "forbid"}
```
- `forbid`: raises `ModelValidationError` if extra keys present
- `allow`: retains extras on the instance
- `ignore`: drops extras (default)

---

## Error handling: result vs exception
- Legacy often used boolean returns or out-of-band error strings
- New default is exception-based: `ModelValidationError(errors=[ValidationError(...), ...])`
- If you need non-raising per-item results in pipelines, use:
  - `StreamValidator.validate(item)` → `ValidationResult`
  - `StreamValidator.validate_stream(iterable, collect_errors=True)`

---

## Performance notes
- v0.3 introduces hybrid micro-batching in the core for `validate_batch` to regain high throughput with bounded memory
- JSON validators support streaming to avoid building intermediate Python objects

---

## Minimal migration checklist
- Replace manual `StreamValidatorCore` schema with `Model` classes + `Field(...)`
- Swap ad-hoc validations for `Model(**data)` or `Model.model_validate(data)`
- For batch: `Model.validator().validate_batch(items)`
- For JSON: `Model.model_validate_json_bytes(...)` and friends
- Decide extras policy via `model_config`

---

## Appendix: API reference touched by migration
- Model construction: `Model(**data)`, `Model.model_construct(**data)`
- Dumping: `model_dump()`, `model_dump_json()`
- Schema: `model_json_schema()`
- JSON input: `model_validate_json`, `model_validate_json_bytes`, `model_validate_json_array_bytes`, `model_validate_ndjson_bytes`
- Streaming/batch: `Model.validator().validate_batch(...)`, `validate_stream(...)`, `validate_json(..., streaming=True)`
