#!/usr/bin/env python3
"""
Quick demo comparing Satya validation vs standard Python jsonschema library.
This is a simplified version that runs quickly and doesn't require matplotlib.
"""
import gc
import time
import json
import random
from typing import Dict, Any, List

# Smaller dataset for quick demo
N_ITEMS = 10_000  # Quick test with 10K items
BATCH_SIZE = 1_000

def generate_test_data(num_items: int) -> List[Dict[str, Any]]:
    """Generate test data for benchmarking"""
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana"]
    last_names = ["Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson"]
    domains = ["example.com", "test.com", "demo.io"]
    
    data = []
    for i in range(num_items):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 80)
        email = f"{name.lower().replace(' ', '.')}@{random.choice(domains)}"
        
        data.append({
            "id": i,
            "name": name,
            "age": age,
            "email": email,
            "is_active": random.choice([True, False]),
            "score": round(random.uniform(0.0, 100.0), 2)
        })
    
    return data

def run_jsonschema_benchmark() -> tuple:
    """Run validation benchmark using standard jsonschema library"""
    try:
        import jsonschema
        from jsonschema import Draft7Validator
    except ImportError:
        print("❌ jsonschema library not installed")
        print("   Install with: pip install jsonschema")
        return None, None
    
    print("\n" + "="*60)
    print("Testing: jsonschema (Python)")
    print("="*60)
    
    # Define JSON Schema
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string", "minLength": 1},
            "age": {"type": "integer", "minimum": 0, "maximum": 150},
            "email": {
                "type": "string",
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            },
            "is_active": {"type": "boolean"},
            "score": {"type": "number", "minimum": 0, "maximum": 100}
        },
        "required": ["id", "name", "age", "email", "is_active", "score"]
    }
    
    validator = Draft7Validator(schema)
    test_data = generate_test_data(N_ITEMS)
    
    # Warm up
    validator.validate(test_data[0])
    
    # Timed run
    start_time = time.time()
    validated = 0
    for item in test_data:
        try:
            validator.validate(item)
            validated += 1
        except jsonschema.ValidationError:
            pass
    
    total_time = time.time() - start_time
    items_per_second = N_ITEMS / total_time
    
    print(f"✓ Total time: {total_time:.3f}s")
    print(f"✓ Items per second: {int(items_per_second):,}")
    
    return total_time, items_per_second

def run_satya_benchmark() -> tuple:
    """Run validation benchmark using Satya"""
    try:
        from satya import Model, Field
    except ImportError:
        print("❌ Satya not installed")
        print("   Install with: pip install satya")
        return None, None
    
    print("\n" + "="*60)
    print("Testing: Satya (Rust-powered)")
    print("="*60)
    
    # Define model
    class DataRecord(Model):
        id: int = Field(ge=0)
        name: str = Field(min_length=1)
        age: int = Field(ge=0, le=150)
        email: str = Field(email=True)
        is_active: bool
        score: float = Field(ge=0.0, le=100.0)
    
    test_data = generate_test_data(N_ITEMS)
    
    # Warm up
    validator = DataRecord.validator()
    validator.validate(test_data[0])
    
    # Timed run
    start_time = time.time()
    validated = 0
    for i in range(0, N_ITEMS, BATCH_SIZE):
        batch = test_data[i:i+BATCH_SIZE]
        # Use _validator to access the core directly
        results = validator._validator.validate_batch(batch)
        validated += sum(1 for r in results if r)
    
    total_time = time.time() - start_time
    items_per_second = N_ITEMS / total_time
    
    print(f"✓ Total time: {total_time:.3f}s")
    print(f"✓ Items per second: {int(items_per_second):,}")
    
    return total_time, items_per_second

def print_comparison(jsonschema_time, jsonschema_ips, satya_time, satya_ips):
    """Print formatted comparison"""
    print("\n" + "="*60)
    print("COMPARISON RESULTS")
    print("="*60)
    
    speedup = satya_ips / jsonschema_ips
    time_reduction = (1 - satya_time / jsonschema_time) * 100
    
    print(f"\n{'Metric':<30} {'jsonschema':<20} {'Satya':<20}")
    print("-" * 70)
    print(f"{'Time taken (seconds)':<30} {jsonschema_time:<20.3f} {satya_time:<20.3f}")
    print(f"{'Items per second':<30} {int(jsonschema_ips):<20,} {int(satya_ips):<20,}")
    
    print("\n" + "="*60)
    print("PERFORMANCE IMPROVEMENT")
    print("="*60)
    print(f"⚡ Satya is {speedup:.1f}x faster than jsonschema")
    print(f"⏱️  Time reduced by {time_reduction:.1f}%")
    print(f"🚀 Processes {int(satya_ips - jsonschema_ips):,} more items per second")
    print("="*60)

if __name__ == "__main__":
    print("\n" + "🏆"*30)
    print("Quick Demo: Satya vs jsonschema")
    print("🏆"*30)
    print(f"\n📊 Validating {N_ITEMS:,} data records...")
    print("   (Use jsonschema_comparison.py for full 1M item benchmark)")
    
    # Run benchmarks
    gc.collect()
    jsonschema_time, jsonschema_ips = run_jsonschema_benchmark()
    
    if jsonschema_time is None:
        exit(1)
    
    gc.collect()
    satya_time, satya_ips = run_satya_benchmark()
    
    if satya_time is None:
        exit(1)
    
    # Print comparison
    print_comparison(jsonschema_time, jsonschema_ips, satya_time, satya_ips)
    
    print("\n💡 Tip: Install matplotlib and run jsonschema_comparison.py")
    print("   for visual charts with 1M items benchmark")
    print()
