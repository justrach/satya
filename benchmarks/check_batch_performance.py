#!/usr/bin/env python3
"""
Check Batch Performance - Verify we didn't regress
==================================================

This checks if our fast batch validation is still working.
"""

import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import satya
from satya.validator import StreamValidator

print("🔍 Checking Batch Performance")
print("=" * 80)

# Create 1 million items
data = [
    {"name": f"User{i}", "age": 20 + (i % 60), "email": f"user{i}@example.com"}
    for i in range(1_000_000)
]

print(f"Testing with {len(data):,} items\n")

# Test 1: validate_batch (should be VERY fast - 4.24M items/sec)
print("1. validate_batch() - Rust batch validation")
validator = StreamValidator()
validator.add_field('name', str)
validator.add_field('age', int)
validator.add_field('email', str)

start = time.perf_counter()
results = validator.validate_batch(data)
elapsed = time.perf_counter() - start

items_per_sec = len(data) / elapsed
print(f"   Performance: {items_per_sec:,.0f} items/sec")
print(f"   Time: {elapsed:.3f}s for {len(data):,} items")
print(f"   Valid: {sum(results):,} / {len(data):,}")

# Test 2: Model instantiation (will be slower)
print("\n2. Model(**data) - Full model instantiation")

class User(satya.Model):
    name: str
    age: int
    email: str

# Test with smaller dataset (100K items)
test_data = data[:100_000]

start = time.perf_counter()
for item in test_data:
    User(**item)
elapsed = time.perf_counter() - start

items_per_sec = len(test_data) / elapsed
print(f"   Performance: {items_per_sec:,.0f} items/sec")
print(f"   Time: {elapsed:.3f}s for {len(test_data):,} items")

# Test 3: Direct validator (should be fast)
print("\n3. validator.validate() - Direct validation")

start = time.perf_counter()
for item in test_data:
    validator.validate(item)
elapsed = time.perf_counter() - start

items_per_sec = len(test_data) / elapsed
print(f"   Performance: {items_per_sec:,.0f} items/sec")
print(f"   Time: {elapsed:.3f}s for {len(test_data):,} items")

print("\n" + "=" * 80)
print("📊 ANALYSIS")
print("=" * 80)
print("""
Expected performance:
- validate_batch_hybrid: 4.24M items/sec (from previous benchmarks)
- Direct validation: 400-500K items/sec
- Model instantiation: 100-200K items/sec (has overhead)

If validate_batch_hybrid is still ~4M items/sec, we're good!
The Model instantiation is slower because it does more work.
""")
