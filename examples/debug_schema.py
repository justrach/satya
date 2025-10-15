"""Debug schema compilation"""

from satya import Model, Field
from satya._satya import compile_schema

class TestModel(Model):
    name: str = Field(min_length=2, max_length=50)
    age: int = Field(ge=0, le=150)

print("Testing schema compilation...")
print("\n1. Check Field objects in __fields__:")
print(f"   name field: {TestModel.__fields__['name']}")
print(f"   name.min_length: {TestModel.__fields__['name'].min_length}")
print(f"   name.max_length: {TestModel.__fields__['name'].max_length}")
print(f"   age field: {TestModel.__fields__['age']}")
print(f"   age.ge: {TestModel.__fields__['age'].ge}")
print(f"   age.le: {TestModel.__fields__['age'].le}")

print("\n2. Compile schema:")
schema = compile_schema(TestModel)
print(f"   Schema: {schema}")

print("\n3. Test with data:")
from satya._satya import SatyaModelInstance

# This should pass
try:
    good = SatyaModelInstance.from_dict(schema, {"name": "Alice", "age": 30})
    print(f"   ✓ Valid data accepted")
except Exception as e:
    print(f"   ✗ Valid data rejected: {e}")

# This should fail (name too short)
try:
    bad = SatyaModelInstance.from_dict(schema, {"name": "A", "age": 30})
    print(f"   ✗ Invalid data accepted (should have failed!)")
except Exception as e:
    print(f"   ✓ Invalid data rejected: {e}")
