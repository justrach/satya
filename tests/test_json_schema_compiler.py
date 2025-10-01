"""
Tests for JSON Schema compiler.

Tests the compile_json_schema function that converts JSON Schema documents
into high-performance Satya validators.
"""

import os
import sys
import unittest

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from satya import compile_json_schema, JSONSchemaCompiler


class TestJSONSchemaCompiler(unittest.TestCase):
    """Tests for JSON Schema compiler"""
    
    def test_compile_string_schema(self):
        """Test compiling a basic string schema"""
        schema = {"type": "string"}
        validator = compile_json_schema(schema)
        
        # Valid
        result = validator.validate("hello")
        self.assertTrue(result.is_valid)
        
        # Invalid
        result = validator.validate(123)
        self.assertFalse(result.is_valid)
    
    def test_compile_string_with_length(self):
        """Test string schema with length constraints"""
        schema = {
            "type": "string",
            "minLength": 3,
            "maxLength": 10
        }
        validator = compile_json_schema(schema)
        
        # Valid
        self.assertTrue(validator.validate("hello").is_valid)
        
        # Too short
        self.assertFalse(validator.validate("hi").is_valid)
        
        # Too long
        self.assertFalse(validator.validate("hello world!").is_valid)
    
    def test_compile_string_with_pattern(self):
        """Test string schema with regex pattern"""
        schema = {
            "type": "string",
            "pattern": "^[a-z]+$"
        }
        validator = compile_json_schema(schema)
        
        # Valid
        self.assertTrue(validator.validate("hello").is_valid)
        
        # Invalid - contains numbers
        self.assertFalse(validator.validate("hello123").is_valid)
    
    def test_compile_string_email_format(self):
        """Test string schema with email format"""
        schema = {
            "type": "string",
            "format": "email"
        }
        validator = compile_json_schema(schema)
        
        # Valid
        self.assertTrue(validator.validate("user@example.com").is_valid)
        
        # Invalid
        self.assertFalse(validator.validate("not-an-email").is_valid)
    
    def test_compile_integer_schema(self):
        """Test compiling an integer schema"""
        schema = {"type": "integer"}
        validator = compile_json_schema(schema)
        
        # Valid
        self.assertTrue(validator.validate(42).is_valid)
        
        # Invalid
        self.assertFalse(validator.validate("42").is_valid)
        self.assertFalse(validator.validate(True).is_valid)
    
    def test_compile_integer_with_bounds(self):
        """Test integer schema with min/max"""
        schema = {
            "type": "integer",
            "minimum": 0,
            "maximum": 100
        }
        validator = compile_json_schema(schema)
        
        # Valid
        self.assertTrue(validator.validate(50).is_valid)
        self.assertTrue(validator.validate(0).is_valid)
        self.assertTrue(validator.validate(100).is_valid)
        
        # Invalid
        self.assertFalse(validator.validate(-1).is_valid)
        self.assertFalse(validator.validate(101).is_valid)
    
    def test_compile_integer_with_exclusive_bounds(self):
        """Test integer schema with exclusive bounds"""
        schema = {
            "type": "integer",
            "exclusiveMinimum": 0,
            "exclusiveMaximum": 100
        }
        validator = compile_json_schema(schema)
        
        # Valid
        self.assertTrue(validator.validate(50).is_valid)
        self.assertTrue(validator.validate(1).is_valid)
        self.assertTrue(validator.validate(99).is_valid)
        
        # Invalid
        self.assertFalse(validator.validate(0).is_valid)
        self.assertFalse(validator.validate(100).is_valid)
    
    def test_compile_number_schema(self):
        """Test compiling a number (float) schema"""
        schema = {"type": "number"}
        validator = compile_json_schema(schema)
        
        # Valid
        self.assertTrue(validator.validate(42.5).is_valid)
        self.assertTrue(validator.validate(42).is_valid)
        
        # Invalid
        self.assertFalse(validator.validate("42.5").is_valid)
        self.assertFalse(validator.validate(True).is_valid)
    
    def test_compile_boolean_schema(self):
        """Test compiling a boolean schema"""
        schema = {"type": "boolean"}
        validator = compile_json_schema(schema)
        
        # Valid
        self.assertTrue(validator.validate(True).is_valid)
        self.assertTrue(validator.validate(False).is_valid)
        
        # Invalid
        self.assertFalse(validator.validate(1).is_valid)
        self.assertFalse(validator.validate("true").is_valid)
    
    def test_compile_array_schema(self):
        """Test compiling an array schema"""
        schema = {
            "type": "array",
            "items": {"type": "string"}
        }
        validator = compile_json_schema(schema)
        
        # Valid
        self.assertTrue(validator.validate(["a", "b", "c"]).is_valid)
        
        # Invalid - contains non-string
        self.assertFalse(validator.validate([1, 2, 3]).is_valid)
    
    def test_compile_array_with_constraints(self):
        """Test array schema with min/max items"""
        schema = {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 1,
            "maxItems": 5
        }
        validator = compile_json_schema(schema)
        
        # Valid
        self.assertTrue(validator.validate([1, 2, 3]).is_valid)
        
        # Too few items
        self.assertFalse(validator.validate([]).is_valid)
        
        # Too many items
        self.assertFalse(validator.validate([1, 2, 3, 4, 5, 6]).is_valid)
    
    def test_compile_array_unique_items(self):
        """Test array schema with uniqueItems"""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "uniqueItems": True
        }
        validator = compile_json_schema(schema)
        
        # Valid - unique items
        self.assertTrue(validator.validate(["a", "b", "c"]).is_valid)
        
        # Invalid - duplicate items
        self.assertFalse(validator.validate(["a", "b", "a"]).is_valid)
    
    def test_optimization_stats(self):
        """Test that optimization stats are tracked"""
        compiler = JSONSchemaCompiler()
        
        # Compile several schemas
        compiler.compile({"type": "string"})
        compiler.compile({"type": "integer"})
        compiler.compile({"type": "number"})
        
        report = compiler.get_optimization_report()
        self.assertEqual(report["total_schemas"], 3)
        self.assertEqual(report["rust_optimized"], 3)
        self.assertEqual(report["python_fallback"], 0)
        self.assertEqual(report["optimization_percentage"], 100.0)
    
    def test_invalid_schema_type(self):
        """Test that invalid schema types raise errors"""
        with self.assertRaises(ValueError):
            compile_json_schema({"type": "invalid_type"})
    
    def test_object_schema_not_implemented(self):
        """Test that object schemas raise NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            compile_json_schema({"type": "object"})


class TestPoetryUseCase(unittest.TestCase):
    """Tests simulating Poetry's JSON Schema validation use cases"""
    
    def test_package_name_validation(self):
        """Test validating package names (Poetry use case)"""
        schema = {
            "type": "string",
            "pattern": "^[a-zA-Z0-9]([a-zA-Z0-9_-]*[a-zA-Z0-9])?$"
        }
        validator = compile_json_schema(schema)
        
        # Valid package names
        self.assertTrue(validator.validate("requests").is_valid)
        self.assertTrue(validator.validate("numpy-ext").is_valid)
        self.assertTrue(validator.validate("my_package").is_valid)
        
        # Invalid package names
        self.assertFalse(validator.validate("-invalid").is_valid)
        self.assertFalse(validator.validate("invalid-").is_valid)
    
    def test_version_string_validation(self):
        """Test validating version strings"""
        schema = {
            "type": "string",
            "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
        }
        validator = compile_json_schema(schema)
        
        # Valid versions
        self.assertTrue(validator.validate("1.2.3").is_valid)
        self.assertTrue(validator.validate("0.1.0").is_valid)
        
        # Invalid versions
        self.assertFalse(validator.validate("1.2").is_valid)
        self.assertFalse(validator.validate("invalid").is_valid)
    
    def test_python_version_constraint(self):
        """Test Python version constraints"""
        schema = {
            "type": "string",
            "pattern": "^[><=!]+[0-9.]+$"
        }
        validator = compile_json_schema(schema)
        
        # Valid constraints
        self.assertTrue(validator.validate(">=3.8").is_valid)
        self.assertTrue(validator.validate("<4.0").is_valid)
        
        # Invalid
        self.assertFalse(validator.validate("invalid").is_valid)


if __name__ == '__main__':
    unittest.main()
