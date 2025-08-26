<p align="center">
  <img src="/assets/satya_logo.jpg" alt="Satya Logo" width="1600"/>
</p>

<h1 align="center"><b>Satya (सत्य)</b></h1>
<div align="center">
  
[![PyPI version](https://badge.fury.io/py/satya.svg)](https://badge.fury.io/py/satya)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Versions](https://img.shields.io/pypi/pyversions/satya.svg)](https://pypi.org/project/satya/)
<!-- [![Downloads](https://pepy.tech/badge/satya)](https://pepy.tech/project/satya) -->

</div>

<p align="center">

# SATYA - High Performance Data Validation for Python

Satya (सत्य) is the Sanskrit word for **truth** and **reality**, embodying our commitment to data integrity and validation. Just as truth is fundamental and unwavering, Satya ensures your data validation is reliable, fast, and efficient. 🚀

Satya is a blazingly fast data validation library for Python, powered by Rust. Early benchmarks show it performing up to 134x faster than Pydantic for large-scale validation tasks.

## Key Features:
- **Lightning fast validation** (134x faster than Pydantic in initial benchmarks)
- **Pydantic-like DX**: automatic validation on instantiation, exception-based errors, familiar helper methods
- **Stream processing support** for handling large datasets
- **Rust-powered core** with a Pythonic API
- **Native Rust-based JSON parsing** for improved performance
- **Support for nested models and complex types**
- **Compatible with standard Python type hints**
- **Minimal memory overhead**

## Quick Start (new DX):
```python
from satya import Model, Field, ModelValidationError

class User(Model):
    id: int = Field(description="User ID")
    name: str = Field(description="User name")
    email: str = Field(description="Email address")
    active: bool = Field(default=True)
    # Optional: control how to handle extra fields (ignore | allow | forbid)
    model_config = {"extra": "forbid"}

# 1) Automatic validation on instantiation
user = User(id=1, name="Ada", email="ada@example.com")

# 2) Raises on validation error
try:
    User(id="not-int", name="Linus", email="linus@example.com")
except ModelValidationError as e:
    print("Validation failed:", e.errors)

# 3) Helper methods
user2 = User.model_validate({"id": 2, "name": "Grace", "email": "grace@example.com"})
json_str = user2.model_dump_json()
schema = User.model_json_schema()
```
## Example 2 (new DX):

```python
from typing import Optional
from satya import Model, Field, List, ModelValidationError

# Pretty printing (optional)
Model.PRETTY_REPR = True

class User(Model):
    id: int
    name: str = Field(default='John Doe')
    email: str = Field(email=True)  # RFC 5322 compliant email validation
    signup_ts: Optional[str] = Field(required=False)
    friends: List[int] = Field(default=[])

external_data = {
    'id': '123',
    'email': 'john.doe@example.com',
    'signup_ts': '2017-06-01 12:22',
    'friends': [1, '2', b'3']
}

try:
    user = User(**external_data)
    print(user)
except ModelValidationError as e:
    print("Errors:", e.errors)

# Alternative (explicit):
user = User.model_validate(external_data)
print(user.model_dump())
```

### Pydantic-like API overview

```python
User.model_validate(dict)            # -> User instance (raises on error)
User.model_validate_json(str)        # -> User instance from JSON
User.parse_obj(dict)                 # alias of model_validate
User.parse_raw(str)                  # alias of model_validate_json
User.model_construct(**data)         # construct without validation

u.model_dump(exclude_none=True)      # dict
u.model_dump_json(exclude_none=True) # JSON string
User.model_json_schema()             # JSON Schema for the model
```

Extra fields handling per model:

```python
class A(Model):
    x: int
    model_config = {"extra": "ignore"}  # or "allow" | "forbid"
```

## 🚀 Performance

Our comprehensive benchmarks show significant performance improvements over existing solutions:

<p align="center">
  <img src="benchmarks/results/streaming_ips_object.png" alt="Satya Performance Comparison" width="800"/>
</p>

<p align="center">
  <img src="benchmarks/results/streaming_mem_object.png" alt="Satya Memory Usage" width="800"/>
</p>

### 📊 Latest Benchmark Results (5M records)

| Validation Mode | Throughput | Memory Usage | Use Case |
|-----------------|------------|--------------|----------|
| **Satya dict-path** | **5.7M items/s** | 7.2MB | Pre-parsed Python dicts |
| **Satya JSON streaming** | **3.2M items/s** | 0.4MB | Large JSON datasets |
| **Satya JSON non-stream** | 1.2M items/s | 0.4MB | Small JSON datasets |
| **orjson + Satya dict** | 2.6M items/s | 21.5MB | End-to-end JSON processing |
| **msgspec + JSON** | 7.5M items/s | 0.4MB | Comparison baseline |
| **Pydantic + orjson** | 0.8M items/s | 0.4MB | Traditional validation |

### 🎯 Performance Highlights
- **7.9x faster** than Pydantic for dict validation
- **4x faster** than Pydantic for JSON processing  
- **Memory bounded**: <8MB even for 5M records
- **Competitive with msgspec**: 76% of msgspec's speed with more flexibility
- **Streaming support**: Process unlimited datasets with constant memory

### 📈 Scale Performance Analysis
- **Small Scale (100k)**: 7.9M items/s - matches msgspec performance
- **Large Scale (5M)**: 5.7M items/s - maintains high throughput
- **Memory Efficiency**: Bounded growth, predictable resource usage

> **Note:** Benchmarks run on Apple Silicon M-series. Results include comprehensive comparison with msgspec and Pydantic using fair JSON parsing (orjson). See `/benchmarks/` for detailed methodology.

## 🎯 Key Features

- **🏃‍♂️ Lightning Fast:** Up to 134x faster than Pydantic
- **🌊 Stream Processing:** Efficient handling of large datasets
- **🦀 Rust-Powered:** High-performance core with zero-cost abstractions
- **📝 Fast JSON Parsing:** Native Rust-based JSON parsing for better performance
- **🐍 Pythonic API:** Familiar interface for Python developers
- **🎯 Type Support:** Full compatibility with Python type hints
- **📧 RFC Compliant:** Email validation following RFC 5322 standards
- **📦 Minimal Overhead:** Efficient memory usage

## Why Satya?
While Pydantic has revolutionized data validation in Python and inspired this project, there are use cases where raw performance is critical. Satya (सत्य) brings the power of truth to your data validation by:
- Leveraging Rust's zero-cost abstractions for core validation logic
- Implementing efficient batch processing with minimal overhead
- Minimizing Python object creation through smart memory management
- Reducing memory allocations with Rust's ownership model
- Providing truthful, precise error messages that pinpoint validation issues

## Ideal Use Cases:
- High-throughput API services
- Real-time data processing
- Large dataset validation
- Stream processing applications
- Performance-critical microservices

## Installation:
```bash
pip install satya
```

### Requirements:
- Python 3.8 or higher

> **Note for developers:** If you're contributing to Satya or building from source, you'll need Rust toolchain 1.70.0 or higher:
>
> ```bash
> # Install Rust if you don't have it
> curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
> 
> # Update existing Rust installation
> rustup update
> ```
>
> You can check your Rust version with:
> ```bash
> rustc --version
> ```

## Breaking changes in v0.3 (DX overhaul)

We introduced a Pydantic-like developer experience. Notable changes:

- __Automatic validation on instantiation__: `User(**data)` now validates and raises `ModelValidationError` on failure.
- __Exception-based errors__: Instead of returning `ValidationResult` by default, user code typically catches `ModelValidationError`.
- __Helper methods__: `model_validate`, `model_validate_json`, `model_dump`, `model_dump_json`, `model_json_schema`, `parse_obj`, `parse_raw`, `model_construct`.
- __JSON Schema__: field examples use `example` key.
- __Extras handling__: per-class `model_config = {"extra": "ignore|allow|forbid"}`.

Still available:

- __Streaming validation__: For high-throughput pipelines use the validator: `User.validator().validate_stream(iterable, collect_errors=True)`.

## Current Status:
Satya is currently in alpha (v0.3). While the core functionality is stable, we're actively working on:
- Expanding type support
- Adding more validation features
- Improving error messages
- Enhancing documentation
- Additional performance optimizations

## Acknowledgments:
Special thanks to the Pydantic project, which has set the standard for Python data validation and heavily influenced Satya's API design. While we've focused on raw performance, Pydantic's elegant API and comprehensive feature set remain a major inspiration.

## 💝 Open Source Spirit

> **Note to Data Validation Library Authors**: Feel free to incorporate our performance optimizations into your libraries! We believe in making the Python ecosystem faster for everyone. All we ask is for appropriate attribution to Satya under our MIT license. Together, we can make data validation blazingly fast for all Python developers!

## 🤝 Contributing

We welcome contributions of all kinds! Whether you're fixing bugs, improving documentation, or sharing new performance optimizations, here's how you can help:

- **🐛 Report issues** and bugs
- **💡 Suggest** new features or optimizations
- **📝 Improve** documentation
- **🔧 Submit** pull requests
- **📊 Share** benchmarks and use cases

Check out our [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.
## License:
Apache 2.0

**Note:** Performance numbers are from initial benchmarks and may vary based on use case and data structure complexity.

## Contact:
- **GitHub Issues:** [Satya Issues](https://github.com/justrach/satya)
- **Author:** Rach Pradhan

**Remember:** Satya is designed for scenarios where validation performance is critical. For general use cases, especially where features and ecosystem compatibility are more important than raw speed, Pydantic remains an excellent choice.

### Using Satya's JSON Parser

Satya includes a fast Rust-based JSON parser that you can use directly:

```python
from satya import load_json  # Rust-backed JSON loader
import json
import time

json_str = '{"name": "example", "value": 123, "items": [1, 2, 3]}'

start = time.time()
parsed_data = load_json(json_str)
end = time.time()
print(f"Satya parsing time: {(end - start)*1000:.6f} ms")

start = time.time()
parsed_data_py = json.loads(json_str)
end = time.time()
print(f"Standard json parsing time: {(end - start)*1000:.6f} ms")
```
