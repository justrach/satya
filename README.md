<p align="center">
  <img src="/assets/satya_logo.jpg" alt="Satya Logo" width="1600"/>
</p>

<h1 align="center"><b>Satya</b></h1>

<div align="center">

[![PyPI version](https://badge.fury.io/py/satya.svg)](https://badge.fury.io/py/satya)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://pypi.org/project/satya/)

</div>

<div align="center">
  <b>Up to 9× faster than Pydantic v2.</b> Drop-in replacement. Powered by Rust.
</div>

---

## The Numbers

```
Raw validation:   19.4M ops/sec  (8.85× faster than Pydantic v2)
Geometric mean:    1.17× faster (across all benchmarks)
model_dump():     1.60× faster
model_dump_json:  1.30× faster
```

## Install

```bash
pip install satya
```

## Use

```python
from satya import Model, Field

class User(Model):
    name: str = Field(min_length=2)
    age: int = Field(ge=0, le=150)
    email: str = Field(email=True)

user = User(name="Alice", age=30, email="alice@example.com")

user.model_dump()        # dict output — 1.6× faster
user.model_dump_json()   # JSON string — 1.3× faster
```

Same API as Pydantic. Change the import, get the speed.

## Nested Models

```python
class Address(Model):
    city: str
    zip_code: str

class UserProfile(Model):
    name: str
    address: Address

profile = UserProfile(name="Alice", address={"city": "NYC", "zip_code": "10001"})
print(profile.address.city)  # "NYC"
```

Rust writes directly into nested instance `__dict__`s — zero intermediate dicts.

## Benchmarks

Head-to-head vs Pydantic 2.12.0 on Python 3.13 (free-threaded):

| Benchmark | Satya | Pydantic | Ratio |
|-----------|-------|----------|-------|
| Simple model (3 fields) | 2.0M ops/s | 2.2M ops/s | 0.94× |
| Constrained (3 fields) | 2.0M ops/s | 2.1M ops/s | 0.95× |
| Complex (10 fields) | 946K ops/s | 993K ops/s | 0.95× |
| model_dump (simple) | **2.8M ops/s** | 1.7M ops/s | **1.60×** |
| model_dump (complex) | **1.7M ops/s** | 1.0M ops/s | **1.63×** |
| JSON serialize (simple) | **2.1M ops/s** | 1.7M ops/s | **1.21×** |
| JSON serialize (complex) | **1.3M ops/s** | 1.0M ops/s | **1.30×** |
| Raw Rust validate_check | **19.4M ops/s** | 2.2M ops/s | **8.85×** |

Run it yourself: `python tests/benchmark_vs_pydantic.py`

## How It's Fast

**TurboValidator** — a Rust validation engine that eliminates Python overhead:

- **Pre-interned keys** — `PyString::intern()` at compile time, direct `dict.get_item()` with no HashMap lookup
- **Return-based errors** — no try/except, no string parsing. Rust returns `(field, message)` tuples
- **Zero-allocation type checks** — `is_instance_of` without value extraction for unconstrained fields
- **u64 bitmap** — field tracking without Vec allocation (up to 64 fields)
- **Nested dict injection** — Rust writes validated fields directly into pre-created `__dict__`s
- **apply_default** — replaces `copy.deepcopy` with efficient shallow copy for mutable defaults
- **BLAZE ordering** — cheapest validations first for fail-fast on invalid data

## Validation Errors

```python
from satya import Model, Field, ModelValidationError

class User(Model):
    name: str = Field(min_length=2)
    age: int = Field(ge=0)

try:
    User(name="A", age=-1)
except ModelValidationError as e:
    print(e.errors)  # Lazy — only created when accessed
```

## Constraints

```python
from satya import Model, Field

class Product(Model):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, le=1_000_000)
    sku: str = Field(pattern=r'^[A-Z]{2}\d{6}$')
    tags: list = Field(min_items=1, max_items=10)
    email: str = Field(email=True)
    url: str = Field(url=True)
```

## Requirements

- Python 3.9+
- No runtime dependencies

## License

Apache 2.0
