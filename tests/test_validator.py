import os
import sys
import unittest
from typing import List, Dict, Any, Iterator
import json

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import satya
from satya import StreamValidator, ValidationResult, ValidationError


class TestStreamValidator(unittest.TestCase):
    """Test StreamValidator functionality"""

    def setUp(self):
        """Set up test validator with common fields"""
        self.validator = StreamValidator()
        self.validator.add_field("name", str, required=True)
        self.validator.add_field("age", int, required=True)
        self.validator.add_field("email", str, required=False)
        self.validator.add_field("active", bool, required=False)

    def test_validator_creation(self):
        """Test basic validator creation"""
        validator = StreamValidator()
        self.assertIsInstance(validator, StreamValidator)
        self.assertIsNotNone(validator._core)

    def test_add_field_basic_types(self):
        """Test adding fields with basic types"""
        validator = StreamValidator()
        validator.add_field("name", str, required=True)
        validator.add_field("age", int, required=True)
        validator.add_field("score", float, required=False)
        validator.add_field("active", bool, required=False)
        
        # These shouldn't raise exceptions
        self.assertTrue(True)

    def test_add_field_complex_types(self):
        """Test adding fields with complex types"""
        validator = StreamValidator()
        validator.add_field("tags", List[str], required=False)
        validator.add_field("metadata", Dict[str, str], required=False)
        validator.add_field("scores", List[int], required=False)
        
        # These shouldn't raise exceptions
        self.assertTrue(True)

    def test_validate_single_valid_item(self):
        """Test validating a single valid item"""
        data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "active": True
        }
        result = self.validator.validate(data)
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, data)
        self.assertEqual(len(result.errors), 0)

    def test_validate_single_invalid_item(self):
        """Test validating a single invalid item"""
        data = {
            "name": "John Doe",
            # Missing required 'age' field
            "email": "john@example.com"
        }
        result = self.validator.validate(data)
        self.assertIsInstance(result, ValidationResult)
        self.assertFalse(result.is_valid)
        self.assertTrue(len(result.errors) > 0)

    def test_validate_batch(self):
        """Test batch validation"""
        data = [
            {"name": "John", "age": 30, "email": "john@example.com"},
            {"name": "Jane", "age": 25},  # Missing email is OK (not required)
            {"name": "Bob"},  # Missing age - should be invalid
        ]
        results = self.validator.validate_batch(data)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0])  # First item valid
        self.assertTrue(results[1])  # Second item valid
        self.assertFalse(results[2])  # Third item invalid (missing age)

    def test_validate_stream(self):
        """Test stream validation"""
        data = [
            {"name": "John", "age": 30, "email": "john@example.com"},
            {"name": "Jane", "age": 25},
            {"name": "Bob"},  # Invalid
            {"name": "Alice", "age": 28, "active": False}
        ]
        
        results = list(self.validator.validate_stream(data))
        valid_results = [r for r in results if r.is_valid]
        self.assertEqual(len(valid_results), 3)  # 3 valid items
        
        # Test with collect_errors=True
        all_results = list(self.validator.validate_stream(data, collect_errors=True))
        self.assertEqual(len(all_results), 4)  # All items including invalid

    def test_batch_size_property(self):
        """Test batch size getter and setter"""
        validator = StreamValidator()
        
        # Test getting default batch size
        default_size = validator.batch_size
        self.assertIsInstance(default_size, int)
        self.assertGreater(default_size, 0)
        
        # Test setting batch size
        new_size = 100
        validator.set_batch_size(new_size)
        self.assertEqual(validator.batch_size, new_size)

    def test_field_constraints(self):
        """Test setting field constraints"""
        validator = StreamValidator()
        validator.add_field("username", str, required=True)
        
        # Set various constraints
        validator.set_constraints(
            "username",
            min_length=3,
            max_length=20,
            pattern=r"^[a-zA-Z0-9_]+$"
        )
        
        # Test valid data
        valid_data = {"username": "john_doe123"}
        result = validator.validate(valid_data)
        self.assertTrue(result.is_valid)

    def test_custom_type_definition(self):
        """Test defining custom types"""
        validator = StreamValidator()
        
        # Define a custom Address type
        validator.define_custom_type("Address")
        validator.add_field_to_custom_type("Address", "street", str, required=True)
        validator.add_field_to_custom_type("Address", "city", str, required=True)
        validator.add_field_to_custom_type("Address", "zipcode", str, required=False)
        
        # Add field using custom type
        validator.add_field("address", "Address", required=True)
        
        # This should not raise an exception
        self.assertTrue(True)

    def test_define_type_helper(self):
        """Test the define_type compatibility helper"""
        validator = StreamValidator()
        
        # Define type using the helper method
        validator.define_type("Person", {
            "name": str,
            "age": int,
            "email": str
        })
        
        # This should not raise an exception
        self.assertTrue(True)


