"""
Benchmark Rust-native architecture (v2.0) vs current dict-based architecture
This will help us track performance improvements as we implement each phase.
"""

import time
import statistics
from typing import List, Dict, Any

# Try importing the new Rust-native classes
try:
    from satya._satya import SatyaModelInstance, compile_schema, CompiledSchema
    RUST_NATIVE_AVAILABLE = True
except ImportError:
    RUST_NATIVE_AVAILABLE = False
    print("⚠️  Rust-native classes not available yet")

# Import current implementation
from satya import Model, Field


def benchmark_function(func, iterations=10000, warmup=1000):
    """Benchmark a function with warmup"""
    # Warmup
    for _ in range(warmup):
        func()
    
    # Actual benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append(end - start)
    
    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'min': min(times),
        'max': max(times),
        'ops_per_sec': 1 / statistics.mean(times) if statistics.mean(times) > 0 else 0
    }


def format_time(seconds):
    """Format time in appropriate unit"""
    if seconds < 1e-6:
        return f"{seconds * 1e9:.2f}ns"
    elif seconds < 1e-3:
        return f"{seconds * 1e6:.2f}µs"
    elif seconds < 1:
        return f"{seconds * 1e3:.2f}ms"
    else:
        return f"{seconds:.2f}s"


def format_ops(ops):
    """Format operations per second"""
    if ops > 1e6:
        return f"{ops / 1e6:.2f}M ops/sec"
    elif ops > 1e3:
        return f"{ops / 1e3:.2f}K ops/sec"
    else:
        return f"{ops:.2f} ops/sec"


class TestModel(Model):
    """Simple model for benchmarking"""
    id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=150)
    email: str = Field(email=True)


def benchmark_current_implementation():
    """Benchmark current dict-based implementation"""
    print("\n" + "="*60)
    print("CURRENT IMPLEMENTATION (Dict-Based)")
    print("="*60)
    
    # Test 1: Simple model creation
    print("\n1. Simple Model Creation")
    data = {"id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"}
    
    def create_model():
        return TestModel(**data)
    
    results = benchmark_function(create_model, iterations=10000)
    print(f"   Mean: {format_time(results['mean'])}")
    print(f"   Throughput: {format_ops(results['ops_per_sec'])}")
    
    # Test 2: Field access
    print("\n2. Field Access")
    model = TestModel(**data)
    
    def access_field():
        return model.name
    
    results = benchmark_function(access_field, iterations=100000)
    print(f"   Mean: {format_time(results['mean'])}")
    print(f"   Throughput: {format_ops(results['ops_per_sec'])}")
    
    # Test 3: Batch validation
    print("\n3. Batch Validation (1000 items)")
    batch_data = [
        {"id": i, "name": f"User{i}", "age": 20 + (i % 50), "email": f"user{i}@example.com"}
        for i in range(1, 1001)
    ]
    
    def validate_batch():
        return [TestModel(**item) for item in batch_data]
    
    results = benchmark_function(validate_batch, iterations=10)
    print(f"   Mean: {format_time(results['mean'])}")
    print(f"   Throughput: {format_ops(results['ops_per_sec'] * 1000)} (items/sec)")
    
    # Test 4: Dict conversion
    print("\n4. Dict Conversion")
    model = TestModel(**data)
    
    def to_dict():
        return model.dict()
    
    results = benchmark_function(to_dict, iterations=10000)
    print(f"   Mean: {format_time(results['mean'])}")
    print(f"   Throughput: {format_ops(results['ops_per_sec'])}")
    
    # Test 5: JSON conversion (using json module for now)
    print("\n5. JSON Conversion")
    import json
    
    def to_json():
        return json.dumps(model.dict())
    
    results = benchmark_function(to_json, iterations=10000)
    print(f"   Mean: {format_time(results['mean'])}")
    print(f"   Throughput: {format_ops(results['ops_per_sec'])}")


def benchmark_rust_native_implementation():
    """Benchmark new Rust-native implementation"""
    if not RUST_NATIVE_AVAILABLE:
        print("\n⚠️  Rust-native implementation not available yet")
        return
    
    print("\n" + "="*60)
    print("RUST-NATIVE IMPLEMENTATION (v2.0)")
    print("="*60)
    print("\n⚠️  Full implementation not complete yet")
    print("   This will be populated as we implement Phase 2-5")
    
    # Placeholder for future benchmarks
    print("\n1. Simple Model Creation - TODO")
    print("2. Field Access - TODO")
    print("3. Batch Validation - TODO")
    print("4. Dict Conversion - TODO")
    print("5. JSON Conversion - TODO")


def benchmark_comparison():
    """Compare current vs Rust-native"""
    print("\n" + "="*60)
    print("PERFORMANCE COMPARISON")
    print("="*60)
    
    if not RUST_NATIVE_AVAILABLE:
        print("\n⚠️  Rust-native implementation not available for comparison")
        print("\nExpected improvements (from architecture design):")
        print("   - Model creation: 2.2× faster")
        print("   - Field access: 3× faster")
        print("   - Batch validation: 3.7× faster")
        print("   - Memory usage: 2.3× less")
    else:
        print("\n⚠️  Full comparison will be available after Phase 2-5")


def main():
    """Run all benchmarks"""
    print("\n" + "="*60)
    print("SATYA v2.0 - RUST-NATIVE ARCHITECTURE BENCHMARKS")
    print("="*60)
    print("\nPhase 1: Core Infrastructure - COMPLETE ✓")
    print("Phase 2: Full Validation Engine - IN PROGRESS")
    print("Phase 3: Python Integration - PENDING")
    print("Phase 4: Optimizations - PENDING")
    print("Phase 5: Testing & Benchmarking - PENDING")
    
    # Benchmark current implementation
    benchmark_current_implementation()
    
    # Benchmark Rust-native implementation
    benchmark_rust_native_implementation()
    
    # Comparison
    benchmark_comparison()
    
    print("\n" + "="*60)
    print("BENCHMARK COMPLETE")
    print("="*60)
    print("\nNote: Full benchmarks will be available after Phase 2-5 implementation")
    print("See RUST_NATIVE_V2_PROGRESS.md for implementation status")


if __name__ == "__main__":
    main()
