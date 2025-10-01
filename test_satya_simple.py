#!/usr/bin/env python3
from satya import Model, Field

class User(Model):
    name: str
    age: int = Field(ge=0)

# Test 1: Single validation
print("Test 1: Single item validation")
u = User(name='John', age=30)
print(f"✓ Success: {u.name}, age {u.age}")

# Test 2: Validator
print("\nTest 2: Using validator")
validator = User.validator()
print(f"✓ Validator created: {validator}")

# Test 3: Single item through validator
print("\nTest 3: Validate single item")
result = validator.validate({"name": "Jane", "age": 25})
print(f"✓ Result: {result}")

# Test 4: Batch validation
print("\nTest 4: Batch validation")
data = [
    {"name": "Alice", "age": 20},
    {"name": "Bob", "age": 30},
]
results = validator._validator.validate_batch(data)
print(f"✓ Batch results: {results}")

print("\n✅ All tests passed!")