class TestJSONValidation(unittest.TestCase):
    """Test JSON bytes/string validation functionality"""

    def setUp(self):
        """Set up test model and validator"""
        class Person(satya.Model):
            name: str
            age: int
            email: str
        
        self.Person = Person
        self.validator = Person.validator()

    def test_validate_json_object_bytes(self):
        """Test validating JSON object from bytes"""
        data = {"name": "John Doe", "age": 30, "email": "john@example.com"}
        json_bytes = json.dumps(data).encode('utf-8')
        
        result = self.validator.validate_json(json_bytes, mode="object")
        self.assertTrue(result)

    def test_validate_json_object_string(self):
        """Test validating JSON object from string"""
        data = {"name": "John Doe", "age": 30, "email": "john@example.com"}
        json_str = json.dumps(data)
        
        result = self.validator.validate_json(json_str, mode="object")
        self.assertTrue(result)

    def test_validate_invalid_json_object(self):
        """Test validating invalid JSON object"""
        invalid_data = {"name": 123, "age": "thirty", "email": False}
        json_bytes = json.dumps(invalid_data).encode('utf-8')
        
        result = self.validator.validate_json(json_bytes, mode="object")
        self.assertFalse(result)

    def test_validate_json_array(self):
        """Test validating JSON array"""
        data = [
            {"name": "John", "age": 30, "email": "john@example.com"},
            {"name": "Jane", "age": 25, "email": "jane@example.com"},
            {"name": "Invalid", "age": "wrong", "email": "bad"}  # Invalid item
        ]
        json_bytes = json.dumps(data).encode('utf-8')
        
        results = self.validator.validate_json(json_bytes, mode="array")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0])  # First item valid
        self.assertTrue(results[1])  # Second item valid
        self.assertFalse(results[2])  # Third item invalid

    def test_validate_ndjson(self):
        """Test validating NDJSON (newline-delimited JSON)"""
        data = [
            {"name": "John", "age": 30, "email": "john@example.com"},
            {"name": "Jane", "age": 25, "email": "jane@example.com"},
            {"name": "Invalid", "age": "wrong", "email": "bad"}
        ]
        ndjson = "\n".join(json.dumps(item) for item in data).encode('utf-8')
        
        results = self.validator.validate_json(ndjson, mode="ndjson")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0])
        self.assertTrue(results[1])
        self.assertFalse(results[2])

    def test_validate_json_streaming_mode(self):
        """Test streaming JSON validation"""
        data = {"name": "John Doe", "age": 30, "email": "john@example.com"}
        json_bytes = json.dumps(data).encode('utf-8')
        
        # Test streaming mode
        result_streaming = self.validator.validate_json(json_bytes, mode="object", streaming=True)
        result_normal = self.validator.validate_json(json_bytes, mode="object", streaming=False)
        
        # Both should give same result
        self.assertEqual(result_streaming, result_normal)
        self.assertTrue(result_streaming)

    def test_validate_json_wrong_mode(self):
        """Test validation with wrong mode raises error"""
        data = [{"name": "John", "age": 30, "email": "john@example.com"}]
        json_bytes = json.dumps(data).encode('utf-8')
        
        # Array data with object mode should raise error
        with self.assertRaises(ValueError):
            self.validator.validate_json(json_bytes, mode="object")

    def test_validate_json_invalid_mode(self):
        """Test validation with invalid mode raises error"""
        data = {"name": "John", "age": 30, "email": "john@example.com"}
        json_bytes = json.dumps(data).encode('utf-8')
        
        with self.assertRaises(ValueError):
            self.validator.validate_json(json_bytes, mode="invalid_mode")

    def test_empty_json_array(self):
        """Test validating empty JSON array"""
        json_bytes = b"[]"
        results = self.validator.validate_json(json_bytes, mode="array")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)

    def test_empty_ndjson(self):
        """Test validating empty NDJSON"""
        json_bytes = b""
        results = self.validator.validate_json(json_bytes, mode="ndjson")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)

    def test_malformed_json(self):
        """Test handling malformed JSON"""
        malformed_json = b'{"name": "John", "age": 30, "email":}'  # Missing value
        
        with self.assertRaises(Exception):
            self.validator.validate_json(malformed_json, mode="object")


class TestValidationResults(unittest.TestCase):
    """Test ValidationResult and ValidationError classes"""

    def test_validation_result_valid(self):
        """Test ValidationResult for valid data"""
        value = {"name": "John", "age": 30}
        result = ValidationResult(value=value)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, value)
        self.assertEqual(len(result.errors), 0)

    def test_validation_result_invalid(self):
        """Test ValidationResult for invalid data"""
        errors = [ValidationError(field="age", message="required field missing", path=["age"])]
        result = ValidationResult(errors=errors)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].field, "age")

    def test_validation_result_value_access_invalid(self):
        """Test accessing value on invalid result raises error"""
        errors = [ValidationError(field="age", message="required field missing", path=["age"])]
        result = ValidationResult(errors=errors)
        
        with self.assertRaises(ValueError):
            _ = result.value

    def test_validation_error_str(self):
        """Test ValidationError string representation"""
        error = ValidationError(field="email", message="invalid format", path=["user", "email"])
        error_str = str(error)
        
        self.assertIn("user.email", error_str)
        self.assertIn("invalid format", error_str)

    def test_validation_error_no_path(self):
        """Test ValidationError without path"""
        error = ValidationError(field="root", message="validation failed", path=[])
        error_str = str(error)
        
        self.assertIn("root", error_str)
        self.assertIn("validation failed", error_str)

    def test_validation_result_str_valid(self):
        """Test ValidationResult string representation for valid result"""
        value = {"name": "John"}
        result = ValidationResult(value=value)
        result_str = str(result)
        
        self.assertIn("Valid", result_str)
        self.assertIn("John", result_str)

    def test_validation_result_str_invalid(self):
        """Test ValidationResult string representation for invalid result"""
        errors = [
            ValidationError(field="age", message="required", path=["age"]),
            ValidationError(field="email", message="invalid", path=["email"])
        ]
        result = ValidationResult(errors=errors)
        result_str = str(result)
        
        self.assertIn("Invalid", result_str)
        self.assertIn("age", result_str)
        self.assertIn("email", result_str)


if __name__ == '__main__':
    unittest.main()
