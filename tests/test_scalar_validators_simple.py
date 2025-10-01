"""
Simple tests for scalar validators to ensure Rust-backed validation works.
"""

import os
import sys
import unittest
import time

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from satya import (
    StringValidator,
    IntValidator,
    NumberValidator,
    BooleanValidator,
)


class TestStringValidator(unittest.TestCase):
    """Tests for StringValidator"""
    
    def test_basic_string_validation(self):
        """Test basic string type checking"""
        validator = StringValidator()
        result = validator.validate("hello")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, "hello")
    
    def test_min_length(self):
        """Test minimum length constraint"""
        validator = StringValidator(min_length=5)
        self.assertTrue(validator.validate("hello").is_valid)
        self.assertFalse(validator.validate("hi").is_valid)
    
    def test_pattern(self):
        """Test regex pattern constraint"""
        validator = StringValidator(pattern=r'^[a-z]+$')
        self.assertTrue(validator.validate("hello").is_valid)
        self.assertFalse(validator.validate("hello123").is_valid)
    
    def test_batch_validation(self):
        """Test batch validation"""
        validator = StringValidator(min_length=3)
        values = ["hello", "hi", "world"]
        results = validator.validate_batch(values)
        
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0].is_valid)  # "hello"
        self.assertFalse(results[1].is_valid)  # "hi" - too short
        self.assertTrue(results[2].is_valid)  # "world"


class TestIntValidator(unittest.TestCase):
    """Tests for IntValidator"""
    
    def test_basic_int_validation(self):
        """Test basic integer type checking"""
        validator = IntValidator()
        result = validator.validate(42)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.value, 42)
    
    def test_ge_constraint(self):
        """Test greater than or equal constraint"""
        validator = IntValidator(ge=0)
        self.assertTrue(validator.validate(0).is_valid)
        self.assertTrue(validator.validate(1).is_valid)
        self.assertFalse(validator.validate(-1).is_valid)
    
    def test_combined_constraints(self):
        """Test multiple constraints together"""
        validator = IntValidator(ge=0, le=100)
        self.assertTrue(validator.validate(50).is_valid)
        self.assertFalse(validator.validate(-1).is_valid)
        self.assertFalse(validator.validate(101).is_valid)


class TestNumberValidator(unittest.TestCase):
    """Tests for NumberValidator"""
    
    def test_basic_number_validation(self):
        """Test basic number type checking"""
        validator = NumberValidator()
        self.assertTrue(validator.validate(42).is_valid)
        self.assertTrue(validator.validate(42.5).is_valid)
    
    def test_ge_constraint(self):
        """Test greater than or equal constraint"""
        validator = NumberValidator(ge=0.0)
        self.assertTrue(validator.validate(0.0).is_valid)
        self.assertTrue(validator.validate(0.1).is_valid)
        self.assertFalse(validator.validate(-0.1).is_valid)


class TestBooleanValidator(unittest.TestCase):
    """Tests for BooleanValidator"""
    
    def test_basic_boolean_validation(self):
        """Test basic boolean type checking"""
        validator = BooleanValidator()
        self.assertTrue(validator.validate(True).is_valid)
        self.assertTrue(validator.validate(False).is_valid)
    
    def test_boolean_rejects_non_boolean(self):
        """Test that non-booleans are rejected"""
        validator = BooleanValidator()
        self.assertFalse(validator.validate(1).is_valid)
        self.assertFalse(validator.validate("true").is_valid)


class TestPerformance(unittest.TestCase):
    """Basic performance tests to ensure Rust backend is being used"""
    
    def test_string_batch_performance(self):
        """Test that batch validation is fast (indicates Rust is being used)"""
        validator = StringValidator(min_length=3, max_length=100)
        values = ["test" + str(i) for i in range(1000)]
        
        start = time.time()
        results = validator.validate_batch(values)
        duration = time.time() - start
        
        self.assertEqual(len(results), 1000)
        self.assertTrue(all(r.is_valid for r in results))
        # Should complete very quickly if using Rust
        print(f"Validated 1000 strings in {duration:.4f}s")


if __name__ == '__main__':
    unittest.main()
