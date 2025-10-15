"""Test dict() and json() methods"""

from satya import Model, Field
from satya._satya import compile_schema, SatyaModelInstance

class User(Model):
    name: str = Field(min_length=2)
    age: int = Field(ge=0)

schema = compile_schema(User)
data = {"name": "Alice", "age": 30}

instance = SatyaModelInstance.from_dict(schema, data)

print("Testing dict() and json() methods...")
print(f"\n1. Instance: {instance}")
print(f"2. __repr__: {repr(instance)}")

try:
    result = instance.dict()
    print(f"3. dict(): {result}")
    print(f"   Type: {type(result)}")
except Exception as e:
    print(f"3. dict() error: {e}")

try:
    result = instance.json()
    print(f"4. json(): {result}")
    print(f"   Type: {type(result)}")
except Exception as e:
    print(f"4. json() error: {e}")
