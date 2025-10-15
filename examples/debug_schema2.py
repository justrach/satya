"""Debug schema compilation - check __fields__"""

from satya import Model, Field

class TestModel(Model):
    name: str = Field(min_length=2, max_length=50)
    age: int = Field(ge=0, le=150)

print("Testing Model structure...")
print(f"\n1. __fields__: {hasattr(TestModel, '__fields__')}")
if hasattr(TestModel, '__fields__'):
    print(f"   Fields: {TestModel.__fields__}")
    for fname, fobj in TestModel.__fields__.items():
        print(f"   - {fname}: {fobj}")
        if hasattr(fobj, 'min_length'):
            print(f"     min_length: {fobj.min_length}")
        if hasattr(fobj, 'ge'):
            print(f"     ge: {fobj.ge}")

print(f"\n2. __annotations__: {TestModel.__annotations__}")

print(f"\n3. __dict__ keys: {list(TestModel.__dict__.keys())}")
