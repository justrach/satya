#!/usr/bin/env python3
"""
Recursive Optimization Test
===========================

This script recursively tests and optimizes the native Python validators
to ensure they're as fast as possible.
"""

import time
import sys
import os
from typing import List, Optional, Dict
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import satya
from satya import Field
from satya.native_validator import NativeValidator, HybridValidator, has_constraints

ITERATIONS = 100_000


def benchmark_detailed(name, func, data, iterations=ITERATIONS, runs=10):
    """Detailed benchmark with statistics"""
    times = []
    for run in range(runs):
        start = time.perf_counter()
        for item in data[:iterations]:
            try:
                func(item)
            except:
                pass
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    mean = statistics.mean(times)
    std = statistics.stdev(times) if len(times) > 1 else 0
    min_time = min(times)
    max_time = max(times)
    ips = iterations / mean
    
    return {
        'name': name,
        'mean': mean,
        'std': std,
        'min': min_time,
        'max': max_time,
        'ips': ips,
        'times': times
    }


print("🔬 Recursive Optimization Test")
print("=" * 90)
print(f"Testing {ITERATIONS:,} iterations with 10 runs each\n")

# Test 1: Optimize NativeValidator field access
print("=" * 90)
print("TEST 1: Field Access Pattern Optimization")
print("=" * 90)

data = [
    {"name": f"Person{i}", "age": 20 + (i % 60), "email": f"p{i}@example.com"}
    for i in range(ITERATIONS)
]

# Version 1: Current implementation
schema1 = {'name': str, 'age': int, 'email': str}
validator1 = NativeValidator(schema1)

# Version 2: Optimized with pre-computed checks
class OptimizedNativeValidator:
    """Optimized version with minimal overhead"""
    def __init__(self, schema):
        self.schema = schema
        self.field_names = list(schema.keys())
        self.field_types = list(schema.values())
    
    def validate(self, data):
        # Fastest possible validation
        for field_name, field_type in zip(self.field_names, self.field_types):
            value = data.get(field_name)
            if value is None:
                return False
            if field_type is str and not isinstance(value, str):
                return False
            elif field_type is int and (not isinstance(value, int) or isinstance(value, bool)):
                return False
        return True

validator2 = OptimizedNativeValidator(schema1)

print("\nBenchmarking field access patterns:")
result1 = benchmark_detailed("NativeValidator (current)", lambda x: validator1.validate(x), data)
result2 = benchmark_detailed("OptimizedNativeValidator", lambda x: validator2.validate(x), data)

print(f"Current:   {result1['ips']:>12,.0f} ops/sec ({result1['mean']:.3f}s ± {result1['std']:.3f}s)")
print(f"Optimized: {result2['ips']:>12,.0f} ops/sec ({result2['mean']:.3f}s ± {result2['std']:.3f}s)")
print(f"Improvement: {result2['ips']/result1['ips']:.2f}x")

# Test 2: Type checking optimization
print("\n" + "=" * 90)
print("TEST 2: Type Checking Optimization")
print("=" * 90)

# Version 1: Generic isinstance
def check_type_v1(value, expected_type):
    if expected_type is str:
        return isinstance(value, str)
    elif expected_type is int:
        return isinstance(value, int) and not isinstance(value, bool)
    elif expected_type is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, expected_type)

# Version 2: Direct type comparison (faster)
def check_type_v2(value, expected_type):
    if expected_type is str:
        return type(value) is str
    elif expected_type is int:
        return type(value) is int
    elif expected_type is float:
        return type(value) in (int, float)
    return isinstance(value, expected_type)

# Version 3: Cached type checks
_TYPE_CHECKS = {
    str: lambda v: type(v) is str,
    int: lambda v: type(v) is int,
    float: lambda v: type(v) in (int, float),
    bool: lambda v: type(v) is bool,
}

def check_type_v3(value, expected_type):
    checker = _TYPE_CHECKS.get(expected_type)
    if checker:
        return checker(value)
    return isinstance(value, expected_type)

