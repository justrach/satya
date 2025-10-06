"""
Tests for TurboAPI Integration Features

Tests the new features added in Satya v0.4.0:
1. Web framework parameter types
2. Zero-copy validation
3. Performance profiling
4. Enhanced error messages
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from satya import Model, Field
from satya.web import (
    QueryParam, PathParam, HeaderParam, CookieParam, FormField,
    validate_int, validate_str, validate_float, validate_param
)
from satya.profiling import ValidationProfiler, ValidationStats, FieldStats
from satya.validator import StreamValidator


class TestWebParameters:
    """Test web framework parameter types"""
    
    def test_query_param_basic(self):
        """Test basic query parameter validation"""
        param = QueryParam(10, ge=1, le=100)
        
        # Valid values
        assert param.validate(50) == 50
        assert param.validate(1) == 1
        assert param.validate(100) == 100
        
        # Use default
        assert param.validate(None) == 10
    
    def test_query_param_constraints(self):
        """Test query parameter constraints"""
        param = QueryParam(ge=1, le=100)
        
        # Out of range
        with pytest.raises(ValueError, match="must be >= 1"):
            param.validate(0)
        
        with pytest.raises(ValueError, match="must be <= 100"):
            param.validate(101)
    
    def test_query_param_required(self):
        """Test required query parameter"""
        param = QueryParam(description="Required param")
        
        with pytest.raises(ValueError, match="required"):
            param.validate(None)
    
    def test_path_param_always_required(self):
        """Test that path parameters are always required"""
        # Path params cannot have defaults
        with pytest.raises(ValueError, match="cannot have default"):
            PathParam(default=10)
        
        # Path params are always required
        param = PathParam(ge=1)
        with pytest.raises(ValueError, match="required"):
            param.validate(None)
    
    def test_header_param_alias(self):
        """Test header parameter with alias"""
        param = HeaderParam(alias="Authorization")
        
        value = param.validate("Bearer token123")
        assert value == "Bearer token123"
    
    def test_string_validation_constraints(self):
        """Test string validation with constraints"""
        param = QueryParam(min_length=3, max_length=10)
        
        # Valid
        assert param.validate("test") == "test"
        
        # Too short
        with pytest.raises(ValueError, match="at least 3"):
            param.validate("ab")
        
        # Too long
        with pytest.raises(ValueError, match="at most 10"):
            param.validate("a" * 11)
    
    def test_email_validation(self):
        """Test email format validation"""
        param = QueryParam(email=True)
        
        # Valid email
        assert param.validate("test@example.com") == "test@example.com"
        
        # Invalid email
        with pytest.raises(ValueError, match="Invalid email"):
            param.validate("not-an-email")
    
    def test_url_validation(self):
        """Test URL format validation"""
        param = QueryParam(url=True)
        
        # Valid URLs
        assert param.validate("http://example.com") == "http://example.com"
        assert param.validate("https://example.com") == "https://example.com"
        
        # Invalid URL
        with pytest.raises(ValueError, match="Invalid URL"):
            param.validate("not-a-url")
    
    def test_enum_validation(self):
        """Test enum constraint"""
        param = QueryParam(enum=["small", "medium", "large"])
        
        # Valid
        assert param.validate("medium") == "medium"
        
        # Invalid
        with pytest.raises(ValueError, match="must be one of"):
            param.validate("extra-large")
    
    def test_validate_int_helper(self):
        """Test validate_int helper function"""
        # Valid
        assert validate_int(42) == 42
        assert validate_int("42") == 42
        
        # With constraints
        assert validate_int(50, ge=1, le=100) == 50
        
        # Out of range
        with pytest.raises(ValueError, match="must be >= 1"):
            validate_int(0, ge=1)
    
    def test_validate_str_helper(self):
        """Test validate_str helper function"""
        # Valid
        assert validate_str("test") == "test"
        
        # With constraints
        assert validate_str("test", min_length=3, max_length=10) == "test"
        
        # Email
        assert validate_str("test@example.com", email=True) == "test@example.com"
        
        with pytest.raises(ValueError, match="Invalid email"):
            validate_str("invalid", email=True)
    
    def test_validate_float_helper(self):
        """Test validate_float helper function"""
        # Valid
        assert validate_float(3.14) == 3.14
        assert validate_float("3.14") == 3.14
        assert validate_float(42) == 42.0
        
        # With constraints
        assert validate_float(50.5, ge=1.0, le=100.0) == 50.5
        
        # Out of range
        with pytest.raises(ValueError, match="must be >= 1.0"):
            validate_float(0.5, ge=1.0)
    
    def test_validate_param_function(self):
        """Test validate_param helper function"""
        param = QueryParam(10, ge=1, le=100)
        
        assert validate_param(50, param) == 50
        assert validate_param(None, param) == 10


class TestZeroCopyValidation:
    """Test zero-copy validation from bytes"""
    
    def test_validate_from_bytes_basic(self):
        """Test basic zero-copy validation"""
        validator = StreamValidator()
        validator.add_field('name', str, required=True)
        validator.add_field('age', int, required=True)
        
        # Valid JSON bytes
        json_bytes = b'{"name": "John", "age": 30}'
        assert validator.validate_from_bytes(json_bytes) == True
    
    def test_validate_from_bytes_invalid(self):
        """Test zero-copy validation with invalid data"""
        validator = StreamValidator()
        validator.add_field('name', str, required=True)
        validator.add_field('age', int, required=True)
        validator.set_constraints('age', ge=0, le=150)
        
        # Invalid age
        json_bytes = b'{"name": "John", "age": 200}'
        assert validator.validate_from_bytes(json_bytes) == False
    
    def test_validate_from_bytes_type_error(self):
        """Test that validate_from_bytes requires bytes"""
        validator = StreamValidator()
        validator.add_field('name', str)
        
        with pytest.raises(TypeError, match="Expected bytes"):
            validator.validate_from_bytes("not bytes")
    
    def test_validate_from_bytes_streaming_flag(self):
        """Test streaming and zero_copy flags"""
        validator = StreamValidator()
        validator.add_field('name', str, required=True)
        
        json_bytes = b'{"name": "test"}'
        
        # Streaming + zero-copy (default)
        assert validator.validate_from_bytes(json_bytes, streaming=True, zero_copy=True)
        
        # Non-streaming
        assert validator.validate_from_bytes(json_bytes, streaming=False, zero_copy=False)
    
    def test_validate_json_stream(self):
        """Test streaming validation from file-like object"""
        import io
        
        validator = StreamValidator()
        validator.add_field('id', int, required=True)
        validator.add_field('name', str, required=True)
        
        # NDJSON data
        ndjson = b'\n'.join([
            b'{"id": 1, "name": "Alice"}',
            b'{"id": 2, "name": "Bob"}',
            b'{"id": 3, "name": "Charlie"}',
        ])
        
        stream = io.BytesIO(ndjson)
        results = list(validator.validate_json_stream(stream))
        
        assert len(results) == 3
        assert all(results)


class TestPerformanceProfiling:
    """Test performance profiling tools"""
    
    def test_profiler_basic(self):
        """Test basic profiler functionality"""
        profiler = ValidationProfiler()
        
        @profiler.track
        class User(Model):
            name: str = Field(min_length=1)
        
        # Run validations
        for _ in range(10):
            try:
                User.model_validate({'name': 'test'})
            except Exception:
                pass
        
        stats = profiler.get_stats()
        assert stats.total_validations == 10
        assert stats.avg_time_us > 0
    
    def test_profiler_disabled(self):
        """Test disabled profiler"""
        profiler = ValidationProfiler(enabled=False)
        
        @profiler.track
        class User(Model):
            name: str
        
        stats = profiler.get_stats()
        assert stats.total_validations == 0
    
    def test_profiler_stats(self):
        """Test validation statistics"""
        profiler = ValidationProfiler()
        
        @profiler.track
        class User(Model):
            name: str = Field(min_length=3)
        
        # Some valid, some invalid
        for i in range(5):
            try:
                User.model_validate({'name': 'test'})
            except Exception:
                pass
        
        for i in range(3):
            try:
                User.model_validate({'name': 'ab'})  # Too short
            except Exception:
                pass
        
        stats = profiler.get_stats()
        assert stats.total_validations == 8
        assert stats.successful_validations == 5
        assert stats.failed_validations == 3
        assert 0 < stats.success_rate <= 1.0
    
    def test_profiler_reset(self):
        """Test profiler reset"""
        profiler = ValidationProfiler()
        
        @profiler.track
        class User(Model):
            name: str
        
        User.model_validate({'name': 'test'})
        assert profiler.get_stats().total_validations == 1
        
        profiler.reset()
        assert profiler.get_stats().total_validations == 0
    
    def test_profiler_report(self):
        """Test profiler report generation"""
        profiler = ValidationProfiler()
        
        @profiler.track
        class User(Model):
            name: str
        
        for _ in range(5):
            User.model_validate({'name': 'test'})
        
        report = profiler.report(verbose=False)
        assert "Total Validations: 5" in report
        assert "Average Time:" in report
    
    def test_validation_stats_properties(self):
        """Test ValidationStats computed properties"""
        from satya.profiling import ValidationStats
        
        stats = ValidationStats()
        stats.total_validations = 5  # Match the length of validation_times
        stats.successful_validations = 4
        stats.failed_validations = 1
        stats.validation_times = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats.total_time_us = sum(stats.validation_times)  # This is 150.0
        
        assert stats.avg_time_us == 30.0  # 150.0 / 5 = 30.0
        assert stats.median_time_us == 30.0
        assert stats.min_time_us == 10.0
        assert stats.max_time_us == 50.0
        assert stats.success_rate == 0.8
    
    def test_field_stats(self):
        """Test FieldStats"""
        from satya.profiling import FieldStats
        
        stats = FieldStats("username")
        stats.validation_count = 10
        stats.total_time_us = 100.0
        stats.min_time_us = 5.0
        stats.max_time_us = 20.0
        
        assert stats.avg_time_us == 10.0
        
        stats_dict = stats.to_dict()
        assert stats_dict['field_name'] == "username"
        assert stats_dict['avg_time_us'] == 10.0


class TestEnhancedErrors:
    """Test enhanced error messages with context"""
    
    def test_enhanced_error_basic(self):
        """Test basic enhanced error"""
        from satya import ValidationError
        
        error = ValidationError(
            field="age",
            message="Value out of range",
            path=["user", "age"],
            value=200,
            constraint="must be >= 0 and <= 150",
            suggestion="Age must be between 0 and 150"
        )
        
        error_str = str(error)
        assert "user.age" in error_str
        assert "Value: 200" in error_str
        assert "Constraint:" in error_str
        assert "Suggestion:" in error_str
    
    def test_enhanced_error_without_extras(self):
        """Test enhanced error without optional fields"""
        from satya import ValidationError
        
        error = ValidationError(
            field="name",
            message="Required field",
            path=["name"]
        )
        
        error_str = str(error)
        assert "name: Required field" in error_str
        assert "Value:" not in error_str
        assert "Constraint:" not in error_str


class TestIntegration:
    """Integration tests combining multiple features"""
    
    def test_web_param_with_model(self):
        """Test using web parameters with Satya models"""
        from satya.web import Query
        
        class SearchParams(Model):
            q: str = Field(min_length=1, max_length=100)
            limit: int = Field(ge=1, le=100, default=10)
        
        # Valid data
        params = SearchParams.model_validate({'q': 'python', 'limit': 25})
        assert params.q == 'python'
        assert params.limit == 25
    
    def test_profiling_with_zero_copy(self):
        """Test profiling zero-copy validation"""
        profiler = ValidationProfiler()
        validator = StreamValidator()
        validator.add_field('name', str, required=True)
        
        json_bytes = b'{"name": "test"}'
        
        # Profile the validation
        import time
        start = time.perf_counter()
        for _ in range(100):
            validator.validate_from_bytes(json_bytes)
        elapsed = time.perf_counter() - start
        
        # Should be very fast (< 10ms for 100 validations)
        assert elapsed < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
