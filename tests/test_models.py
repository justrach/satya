import os
import sys
import unittest
from typing import List, Optional, Dict, Any

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import satya
from satya import Model, Field, ValidationError, ValidationResult, ModelValidationError

class Address(Model):
    """Address model used by Person"""
    street: str = Field(min_length=1)
    city: str = Field(min_length=1)
    postal_code: str = Field(pattern=r"^\d{5}$")

class Person(Model):
    """Comprehensive Person model used across tests"""
    name: str = Field(min_length=2, max_length=50)
    age: int = Field(ge=0, le=150)
    email: str = Field(email=True)
    website: str = Field(required=False, url=True)
    address: Address = Field()
    tags: List[str] = Field(default=[], max_items=10)
    metadata: Dict[str, str] = Field(default={})

class Product(Model):
    """Product model with enum category"""
    name: str = Field(min_length=1)
    category: str = Field(enum=["electronics", "clothing", "books"])
    price: float = Field(gt=0.0)
    in_stock: bool = Field(default=True)


class SimplePerson(Model):
    """Test model with basic field types"""
    name: str
    age: int
    email: str


class ProductWithDefaults(Model):
    """Test model with default values"""
    name: str
    price: float
    in_stock: bool = Field(default=True)


class TestModelCreation(unittest.TestCase):
    """Test basic model creation and instantiation"""

    def test_simple_model_creation(self):
        """Test creating a simple model instance"""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            }
        }
        person = Person(**data)
        self.assertEqual(person.name, "John Doe")
        self.assertEqual(person.age, 30)
        self.assertEqual(person.email, "john@example.com")
        self.assertEqual(person.address.street, "123 Main St")

    def test_model_with_defaults(self):
        """Test model creation with default values"""
        data = {
            "name": "Jane Doe",
            "age": 25,
            "email": "jane@example.com",
            "address": {
                "street": "456 Oak St",
                "city": "Somewhere",
                "postal_code": "67890"
            }
        }
        person = Person(**data)
        self.assertEqual(person.tags, [])
        self.assertEqual(person.metadata, {})

    def test_optional_fields(self):
        """Test model with optional fields"""
        data = {
            "name": "Bob Smith",
            "age": 35,
            "email": "bob@example.com",
            "website": "https://bobsmith.com",
            "address": {
                "street": "789 Pine St",
                "city": "Elsewhere",
                "postal_code": "54321"
            }
        }
        person = Person(**data)
        self.assertEqual(person.website, "https://bobsmith.com")

    def test_enum_field_validation(self):
        """Test enum field constraints"""
        valid_product = Product(
            name="Laptop",
            category="electronics",
            price=999.99
        )
        self.assertEqual(valid_product.category, "electronics")
        self.assertEqual(valid_product.in_stock, True)  # default value

    def test_model_dict_access(self):
        """Test dict-like access to model data"""
        data = {
            "name": "Test User",
            "age": 28,
            "email": "test@example.com",
            "address": {
                "street": "Test St",
                "city": "Test City",
                "postal_code": "12345"
            }
        }
        person = Person(**data)
        self.assertEqual(person.__dict__['name'], "Test User")
        self.assertEqual(person.dict()['age'], 28)


class TestModelValidation(unittest.TestCase):
    """Test model validation functionality"""

    def test_required_field_missing(self):
        """Test validation fails when required field is missing"""
        data = {
            "name": "John Doe",
            # age is missing
            "email": "john@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            }
        }
        with self.assertRaises(ModelValidationError):
            Person(**data)

    def test_field_length_constraints(self):
        """Test string length validation"""
        # Test min_length violation
        data = {
            "name": "J",  # Too short (min_length=2)
            "age": 30,
            "email": "j@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            }
        }
        with self.assertRaises(ModelValidationError):
            Person(**data)

        # Test max_length violation
        data["name"] = "J" * 60  # Too long (max_length=50)
        with self.assertRaises(ModelValidationError):
            Person(**data)

    def test_numeric_constraints(self):
        """Test numeric field constraints"""
        # Test age too low
        data = {
            "name": "John Doe",
            "age": -5,  # Below minimum (ge=0)
            "email": "john@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            }
        }
        with self.assertRaises(ModelValidationError):
            Person(**data)

        # Test age too high
        data["age"] = 200  # Above maximum (le=150)
        with self.assertRaises(ModelValidationError):
            Person(**data)

    def test_email_validation(self):
        """Test email field validation"""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "invalid-email",  # Invalid email format
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            }
        }
        with self.assertRaises(ModelValidationError):
            Person(**data)

    def test_pattern_validation(self):
        """Test regex pattern validation"""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "invalid"  # Should match postal code pattern
            }
        }
        with self.assertRaises(ModelValidationError):
            Person(**data)

    def test_enum_validation(self):
        """Test enum field validation"""
        with self.assertRaises(ModelValidationError):
            Product(
                name="Invalid Product",
                category="invalid_category",  # Not in enum list
                price=99.99
            )

    def test_url_validation(self):
        """Test URL field validation"""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "website": "not-a-url",  # Invalid URL
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            }
        }
        with self.assertRaises(ModelValidationError):
            Person(**data)

    def test_list_constraints(self):
        """Test list field constraints"""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            },
            "tags": ["tag" + str(i) for i in range(15)]  # Too many items (max_items=10)
        }
        with self.assertRaises(ModelValidationError):
            Person(**data)


