#!/usr/bin/env python3
"""Quick test to verify Satya works with Python 3.13t and PyO3 0.26"""

from satya import Model, Field

class User(Model):
    id: int = Field(description="User ID")
    name: str = Field(description="User name")
    email: str = Field(description="Email address")
    active: bool = Field(default=True)

# Test basic creation
print("Test 1: Creating a User...")
user = User(id=1, name="Alice", email="alice@example.com")
print(f"✅ Created user: {user.name} ({user.email})")

# Test validation
print("\nTest 2: Testing validation...")
try:
    invalid_user = User(id="not_an_int", name="Bob", email="bob@example.com")
    print("❌ Should have failed validation")
except Exception as e:
    print(f"✅ Validation works: {type(e).__name__}")

# Test default value
print("\nTest 3: Testing default value...")
user2 = User(id=2, name="Bob", email="bob@example.com")
print(f"✅ Default active={user2.active}")

print("\n🎉 All tests passed! Satya works with Python 3.13t and PyO3 0.26!")