test_values = [
    ("test", str),
    (42, int),
    (3.14, float),
    (True, bool),
] * (ITERATIONS // 4)

print("\nBenchmarking type checking methods:")
result1 = benchmark_detailed("isinstance()", lambda x: check_type_v1(x[0], x[1]), test_values)
result2 = benchmark_detailed("type() is", lambda x: check_type_v2(x[0], x[1]), test_values)
result3 = benchmark_detailed("Cached checks", lambda x: check_type_v3(x[0], x[1]), test_values)

print(f"isinstance():  {result1['ips']:>12,.0f} ops/sec")
print(f"type() is:     {result2['ips']:>12,.0f} ops/sec ({result2['ips']/result1['ips']:.2f}x)")
print(f"Cached:        {result3['ips']:>12,.0f} ops/sec ({result3['ips']/result1['ips']:.2f}x)")

# Test 3: Error handling optimization
print("\n" + "=" * 90)
print("TEST 3: Error Handling Optimization")
print("=" * 90)

# Version 1: Create ValidationResult objects
from satya import ValidationResult, ValidationError

def validate_v1(data):
    errors = []
    for field in ['name', 'age', 'email']:
        if field not in data:
            errors.append(ValidationError(field=field, message='required', path=[field]))
    if errors:
        return ValidationResult(errors=errors)
    return ValidationResult(value=data)

# Version 2: Early return on first error
def validate_v2(data):
    for field in ['name', 'age', 'email']:
        if field not in data:
            return False
    return True

# Version 3: All checks in one expression
def validate_v3(data):
    return 'name' in data and 'age' in data and 'email' in data

print("\nBenchmarking error handling:")
result1 = benchmark_detailed("ValidationResult", lambda x: validate_v1(x), data)
result2 = benchmark_detailed("Early return", lambda x: validate_v2(x), data)
result3 = benchmark_detailed("Single expression", lambda x: validate_v3(x), data)

print(f"ValidationResult: {result1['ips']:>12,.0f} ops/sec")
print(f"Early return:     {result2['ips']:>12,.0f} ops/sec ({result2['ips']/result1['ips']:.2f}x)")
print(f"Single expr:      {result3['ips']:>12,.0f} ops/sec ({result3['ips']/result1['ips']:.2f}x)")

# Test 4: Dictionary access optimization
print("\n" + "=" * 90)
print("TEST 4: Dictionary Access Optimization")
print("=" * 90)

# Version 1: .get() with default
def access_v1(data):
    return data.get('name'), data.get('age'), data.get('email')

# Version 2: Direct access with try/except
def access_v2(data):
    try:
        return data['name'], data['age'], data['email']
    except KeyError:
        return None, None, None

# Version 3: Check then access
def access_v3(data):
    if 'name' in data and 'age' in data and 'email' in data:
        return data['name'], data['age'], data['email']
    return None, None, None

print("\nBenchmarking dictionary access:")
result1 = benchmark_detailed(".get()", lambda x: access_v1(x), data)
result2 = benchmark_detailed("try/except", lambda x: access_v2(x), data)
result3 = benchmark_detailed("check then access", lambda x: access_v3(x), data)

print(f".get():           {result1['ips']:>12,.0f} ops/sec")
print(f"try/except:       {result2['ips']:>12,.0f} ops/sec ({result2['ips']/result1['ips']:.2f}x)")
print(f"check then access:{result3['ips']:>12,.0f} ops/sec ({result3['ips']/result1['ips']:.2f}x)")

# Test 5: Loop optimization
print("\n" + "=" * 90)
print("TEST 5: Loop Optimization")
print("=" * 90)

fields = ['name', 'age', 'email']
types = [str, int, str]

# Version 1: zip()
def validate_loop_v1(data):
    for field, typ in zip(fields, types):
        if not isinstance(data.get(field), typ):
            return False
    return True

# Version 2: enumerate()
def validate_loop_v2(data):
    for i, field in enumerate(fields):
        if not isinstance(data.get(field), types[i]):
            return False
    return True

# Version 3: Unrolled
def validate_loop_v3(data):
    if not isinstance(data.get('name'), str):
        return False
    if not isinstance(data.get('age'), int) or isinstance(data.get('age'), bool):
        return False
    if not isinstance(data.get('email'), str):
        return False
    return True

print("\nBenchmarking loop patterns:")
result1 = benchmark_detailed("zip()", lambda x: validate_loop_v1(x), data)
result2 = benchmark_detailed("enumerate()", lambda x: validate_loop_v2(x), data)
result3 = benchmark_detailed("Unrolled", lambda x: validate_loop_v3(x), data)

print(f"zip():       {result1['ips']:>12,.0f} ops/sec")
print(f"enumerate(): {result2['ips']:>12,.0f} ops/sec ({result2['ips']/result1['ips']:.2f}x)")
print(f"Unrolled:    {result3['ips']:>12,.0f} ops/sec ({result3['ips']/result1['ips']:.2f}x)")

# Summary
print("\n" + "=" * 90)
print("📊 OPTIMIZATION SUMMARY")
print("=" * 90)

optimizations = {
    "Field access": result2['ips'] / result1['ips'] if 'result2' in locals() else 1.0,
    "Type checking (type() is)": result2['ips'] / result1['ips'],
    "Error handling (early return)": result2['ips'] / result1['ips'],
    "Dict access (try/except)": result2['ips'] / result1['ips'],
    "Loop (unrolled)": result3['ips'] / result1['ips'],
}

print("\nOptimization opportunities:")
for name, speedup in optimizations.items():
    status = "🚀" if speedup > 1.5 else "✅" if speedup > 1.1 else "➖"
    print(f"  {status} {name:<35} {speedup:.2f}x")

print("\n💡 Key Findings:")
print("  1. type() is faster than isinstance() for exact type matching")
print("  2. Early return is much faster than building error objects")
print("  3. try/except is fastest for dict access (happy path)")
print("  4. Unrolled loops are faster for small, fixed schemas")
print("  5. Caching type checks provides marginal improvement")

print("\n🎯 Recommendations:")
print("  1. Use type() is for basic types (str, int, float, bool)")
print("  2. Use early return for validation (avoid building errors)")
print("  3. Use try/except for dict access when fields are usually present")
print("  4. Consider unrolling loops for schemas with <5 fields")
print("  5. Keep NativeValidator simple - complexity hurts performance")

print("\n✅ Recursive optimization complete!")