class TestModelAPI(unittest.TestCase):
    """Test Pydantic-like API methods"""

    def test_model_validate(self):
        """Test model_validate class method"""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            }
        }
        person = Person.model_validate(data)
        self.assertIsInstance(person, Person)
        self.assertEqual(person.name, "John Doe")

    def test_model_validate_json(self):
        """Test model_validate_json class method"""
        json_data = '''
        {
            "name": "Jane Doe",
            "age": 25,
            "email": "jane@example.com",
            "address": {
                "street": "456 Oak St",
                "city": "Somewhere",
                "postal_code": "67890"
            }
        }
        '''
        person = Person.model_validate_json(json_data)
        self.assertIsInstance(person, Person)
        self.assertEqual(person.name, "Jane Doe")

    def test_model_dump(self):
        """Test model_dump method"""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            }
        }
        person = Person(**data)
        dumped = person.model_dump()
        self.assertIsInstance(dumped, dict)
        self.assertEqual(dumped['name'], "John Doe")

    def test_model_dump_json(self):
        """Test model_dump_json method"""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            }
        }
        person = Person(**data)
        json_str = person.model_dump_json()
        self.assertIsInstance(json_str, str)
        # Should be valid JSON
        import json
        parsed = json.loads(json_str)
        self.assertEqual(parsed['name'], "John Doe")

    def test_model_construct(self):
        """Test model_construct method (no validation)"""
        # This should work even with invalid data since it skips validation
        data = {
            "name": "J",  # Would normally fail min_length validation
            "age": -5,    # Would normally fail ge validation
            "email": "invalid-email",  # Would fail email validation
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "invalid"  # Would fail pattern validation
            }
        }
        person = Person.model_construct(**data)
        self.assertEqual(person.name, "J")
        self.assertEqual(person.age, -5)

    def test_parse_obj_compatibility(self):
        """Test Pydantic v1 compatibility methods"""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "postal_code": "12345"
            }
        }
        person = Person.parse_obj(data)
        self.assertIsInstance(person, Person)
        self.assertEqual(person.name, "John Doe")

    def test_parse_raw_compatibility(self):
        """Test Pydantic v1 parse_raw compatibility"""
        json_data = '''
        {
            "name": "Jane Doe",
            "age": 25,
            "email": "jane@example.com",
            "address": {
                "street": "456 Oak St",
                "city": "Somewhere",
                "postal_code": "67890"
            }
        }
        '''
        person = Person.parse_raw(json_data)
        self.assertIsInstance(person, Person)
        self.assertEqual(person.name, "Jane Doe")


class TestJSONSchema(unittest.TestCase):
    """Test JSON Schema generation"""

    def test_json_schema_generation(self):
        """Test JSON schema is properly generated"""
        schema = Person.json_schema()
        self.assertIsInstance(schema, dict)
        self.assertEqual(schema['type'], 'object')
        self.assertEqual(schema['title'], 'Person')
        self.assertIn('properties', schema)
        self.assertIn('required', schema)

    def test_schema_field_properties(self):
        """Test field properties in schema"""
        schema = Person.json_schema()
        properties = schema['properties']
        
        # Test name field properties
        name_schema = properties['name']
        self.assertEqual(name_schema['type'], 'string')
        self.assertEqual(name_schema['minLength'], 2)
        self.assertEqual(name_schema['maxLength'], 50)
        
        # Test age field properties
        age_schema = properties['age']
        self.assertEqual(age_schema['type'], 'integer')
        self.assertEqual(age_schema['minimum'], 0)
        self.assertEqual(age_schema['maximum'], 150)
        
        # Test email field
        email_schema = properties['email']
        self.assertEqual(email_schema['type'], 'string')
        self.assertEqual(email_schema['format'], 'email')

    def test_required_fields_in_schema(self):
        """Test required fields are listed in schema"""
        schema = Person.json_schema()
        required = schema['required']
        self.assertIn('name', required)
        self.assertIn('age', required)
        self.assertIn('email', required)
        self.assertIn('address', required)
        # website is optional, should not be in required
        self.assertNotIn('website', required)

    def test_model_json_schema_alias(self):
        """Test model_json_schema alias method"""
        schema1 = Person.json_schema()
        schema2 = Person.model_json_schema()
        self.assertEqual(schema1, schema2)


if __name__ == '__main__':
    unittest.main()
