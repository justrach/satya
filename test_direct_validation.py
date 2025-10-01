#!/usr/bin/env python3
"""Test different validation approaches to find the fastest"""

import time
import json
from satya import Model, Field

class DataRecord(Model):
    id: int = Field(ge=0)
    name: str = Field(min_length=1)
    age: int = Field(ge=0, le=150)
    email: str = Field(email=True)
    is_active: bool
    score: float = Field(ge=0.0, le=100.0)

# Test data
test_data = []
for i in range(10000):
    test_data.append({
        "id": i,
        "name": "John Smith",
        "age": 30,
        "email": "john.smith@example.com",
        "is_active": True,
        "score": 95.5
    })

validator = DataRecord.validator()
validator.set_batch_size(10000)

print("Testing different validation approaches:\n")

# Method 1: Direct dict validation (validate_batch)
print("1. validate_batch (Python dicts directly)")
start = time.time()
results = validator._validator.validate_batch(test_data)
elapsed = time.time() - start
print(f"   10,000 items: {elapsed:.4f}s ({10000/elapsed:.0f} items/sec)")
print(f"   Valid: {sum(results)}/{len(results)}\n")

# Method 2: JSON string validation
print("2. validate_json (JSON string)")
json_str = json.dumps(test_data)
start = time.time()
results = validator.validate_json(json_str, mode="array", streaming=False)
elapsed = time.time() - start
print(f"   10,000 items: {elapsed:.4f}s ({10000/elapsed:.0f} items/sec)")
print(f"   Valid: {sum(results)}/{len(results)}\n")

# Method 3: validate_batch with hybrid mode (if available)
print("3. validate_batch_hybrid (if available)")
try:
    start = time.time()
    results = validator._validator.validate_batch_hybrid(test_data)
    elapsed = time.time() - start
    print(f"   10,000 items: {elapsed:.4f}s ({10000/elapsed:.0f} items/sec)")
    print(f"   Valid: {sum(results)}/{len(results)}\n")
except AttributeError:
    print("   Not available\n")

# Method 4: Streaming JSON validation
print("4. validate_json with streaming")
start = time.time()
results = validator.validate_json(json_str, mode="array", streaming=True)
elapsed = time.time() - start
print(f"   10,000 items: {elapsed:.4f}s ({10000/elapsed:.0f} items/sec)")
print(f"   Valid: {sum(results)}/{len(results)}\n")

print("=" * 60)
print("Best approach: Use validate_batch for maximum speed!")
