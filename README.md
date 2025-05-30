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

Satya (सत्य) is the Sanskrit word for **truth** and **reality**, embodying our commitment to data integrity and validation. Just as truth is fundamental and unwavering, Satya ensures your data validation is reliable, fast, and efficient.

Satya is a blazingly fast data validation library for Python, powered by Rust. It provides comprehensive validation capabilities while maintaining exceptional performance through innovative batch processing techniques.

## Key Features:
- **High-performance validation** with Rust-powered core
- **Batch processing** with configurable batch sizes for optimal throughput
- **Stream processing support** for handling large datasets
- **Comprehensive validation** including email, URL, regex, numeric ranges, and more
- **Type coercion** with intelligent type conversion
- **Decimal support** for financial-grade precision
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

# Enable batching for optimal performance
validator = User.validator()
validator.set_batch_size(1000)  # Recommended for most workloads

# Process data efficiently
for valid_item in validator.validate_stream(data):
    process(valid_item)
```

## Example 2:

```python 
from typing import Optional
from decimal import Decimal
from satya import Model, Field, List

# Enable pretty printing for this module
Model.PRETTY_REPR = True

class User(Model):
    id: int
    name: str = Field(default='John Doe')
    email: str = Field(email=True)  # RFC 5322 compliant email validation
    signup_ts: Optional[str] = Field(required=False)  # Using str for datetime
    friends: List[int] = Field(default=[])
    balance: Decimal = Field(ge=0, description="Account balance")  # Decimal support

external_data = {
    'id': '123',
    'email': 'john.doe@example.com',
    'signup_ts': '2017-06-01 12:22',
    'friends': [1, '2', b'3'],
    'balance': '1234.56'
}
validator = User.validator()
validator.set_batch_size(1000)  # Enable batching for performance
result = validator.validate(external_data)
user = User(**result.value)
print(user)
#> User(id=123, name='John Doe', email='john.doe@example.com', signup_ts='2017-06-01 12:22', friends=[1, 2, 3], balance=1234.56)
```

## 🚀 Performance

### Latest Benchmark Results (v0.2.15)

Our comprehensive benchmarks demonstrate Satya's exceptional performance when using batch processing:

<p align="center">
  <img src="benchmarks/results/example5_comprehensive_performance.png" alt="Comprehensive Performance Comparison" width="800"/>
</p>

#### Performance Summary
- **Satya (batch=1000):** 2,072,070 items/second
- **msgspec:** 1,930,466 items/second
- **Satya (single-item):** 637,362 items/second

Key findings:
- Batch processing provides up to 3.3x performance improvement
- Optimal batch size of 1,000 items for complex validation workloads
- Competitive performance with msgspec while providing comprehensive validation

#### Memory Efficiency
<p align="center">
  <img src="benchmarks/results/example5_memory_comparison.png" alt="Memory Usage Comparison" width="800"/>
</p>

Memory usage remains comparable across all approaches, demonstrating that performance gains don't come at the cost of increased memory consumption.

### Previous Benchmarks

Our earlier benchmarks also show significant performance improvements:

<p align="center">
  <img src="benchmark_results.png" alt="Satya Benchmark Results" width="800"/>
</p>

#### Large Dataset Processing (5M records)
- **Satya:** 207,321 items/second
- **Pydantic:** 72,302 items/second
- **Speed improvement:** 2.9x
- **Memory usage:** Nearly identical (Satya: 158.2MB, Pydantic: 162.5MB)

#### Web Service Benchmark (10,000 requests)
- **Satya:** 177,790 requests/second
- **Pydantic:** 1,323 requests/second
- **Average latency improvement:** 134.4x
- **P99 latency improvement:** 134.4x

> **Note:** All benchmarks were run on identical hardware using standardized test cases. Your results may vary depending on your specific use case and data structure complexity.

## 🎯 Key Features

- **High Performance:** Rust-powered core with efficient batch processing
- **Comprehensive Validation:** 
  - Email validation (RFC 5322 compliant)
  - URL format validation
  - Regex pattern matching
  - Numeric constraints (min/max, ge/le/gt/lt)
  - Decimal precision handling
  - UUID format validation
  - Enum and literal type support
  - Array constraints (min/max items, unique items)
  - Deep nested object validation
- **Stream Processing:** Efficient handling of large datasets
- **Type Safety:** Full compatibility with Python type hints
- **Error Reporting:** Detailed validation error messages
- **Memory Efficient:** Minimal overhead design

## Why Satya?

Satya brings together high performance and comprehensive validation capabilities. While inspired by projects like Pydantic (for its elegant API) and msgspec (for performance benchmarks), Satya offers:

- **Rust-powered performance** with zero-cost abstractions
- **Batch processing** for optimal throughput
- **Comprehensive validation** beyond basic type checking
- **Production-ready** error handling and reporting
- **Memory-efficient** design for large-scale applications

## Ideal Use Cases:
- High-throughput API services
- Real-time data processing pipelines
- Large dataset validation
- Stream processing applications
- Financial and healthcare systems requiring strict validation
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

## Performance Optimization Guide

### Batch Processing
For optimal performance, always use batch processing:

```python
# Configure batch size based on your workload
validator = MyModel.validator()
validator.set_batch_size(1000)  # Start with 1000, adjust as needed

# Use stream processing for large datasets
for valid_item in validator.validate_stream(data):
    process(valid_item)
```

### Batch Size Guidelines
- **Default recommendation:** 1,000 items
- **Large objects:** Consider smaller batches (500-1000)
- **Small objects:** Can use larger batches (5000-10000)
- **Memory constrained:** Use smaller batches
- **Always benchmark** with your specific data

## Validation Capabilities

### Supported Validation Types

Satya provides comprehensive validation that goes beyond basic type checking:

| Feature | Satya | msgspec | Pydantic |
|---------|-------|---------|----------|
| Basic type validation | ✅ | ✅ | ✅ |
| Email validation (RFC 5322) | ✅ | ❌ | ✅ |
| URL validation | ✅ | ❌ | ✅ |
| Regex patterns | ✅ | ❌ | ✅ |
| Numeric constraints | ✅ | ❌ | ✅ |
| Decimal precision | ✅ | ❌ | ✅ |
| UUID validation | ✅ | ❌ | ✅ |
| Enum/Literal types | ✅ | ✅ | ✅ |
| Array constraints | ✅ | ❌ | ✅ |
| Deep nesting (4+ levels) | ✅ | ✅ | ✅ |
| Custom error messages | ✅ | Limited | ✅ |
| Batch processing | ✅ | ❌ | ❌ |

## Current Status:
Satya is currently in alpha (v0.2.15). The core functionality is stable and performant. We're actively working on:
- Expanding type support
- Adding more validation features
- Improving error messages
- Enhancing documentation
- Performance optimizations
- Auto-optimization features

## Acknowledgments:
- **Pydantic project** for setting the standard in Python data validation and inspiring our API design
- **msgspec project** for demonstrating high-performance validation is achievable
- **Rust community** for providing the foundation for our performance

## 💝 Open Source Spirit

> **Note to Data Validation Library Authors**: Feel free to incorporate our performance optimizations into your libraries! We believe in making the Python ecosystem faster for everyone. All we ask is for appropriate attribution to Satya under our Apache 2.0 license. Together, we can make data validation blazingly fast for all Python developers!

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

**Note:** Performance numbers are from comprehensive benchmarks and may vary based on use case and data structure complexity.

## Contact:
- **GitHub Issues:** [Satya Issues](https://github.com/justrach/satya)
- **Author:** Rach Pradhan
