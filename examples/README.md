# Satya Examples

This directory contains examples demonstrating Satya's validation capabilities.

## Example 4: Advanced Validation & Schema Generation

This example shows Satya's advanced features including nested validation, complex types, and JSON Schema generation.

### Features Demonstrated
- Complex nested model validation
- Enum and Literal type support
- Field constraints (min/max, patterns)
- Email and URL validation
- JSON Schema generation
- Optional fields
- Custom types

### Code Example

<?> python
from satya import StreamValidator, Model, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime
from uuid import UUID

class Address(Model):
    street: str = Field(min_length=5, max_length=100)
    city: str = Field(pattern=r'^[A-Za-z\s]+$')
    postal_code: str = Field(pattern=r'^\d{5}(-\d{4})?$')
    country: str = Field(min_length=2, max_length=2)

class User(Model):
    id: UUID = Field(description="User UUID")
    email: str = Field(email=True)
    website: Optional[str] = Field(url=True, required=False)
    address: Address
    interests: List[str] = Field(min_length=1, max_length=5)
    metadata: Dict[str, Any] = Field(description="Additional data")
<?>

### Generated JSON Schema

<?> json
{
  "type": "object",
  "title": "User",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "User UUID"
    },
    "email": {
      "type": "string",
      "format": "email"
    },
    "website": {
      "type": "string",
      "format": "uri",
      "nullable": true
    },
    "address": {
      "type": "object",
      "properties": {
        "street": {
          "type": "string",
          "minLength": 5,
          "maxLength": 100
        },
        "city": {
          "type": "string",
          "pattern": "^[A-Za-z\\s]+$"
        }
      },
      "required": ["street", "city", "postal_code", "country"]
    },
    "interests": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1,
      "maxItems": 5
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  },
  "required": ["id", "email", "address", "interests", "metadata"]
}
<?>

### Usage

<?> python
# Create validator from model
validator = User.validator()

# Get JSON Schema
schema = User.json_schema()

# Validate data
result = validator.validate({
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "website": "https://example.com",
    "address": {
        "street": "123 Main St",
        "city": "New York",
        "postal_code": "10001",
        "country": "US"
    },
    "interests": ["coding", "music"],
    "metadata": {"theme": "dark"}
})

print(f"Valid: {result.is_valid}")
<?>

### Key Benefits
1. Type safety with Python type hints
2. Rich validation rules
3. Nested model support
4. OpenAPI/JSON Schema compatibility
5. Clear error messages
6. Optional field support
7. Custom type validation

For more examples, check out the other example files in this directory. 