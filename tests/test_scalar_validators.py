"""
Tests for scalar validators (StringValidator, IntValidator, NumberValidator, BooleanValidator).

These validators use Rust-backed validation via StreamValidatorCore.
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
    
    def test_string_rejects_non_string(self):
        """Test that non-strings are rejected"""
        validator = StringValidator()
        result = validator.validate(123)
        assert not result.is_valid
        assert "Expected string" in result.errors[0].message
    
    def test_min_length(self):
        """Test minimum length constraint"""
        validator = StringValidator(min_length=5)
        
        # Valid
        assert validator.validate("hello").is_valid
        assert validator.validate("hello world").is_valid
        
        # Invalid - too short
        result = validator.validate("hi")
        assert not result.is_valid
        assert "shorter than min_length" in result.errors[0].message.lower()
    
    def test_max_length(self):
        """Test maximum length constraint"""
        validator = StringValidator(max_length=10)
        
        # Valid
        assert validator.validate("hello").is_valid
        assert validator.validate("1234567890").is_valid
        
        # Invalid - too long
        result = validator.validate("hello world!")
        assert not result.is_valid
        assert "longer than max_length" in result.errors[0].message.lower()
    
    def test_pattern(self):
        """Test regex pattern constraint"""
        validator = StringValidator(pattern=r'^[a-z]+$')
        
        # Valid
        assert validator.validate("hello").is_valid
        assert validator.validate("abc").is_valid
        
        # Invalid - contains numbers
        result = validator.validate("hello123")
        assert not result.is_valid
        assert "does not match pattern" in result.errors[0].message.lower()
    
    def test_email(self):
        """Test email validation"""
        validator = StringValidator(email=True)
        
        # Valid
        assert validator.validate("test@example.com").is_valid
        assert validator.validate("user.name+tag@example.co.uk").is_valid
        
        # Invalid
        result = validator.validate("not-an-email")
        assert not result.is_valid
        assert "email" in result.errors[0].message.lower()
    
    def test_url(self):
        """Test URL validation"""
        validator = StringValidator(url=True)
        
        # Valid
        assert validator.validate("https://example.com").is_valid
        assert validator.validate("http://localhost:8080/path").is_valid
        
        # Invalid
        result = validator.validate("not-a-url")
        assert not result.is_valid
        assert "url" in result.errors[0].message.lower()
    
    def test_enum(self):
        """Test enum constraint"""
        validator = StringValidator(enum=["red", "green", "blue"])
        
        # Valid
        assert validator.validate("red").is_valid
        assert validator.validate("blue").is_valid
        
        # Invalid
        result = validator.validate("yellow")
        assert not result.is_valid
        assert "enum" in result.errors[0].message.lower()
    
    def test_batch_validation(self):
        """Test batch validation"""
        validator = StringValidator(min_length=3)
        values = ["hello", "hi", "world", "a"]
        results = validator.validate_batch(values)
        
        assert len(results) == 4
        assert results[0].is_valid  # "hello"
        assert not results[1].is_valid  # "hi" - too short
        assert results[2].is_valid  # "world"
        assert not results[3].is_valid  # "a" - too short


class TestIntValidator:
    """Tests for IntValidator"""
    
    def test_basic_int_validation(self):
        """Test basic integer type checking"""
        validator = IntValidator()
        result = validator.validate(42)
        assert result.is_valid
        assert result.value == 42
    
    def test_int_rejects_non_int(self):
        """Test that non-integers are rejected"""
        validator = IntValidator()
        result = validator.validate("123")
        assert not result.is_valid
        assert "Expected integer" in result.errors[0].message
    
    def test_int_rejects_bool(self):
        """Test that booleans are rejected (even though bool is subclass of int)"""
        validator = IntValidator()
        result = validator.validate(True)
        assert not result.is_valid
        assert "Expected integer" in result.errors[0].message
    
    def test_ge_constraint(self):
        """Test greater than or equal constraint"""
        validator = IntValidator(ge=0)
        
        # Valid
        assert validator.validate(0).is_valid
        assert validator.validate(1).is_valid
        assert validator.validate(100).is_valid
        
        # Invalid
        result = validator.validate(-1)
        assert not result.is_valid
        assert ">=" in result.errors[0].message
    
    def test_le_constraint(self):
        """Test less than or equal constraint"""
        validator = IntValidator(le=100)
        
        # Valid
        assert validator.validate(100).is_valid
        assert validator.validate(0).is_valid
        
        # Invalid
        result = validator.validate(101)
        assert not result.is_valid
        assert "<=" in result.errors[0].message
    
    def test_gt_constraint(self):
        """Test greater than constraint"""
        validator = IntValidator(gt=0)
        
        # Valid
        assert validator.validate(1).is_valid
        assert validator.validate(100).is_valid
        
        # Invalid
        result = validator.validate(0)
        assert not result.is_valid
        assert ">" in result.errors[0].message
    
    def test_lt_constraint(self):
        """Test less than constraint"""
        validator = IntValidator(lt=100)
        
        # Valid
        assert validator.validate(99).is_valid
        assert validator.validate(0).is_valid
        
        # Invalid
        result = validator.validate(100)
        assert not result.is_valid
        assert "<" in result.errors[0].message
    
    def test_multiple_of(self):
        """Test multiple of constraint"""
        validator = IntValidator(multiple_of=5)
        
        # Valid
        assert validator.validate(0).is_valid
        assert validator.validate(5).is_valid
        assert validator.validate(15).is_valid
        
        # Invalid
        result = validator.validate(7)
        assert not result.is_valid
        assert "multiple" in result.errors[0].message.lower()
    
    def test_combined_constraints(self):
        """Test multiple constraints together"""
        validator = IntValidator(ge=0, le=100)
        
        # Valid
        assert validator.validate(0).is_valid
        assert validator.validate(50).is_valid
        assert validator.validate(100).is_valid
        
        # Invalid
        assert not validator.validate(-1).is_valid
        assert not validator.validate(101).is_valid


class TestNumberValidator:
    """Tests for NumberValidator"""
    
    def test_basic_number_validation(self):
        """Test basic number type checking"""
        validator = NumberValidator()
        
        # Valid - both int and float
        assert validator.validate(42).is_valid
        assert validator.validate(42.5).is_valid
        assert validator.validate(0.0).is_valid
    
    def test_number_rejects_non_number(self):
        """Test that non-numbers are rejected"""
        validator = NumberValidator()
        result = validator.validate("123")
        assert not result.is_valid
        assert "Expected number" in result.errors[0].message
    
    def test_number_rejects_bool(self):
        """Test that booleans are rejected"""
        validator = NumberValidator()
        result = validator.validate(True)
        assert not result.is_valid
        assert "Expected number" in result.errors[0].message
    
    def test_ge_constraint(self):
        """Test greater than or equal constraint"""
        validator = NumberValidator(ge=0.0)
        
        # Valid
        assert validator.validate(0.0).is_valid
        assert validator.validate(0.1).is_valid
        assert validator.validate(100.5).is_valid
        
        # Invalid
        result = validator.validate(-0.1)
        assert not result.is_valid
        assert ">=" in result.errors[0].message
    
    def test_le_constraint(self):
        """Test less than or equal constraint"""
        validator = NumberValidator(le=100.0)
        
        # Valid
        assert validator.validate(100.0).is_valid
        assert validator.validate(99.9).is_valid
        
        # Invalid
        result = validator.validate(100.1)
        assert not result.is_valid
        assert "<=" in result.errors[0].message
    
    def test_gt_constraint(self):
        """Test greater than constraint"""
        validator = NumberValidator(gt=0.0)
        
        # Valid
        assert validator.validate(0.1).is_valid
        assert validator.validate(100.0).is_valid
        
        # Invalid
        result = validator.validate(0.0)
        assert not result.is_valid
        assert ">" in result.errors[0].message
    
    def test_lt_constraint(self):
        """Test less than constraint"""
        validator = NumberValidator(lt=100.0)
        
        # Valid
        assert validator.validate(99.9).is_valid
        
        # Invalid
        result = validator.validate(100.0)
        assert not result.is_valid
        assert "<" in result.errors[0].message
    
    def test_multiple_of_float(self):
        """Test multiple of constraint with floats"""
        validator = NumberValidator(multiple_of=0.5)
        
        # Valid
        assert validator.validate(0.0).is_valid
        assert validator.validate(0.5).is_valid
        assert validator.validate(1.5).is_valid
        
        # Invalid (within epsilon tolerance)
        result = validator.validate(0.3)
        assert not result.is_valid
        assert "multiple" in result.errors[0].message.lower()


class TestBooleanValidator:
    """Tests for BooleanValidator"""
    
    def test_basic_boolean_validation(self):
        """Test basic boolean type checking"""
        validator = BooleanValidator()
        
        # Valid
        assert validator.validate(True).is_valid
        assert validator.validate(False).is_valid
    
    def test_boolean_rejects_non_boolean(self):
        """Test that non-booleans are rejected"""
        validator = BooleanValidator()
        
        # Invalid
        result = validator.validate(1)
        assert not result.is_valid
        assert "Expected boolean" in result.errors[0].message
        
        result = validator.validate("true")
        assert not result.is_valid
        assert "Expected boolean" in result.errors[0].message
    
    def test_boolean_enum(self):
        """Test enum constraint (edge case)"""
        validator = BooleanValidator(enum=[True])
        
        # Valid
        assert validator.validate(True).is_valid
        
        # Invalid
        result = validator.validate(False)
        assert not result.is_valid
    
    def test_batch_validation(self):
        """Test batch validation"""
        validator = BooleanValidator()
        values = [True, False, 1, "true"]
        results = validator.validate_batch(values)
        
        assert len(results) == 4
        assert results[0].is_valid  # True
        assert results[1].is_valid  # False
        assert not results[2].is_valid  # 1
        assert not results[3].is_valid  # "true"


class TestPerformance:
    """Basic performance tests to ensure Rust backend is being used"""
    
    def test_string_batch_performance(self):
        """Test that batch validation is fast (indicates Rust is being used)"""
        import time
        
        validator = StringValidator(min_length=3, max_length=100)
        values = ["test" + str(i) for i in range(10000)]
        
        start = time.time()
        results = validator.validate_batch(values)
        duration = time.time() - start
        
        assert len(results) == 10000
        assert all(r.is_valid for r in results)
        # Should complete in under 1 second if using Rust
        assert duration < 1.0, f"Batch validation took {duration}s - too slow!"
    
    def test_int_batch_performance(self):
        """Test integer batch validation performance"""
        import time
        
        validator = IntValidator(ge=0, le=1000000)
        values = list(range(10000))
        
        start = time.time()
        results = validator.validate_batch(values)
        duration = time.time() - start
        
        assert len(results) == 10000
        assert all(r.is_valid for r in results)
        assert duration < 1.0, f"Batch validation took {duration}s - too slow!"
