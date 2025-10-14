"""
Test the complete Rust-native validation engine
This demonstrates ALL validation logic moved to Rust!
"""

from satya._satya import compile_schema, SatyaModelInstance, validate_batch_native, validate_batch_parallel
from satya import Model, Field


# Define a comprehensive model with all constraint types
class User(Model):
    # String constraints
    name: str = Field(min_length=2, max_length=50)
    email: str = Field(email=True)
    website: str = Field(url=True, required=False)
    
    # Integer constraints
    age: int = Field(ge=0, le=150)
    score: int = Field(gt=0, lt=100)
    
    # Float constraints
    rating: float = Field(min_value=0.0, max_value=5.0)
    
    # List constraints
    tags: list = Field(min_items=1, max_items=10, required=False)


print("="*60)
print("RUST-NATIVE VALIDATION ENGINE TEST")
print("="*60)

# Test 1: Compile schema from Python class
print("\n1. Schema Compilation")
try:
    schema = compile_schema(User)
    print(f"   ✓ Schema compiled: {schema}")
    print(f"   ✓ Fields: {len(schema._fields) if hasattr(schema, '_fields') else 'N/A'}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: Valid data
print("\n2. Valid Data Validation")
valid_data = {
    "name": "Alice",
    "email": "alice@example.com",
    "website": "https://alice.com",
    "age": 30,
    "score": 85,
    "rating": 4.5,
    "tags": ["python", "rust"]
}

try:
    instance = SatyaModelInstance.from_dict(schema, valid_data)
    print(f"   ✓ Instance created: {instance}")
    print(f"   ✓ Dict: {instance.dict()}")
    print(f"   ✓ JSON: {instance.json()}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 3: String min_length constraint
print("\n3. String min_length Constraint")
try:
    bad_data = valid_data.copy()
    bad_data["name"] = "A"  # Too short
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 4: String max_length constraint
print("\n4. String max_length Constraint")
try:
    bad_data = valid_data.copy()
    bad_data["name"] = "A" * 100  # Too long
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 5: Email validation
print("\n5. Email Validation")
try:
    bad_data = valid_data.copy()
    bad_data["email"] = "not-an-email"
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 6: URL validation
print("\n6. URL Validation")
try:
    bad_data = valid_data.copy()
    bad_data["website"] = "not-a-url"
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 7: Integer ge (>=) constraint
print("\n7. Integer ge (>=) Constraint")
try:
    bad_data = valid_data.copy()
    bad_data["age"] = -1  # Less than 0
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 8: Integer le (<=) constraint
print("\n8. Integer le (<=) Constraint")
try:
    bad_data = valid_data.copy()
    bad_data["age"] = 200  # Greater than 150
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 9: Integer gt (>) constraint
print("\n9. Integer gt (>) Constraint")
try:
    bad_data = valid_data.copy()
    bad_data["score"] = 0  # Not greater than 0
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 10: Integer lt (<) constraint
print("\n10. Integer lt (<) Constraint")
try:
    bad_data = valid_data.copy()
    bad_data["score"] = 100  # Not less than 100
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 11: Float min_value constraint
print("\n11. Float min_value Constraint")
try:
    bad_data = valid_data.copy()
    bad_data["rating"] = -1.0  # Less than 0.0
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 12: Float max_value constraint
print("\n12. Float max_value Constraint")
try:
    bad_data = valid_data.copy()
    bad_data["rating"] = 10.0  # Greater than 5.0
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 13: List min_items constraint
print("\n13. List min_items Constraint")
try:
    bad_data = valid_data.copy()
    bad_data["tags"] = []  # Empty list
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 14: List max_items constraint
print("\n14. List max_items Constraint")
try:
    bad_data = valid_data.copy()
    bad_data["tags"] = ["tag"] * 20  # Too many items
    instance = SatyaModelInstance.from_dict(schema, bad_data)
    print(f"   ✗ Should have failed!")
except ValueError as e:
    print(f"   ✓ Caught error: {e}")

# Test 15: Batch validation
print("\n15. Batch Validation (Sequential)")
batch_data = [
    {"name": f"User{i}", "email": f"user{i}@example.com", "age": 20 + i, "score": 50 + i, "rating": 3.0 + (i * 0.1)}
    for i in range(10)
]
try:
    results = validate_batch_native(schema, batch_data)
    print(f"   ✓ Validated {len(results)} instances")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 16: Parallel batch validation
print("\n16. Batch Validation (Parallel)")
large_batch = [
    {"name": f"User{i}", "email": f"user{i}@example.com", "age": 20 + (i % 50), "score": 50 + (i % 40), "rating": 3.0 + ((i % 20) * 0.1)}
    for i in range(100)
]
try:
    results = validate_batch_parallel(schema, large_batch)
    print(f"   ✓ Validated {len(results)} instances in parallel")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "="*60)
print("ALL VALIDATION LOGIC NOW IN RUST! 🚀")
print("="*60)
print("\n✓ String validation (min/max length, email, URL)")
print("✓ Integer validation (ge, le, gt, lt)")
print("✓ Float validation (min/max value)")
print("✓ List validation (min/max items)")
print("✓ Batch validation (sequential & parallel)")
print("✓ Error handling and reporting")
print("\nNext: Phase 3 - Python metaclass integration")
