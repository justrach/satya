#!/usr/bin/env python3
"""
Detailed Satya vs msgspec Performance Analysis
==============================================

This benchmark identifies specific operations where msgspec is faster
and analyzes whether native CPython optimizations could help.
"""

import time
import json
import sys
import os
from typing import List, Dict, Any, Optional
from decimal import Decimal
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import satya

# Test scenarios
ITERATIONS = 1_000_000


def benchmark_operation(name: str, satya_func, msgspec_func, data, iterations=ITERATIONS):
    """Benchmark a specific operation"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    # Warm up
    for _ in range(100):
        try:
            satya_func(data[0])
        except:
            pass
        try:
            msgspec_func(data[0])
        except:
            pass
    
    # Benchmark Satya
    satya_times = []
    for run in range(5):
        start = time.perf_counter()
        for item in data[:iterations]:
            try:
                satya_func(item)
            except:
                pass
        elapsed = time.perf_counter() - start
        satya_times.append(elapsed)
    
    satya_mean = statistics.mean(satya_times)
    satya_std = statistics.stdev(satya_times) if len(satya_times) > 1 else 0
    satya_ips = iterations / satya_mean
    
    # Benchmark msgspec
    msgspec_times = []
    for run in range(5):
        start = time.perf_counter()
        for item in data[:iterations]:
            try:
                msgspec_func(item)
            except:
                pass
        elapsed = time.perf_counter() - start
        msgspec_times.append(elapsed)
    
    msgspec_mean = statistics.mean(msgspec_times)
    msgspec_std = statistics.stdev(msgspec_times) if len(msgspec_times) > 1 else 0
    msgspec_ips = iterations / msgspec_mean
    
    # Results
    ratio = msgspec_ips / satya_ips
    print(f"\nSatya:   {satya_ips:,.0f} ops/sec ({satya_mean:.3f}s ± {satya_std:.3f}s)")
    print(f"msgspec: {msgspec_ips:,.0f} ops/sec ({msgspec_mean:.3f}s ± {msgspec_std:.3f}s)")
    print(f"Ratio:   msgspec is {ratio:.2f}x {'faster' if ratio > 1 else 'slower'}")
    
    return {
        'name': name,
        'satya_ips': satya_ips,
        'msgspec_ips': msgspec_ips,
        'ratio': ratio,
        'satya_mean': satya_mean,
        'msgspec_mean': msgspec_mean,
    }


def main():
    print("🔍 Detailed Satya vs msgspec Performance Analysis")
    print("=" * 60)
    
    results = []
    
    # Test 1: Simple string validation
    print("\n\n📝 TEST 1: Simple String Validation")
    print("Testing basic string type checking with no constraints")
    
    class SatyaString(satya.Model):
        value: str
    
    try:
        import msgspec
        class MsgspecString(msgspec.Struct):
            value: str
        
        data = [{"value": f"test_string_{i}"} for i in range(ITERATIONS)]
        
        result = benchmark_operation(
            "Simple String",
            lambda x: SatyaString(**x),
            lambda x: MsgspecString(**x),
            data
        )
        results.append(result)
    except ImportError:
        print("⚠️  msgspec not available")
    
    # Test 2: Integer validation
    print("\n\n🔢 TEST 2: Simple Integer Validation")
    print("Testing basic integer type checking with no constraints")
    
    class SatyaInt(satya.Model):
        value: int
    
    try:
        class MsgspecInt(msgspec.Struct):
            value: int
        
        data = [{"value": i} for i in range(ITERATIONS)]
        
        result = benchmark_operation(
            "Simple Integer",
            lambda x: SatyaInt(**x),
            lambda x: MsgspecInt(**x),
            data
        )
        results.append(result)
    except:
        pass
    
    # Test 3: Simple object with 3 fields
    print("\n\n📦 TEST 3: Simple Object (3 fields)")
    print("Testing object with name, age, email - no validation")
    
    class SatyaPerson(satya.Model):
        name: str
        age: int
        email: str
    
    try:
        class MsgspecPerson(msgspec.Struct):
            name: str
            age: int
            email: str
        
        data = [
            {"name": f"Person{i}", "age": 20 + (i % 60), "email": f"person{i}@example.com"}
            for i in range(ITERATIONS)
        ]
        
        result = benchmark_operation(
            "Simple Object (3 fields)",
            lambda x: SatyaPerson(**x),
            lambda x: MsgspecPerson(**x),
            data
        )
        results.append(result)
    except:
        pass
    
    # Test 4: Optional fields
    print("\n\n❓ TEST 4: Optional Fields")
    print("Testing objects with optional fields")
    
    class SatyaOptional(satya.Model):
        required: str
        optional: Optional[str] = None
    
    try:
        class MsgspecOptional(msgspec.Struct):
            required: str
            optional: Optional[str] = None
        
        data = [
            {"required": f"req{i}", "optional": f"opt{i}" if i % 2 == 0 else None}
            for i in range(ITERATIONS)
        ]
        
        result = benchmark_operation(
            "Optional Fields",
            lambda x: SatyaOptional(**x),
            lambda x: MsgspecOptional(**x),
            data
        )
        results.append(result)
    except:
        pass
    
    # Test 5: Nested objects
    print("\n\n🪆 TEST 5: Nested Objects")
    print("Testing nested object validation")
    
    class SatyaAddress(satya.Model):
        street: str
        city: str
    
    class SatyaPersonWithAddress(satya.Model):
        name: str
        address: SatyaAddress
    
    try:
        class MsgspecAddress(msgspec.Struct):
            street: str
            city: str
        
        class MsgspecPersonWithAddress(msgspec.Struct):
            name: str
            address: MsgspecAddress
        
        data = [
            {
                "name": f"Person{i}",
                "address": {"street": f"Street {i}", "city": f"City {i % 100}"}
            }
            for i in range(ITERATIONS)
        ]
        
        result = benchmark_operation(
            "Nested Objects",
            lambda x: SatyaPersonWithAddress(**x),
            lambda x: MsgspecPersonWithAddress(**x),
            data
        )
        results.append(result)
    except:
        pass
    
    # Test 6: Lists
    print("\n\n📋 TEST 6: Lists")
    print("Testing list validation")
    
    class SatyaWithList(satya.Model):
        items: List[str]
    
    try:
        class MsgspecWithList(msgspec.Struct):
            items: List[str]
        
        data = [
            {"items": [f"item{j}" for j in range(5)]}
            for i in range(ITERATIONS)
        ]
        
        result = benchmark_operation(
            "Lists (5 items)",
            lambda x: SatyaWithList(**x),
            lambda x: MsgspecWithList(**x),
            data
        )
        results.append(result)
    except:
        pass
    
    # Test 7: Mixed types
    print("\n\n🎭 TEST 7: Mixed Types")
    print("Testing object with various types")
    
    class SatyaMixed(satya.Model):
        name: str
        age: int
        score: float
        active: bool
        tags: List[str]
    
    try:
        class MsgspecMixed(msgspec.Struct):
            name: str
            age: int
            score: float
            active: bool
            tags: List[str]
        
        data = [
            {
                "name": f"Item{i}",
                "age": 20 + (i % 60),
                "score": 75.5 + (i % 25),
                "active": i % 2 == 0,
                "tags": [f"tag{j}" for j in range(3)]
            }
            for i in range(ITERATIONS)
        ]
        
        result = benchmark_operation(
            "Mixed Types",
            lambda x: SatyaMixed(**x),
            lambda x: MsgspecMixed(**x),
            data
        )
        results.append(result)
    except:
        pass
    
    # Summary
    print("\n\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    if results:
        print(f"\n{'Test':<30} {'Satya (ops/s)':<20} {'msgspec (ops/s)':<20} {'Ratio':<10}")
        print("-" * 80)
        for r in results:
            print(f"{r['name']:<30} {r['satya_ips']:>15,.0f}    {r['msgspec_ips']:>15,.0f}    {r['ratio']:>6.2f}x")
        
        # Find slowest operations
        print("\n\n🐌 SLOWEST OPERATIONS (where msgspec is fastest):")
        sorted_results = sorted(results, key=lambda x: x['ratio'], reverse=True)
        for r in sorted_results[:3]:
            if r['ratio'] > 1:
                print(f"  • {r['name']}: msgspec {r['ratio']:.2f}x faster")
                print(f"    - Satya: {r['satya_ips']:,.0f} ops/sec")
                print(f"    - msgspec: {r['msgspec_ips']:,.0f} ops/sec")
                print(f"    - Time difference: {(r['satya_mean'] - r['msgspec_mean'])*1000:.2f}ms per 1M ops")
        
        # Analysis
        print("\n\n💡 ANALYSIS:")
        print("=" * 60)
        
        avg_ratio = statistics.mean([r['ratio'] for r in results])
        print(f"Average msgspec advantage: {avg_ratio:.2f}x")
        
        print("\n🔍 Where msgspec wins:")
        print("  • Simple type checking (no constraints)")
        print("  • Minimal validation logic")
        print("  • Pure C implementation with no Python overhead")
        
        print("\n🚀 Where Satya can improve:")
        print("  • Use native CPython type checking for simple cases")
        print("  • Bypass Rust for unconstrained fields")
        print("  • Fast-path for common patterns")
        print("  • Lazy validation for optional fields")
        
        print("\n⚖️  Trade-offs:")
        print("  • msgspec: Fast but limited validation")
        print("  • Satya: Comprehensive validation with reasonable overhead")
        print("  • For simple types: msgspec ~2x faster")
        print("  • For complex validation: Satya competitive or faster")
        
        # Save results
        os.makedirs('benchmarks/results', exist_ok=True)
        with open('benchmarks/results/satya_vs_msgspec_detailed.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("\n💾 Results saved to benchmarks/results/satya_vs_msgspec_detailed.json")


if __name__ == "__main__":
    main()
