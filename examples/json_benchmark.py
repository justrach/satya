#!/usr/bin/env python3
"""
Benchmark comparing JSON serialization performance between:
1. Standard json.dumps()
2. orjson.dumps() 
3. Satya's native Rust JSON serialization
4. Satya's Model.json() method
5. orjson + Satya Model.dict() combination
6. orjson + Satya validation combination
"""

import time
import json
from satya import StreamValidator, Model, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False
    print("⚠️  orjson not available, install with: pip install orjson")

class Address(Model):
    street: str = Field(min_length=5, max_length=100)
    city: str = Field(pattern=r'^[A-Za-z\s]+$')
    postal_code: str = Field(pattern=r'^\d{5}(-\d{4})?$')
    country: str = Field(min_length=2, max_length=2)

class User(Model):
    id: str = Field(pattern=r'^[0-9a-f-]+$')
    username: str = Field(min_length=3, max_length=20)
    email: str = Field(email=True)
    age: int = Field(min_value=13, max_value=120)
    score: float = Field(min_value=0.0, max_value=100.0)
    address: Address
    interests: List[str] = Field(min_length=1, max_length=5)
    metadata: Dict[str, Any]
    last_login: Optional[datetime] = Field(required=False)

def generate_test_data(count: int = 1000) -> List[Dict]:
    """Generate test data for benchmarking"""
    base_data = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "username": "john_doe",
        "email": "john@example.com",
        "age": 25,
        "score": 85.5,
        "address": {
            "street": "123 Main Street",
            "city": "New York",
            "postal_code": "10001",
            "country": "US"
        },
        "interests": ["coding", "music", "sports"],
        "metadata": {
            "language": "en",
            "theme": "dark",
            "notifications": True
        },
        "last_login": "2024-01-01T12:00:00Z"
    }
    
    return [
        {**base_data, "id": f"123e4567-e89b-12d3-a456-42661417{i:04d}", "username": f"user_{i}"}
        for i in range(count)
    ]

