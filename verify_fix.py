#!/usr/bin/env python3
"""
Verification script for Field access fix.
Tests the exact scenario reported by the user.
"""

print("=" * 80)
print("VERIFYING FIELD ACCESS FIX")
print("=" * 80)

# Test 1: User's exact example
print("\n1. Testing user's exact example:")
print("-" * 80)

from satya import BaseModel, Field

class User(BaseModel):
    id: str = Field(..., description="User ID")

user = User(**{"id": "123"})
print(f"user.id = {user.id}")

# Verify it's NOT a Field object
assert "Field object" not in str(user.id), f"❌ FAILED: Got Field object: {user.id}"
assert user.id == "123", f"❌ FAILED: Expected '123', got {user.id}"
assert isinstance(user.id, str), f"❌ FAILED: Expected str, got {type(user.id)}"

print("✅ PASSED: Returns '123' (not Field object)")

# Test 2: Math operations
print("\n2. Testing math operations:")
print("-" * 80)

class Account(BaseModel):
    balance: float = Field(default=1000.0)

account = Account()
result = account.balance - 100
print(f"account.balance - 100 = {result}")
assert result == 900.0, f"❌ FAILED: Expected 900.0, got {result}"
print("✅ PASSED: Math operations work")

# Test 3: Comparisons
print("\n3. Testing comparisons:")
print("-" * 80)

class Product(BaseModel):
    price: float = Field(default=99.99)

product = Product()
result = product.price < 100
print(f"product.price < 100 = {result}")
assert result == True, f"❌ FAILED: Expected True, got {result}"
print("✅ PASSED: Comparisons work")

# Test 4: String formatting
print("\n4. Testing string formatting:")
print("-" * 80)

class Person(BaseModel):
    name: str = Field(default="Alice")
    age: int = Field(default=30)

person = Person()
result = f"{person.name} is {person.age} years old"
print(f"f-string: {result}")
assert "Alice" in result and "30" in result, f"❌ FAILED: Got {result}"
assert "Field object" not in result, f"❌ FAILED: Field object in string: {result}"
print("✅ PASSED: String formatting works")

# Test 5: Default values
print("\n5. Testing default values:")
print("-" * 80)

class Config(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=8080)

config = Config()
print(f"config.host = {config.host}")
print(f"config.port = {config.port}")
assert config.host == "localhost", f"❌ FAILED: Expected 'localhost', got {config.host}"
assert config.port == 8080, f"❌ FAILED: Expected 8080, got {config.port}"
assert isinstance(config.port, int), f"❌ FAILED: Expected int, got {type(config.port)}"
print("✅ PASSED: Default values work")

# Test 6: Pydantic-style Field(...)
print("\n6. Testing Pydantic-style Field(...):")
print("-" * 80)

class RequiredFields(BaseModel):
    required_field: str = Field(..., description="Required")
    optional_field: str = Field(default="optional")

obj = RequiredFields(required_field="test")
print(f"required_field = {obj.required_field}")
print(f"optional_field = {obj.optional_field}")
assert obj.required_field == "test", f"❌ FAILED: Expected 'test', got {obj.required_field}"
assert obj.optional_field == "optional", f"❌ FAILED: Expected 'optional', got {obj.optional_field}"
print("✅ PASSED: Field(...) works")

print("\n" + "=" * 80)
print("✅ ALL TESTS PASSED!")
print("=" * 80)
print("\nSatya now provides the same developer experience as Pydantic!")
print("Field values are returned directly - no Field objects, no manual conversions.")
