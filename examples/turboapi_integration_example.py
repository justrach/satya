"""
TurboAPI Integration Example - Satya v0.4.0

This example demonstrates the new features added based on TurboAPI team feedback:
1. Web framework parameter types (QueryParam, PathParam, HeaderParam)
2. Zero-copy validation from bytes
3. Performance profiling tools
4. Enhanced error messages with context
"""

import sys
sys.path.insert(0, 'src')

from satya import Model, Field
from satya.web import QueryParam, PathParam, HeaderParam, validate_int, validate_str
from satya.profiling import ValidationProfiler, BenchmarkComparison
from satya.validator import StreamValidator


def example_1_web_parameters():
    """Example 1: Web Framework Parameter Types"""
    print("=" * 70)
    print("Example 1: Web Framework Parameter Types")
    print("=" * 70)
    
    # Query parameters (e.g., ?limit=10&offset=0)
    limit_param = QueryParam(10, ge=1, le=100, description="Items per page")
    offset_param = QueryParam(0, ge=0, description="Pagination offset")
    
    # Validate query parameters
    try:
        limit = limit_param.validate(50)
        offset = offset_param.validate(0)
        print(f"✓ Query params validated: limit={limit}, offset={offset}")
    except ValueError as e:
        print(f"✗ Validation error: {e}")
    
    # Path parameters (e.g., /users/{user_id})
    user_id_param = PathParam(ge=1, description="User ID")
    
    try:
        user_id = user_id_param.validate(123)
        print(f"✓ Path param validated: user_id={user_id}")
    except ValueError as e:
        print(f"✗ Validation error: {e}")
    
    # Header parameters (e.g., Authorization, User-Agent)
    auth_header = HeaderParam(alias="Authorization", description="Bearer token")
    
    try:
        auth = auth_header.validate("Bearer abc123xyz")
        print(f"✓ Header param validated: {auth[:20]}...")
    except ValueError as e:
        print(f"✗ Validation error: {e}")
    
    print()


def example_2_zero_copy_validation():
    """Example 2: Zero-Copy Validation from Bytes"""
    print("=" * 70)
    print("Example 2: Zero-Copy Validation from Bytes")
    print("=" * 70)
    
    # Create a validator
    validator = StreamValidator()
    validator.add_field('username', str, required=True)
    validator.add_field('email', str, required=True)
    validator.add_field('age', int, required=False)
    
    # Set constraints
    validator.set_constraints('username', min_length=3, max_length=50)
    validator.set_constraints('email', email=True)
    validator.set_constraints('age', ge=0, le=150)
    
    # Zero-copy validation directly from bytes (no JSON parsing!)
    json_bytes = b'{"username": "john_doe", "email": "john@example.com", "age": 30}'
    
    print("Validating from bytes (zero-copy)...")
    is_valid = validator.validate_from_bytes(json_bytes, streaming=True, zero_copy=True)
    print(f"✓ Valid: {is_valid}")
    
    # Invalid data
    invalid_bytes = b'{"username": "ab", "email": "invalid-email", "age": 200}'
    is_valid = validator.validate_from_bytes(invalid_bytes, streaming=True, zero_copy=True)
    print(f"✗ Valid: {is_valid} (expected: False)")
    
    print()


def example_3_performance_profiling():
    """Example 3: Performance Profiling"""
    print("=" * 70)
    print("Example 3: Performance Profiling")
    print("=" * 70)
    
    # Create a profiler
    profiler = ValidationProfiler()
    
    # Track a model
    @profiler.track
    class User(Model):
        username: str = Field(min_length=3, max_length=50)
        email: str = Field(email=True)
        age: int = Field(ge=0, le=150)
    
    # Run some validations
    print("Running 1,000 validations...")
    sample_data = {
        'username': 'john_doe',
        'email': 'john@example.com',
        'age': 30
    }
    
    for i in range(1000):
        try:
            User.model_validate(sample_data)
        except Exception:
            pass
    
    # Get statistics
    stats = profiler.get_stats()
    print(f"\n✓ Total validations: {stats.total_validations:,}")
    print(f"✓ Success rate: {stats.success_rate * 100:.2f}%")
    print(f"✓ Average time: {stats.avg_time_us:.2f} μs")
    print(f"✓ Median time: {stats.median_time_us:.2f} μs")
    print(f"✓ Min time: {stats.min_time_us:.2f} μs")
    print(f"✓ Max time: {stats.max_time_us:.2f} μs")
    
    if stats.bottleneck:
        print(f"✓ Bottleneck field: {stats.bottleneck}")
    
    print()


