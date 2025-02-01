<p align="center">
  <img src="/assets/satya_logo.jpg" alt="Satya Logo" width="1600"/>
</p>

<h1 align="center"><b>Satya (सत्य)</b></h1>
<div align="center">
  
[![PyPI version](https://badge.fury.io/py/satya.svg)](https://badge.fury.io/py/satya)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/satya.svg)](https://pypi.org/project/satya/)
[![Downloads](https://pepy.tech/badge/satya)](https://pepy.tech/project/satya)

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

## Performance:
In our latest benchmarks:

### Large Dataset Processing (5M records):
- **Satya:** 207,321 items/second
- **Pydantic:** 72,302 items/second
- **Speed improvement:** 2.9x
- **Memory usage:** Nearly identical (Satya: 158.2MB, Pydantic: 162.5MB)

### Web Service Benchmark (10,000 requests):
- **Satya:** 177,790 requests/second
- **Pydantic:** 1,323 requests/second
- **Average latency improvement:** 134.4x
- **P99 latency improvement:** 134.4x

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

## Current Status:
Satya is currently in alpha (v0.2.1). While the core functionality is stable, we're actively working on:
- Expanding type support
- Adding more validation features
- Improving error messages
- Enhancing documentation
- Additional performance optimizations

## Acknowledgments:
Special thanks to the Pydantic project, which has set the standard for Python data validation and heavily influenced Satya's API design. While we've focused on raw performance, Pydantic's elegant API and comprehensive feature set remain a major inspiration.

## Contributing:
Satya is open source and welcomes contributions. Whether it's bug reports, feature requests, or code contributions, please visit our GitHub repository.

## License:
MIT License

**Note:** Performance numbers are from initial benchmarks and may vary based on use case and data structure complexity.

## Contact:
- **GitHub Issues:** [repository-url/issues](repository-url/issues)
- **Author:** Rach Pradhan

**Remember:** Satya is designed for scenarios where validation performance is critical. For general use cases, especially where features and ecosystem compatibility are more important than raw speed, Pydantic remains an excellent choice.
