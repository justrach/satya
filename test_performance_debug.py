#!/usr/bin/env python3
"""Debug performance to understand where time is spent"""

import time
import json
from satya import Model, Field

class DataRecord(Model):
    id: int = Field(ge=0)
    name: str = Field(min_length=1)
    age: int = Field(ge=0, le=150)
    email: str = Field(email=True)  # THIS is the expensive part!
    is_active: bool
    score: float = Field(ge=0.0, le=100.0)

# Test data
test_item = {
    "id": 1,
    "name": "John Smith",
    "age": 30,
    "email": "john.smith@example.com",
    "is_active": True,
    "score": 95.5
}

# Test 1: Direct Python model creation
print("Test 1: Direct model creation")
start = time.time()
for i in range(10000):
    DataRecord(**test_item)
elapsed = time.time() - start
print(f"  10,000 items: {elapsed:.3f}s ({10000/elapsed:.0f} items/sec)")

# Test 2: Batch validation via JSON
print("\nTest 2: Batch validation via JSON")
validator = DataRecord.validator()
batch = [test_item] * 10000
json_str = json.dumps(batch)
start = time.time()
results = validator.validate_json(json_str, mode="array", streaming=False)
elapsed = time.time() - start
print(f"  10,000 items: {elapsed:.3f}s ({10000/elapsed:.0f} items/sec)")
print(f"  Valid: {sum(results)}/{len(results)}")

# Test 3: Simplified model without email validation
class SimpleRecord(Model):
    id: int = Field(ge=0)
    name: str = Field(min_length=1)
    age: int = Field(ge=0, le=150)
    email: str  # NO email validation!
    is_active: bool
    score: float = Field(ge=0.0, le=100.0)

print("\nTest 3: Simplified model (no email validation)")
validator2 = SimpleRecord.validator()
start = time.time()
results = validator2.validate_json(json_str, mode="array", streaming=False)
elapsed = time.time() - start
print(f"  10,000 items: {elapsed:.3f}s ({10000/elapsed:.0f} items/sec)")
print(f"  Valid: {sum(results)}/{len(results)}")

#Test 4: jsonschema
print("\nTest 4: jsonschema")
try:
    import jsonschema
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string", "minLength": 1},
            "age": {"type": "integer", "minimum": 0, "maximum": 150},
            "email": {
                "type": "string",
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            },
            "is_active": {"type": "boolean"},
            "score": {"type": "number", "minimum": 0, "maximum": 100}
        },
        "required": ["id", "name", "age", "email", "is_active", "score"]
    }
    validator_js = jsonschema.Draft7Validator(schema)
    start = time.time()
    for item in batch:
        validator_js.validate(item)
    elapsed = time.time() - start
    print(f"  10,000 items: {elapsed:.3f}s ({10000/elapsed:.0f} items/sec)")
except ImportError:
    print("  jsonschema not installed")
