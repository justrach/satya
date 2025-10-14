# Migrating from Pydantic to Satya

Satya is designed to be a **drop-in replacement** for Pydantic with superior performance. This guide covers the migration process and compatibility features.

## Quick Migration

### Step 1: Change Imports

```python
# Before (Pydantic)
from pydantic import BaseModel, Field

# After (Satya)
from satya import Model as BaseModel, Field
```

That's it! Your existing Pydantic code should work with Satya.

## Supported Pydantic Features

### ✅ Field Attributes (Fully Supported)

All major Pydantic Field attributes are supported:

#### Validation Constraints
- `gt`, `ge`, `lt`, `le` - Numeric comparisons
- `min_length`, `max_length` - String/list length
- `pattern` - Regex pattern matching
- `email`, `url` - Format validation
- `min_items`, `max_items`, `unique_items` - List constraints
- `multiple_of` - Numeric divisibility
- `max_digits`, `decimal_places` - Decimal precision

#### Default Values
- `default` - Static default value
- `default_factory` - **NEW!** Factory function for mutable defaults

#### Metadata
- `description` - Field description
- `title` - **NEW!** Field title
- `example` - Example value
- `alias` - Field alias

#### Pydantic V2 Compatibility
- `frozen` - **NEW!** Mark field as immutable (metadata)
- `validate_default` - **NEW!** Validate default values (metadata)
- `repr` - **NEW!** Include in repr (metadata)
- `init_var` - **NEW!** Init-only variable (metadata)
- `kw_only` - **NEW!** Keyword-only argument (metadata)

### ✅ Model Features

- `model_validate()` - Validate dict to model
- `model_validate_json()` - Validate JSON string to model
- `model_dump()` - Convert model to dict
- `model_dump_json()` - Convert model to JSON string
- `model_construct()` - Create model without validation
- `model_json_schema()` - Generate JSON schema

## Migration Examples

### Example 1: Basic Model with Defaults

```python
# Pydantic
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    name: str = Field(..., min_length=1)
    email: str = Field(..., email=True)
    tags: list[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)

# Satya (identical!)
from satya import Model as BaseModel, Field

class User(BaseModel):
    id: int
    name: str = Field(..., min_length=1)
    email: str = Field(..., email=True)
    tags: list[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)
```

### Example 2: Nested Models

```python
# Works identically in both Pydantic and Satya
from satya import Model as BaseModel, Field
from typing import List

class Address(BaseModel):
    street: str
    city: str
    zipcode: str = Field(pattern=r"^\d{5}$")

class Person(BaseModel):
    name: str
    age: int = Field(ge=0, le=150)
    addresses: List[Address] = Field(default_factory=list)

# Usage
person = Person(
    name="Alice",
    age=30,
    addresses=[
        {"street": "123 Main St", "city": "NYC", "zipcode": "10001"}
    ]
)
```

### Example 3: Using default_factory

```python
from satya import Model as BaseModel, Field
from typing import List, Dict
from datetime import datetime

class Document(BaseModel):
    title: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

# Each instance gets its own list/dict
doc1 = Document(title="Doc 1")
doc2 = Document(title="Doc 2")

doc1.tags.append("important")
# doc2.tags is still empty - not shared!
```

### Example 4: Validation Methods

```python
from satya import Model as BaseModel, Field

class Product(BaseModel):
    name: str
    price: float = Field(gt=0)

# Method 1: Constructor (raises exception on error)
try:
    product = Product(name="Widget", price=-10)
except Exception as e:
    print(f"Validation failed: {e}")

# Method 2: model_validate (same as Pydantic)
product = Product.model_validate({"name": "Widget", "price": 99.99})

# Method 3: model_validate_json
json_str = '{"name": "Widget", "price": 99.99}'
product = Product.model_validate_json(json_str)

# Export
data = product.model_dump()  # {"name": "Widget", "price": 99.99}
json_str = product.model_dump_json()  # '{"name":"Widget","price":99.99}'
```

## Performance Benefits

Satya provides the same API as Pydantic but with **5-10× better performance**:

```python
from satya import Model as BaseModel, Field

class User(BaseModel):
    id: int
    name: str
    email: str

# Single validation: 5-10× faster than Pydantic
user = User(id=1, name="Alice", email="alice@example.com")

# Batch validation: 10-30× faster than Pydantic
users = User.validate_many([
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"},
    # ... thousands more
])
```

## Differences from Pydantic

### Minor Differences

1. **Import name**: Use `Model` instead of `BaseModel` (or alias it)
   ```python
   from satya import Model as BaseModel  # Recommended
   # or
   from satya import Model
   ```

2. **Validation errors**: Satya uses `ModelValidationError` instead of `ValidationError`
   ```python
   from satya import ModelValidationError
   
   try:
       user = User(id="invalid")
   except ModelValidationError as e:
       print(e.errors)
   ```

3. **Metadata-only attributes**: Some attributes like `frozen`, `validate_default`, etc. are stored but not enforced yet
   - They're available for introspection
   - Full enforcement coming in future releases

### Not Yet Supported

- Custom validators (`@validator`, `@root_validator`)
- Field validators (`@field_validator`)
- Model validators (`@model_validator`)
- Config class customization (some options)
- Discriminated unions
- Computed fields

These features are on the roadmap. For now, use standard Python validation in `__init__` if needed.

## Langchain Migration

Satya works great with Langchain! Here's how to migrate:

```python
# Before (Pydantic)
from pydantic import BaseModel, Field
from langchain.tools import tool

class SearchInput(BaseModel):
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=10, ge=1, le=100)

@tool(args_schema=SearchInput)
def search(query: str, max_results: int = 10):
    """Search for information"""
    # ... implementation

# After (Satya) - identical!
from satya import Model as BaseModel, Field
from langchain.tools import tool

class SearchInput(BaseModel):
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=10, ge=1, le=100)

@tool(args_schema=SearchInput)
def search(query: str, max_results: int = 10):
    """Search for information"""
    # ... implementation
```

## Testing Your Migration

1. **Run your existing tests** - They should pass with minimal changes
2. **Check validation behavior** - Ensure constraints work as expected
3. **Verify nested models** - Test complex model hierarchies
4. **Test serialization** - Check `model_dump()` and `model_dump_json()`

## Getting Help

If you encounter issues during migration:

1. Check this guide for common patterns
2. Review the [examples](examples/) directory
3. Open an issue on GitHub with a minimal reproduction

## Summary

**Migration is simple:**
1. Change `from pydantic import BaseModel` to `from satya import Model as BaseModel`
2. Keep everything else the same
3. Enjoy 5-10× better performance!

Satya is designed to make migration painless while giving you significant performance improvements.
