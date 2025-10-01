"""
Example demonstrating Satya's JSON Schema compiler.

This shows how to compile JSON Schema documents directly into high-performance
Rust-backed validators, making Satya a drop-in replacement for fastjsonschema.
"""

from satya import compile_json_schema, JSONSchemaCompiler
import time

print("=" * 70)
print("Satya JSON Schema Compiler - Drop-In fastjsonschema Replacement")
print("=" * 70)

# ===== String Schema =====
print("\n📝 STRING SCHEMA VALIDATION")
print("-" * 70)

schema = {
    "type": "string",
    "minLength": 3,
    "maxLength": 50,
    "pattern": "^[a-zA-Z0-9_-]+$"
}

validator = compile_json_schema(schema)

# Valid strings
result = validator.validate("my-package-name")
print(f"✓ 'my-package-name' is valid: {result.is_valid}")

result = validator.validate("test_123")
print(f"✓ 'test_123' is valid: {result.is_valid}")

# Invalid strings
result = validator.validate("ab")  # Too short
print(f"✗ 'ab' is valid: {result.is_valid} - {result.errors[0].message if result.errors else ''}")

result = validator.validate("invalid package!")  # Contains space
print(f"✗ 'invalid package!' is valid: {result.is_valid}")

# ===== Email Schema =====
print("\n📧 EMAIL FORMAT VALIDATION")
print("-" * 70)

schema = {
    "type": "string",
    "format": "email"
}

validator = compile_json_schema(schema)

result = validator.validate("user@example.com")
print(f"✓ 'user@example.com' is valid: {result.is_valid}")

result = validator.validate("not-an-email")
print(f"✗ 'not-an-email' is valid: {result.is_valid}")

# ===== Integer Schema =====
print("\n🔢 INTEGER SCHEMA WITH BOUNDS")
print("-" * 70)

schema = {
    "type": "integer",
    "minimum": 0,
    "maximum": 100,
    "multipleOf": 5
}

validator = compile_json_schema(schema)

result = validator.validate(50)
print(f"✓ 50 is valid: {result.is_valid}")

result = validator.validate(25)
print(f"✓ 25 is valid (multiple of 5): {result.is_valid}")

result = validator.validate(27)
print(f"✗ 27 is valid: {result.is_valid} - {result.errors[0].message if result.errors else ''}")

result = validator.validate(150)
print(f"✗ 150 is valid: {result.is_valid} - {result.errors[0].message if result.errors else ''}")

# ===== Array Schema =====
print("\n📚 ARRAY SCHEMA VALIDATION")
print("-" * 70)

schema = {
    "type": "array",
    "items": {"type": "string"},
    "minItems": 1,
    "maxItems": 5,
    "uniqueItems": True
}

validator = compile_json_schema(schema)

result = validator.validate(["python", "rust", "javascript"])
print(f"✓ ['python', 'rust', 'javascript'] is valid: {result.is_valid}")

result = validator.validate([])
print(f"✗ [] is valid: {result.is_valid} - {result.errors[0].message if result.errors else ''}")

result = validator.validate(["a", "b", "a"])
print(f"✗ ['a', 'b', 'a'] (duplicates) is valid: {result.is_valid}")

# ===== Poetry Use Case: Package Name =====
print("\n📦 POETRY USE CASE: Package Name Validation")
print("-" * 70)

schema = {
    "type": "string",
    "pattern": "^[a-zA-Z0-9]([a-zA-Z0-9_-]*[a-zA-Z0-9])?$",
    "description": "Valid Python package name"
}

validator = compile_json_schema(schema)

packages = ["requests", "numpy-ext", "my_package", "-invalid", "invalid-"]

for pkg in packages:
    result = validator.validate(pkg)
    status = "✓" if result.is_valid else "✗"
    print(f"{status} '{pkg}' is valid: {result.is_valid}")

# ===== Poetry Use Case: Version String =====
print("\n🏷️  POETRY USE CASE: Version String Validation")
print("-" * 70)

schema = {
    "type": "string",
    "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$",
    "description": "Semantic version string"
}

validator = compile_json_schema(schema)

versions = ["1.2.3", "0.1.0", "2.4.10", "1.2", "invalid"]

for ver in versions:
    result = validator.validate(ver)
    status = "✓" if result.is_valid else "✗"
    print(f"{status} '{ver}' is valid: {result.is_valid}")

# ===== Performance Demonstration =====
print("\n⚡ PERFORMANCE BENCHMARK")
print("-" * 70)

schema = {
    "type": "string",
    "minLength": 3,
    "maxLength": 100,
    "pattern": "^[a-zA-Z0-9_-]+$"
}

validator = compile_json_schema(schema)
test_data = ["package-" + str(i) for i in range(100000)]

start = time.time()
results = validator.validate_batch(test_data)
duration = time.time() - start

valid_count = sum(1 for r in results if r.is_valid)
rate = len(test_data) / duration

print(f"Validated {len(test_data):,} package names in {duration:.4f}s")
print(f"Performance: {rate:,.0f} validations/second")
print(f"Valid results: {valid_count:,}/{len(test_data):,}")

# ===== Optimization Report =====
print("\n📊 OPTIMIZATION REPORT")
print("-" * 70)

compiler = JSONSchemaCompiler()

# Compile multiple schemas
schemas = [
    {"type": "string", "minLength": 3},
    {"type": "integer", "minimum": 0},
    {"type": "number", "maximum": 100.0},
    {"type": "boolean"},
    {"type": "array", "items": {"type": "string"}},
]

for schema in schemas:
    compiler.compile(schema)

report = compiler.get_optimization_report()

print(f"Total schemas compiled: {report['total_schemas']}")
print(f"Rust-optimized: {report['rust_optimized']}")
print(f"Python fallback: {report['python_fallback']}")
print(f"Optimization rate: {report['optimization_percentage']:.1f}%")

print("\n" + "=" * 70)
print("✨ Satya: Drop-in fastjsonschema replacement with 5-20x better performance!")
print("=" * 70)
