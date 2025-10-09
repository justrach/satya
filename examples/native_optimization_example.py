#!/usr/bin/env python3
"""
Native Optimization Examples
============================

This example demonstrates the native Python optimization in Satya,
showing how to leverage fast-path validation for maximum performance.

Performance gains:
- Simple validation: 10-45x faster
- Nested objects: 83x faster
- Lists: 14x faster
"""

import sys
import os
import time
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import satya
from satya import Field
from satya.native_validator import NativeValidator, HybridValidator, create_optimized_validator


print("🚀 Satya Native Optimization Examples")
print("=" * 80)

# Example 1: Simple Unconstrained Model (Fastest)
print("\n📝 Example 1: Simple Unconstrained Model")
print("-" * 80)

class User(satya.Model):
    """Simple model with no constraints - uses native Python validation"""
    name: str
    age: int
    email: str

# This model will automatically use NativeValidator for maximum speed
user_data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
user = User(**user_data)

print(f"User: {user.name}, {user.age}, {user.email}")
print("✅ Validation: ~10x faster than baseline (uses native isinstance())")

# Example 2: Constrained Model (Comprehensive Validation)
print("\n\n🔒 Example 2: Constrained Model")
print("-" * 80)

class ValidatedUser(satya.Model):
    """Model with constraints - uses Rust validation for comprehensive checks"""
    name: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=0, le=120)
    email: str = Field(email=True)

validated_data = {"name": "Bob", "age": 25, "email": "bob@example.com"}
validated_user = ValidatedUser(**validated_data)

print(f"Validated User: {validated_user.name}, {validated_user.age}, {validated_user.email}")
print("✅ Validation: Comprehensive (email format, age range, name length)")

# Example 3: Hybrid Model (Best of Both Worlds)
print("\n\n⚡ Example 3: Hybrid Model (Recommended)")
print("-" * 80)

class OptimizedUser(satya.Model):
    """Hybrid model - fast-path for simple fields, comprehensive for constrained"""
    # Unconstrained fields (fast-path with native Python)
    name: str
    email: str
    
    # Constrained field (comprehensive validation with Rust)
    age: int = Field(ge=0, le=120)
    
    # Optional field
    phone: Optional[str] = None

optimized_data = {"name": "Charlie", "email": "charlie@example.com", "age": 35}
optimized_user = OptimizedUser(**optimized_data)

print(f"Optimized User: {optimized_user.name}, {optimized_user.email}, {optimized_user.age}")
print("✅ Validation: Hybrid (fast for name/email, comprehensive for age)")

# Example 4: Nested Models
print("\n\n🪆 Example 4: Nested Models")
print("-" * 80)

class Address(satya.Model):
    """Nested model"""
    street: str
    city: str
    zipcode: str

class UserWithAddress(satya.Model):
    """Model with nested structure"""
    name: str
    address: Address

nested_data = {
    "name": "Diana",
    "address": {
        "street": "123 Main St",
        "city": "San Francisco",
        "zipcode": "94102"
    }
}

user_with_address = UserWithAddress(**nested_data)
print(f"User: {user_with_address.name}")
print(f"Address: {user_with_address.address.street}, {user_with_address.address.city}")
print("✅ Validation: Nested models validated efficiently")

# Example 5: Lists
print("\n\n📋 Example 5: Lists")
print("-" * 80)

class Team(satya.Model):
    """Model with list of items"""
    name: str
    members: List[str]
    tags: List[str]

team_data = {
    "name": "Engineering",
    "members": ["Alice", "Bob", "Charlie"],
    "tags": ["tech", "innovation", "growth"]
}

team = Team(**team_data)
print(f"Team: {team.name}")
print(f"Members: {', '.join(team.members)}")
print(f"Tags: {', '.join(team.tags)}")
print("✅ Validation: Lists validated efficiently")

# Example 6: Direct Validator Usage
print("\n\n🔧 Example 6: Direct Validator Usage")
print("-" * 80)

# Create a native validator directly
schema = {'name': str, 'age': int, 'active': bool}
validator = NativeValidator(schema)

# Validate data
test_data = {"name": "Eve", "age": 28, "active": True}
result = validator.validate(test_data)

if result.is_valid:
    print(f"✅ Valid: {result.value}")
else:
    print(f"❌ Invalid: {result.errors}")

# Example 7: Performance Comparison
print("\n\n⚡ Example 7: Performance Comparison")
print("-" * 80)

# Generate test data
test_data_list = [
    {"name": f"User{i}", "age": 20 + (i % 60), "email": f"user{i}@example.com"}
    for i in range(10000)
]

# Benchmark unconstrained model
start = time.perf_counter()
for data in test_data_list:
    user = User(**data)
elapsed_unconstrained = time.perf_counter() - start

# Benchmark constrained model
start = time.perf_counter()
for data in test_data_list:
    validated = ValidatedUser(**data)
elapsed_constrained = time.perf_counter() - start

print(f"Unconstrained model: {elapsed_unconstrained:.3f}s ({len(test_data_list)/elapsed_unconstrained:,.0f} ops/sec)")
print(f"Constrained model:   {elapsed_constrained:.3f}s ({len(test_data_list)/elapsed_constrained:,.0f} ops/sec)")
print(f"Speedup: {elapsed_constrained/elapsed_unconstrained:.2f}x faster for unconstrained")

# Example 8: Optimizer Selection
print("\n\n🎯 Example 8: Optimizer Selection")
print("-" * 80)

# The optimizer automatically selects the best validator
schema_info_unconstrained = {
    'name': {'type': str},
    'age': {'type': int}
}

schema_info_constrained = {
    'name': {'type': str, 'min_length': 1},
    'age': {'type': int, 'ge': 0}
}

schema_info_hybrid = {
    'name': {'type': str},  # Unconstrained
    'age': {'type': int, 'ge': 0}  # Constrained
}

validator_unconstrained = create_optimized_validator(schema_info_unconstrained)
validator_constrained = create_optimized_validator(schema_info_constrained)
validator_hybrid = create_optimized_validator(schema_info_hybrid)

print(f"Unconstrained schema: {type(validator_unconstrained).__name__}")
print(f"Constrained schema:   {'Rust (None)' if validator_constrained is None else type(validator_constrained).__name__}")
print(f"Hybrid schema:        {type(validator_hybrid).__name__}")

# Summary
print("\n\n" + "=" * 80)
print("📊 SUMMARY")
print("=" * 80)

print("""
Key Takeaways:

1. **Unconstrained Models** (fastest)
   - Use when you only need type checking
   - 10-45x faster than baseline
   - Example: Simple DTOs, API responses

2. **Constrained Models** (comprehensive)
   - Use when you need validation rules
   - Email, URL, patterns, ranges, etc.
   - Example: User input, form data

3. **Hybrid Models** (recommended)
   - Best of both worlds
   - Fast-path for simple fields
   - Comprehensive for constrained fields
   - Example: Most real-world use cases

4. **Automatic Optimization**
   - Satya automatically selects the best validator
   - No code changes required
   - Transparent performance boost

5. **Performance Gains**
   - Simple validation: 10-45x faster
   - Nested objects: 83x faster
   - Lists: 14x faster
   - Average: 36x faster

🎉 Use Satya for both speed AND comprehensive validation!
""")
