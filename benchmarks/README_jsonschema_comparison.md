# Satya vs jsonschema Performance Benchmark

This benchmark compares Satya's Rust-powered validation against the standard Python `jsonschema` library to demonstrate the significant performance improvements achievable with Satya.

## Overview

The `jsonschema` library is the de-facto standard for JSON Schema validation in Python, but it's implemented in pure Python. Satya, leveraging Rust under the hood, provides dramatically faster validation while maintaining comprehensive validation capabilities.

## What This Benchmark Tests

We validate 1,000,000 data records with the following schema:

```python
{
    "id": int (>= 0),
    "name": str (min_length=1),
    "age": int (0-150),
    "email": str (email format),
    "is_active": bool,
    "score": float (0.0-100.0)
}
```

Both libraries validate:
- Type checking
- Numeric constraints (min/max values)
- String constraints (min length, regex patterns)
- Email format validation
- Boolean values

## Running the Benchmark

### Prerequisites

Install required dependencies:
```bash
pip install jsonschema memory-profiler matplotlib numpy
```

Make sure Satya is installed:
```bash
pip install satya
# or if developing locally
pip install -e .
```

### Run the Benchmark

```bash
python benchmarks/jsonschema_comparison.py
```

The benchmark will:
1. Generate 1,000,000 test records
2. Validate them with jsonschema
3. Validate them with Satya
4. Generate comparison charts
5. Save results to JSON

## Expected Results

Based on Satya's architecture, you should see:

- **Speed**: Satya is typically **10-50x faster** than jsonschema
- **Memory**: Similar or better memory efficiency
- **Accuracy**: Both provide correct validation results

### Sample Output

```
🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆
Satya vs jsonschema Performance Benchmark
🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆🏆

============================================================
jsonschema (Python) Benchmark
============================================================
Total time: 45.32s
Items per second: 22,075

============================================================
Satya (Rust-powered) Benchmark
============================================================
Total time: 1.58s
Items per second: 632,911

============================================================
PERFORMANCE IMPROVEMENT
============================================================
⚡ Speed improvement: 28.7x faster
⏱️  Time reduction: 96.5% faster
💾 Memory usage: 0.95x (relative to jsonschema)
🚀 Throughput gain: 610,836 more items/sec
============================================================
```

## Output Files

The benchmark generates the following files in `benchmarks/results/`:

- `jsonschema_comparison.png` - Side-by-side comparison of speed and memory
- `jsonschema_relative_performance.png` - Relative performance chart
- `jsonschema_comparison_results.json` - Raw benchmark data

## Why the Difference?

### jsonschema (Pure Python)
- Pure Python implementation
- Schema compilation overhead
- Python interpreter overhead for each validation
- Deep recursion for nested structures

### Satya (Rust-powered)
- Compiled Rust core for validation logic
- Zero-copy validation where possible
- Batch processing optimization
- Efficient memory layout
- Native type handling

## Use Cases for Replacement

Consider replacing `jsonschema` with Satya when:

1. **High-throughput APIs** - Validating thousands of requests per second
2. **Data pipelines** - Processing large datasets
3. **Real-time systems** - Low-latency validation requirements
4. **Microservices** - Where every millisecond counts
5. **ETL processes** - Validating millions of records

## Migration Example

### Before (jsonschema)
```python
import jsonschema
from jsonschema import validate

schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0}
    },
    "required": ["name", "age"]
}

# Validate single item
validate(instance={"name": "John", "age": 30}, schema=schema)
```

### After (Satya)
```python
from satya import Model, Field

class Person(Model):
    name: str
    age: int = Field(ge=0)

# Validate single item
person = Person(name="John", age=30)

# Or batch validate for maximum performance
validator = Person.validator()
results = validator.validate_batch(data_list)
```

## Performance Tips

1. **Use batch validation** with Satya for maximum throughput
2. **Reuse validators** - Create once, validate many times
3. **Enable streaming** for large JSON files
4. **Adjust batch size** based on your data size and memory constraints

## Benchmark Configuration

You can adjust these parameters in the script:

```python
N_ITEMS = 1_000_000  # Total items to validate
BATCH_SIZE = 10_000  # Batch size for processing
```

For quick tests, reduce `N_ITEMS` to 100,000 or 10,000.

## Contributing

If you find ways to make the benchmark more fair or comprehensive, please submit a PR!

## License

Apache 2.0 - Same as Satya
