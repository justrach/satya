import os
import sys
import unittest
import json

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import satya
from satya import Model, Field, StreamValidator, ValidationResult, ValidationError, ModelValidationError


class BasicPerson(satya.Model):
    """Basic person model for testing"""
    name: str
    age: int
    email: str


class TestBasicModelFunctionality(unittest.TestCase):
    """Test core model functionality that is known to work"""

    def test_basic_model_creation(self):
        """Test basic model instantiation"""
        person = BasicPerson(name="John Doe", age=30, email="john@example.com")
        self.assertEqual(person.name, "John Doe")
        self.assertEqual(person.age, 30)
        self.assertEqual(person.email, "john@example.com")

    def test_model_validation_success(self):
        """Test successful model validation"""
        data = {"name": "Jane Doe", "age": 25, "email": "jane@example.com"}
        person = BasicPerson(**data)
        self.assertIsInstance(person, BasicPerson)

    def test_model_validation_failure(self):
        """Test model validation failure with missing required field"""
        with self.assertRaises(ModelValidationError):
            BasicPerson(name="John", age=30)  # Missing email

    def test_model_dict_access(self):
        """Test accessing model data as dictionary"""
        person = BasicPerson(name="Test", age=25, email="test@example.com")
        data_dict = person.dict()
        self.assertIsInstance(data_dict, dict)
        self.assertEqual(data_dict['name'], "Test")

    def test_model_json_methods(self):
        """Test JSON serialization methods"""
        person = BasicPerson(name="John", age=30, email="john@example.com")
        
        # Test model_dump
        dumped = person.model_dump()
        self.assertIsInstance(dumped, dict)
        self.assertEqual(dumped['name'], "John")
        
        # Test model_dump_json
        json_str = person.model_dump_json()
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed['name'], "John")

    def test_model_validate_class_method(self):
        """Test model_validate class method"""
        data = {"name": "Alice", "age": 28, "email": "alice@example.com"}
        person = BasicPerson.model_validate(data)
        self.assertEqual(person.name, "Alice")

    def test_model_validate_json_class_method(self):
        """Test model_validate_json class method"""
        data = {"name": "Bob", "age": 35, "email": "bob@example.com"}
        json_str = json.dumps(data)
        person = BasicPerson.model_validate_json(json_str)
        self.assertEqual(person.name, "Bob")

    def test_model_construct(self):
        """Test model_construct (bypasses validation)"""
        # This should work even with missing fields since it bypasses validation
        person = BasicPerson.model_construct(name="Test", age=25)
        self.assertEqual(person.name, "Test")

    def test_json_schema_generation(self):
        """Test JSON schema generation"""
        schema = BasicPerson.json_schema()
        self.assertIsInstance(schema, dict)
        self.assertEqual(schema['type'], 'object')
        self.assertIn('properties', schema)
        self.assertIn('name', schema['properties'])
        self.assertIn('age', schema['properties'])
        self.assertIn('email', schema['properties'])


class TestStreamValidatorCore(unittest.TestCase):
    """Test core StreamValidator functionality"""

    def setUp(self):
        """Set up validator for tests"""
        self.validator = StreamValidator()
        self.validator.add_field("name", str, required=True)
        self.validator.add_field("age", int, required=True)
        self.validator.add_field("email", str, required=False)

    def test_validator_creation(self):
        """Test validator creation"""
        validator = StreamValidator()
        self.assertIsInstance(validator, StreamValidator)

    def test_add_fields(self):
        """Test adding fields to validator"""
        validator = StreamValidator()
        validator.add_field("test_field", str, required=True)
        # Should not raise any exceptions

    def test_validate_single_valid_item(self):
        """Test validating single valid item"""
        data = {"name": "John", "age": 30, "email": "john@example.com"}
        result = self.validator.validate(data)
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)

    def test_validate_single_invalid_item(self):
        """Test validating single invalid item"""
        data = {"name": "John"}  # Missing required age
        result = self.validator.validate(data)
        self.assertFalse(result.is_valid)

    def test_validate_batch(self):
        """Test batch validation"""
        data = [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25, "email": "jane@example.com"},
            {"name": "Bob"}  # Missing age - invalid
        ]
        results = self.validator.validate_batch(data)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0])
        self.assertTrue(results[1])
        self.assertFalse(results[2])

    def test_validate_stream(self):
        """Test stream validation"""
        data = [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25},
        ]
        results = list(self.validator.validate_stream(data))
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.is_valid for r in results))

    def test_batch_size_settings(self):
        """Test batch size getter/setter"""
        validator = StreamValidator()
        original_size = validator.batch_size
        self.assertIsInstance(original_size, int)
        
        new_size = 50
        validator.set_batch_size(new_size)
        self.assertEqual(validator.batch_size, new_size)


