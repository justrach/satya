"""
Example demonstrating Satya's new Rust-backed scalar validators.

These validators provide high-performance validation for primitive types:
- StringValidator: min/max length, pattern, email, URL validation
- IntValidator: ge/le/gt/lt bounds, multiple_of, enum
- NumberValidator: float validation with bounds
- BooleanValidator: boolean type validation
"""

from satya import StringValidator, IntValidator, NumberValidator, BooleanValidator
import time

print("=" * 70)
print("Satya Scalar Validators - Rust-Backed Performance")
print("=" * 70)

# ===== StringValidator Example =====
print("\n📝 STRING VALIDATION")
print("-" * 70)

# Basic string validation
string_validator = StringValidator(min_length=3, max_length=50)
result = string_validator.validate("hello world")
print(f"✓ '{result.value}' is valid: {result.is_valid}")

# Invalid string
result = string_validator.validate("hi")
print(f"✗ 'hi' is valid: {result.is_valid} - {result.errors[0].message if result.errors else ''}")

# Email validation
email_validator = StringValidator(email=True)
result = email_validator.validate("user@example.com")
print(f"✓ Email 'user@example.com' is valid: {result.is_valid}")

result = email_validator.validate("not-an-email")
print(f"✗ 'not-an-email' is valid: {result.is_valid} - {result.errors[0].message if result.errors else ''}")

# Pattern validation (alphanumeric only)
pattern_validator = StringValidator(pattern=r'^[a-zA-Z0-9]+$')
result = pattern_validator.validate("User123")
print(f"✓ 'User123' matches pattern: {result.is_valid}")

result = pattern_validator.validate("User-123")
print(f"✗ 'User-123' matches pattern: {result.is_valid}")

# ===== IntValidator Example =====
print("\n🔢 INTEGER VALIDATION")
print("-" * 70)

# Range validation
int_validator = IntValidator(ge=0, le=100)
result = int_validator.validate(42)
print(f"✓ {result.value} is in range [0, 100]: {result.is_valid}")

result = int_validator.validate(150)
print(f"✗ 150 is in range [0, 100]: {result.is_valid} - {result.errors[0].message if result.errors else ''}")

# Multiple of validation
multiple_validator = IntValidator(multiple_of=5)
result = multiple_validator.validate(25)
print(f"✓ 25 is multiple of 5: {result.is_valid}")

result = multiple_validator.validate(27)
print(f"✗ 27 is multiple of 5: {result.is_valid} - {result.errors[0].message if result.errors else ''}")

# ===== NumberValidator Example =====
print("\n🔢 NUMBER (FLOAT) VALIDATION")
print("-" * 70)

# Float validation with bounds
number_validator = NumberValidator(ge=0.0, le=100.0)
result = number_validator.validate(42.5)
print(f"✓ {result.value} is in range [0.0, 100.0]: {result.is_valid}")

result = number_validator.validate(-0.5)
print(f"✗ -0.5 is in range [0.0, 100.0]: {result.is_valid} - {result.errors[0].message if result.errors else ''}")

# Exclusive bounds (gt/lt)
exclusive_validator = NumberValidator(gt=0.0, lt=1.0)
result = exclusive_validator.validate(0.5)
print(f"✓ 0.5 is in range (0.0, 1.0): {result.is_valid}")

result = exclusive_validator.validate(0.0)
print(f"✗ 0.0 is in range (0.0, 1.0): {result.is_valid}")

# ===== BooleanValidator Example =====
print("\n✓ BOOLEAN VALIDATION")
print("-" * 70)

bool_validator = BooleanValidator()
result = bool_validator.validate(True)
print(f"✓ True is boolean: {result.is_valid}")

result = bool_validator.validate(1)
print(f"✗ 1 is boolean: {result.is_valid} - {result.errors[0].message if result.errors else ''}")

# ===== Performance Demonstration =====
print("\n⚡ PERFORMANCE BENCHMARK")
print("-" * 70)

# Batch validation performance
string_validator = StringValidator(min_length=3, max_length=100)
test_data = ["test" + str(i) for i in range(100000)]

start = time.time()
results = string_validator.validate_batch(test_data)
duration = time.time() - start

valid_count = sum(1 for r in results if r.is_valid)
rate = len(test_data) / duration

print(f"Validated {len(test_data):,} strings in {duration:.4f}s")
print(f"Performance: {rate:,.0f} validations/second")
print(f"Valid results: {valid_count:,}/{len(test_data):,}")

# Compare with Python loop (for reference)
start = time.time()
python_results = [string_validator.validate(s) for s in test_data[:10000]]
python_duration = time.time() - start
python_rate = 10000 / python_duration

print(f"\nFor comparison (10k items):")
print(f"Python loop: {python_rate:,.0f} validations/second")

print("\n" + "=" * 70)
print("✨ Rust-backed validators provide massive performance improvements!")
print("=" * 70)