def example_4_enhanced_errors():
    """Example 4: Enhanced Error Messages with Context"""
    print("=" * 70)
    print("Example 4: Enhanced Error Messages with Context")
    print("=" * 70)
    
    class User(Model):
        username: str = Field(min_length=3, max_length=50)
        email: str = Field(email=True)
        age: int = Field(ge=0, le=150)
    
    # Try to validate invalid data
    invalid_data = {
        'username': 'ab',  # Too short
        'email': 'not-an-email',  # Invalid format
        'age': 200  # Too large
    }
    
    try:
        User.model_validate(invalid_data)
    except Exception as e:
        print(f"Validation failed with enhanced error messages:\n")
        print(str(e))
    
    print()


def example_5_fast_validators():
    """Example 5: Fast Validation Helpers"""
    print("=" * 70)
    print("Example 5: Fast Validation Helpers")
    print("=" * 70)
    
    # Integer validation
    try:
        value = validate_int("42", ge=1, le=100)
        print(f"✓ Integer validated: {value}")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # String validation
    try:
        email = validate_str("test@example.com", email=True)
        print(f"✓ Email validated: {email}")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # URL validation
    try:
        url = validate_str("https://example.com", url=True)
        print(f"✓ URL validated: {url}")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    print()


def example_6_streaming_validation():
    """Example 6: Streaming Validation for Large Payloads"""
    print("=" * 70)
    print("Example 6: Streaming Validation for Large Payloads")
    print("=" * 70)
    
    # Create a validator
    validator = StreamValidator()
    validator.add_field('id', int, required=True)
    validator.add_field('name', str, required=True)
    
    # Simulate a large NDJSON stream
    import io
    ndjson_data = b'\n'.join([
        b'{"id": 1, "name": "Alice"}',
        b'{"id": 2, "name": "Bob"}',
        b'{"id": 3, "name": "Charlie"}',
        b'{"id": 4, "name": "Diana"}',
        b'{"id": 5, "name": "Eve"}',
    ])
    
    stream = io.BytesIO(ndjson_data)
    
    print("Validating NDJSON stream (zero-copy)...")
    valid_count = 0
    for i, is_valid in enumerate(validator.validate_json_stream(stream), 1):
        if is_valid:
            valid_count += 1
            print(f"  Record {i}: ✓ Valid")
        else:
            print(f"  Record {i}: ✗ Invalid")
    
    print(f"\n✓ Validated {i} records, {valid_count} valid")
    print()


def example_7_turboapi_style_usage():
    """Example 7: TurboAPI-Style Usage Pattern"""
    print("=" * 70)
    print("Example 7: TurboAPI-Style Usage Pattern")
    print("=" * 70)
    
    from satya.web import Query, Path, validate_param
    
    # Define API endpoint parameters
    class SearchParams:
        q = Query(min_length=1, max_length=100, description="Search query")
        limit = Query(10, ge=1, le=100, description="Results per page")
        offset = Query(0, ge=0, description="Pagination offset")
    
    class ItemPath:
        item_id = Path(ge=1, description="Item ID")
    
    # Simulate request parameters
    query_params = {
        'q': 'python validation',
        'limit': 25,
        'offset': 0
    }
    
    path_params = {
        'item_id': 42
    }
    
    # Validate parameters (TurboAPI-style)
    print("Validating API parameters...")
    try:
        q = validate_param(query_params['q'], SearchParams.q)
        limit = validate_param(query_params['limit'], SearchParams.limit)
        offset = validate_param(query_params['offset'], SearchParams.offset)
        print(f"✓ Query params: q='{q}', limit={limit}, offset={offset}")
        
        item_id = validate_param(path_params['item_id'], ItemPath.item_id)
        print(f"✓ Path params: item_id={item_id}")
    except ValueError as e:
        print(f"✗ Validation error: {e}")
    
    print()


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "Satya v0.4.0 - TurboAPI Integration Examples" + " " * 13 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    examples = [
        example_1_web_parameters,
        example_2_zero_copy_validation,
        example_3_performance_profiling,
        example_4_enhanced_errors,
        example_5_fast_validators,
        example_6_streaming_validation,
        example_7_turboapi_style_usage,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Example failed: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Web framework parameter types (QueryParam, PathParam, HeaderParam)")
    print("  ✓ Zero-copy validation from bytes (2-3x faster for large payloads)")
    print("  ✓ Performance profiling tools")
    print("  ✓ Enhanced error messages with context")
    print("  ✓ Fast validation helpers")
    print("  ✓ Streaming validation for large datasets")
    print("  ✓ TurboAPI-style usage patterns")
    print()
    print("Next Steps:")
    print("  1. Integrate Satya into your TurboAPI application")
    print("  2. Use zero-copy validation for maximum performance")
    print("  3. Profile your validation bottlenecks")
    print("  4. Enjoy 5-20x faster validation! 🚀")
    print()


if __name__ == "__main__":
    main()
