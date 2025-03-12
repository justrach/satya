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

``` python
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
```

### Generated JSON Schema

``` json
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
```

### Usage

``` python
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
```

### Key Benefits
1. Type safety with Python type hints
2. Rich validation rules
3. Nested model support
4. OpenAPI/JSON Schema compatibility
5. Clear error messages
6. Optional field support
7. Custom type validation

For more examples, check out the other example files in this directory.

## Supported Types and Validations

### Primitive Types
``` python
class Types(Model):
    # String types with various validations
    string_field: str = Field(min_length=1, max_length=100)
    email_field: str = Field(email=True)
    url_field: str = Field(url=True)
    pattern_field: str = Field(pattern=r'^[A-Z][a-z]+$')
    
    # Numeric types with range validation
    integer_field: int = Field(min_value=-10, max_value=10)
    float_field: float = Field(min_value=0.0, max_value=1.0)
    positive_int: int = Field(min_value=0)
    
    # Boolean type
    boolean_field: bool = Field()
    
    # Date and Time types
    datetime_field: datetime
    date_field: date
    time_field: time
    
    # Special string formats
    uuid_field: UUID = Field()
    ipv4_field: str = Field(pattern=r'^(\d{1,3}\.){3}\d{1,3}$')
    ipv6_field: str = Field(pattern=r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$')
    hostname_field: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9\-\.]+[a-zA-Z0-9]$')
    
    # Enum and Literal types
    status: Literal["active", "inactive", "pending"]
    role: UserRole  # Enum class
    
    # Numeric constraints
    percentage: float = Field(min_value=0.0, max_value=100.0)
    port_number: int = Field(min_value=1, max_value=65535)
```

### Container Types
``` python
class Containers(Model):
    # Lists with type constraints
    string_list: List[str]
    int_list: List[int]
    model_list: List[SubModel]
    bounded_list: List[str] = Field(min_length=1, max_length=10)
    
    # Dictionaries with various value types
    string_dict: Dict[str, str]
    int_dict: Dict[str, int]
    model_dict: Dict[str, SubModel]
    any_dict: Dict[str, Any]
    
    # Optional fields
    optional_string: Optional[str]
    optional_model: Optional[SubModel]
    
    # Nested structures
    nested_list: List[List[int]]
    nested_dict: Dict[str, Dict[str, str]]
    
    # Tuple with fixed types
    coordinates: Tuple[float, float]
    rgb_color: Tuple[int, int, int]
```

### Special Validations
``` python
class SpecialValidations(Model):
    # Credit card number
    credit_card: str = Field(pattern=r'^\d{4}(-?\d{4}){3}$')
    
    # Phone number
    phone: str = Field(pattern=r'^\+?1?\d{9,15}$')
    
    # Social security number
    ssn: str = Field(pattern=r'^\d{3}-\d{2}-\d{4}$')
    
    # Password with complexity requirements
    password: str = Field(
        pattern=r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$',
        min_length=8
    )
    
    # Currency amount
    amount: Decimal = Field(min_value=0)
    
    # File size in bytes
    file_size: int = Field(min_value=0, max_value=10_485_760)  # Max 10MB
    
    # Semantic version
    version: str = Field(pattern=r'^\d+\.\d+\.\d+$')
    
    # Color hex code
    color_hex: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
``` 