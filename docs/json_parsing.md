# JSON Parsing in Satya

Satya now includes a blazingly fast JSON parser implemented in Rust. This feature leverages the same Rust-powered performance that makes Satya's validation so fast, but applied to JSON parsing.

## Features

- Native Rust implementation using serde_json
- Seamless conversion between Rust and Python data structures
- Significantly faster than Python's standard library json module
- Compatible with Satya's streaming validation pipeline

## Usage

### Basic Usage

```python
import satya._satya

# Parse a JSON string
json_string = '{"name": "example", "value": 123, "items": [1, 2, 3]}'
parsed_data = satya._satya.load_json_str(json_string)

# The result is a standard Python object (dict, list, etc.)
print(parsed_data)  # {'name': 'example', 'value': 123, 'items': [1, 2, 3]}
```

### Performance Comparison

Compared to Python's built-in `json.loads()` and even the high-performance `orjson` library, Satya's JSON parser offers excellent performance, especially for larger documents.

```python
import json
import time
import satya._satya

try:
    import orjson
except ImportError:
    orjson = None

json_string = '{"name": "example", "value": 123, "items": [1, 2, 3]}'

# Using Python's json module
start = time.time()
parsed_py = json.loads(json_string)
py_time = time.time() - start

# Using Satya's Rust-based parser
start = time.time()
parsed_satya = satya._satya.load_json_str(json_string)
satya_time = time.time() - start

print(f"Python json: {py_time*1000:.6f} ms")
print(f"Satya Rust: {satya_time*1000:.6f} ms")
print(f"Speedup: {py_time/satya_time:.2f}x")

# Compare with orjson if available
if orjson:
    start = time.time()
    parsed_orjson = orjson.loads(json_string)
    orjson_time = time.time() - start
    print(f"orjson: {orjson_time*1000:.6f} ms")
    print(f"Satya vs orjson: {orjson_time/satya_time:.2f}x")
```

## Using with Satya Validation

The JSON parser integrates seamlessly with Satya's validation pipeline, allowing you to parse and validate in a single workflow:

```python
import satya._satya
from satya import StreamValidator

# Create a validator
validator = StreamValidator()
validator.add_field("name", str)
validator.add_field("value", int)
validator.add_field("items", "List[int]")

# JSON data to parse and validate
json_string = '{"name": "example", "value": 123, "items": [1, 2, 3]}'

# Parse JSON using Satya's Rust implementation
data = satya._satya.load_json_str(json_string)

# Validate the parsed data
result = validator.validate(data)
print(f"Validation result: {result.is_valid}")
```

## Benchmarks

Comprehensive benchmarks comparing Satya's JSON parser to Python's `json` module and `orjson` are available in the `benchmarks` directory. You can run them with:

```bash
# Run from project root
cd benchmarks
./run_json_benchmarks.sh
```

The benchmarks measure both raw parsing performance and end-to-end pipeline performance (parsing + validation).

## Technical Details

Satya's JSON parser is built on Rust's `serde_json` library, which is one of the fastest JSON parsers available. It handles the conversion between Rust's native data structures and Python objects automatically and efficiently.

The implementation includes:

1. Parsing JSON strings into Rust's `serde_json::Value` representation
2. Converting `serde_json::Value` into appropriate Python objects
3. Proper error handling for malformed JSON

This feature is particularly beneficial for high-throughput applications that need to process large amounts of JSON data quickly. 