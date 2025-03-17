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
- **Stream processing support** for handling large datasets
- **Rust-powered core** with a Pythonic API
- **Support for nested models and complex types**
- **Compatible with standard Python type hints**
- **Minimal memory overhead**

## Quick Start:
```python
from satya import Model, Field

class User(Model):
    id: int = Field(description="User ID")
    name: str = Field(description="User name")
    email: str = Field(description="Email address")
    active: bool = Field(default=True)
```
## Example 2:

```python 
from typing import Optional
from satya import Model, Field, List

# Enable pretty printing for this module
Model.PRETTY_REPR = True

class User(Model):
    id: int
    name: str = Field(default='John Doe')
    email: str = Field(email=True)  # RFC 5322 compliant email validation
    signup_ts: Optional[str] = Field(required=False)  # Using str for datetime
    friends: List[int] = Field(default=[])

external_data = {
    'id': '123',
    'email': 'john.doe@example.com',
    'signup_ts': '2017-06-01 12:22',
    'friends': [1, '2', b'3']
}
validator = User.validator()
result = validator.validate(external_data)
user = User(**result.value)
print(user)
#> User(id=123, name='John Doe', email='john.doe@example.com', signup_ts='2017-06-01 12:22', friends=[1, 2, 3])
```

## 🚀 Performance

Our benchmarks show significant performance improvements over existing solutions:

<p align="center">
  <img src="benchmark_results.png" alt="Satya Benchmark Results" width="800"/>
</p>

### 📊 Large Dataset Processing (5M records)
- **Satya:** 207,321 items/second
- **Pydantic:** 72,302 items/second
- **Speed improvement:** 2.9x
- **Memory usage:** Nearly identical (Satya: 158.2MB, Pydantic: 162.5MB)

### 🌐 Web Service Benchmark (10,000 requests)
- **Satya:** 177,790 requests/second
- **Pydantic:** 1,323 requests/second
- **Average latency improvement:** 134.4x
- **P99 latency improvement:** 134.4x

> **Note:** All benchmarks were run on identical hardware using standardized test cases. Your results may vary depending on your specific use case and data structure complexity.

## 🎯 Key Features

- **🏃‍♂️ Lightning Fast:** Up to 134x faster than Pydantic
- **🌊 Stream Processing:** Efficient handling of large datasets
- **🦀 Rust-Powered:** High-performance core with zero-cost abstractions
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
- Python 3.7 or higher
- Rust toolchain 1.70.0 or higher (if installing from source)

If you're installing from source or encountering Rust-related errors, make sure you have an updated Rust toolchain:

```bash
# Install Rust if you don't have it
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Update existing Rust installation
rustup update
```

You can check your Rust version with:
```bash
rustc --version
```

## Current Status:
Satya is currently in alpha (v0.2.1). While the core functionality is stable, we're actively working on:
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
- **GitHub Issues:** [repository-url/issues](https://github.com/rachpradhan/satya/issues)
- **Author:** Rach Pradhan

**Remember:** Satya is designed for scenarios where validation performance is critical. For general use cases, especially where features and ecosystem compatibility are more important than raw speed, Pydantic remains an excellent choice.