class TestJSONValidationCore(unittest.TestCase):
    """Test JSON validation functionality"""

    def setUp(self):
        """Set up for JSON validation tests"""
        self.validator = BasicPerson.validator()

    def test_json_object_validation(self):
        """Test JSON object validation"""
        data = {"name": "John", "age": 30, "email": "john@example.com"}
        json_bytes = json.dumps(data).encode()
        
        result = self.validator.validate_json(json_bytes, mode="object")
        self.assertTrue(result)

    def test_json_object_validation_invalid(self):
        """Test JSON object validation with invalid data"""
        data = {"name": 123, "age": "invalid", "email": False}
        json_bytes = json.dumps(data).encode()
        
        result = self.validator.validate_json(json_bytes, mode="object")
        self.assertFalse(result)

    def test_json_array_validation(self):
        """Test JSON array validation"""
        data = [
            {"name": "John", "age": 30, "email": "john@example.com"},
            {"name": "Jane", "age": 25, "email": "jane@example.com"}
        ]
        json_bytes = json.dumps(data).encode()
        
        results = self.validator.validate_json(json_bytes, mode="array")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(results))

    def test_ndjson_validation(self):
        """Test NDJSON validation"""
        data = [
            {"name": "John", "age": 30, "email": "john@example.com"},
            {"name": "Jane", "age": 25, "email": "jane@example.com"}
        ]
        ndjson = "\n".join(json.dumps(item) for item in data).encode()
        
        results = self.validator.validate_json(ndjson, mode="ndjson")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(results))

    def test_streaming_validation(self):
        """Test streaming vs non-streaming validation"""
        data = {"name": "John", "age": 30, "email": "john@example.com"}
        json_bytes = json.dumps(data).encode()
        
        result1 = self.validator.validate_json(json_bytes, mode="object", streaming=False)
        result2 = self.validator.validate_json(json_bytes, mode="object", streaming=True)
        
        self.assertEqual(result1, result2)
        self.assertTrue(result1)


class TestValidationResults(unittest.TestCase):
    """Test ValidationResult and ValidationError classes"""

    def test_valid_result(self):
        """Test valid ValidationResult"""
        data = {"test": "value"}
        result = ValidationResult(value=data)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, data)
        self.assertEqual(len(result.errors), 0)

    def test_invalid_result(self):
        """Test invalid ValidationResult"""
        error = ValidationError(field="test", message="error", path=[])
        result = ValidationResult(errors=[error])
        
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        
        # Should raise when accessing value
        with self.assertRaises(ValueError):
            _ = result.value

    def test_validation_error_string(self):
        """Test ValidationError string representation"""
        error = ValidationError(field="name", message="required", path=["user", "name"])
        error_str = str(error)
        
        self.assertIn("user.name", error_str)
        self.assertIn("required", error_str)

    def test_validation_result_string(self):
        """Test ValidationResult string representation"""
        valid_result = ValidationResult(value={"name": "John"})
        valid_str = str(valid_result)
        self.assertIn("Valid", valid_str)
        
        error = ValidationError(field="name", message="required", path=[])
        invalid_result = ValidationResult(errors=[error])
        invalid_str = str(invalid_result)
        self.assertIn("Invalid", invalid_str)


class TestModuleImports(unittest.TestCase):
    """Test module imports and version"""

    def test_version_attribute(self):
        """Test that __version__ is accessible"""
        self.assertTrue(hasattr(satya, '__version__'))
        self.assertIsInstance(satya.__version__, str)

    def test_core_classes_importable(self):
        """Test that core classes can be imported"""
        self.assertTrue(hasattr(satya, 'Model'))
        self.assertTrue(hasattr(satya, 'Field'))
        self.assertTrue(hasattr(satya, 'StreamValidator'))
        self.assertTrue(hasattr(satya, 'ValidationResult'))
        self.assertTrue(hasattr(satya, 'ValidationError'))
        self.assertTrue(hasattr(satya, 'ModelValidationError'))

    def test_lazy_imports(self):
        """Test lazy import functionality"""
        # These should work through the __getattr__ mechanism
        sv = satya.StreamValidator()
        self.assertIsInstance(sv, satya.StreamValidator)
        
        svc = satya.StreamValidatorCore
        self.assertIsNotNone(svc)


if __name__ == '__main__':
    unittest.main()
