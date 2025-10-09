# Satya Library Guide for AI Agents

## Overview
Satya is a high-performance Python data validation library powered by Rust, designed for scenarios where validation speed is critical. It provides a Pydantic-like API with significant performance improvements.

## When to Use Satya
- **High-throughput API services** requiring fast validation
- **Large dataset processing** (millions of records)
- **Real-time data pipelines** with strict latency requirements
- **Stream processing applications** with memory constraints
- **Performance-critical microservices**

## Performance Characteristics
- **Dict validation**: 5.7M items/s for large datasets (5M records)
- **JSON streaming**: 3.2M items/s with constant memory (0.4MB)
- **Memory bounded**: <8MB even for 5M records
- **7.9x faster** than Pydantic for dict validation
- **Competitive with msgspec**: 76% of msgspec's speed with more flexibility

## Basic Usage Patterns

### 1. Simple Model Definition
```python
from satya import Model, Field

class User(Model):
    id: int
    name: str = Field(description="User name")
    email: str = Field(email=True)  # RFC 5322 email validation
    active: bool = Field(default=True)
```

### 2. Validation Methods
```python
# Automatic validation on instantiation
user = User(id=1, name="Alice", email="alice@example.com")

# Explicit validation from dict
user = User.model_validate({"id": 1, "name": "Alice", "email": "alice@example.com"})

# Validation from JSON string
user = User.model_validate_json('{"id": 1, "name": "Alice", "email": "alice@example.com"}')

# Construction without validation (use carefully)
user = User.model_construct(id=1, name="Alice", email="alice@example.com")
```

### 3. Error Handling
```python
from satya import ModelValidationError

try:
    user = User(id="invalid", name="Alice", email="not-an-email")
except ModelValidationError as e:
    print("Validation errors:", e.errors)
```

### 4. High-Performance Batch Processing
```python
# For large datasets, use the validator directly
validator = User.validator()

# Stream processing (constant memory)
data_stream = [{"id": i, "name": f"User{i}", "email": f"user{i}@example.com"} 
               for i in range(1000000)]

results = validator.validate_stream(data_stream, collect_errors=True)
for result in results:
    if result.is_valid:
        print(f"Valid: {result.data}")
    else:
        print(f"Invalid: {result.errors}")
```

## Advanced Features

### 1. Field Constraints
```python
class Product(Model):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, le=10000)  # Greater than 0, less than or equal to 10000
    tags: List[str] = Field(min_items=1, max_items=10, unique_items=True)
    email: str = Field(email=True)  # RFC 5322 compliant
    url: str = Field(url=True)
```

### 2. Nested Models
```python
class Address(Model):
    street: str
    city: str
    country: str

class User(Model):
    name: str
    address: Address
    addresses: List[Address] = Field(default=[])
```

### 3. Extra Fields Handling
```python
class StrictUser(Model):
    name: str
    email: str
    model_config = {"extra": "forbid"}  # Reject extra fields

class FlexibleUser(Model):
    name: str
    email: str
    model_config = {"extra": "allow"}   # Allow extra fields

class IgnoreExtraUser(Model):
    name: str
    email: str
    model_config = {"extra": "ignore"}  # Ignore extra fields
```

## Performance Optimization Tips

### 1. Choose the Right Validation Mode
```python
# For pre-parsed Python dicts (fastest: 5.7M items/s)
validator.validate_batch(python_dicts)

# For large JSON datasets (memory efficient: 3.2M items/s, 0.4MB)
validator.validate_json_stream(json_bytes)

# For small JSON datasets (1.2M items/s, 0.4MB)
validator.validate_json_bytes(json_bytes)
```

### 2. Batch Processing
```python
# Process in batches for optimal performance
validator = User.validator()
validator.set_batch_size(50000)  # Adjust based on memory constraints

# Validate large datasets efficiently
results = validator.validate_batch(large_dataset)
```

### 3. Memory Management
```python
# For unlimited datasets, use streaming
def process_large_file(filename):
    validator = User.validator()
    
    with open(filename, 'r') as f:
        for line in f:
            data = json.loads(line)
            result = validator.validate_item(data)
            if result.is_valid:
                yield result.data
```

## JSON Processing
```python
# Use Satya's fast JSON parser directly
from satya import load_json

json_str = '{"name": "example", "value": 123}'
parsed_data = load_json(json_str)  # Rust-backed parsing
```

## Common Patterns for AI Agents

### 1. API Request Validation
```python
class APIRequest(Model):
    endpoint: str
    method: str = Field(enum_values=["GET", "POST", "PUT", "DELETE"])
    headers: dict = Field(default={})
    body: Optional[dict] = Field(default=None)

# Fast validation for incoming requests
try:
    request = APIRequest.model_validate(request_data)
except ModelValidationError as e:
    return {"error": "Invalid request", "details": e.errors}
```

### 2. Data Pipeline Validation
```python
class DataRecord(Model):
    timestamp: str
    user_id: int
    event_type: str
    metadata: dict = Field(default={})

# Process streaming data
validator = DataRecord.validator()
for batch in data_batches:
    results = validator.validate_batch(batch)
    valid_records = [r.data for r in results if r.is_valid]
    process_valid_records(valid_records)
```

### 3. Configuration Validation
```python
class ServiceConfig(Model):
    host: str = Field(default="localhost")
    port: int = Field(ge=1, le=65535)
    debug: bool = Field(default=False)
    database_url: str = Field(url=True)

# Validate configuration on startup
config = ServiceConfig.model_validate(config_dict)
```

## Migration from Pydantic

Satya provides a Pydantic-compatible API, making migration straightforward:

```python
# Pydantic code
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')

# Satya equivalent
from satya import Model, Field

class User(Model):
    name: str
    email: str = Field(email=True)  # Built-in RFC 5322 validation
```

## Performance Monitoring

Monitor these metrics when using Satya:
- **Throughput**: Items validated per second
- **Memory usage**: Should remain bounded even for large datasets
- **Error rates**: Track validation failure patterns
- **Latency**: P50, P95, P99 validation times

## Best Practices

1. **Use streaming for large datasets** to maintain constant memory usage
2. **Batch process when possible** for optimal throughput
3. **Choose appropriate field constraints** - simpler constraints validate faster
4. **Handle validation errors gracefully** with proper error reporting
5. **Monitor performance metrics** to detect regressions
6. **Use dict validation for pre-parsed data** when maximum speed is needed

## Troubleshooting

- **High memory usage**: Switch to streaming validation
- **Slow validation**: Check if using appropriate validation mode
- **Validation errors**: Use `collect_errors=True` for detailed error reporting
- **Type issues**: Ensure proper type hints and field definitions