def benchmark_json_methods(data_list: List[Dict], iterations: int = 100):
    """Benchmark different JSON serialization methods"""
    print(f"\n🚀 Benchmarking JSON serialization with {len(data_list)} records, {iterations} iterations each\n")
    
    # Create validator and user instances
    validator = User.validator()
    user_instances = [User(**data) for data in data_list]
    
    results = {}
    
    # 1. Standard json.dumps()
    print("1️⃣  Testing standard json.dumps()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for data in data_list:
            json.dumps(data)
    end_time = time.perf_counter()
    results['json.dumps'] = end_time - start_time
    print(f"   ⏱️  Time: {results['json.dumps']:.4f}s")
    
    # 2. orjson.dumps() (if available)
    if HAS_ORJSON:
        print("2️⃣  Testing orjson.dumps()...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for data in data_list:
                orjson.dumps(data)
        end_time = time.perf_counter()
        results['orjson.dumps'] = end_time - start_time
        print(f"   ⏱️  Time: {results['orjson.dumps']:.4f}s")
    
    # 3. Satya's Rust JSON serialization
    print("3️⃣  Testing Satya validator.to_json()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for data in data_list:
            validator.to_json(data)
    end_time = time.perf_counter()
    results['satya_validator'] = end_time - start_time
    print(f"   ⏱️  Time: {results['satya_validator']:.4f}s")
    
    # 4. Satya's Model.json() method
    print("4️⃣  Testing Satya Model.json()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for user in user_instances:
            user.json()
    end_time = time.perf_counter()
    results['satya_model'] = end_time - start_time
    print(f"   ⏱️  Time: {results['satya_model']:.4f}s")
    
    # 5. orjson + Satya Model.dict() combination
    if HAS_ORJSON:
        print("5️⃣  Testing orjson.dumps(Model.dict())...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for user in user_instances:
                orjson.dumps(user.dict())
        end_time = time.perf_counter()
        results['orjson_model_dict'] = end_time - start_time
        print(f"   ⏱️  Time: {results['orjson_model_dict']:.4f}s")
    
    # 6. orjson + Satya validation combination
    if HAS_ORJSON:
        print("6️⃣  Testing orjson + Satya validation...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for data in data_list:
                # Validate first, then serialize
                result = validator.validate(data)
                if result.is_valid:
                    orjson.dumps(result.value)
        end_time = time.perf_counter()
        results['orjson_validated'] = end_time - start_time
        print(f"   ⏱️  Time: {results['orjson_validated']:.4f}s")
    
    # Print comparison
    print("\n📊 Performance Comparison:")
    baseline = results['json.dumps']
    for method, time_taken in results.items():
        speedup = baseline / time_taken
        print(f"   {method:20}: {time_taken:.4f}s ({speedup:.2f}x {'faster' if speedup > 1 else 'slower'})")
    
    return results

def benchmark_parsing(json_strings: List[str], iterations: int = 100):
    """Benchmark JSON parsing methods"""
    print(f"\n🔄 Benchmarking JSON parsing with {len(json_strings)} records, {iterations} iterations each\n")
    
    validator = User.validator()
    results = {}
    
    # 1. Standard json.loads()
    print("1️⃣  Testing standard json.loads()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for json_str in json_strings:
            json.loads(json_str)
    end_time = time.perf_counter()
    results['json.loads'] = end_time - start_time
    print(f"   ⏱️  Time: {results['json.loads']:.4f}s")
    
    # 2. orjson.loads() (if available)
    if HAS_ORJSON:
        print("2️⃣  Testing orjson.loads()...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for json_str in json_strings:
                orjson.loads(json_str)
        end_time = time.perf_counter()
        results['orjson.loads'] = end_time - start_time
        print(f"   ⏱️  Time: {results['orjson.loads']:.4f}s")
    
    # 3. Satya's Rust JSON parsing
    print("3️⃣  Testing Satya validator.from_json()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for json_str in json_strings:
            validator.from_json(json_str)
    end_time = time.perf_counter()
    results['satya_validator'] = end_time - start_time
    print(f"   ⏱️  Time: {results['satya_validator']:.4f}s")
    
    # 4. Satya's Model.from_json() method
    print("4️⃣  Testing Satya Model.from_json()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for json_str in json_strings:
            User.from_json(json_str)
    end_time = time.perf_counter()
    results['satya_model'] = end_time - start_time
    print(f"   ⏱️  Time: {results['satya_model']:.4f}s")
    
    # 5. orjson + Satya validation combination
    if HAS_ORJSON:
        print("5️⃣  Testing orjson + Satya validation...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for json_str in json_strings:
                # Parse first, then validate
                data = orjson.loads(json_str)
                validator.validate(data)
        end_time = time.perf_counter()
        results['orjson_validated'] = end_time - start_time
        print(f"   ⏱️  Time: {results['orjson_validated']:.4f}s")
    
    # Print comparison
    print("\n📊 Performance Comparison:")
    baseline = results['json.loads']
    for method, time_taken in results.items():
        speedup = baseline / time_taken
        print(f"   {method:20}: {time_taken:.4f}s ({speedup:.2f}x {'faster' if speedup > 1 else 'slower'})")
    
    return results

def main():
    print("🔥 Satya JSON Performance Benchmark")
    print("=" * 50)
    
    # Generate test data
    data_count = 1000
    iterations = 50
    
    print(f"📝 Generating {data_count} test records...")
    test_data = generate_test_data(data_count)
    
    # Benchmark serialization
    serialization_results = benchmark_json_methods(test_data, iterations)
    
    # Generate JSON strings for parsing benchmark
    print(f"\n📝 Generating JSON strings for parsing benchmark...")
    if HAS_ORJSON:
        json_strings = [orjson.dumps(data).decode('utf-8') for data in test_data]
    else:
        json_strings = [json.dumps(data) for data in test_data]
    
    # Benchmark parsing
    parsing_results = benchmark_parsing(json_strings, iterations)
    
    print("\n🎉 Benchmark Complete!")
    print("\n💡 Key Takeaways:")
    print("   • Satya provides native Rust-powered JSON serialization")
    print("   • Model.json() method uses orjson when available for maximum speed")
    print("   • orjson + Satya combinations provide validation with performance")
    print("   • Validator methods provide additional validation during serialization")
    print("   • All methods maintain full compatibility with Python's json module")

if __name__ == "__main__":
    main() 