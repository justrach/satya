#!/usr/bin/env python3
"""
Performance Diagnostic - Find the Bottleneck
============================================

This script tests different parts of Satya to find where the slowdown is.
"""

import time
import sys
import os
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

ITERATIONS = 10_000

def benchmark(name, func, data):
    """Quick benchmark"""
    times = []
    for run in range(5):
        start = time.perf_counter()
        for item in data:
            func(item)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    mean = statistics.mean(times)
    ips = len(data) / mean
    print(f"{name:<50} {ips:>12,.0f} ops/sec")
    return ips

print("🔍 Performance Diagnostic")
print("=" * 80)

data = [
    {"name": f"User{i}", "age": 20 + (i % 60), "email": f"user{i}@example.com"}
    for i in range(ITERATIONS)
]

# Test 1: Direct Rust validator (baseline - should be fast)
print("\n1. Direct Rust Validator (StreamValidator)")
from satya.validator import StreamValidator

validator = StreamValidator()
validator.add_field('name', str)
validator.add_field('age', int)
validator.add_field('email', str)

result1 = benchmark("StreamValidator.validate()", lambda x: validator.validate(x), data)

# Test 2: Native Python validator (should be even faster)
print("\n2. Native Python Validator")
from satya.native_validator import NativeValidator

native_val = NativeValidator({'name': str, 'age': int, 'email': str})
result2 = benchmark("NativeValidator.validate()", lambda x: native_val.validate(x), data)

# Test 3: Model with NO validators (current - slow)
print("\n3. Satya Model (full __init__)")
import satya

class SimpleModel(satya.Model):
    name: str
    age: int
    email: str

result3 = benchmark("Model(**data)", lambda x: SimpleModel(**x), data)

# Test 4: Model.validator() - what Model uses internally
print("\n4. Model.validator() - cached validator")
model_validator = SimpleModel.validator()
result4 = benchmark("Model.validator().validate()", lambda x: model_validator.validate(x), data)

# Test 5: Just dict creation (baseline)
print("\n5. Baseline - dict creation")
result5 = benchmark("dict(**data)", lambda x: dict(**x), data)

# Test 6: Pydantic for comparison
print("\n6. Pydantic (for comparison)")
try:
    from pydantic import BaseModel
    
    class PydanticModel(BaseModel):
        name: str
        age: int
        email: str
    
    result6 = benchmark("Pydantic Model(**data)", lambda x: PydanticModel(**x), data)
except ImportError:
    result6 = 0
    print("Pydantic not available")

# Analysis
print("\n" + "=" * 80)
print("📊 ANALYSIS")
print("=" * 80)

print(f"\nDirect Rust validator:     {result1:>12,.0f} ops/sec (baseline)")
print(f"Native Python validator:   {result2:>12,.0f} ops/sec ({result2/result1:>5.2f}x vs Rust)")
print(f"Model.__init__:            {result3:>12,.0f} ops/sec ({result3/result1:>5.2f}x vs Rust)")
print(f"Model.validator():         {result4:>12,.0f} ops/sec ({result4/result1:>5.2f}x vs Rust)")
print(f"Dict creation:             {result5:>12,.0f} ops/sec ({result5/result1:>5.2f}x vs Rust)")
if result6:
    print(f"Pydantic:                  {result6:>12,.0f} ops/sec ({result6/result1:>5.2f}x vs Rust)")

print("\n💡 FINDINGS:")
print("-" * 80)

overhead = result1 / result3
print(f"\n1. Model.__init__ overhead: {overhead:.1f}x slower than direct Rust validator")
print(f"   This means Model.__init__ is doing {overhead:.1f}x more work than just validation")

if result2 > result1:
    print(f"\n2. Native Python IS faster: {result2/result1:.2f}x faster than Rust")
    print(f"   But Model is NOT using it!")
else:
    print(f"\n2. Native Python is slower: {result1/result2:.2f}x slower than Rust")

validator_overhead = result1 / result4
print(f"\n3. Model.validator() overhead: {validator_overhead:.2f}x slower than direct validator")
print(f"   This is the overhead of the Model.validator() wrapper")

if result6:
    pydantic_vs_satya = result6 / result3
    print(f"\n4. Pydantic vs Satya Model: {pydantic_vs_satya:.1f}x faster")
    print(f"   Pydantic is highly optimized for model instantiation")

print("\n🎯 HYPOTHESIS:")
print("-" * 80)
print("""
The slowdown is caused by:

1. Model.__init__ does LOTS of work beyond validation:
   - Field preprocessing (List[Model], Dict[str, Model] detection)
   - Nested model instantiation
   - Default value handling with deep copy
   - Extra field handling (allow/forbid/ignore)
   - Additional Python-side constraint checks
   - Validator lookups (even when no validators exist)

2. Model is NOT using the native optimization:
   - We built NativeValidator but Model doesn't use it
   - Model.validator() returns StreamValidator, not optimized validator

3. Pydantic is heavily optimized:
   - C implementation
   - Minimal overhead
   - Optimized for the common case

SOLUTION:
1. Skip validator lookups if class has no validators (cache this!)
2. Use native optimization in Model.validator()
3. Optimize the hot path in Model.__init__
4. Consider lazy field processing
""")
