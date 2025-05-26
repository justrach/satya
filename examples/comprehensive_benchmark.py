#!/usr/bin/env python3
"""
Comprehensive JSON/Serialization Benchmark comparing:
1. Standard json
2. orjson
3. msgspec
4. Satya (various methods)
5. Combinations of the above

Generates performance graphs for visualization.
"""

import time
import json
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

# Satya imports
from satya import StreamValidator, Model, Field

# Optional imports with fallbacks
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False
    print("⚠️  orjson not available")

try:
    import msgspec
    HAS_MSGSPEC = True
except ImportError:
    HAS_MSGSPEC = False
    print("⚠️  msgspec not available (install with: pip install msgspec)")

try:
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️  matplotlib not available (install with: pip install matplotlib)")

# Satya Models
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

# msgspec equivalents (if available)
if HAS_MSGSPEC:
    class MsgspecAddress(msgspec.Struct):
        street: str
        city: str
        postal_code: str
        country: str

    class MsgspecUser(msgspec.Struct):
        id: str
        username: str
        email: str
        age: int
        score: float
        address: MsgspecAddress
        interests: List[str]
        metadata: Dict[str, Any]
        last_login: Optional[str] = None

@dataclass
class BenchmarkResult:
    name: str
    serialization_time: float
    parsing_time: float
    serialization_ops_per_sec: float
    parsing_ops_per_sec: float

def generate_test_data(count: int = 1000) -> Tuple[List[Dict], List[User], List]:
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
    
    # Generate raw dicts
    raw_data = [
        {**base_data, "id": f"123e4567-e89b-12d3-a456-42661417{i:04d}", "username": f"user_{i}"}
        for i in range(count)
    ]
    
    # Generate Satya models
    satya_users = [User(**data) for data in raw_data]
    
    # Generate msgspec models (if available)
    msgspec_users = []
    if HAS_MSGSPEC:
        for data in raw_data:
            addr = MsgspecAddress(**data["address"])
            user = MsgspecUser(
                id=data["id"],
                username=data["username"],
                email=data["email"],
                age=data["age"],
                score=data["score"],
                address=addr,
                interests=data["interests"],
                metadata=data["metadata"],
                last_login=data["last_login"]
            )
            msgspec_users.append(user)
    
    return raw_data, satya_users, msgspec_users

def benchmark_serialization(raw_data: List[Dict], satya_users: List[User], msgspec_users: List, iterations: int = 100) -> List[BenchmarkResult]:
    """Benchmark serialization methods"""
    results = []
    total_ops = len(raw_data) * iterations
    
    print(f"\n🚀 Benchmarking Serialization ({len(raw_data)} records × {iterations} iterations)\n")
    
    # 1. Standard json.dumps()
    print("1️⃣  json.dumps()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for data in raw_data:
            json.dumps(data)
    end_time = time.perf_counter()
    json_time = end_time - start_time
    results.append(BenchmarkResult(
        "json.dumps", json_time, 0, total_ops / json_time, 0
    ))
    print(f"   ⏱️  {json_time:.4f}s ({total_ops / json_time:.0f} ops/sec)")
    
    # 2. orjson.dumps()
    if HAS_ORJSON:
        print("2️⃣  orjson.dumps()...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for data in raw_data:
                orjson.dumps(data)
        end_time = time.perf_counter()
        orjson_time = end_time - start_time
        results.append(BenchmarkResult(
            "orjson.dumps", orjson_time, 0, total_ops / orjson_time, 0
        ))
        print(f"   ⏱️  {orjson_time:.4f}s ({total_ops / orjson_time:.0f} ops/sec)")
    
    # 3. msgspec.json.encode()
    if HAS_MSGSPEC:
        print("3️⃣  msgspec.json.encode()...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for user in msgspec_users:
                msgspec.json.encode(user)
        end_time = time.perf_counter()
        msgspec_time = end_time - start_time
        results.append(BenchmarkResult(
            "msgspec.encode", msgspec_time, 0, total_ops / msgspec_time, 0
        ))
        print(f"   ⏱️  {msgspec_time:.4f}s ({total_ops / msgspec_time:.0f} ops/sec)")
    
    # 4. Satya Model.json()
    print("4️⃣  Satya Model.json()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for user in satya_users:
            user.json()
    end_time = time.perf_counter()
    satya_model_time = end_time - start_time
    results.append(BenchmarkResult(
        "Satya Model.json", satya_model_time, 0, total_ops / satya_model_time, 0
    ))
    print(f"   ⏱️  {satya_model_time:.4f}s ({total_ops / satya_model_time:.0f} ops/sec)")
    
    # 5. Satya validator.to_json()
    validator = User.validator()
    print("5️⃣  Satya validator.to_json()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for data in raw_data:
            validator.to_json(data)
    end_time = time.perf_counter()
    satya_validator_time = end_time - start_time
    results.append(BenchmarkResult(
        "Satya validator.to_json", satya_validator_time, 0, total_ops / satya_validator_time, 0
    ))
    print(f"   ⏱️  {satya_validator_time:.4f}s ({total_ops / satya_validator_time:.0f} ops/sec)")
    
    # 6. orjson + Satya Model.dict()
    if HAS_ORJSON:
        print("6️⃣  orjson + Satya Model.dict()...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for user in satya_users:
                orjson.dumps(user.dict())
        end_time = time.perf_counter()
        orjson_satya_time = end_time - start_time
        results.append(BenchmarkResult(
            "orjson + Satya.dict", orjson_satya_time, 0, total_ops / orjson_satya_time, 0
        ))
        print(f"   ⏱️  {orjson_satya_time:.4f}s ({total_ops / orjson_satya_time:.0f} ops/sec)")
    
    return results

def benchmark_parsing(json_strings: List[str], iterations: int = 100) -> List[BenchmarkResult]:
    """Benchmark parsing methods"""
    results = []
    total_ops = len(json_strings) * iterations
    
    print(f"\n🔄 Benchmarking Parsing ({len(json_strings)} records × {iterations} iterations)\n")
    
    # 1. Standard json.loads()
    print("1️⃣  json.loads()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for json_str in json_strings:
            json.loads(json_str)
    end_time = time.perf_counter()
    json_time = end_time - start_time
    results.append(BenchmarkResult(
        "json.loads", 0, json_time, 0, total_ops / json_time
    ))
    print(f"   ⏱️  {json_time:.4f}s ({total_ops / json_time:.0f} ops/sec)")
    
    # 2. orjson.loads()
    if HAS_ORJSON:
        print("2️⃣  orjson.loads()...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for json_str in json_strings:
                orjson.loads(json_str)
        end_time = time.perf_counter()
        orjson_time = end_time - start_time
        results.append(BenchmarkResult(
            "orjson.loads", 0, orjson_time, 0, total_ops / orjson_time
        ))
        print(f"   ⏱️  {orjson_time:.4f}s ({total_ops / orjson_time:.0f} ops/sec)")
    
    # 3. msgspec.json.decode()
    if HAS_MSGSPEC:
        print("3️⃣  msgspec.json.decode()...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for json_str in json_strings:
                msgspec.json.decode(json_str.encode(), type=MsgspecUser)
        end_time = time.perf_counter()
        msgspec_time = end_time - start_time
        results.append(BenchmarkResult(
            "msgspec.decode", 0, msgspec_time, 0, total_ops / msgspec_time
        ))
        print(f"   ⏱️  {msgspec_time:.4f}s ({total_ops / msgspec_time:.0f} ops/sec)")
    
    # 4. Satya Model.from_json()
    print("4️⃣  Satya Model.from_json()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for json_str in json_strings:
            User.from_json(json_str)
    end_time = time.perf_counter()
    satya_model_time = end_time - start_time
    results.append(BenchmarkResult(
        "Satya Model.from_json", 0, satya_model_time, 0, total_ops / satya_model_time
    ))
    print(f"   ⏱️  {satya_model_time:.4f}s ({total_ops / satya_model_time:.0f} ops/sec)")
    
    # 5. Satya validator.from_json()
    validator = User.validator()
    print("5️⃣  Satya validator.from_json()...")
    start_time = time.perf_counter()
    for _ in range(iterations):
        for json_str in json_strings:
            validator.from_json(json_str)
    end_time = time.perf_counter()
    satya_validator_time = end_time - start_time
    results.append(BenchmarkResult(
        "Satya validator.from_json", 0, satya_validator_time, 0, total_ops / satya_validator_time
    ))
    print(f"   ⏱️  {satya_validator_time:.4f}s ({total_ops / satya_validator_time:.0f} ops/sec)")
    
    return results

def create_performance_graphs(serialization_results: List[BenchmarkResult], parsing_results: List[BenchmarkResult]):
    """Create performance comparison graphs"""
    if not HAS_MATPLOTLIB:
        print("⚠️  matplotlib not available, skipping graph generation")
        return
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('JSON Serialization Performance Benchmark', fontsize=16, fontweight='bold')
    
    # Serialization Time Comparison
    ser_names = [r.name for r in serialization_results]
    ser_times = [r.serialization_time for r in serialization_results]
    
    bars1 = ax1.bar(range(len(ser_names)), ser_times, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'])
    ax1.set_title('Serialization Time (Lower is Better)', fontweight='bold')
    ax1.set_ylabel('Time (seconds)')
    ax1.set_xticks(range(len(ser_names)))
    ax1.set_xticklabels(ser_names, rotation=45, ha='right')
    
    # Add value labels on bars
    for bar, time_val in zip(bars1, ser_times):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{time_val:.3f}s', ha='center', va='bottom', fontsize=9)
    
    # Serialization Ops/sec Comparison
    ser_ops = [r.serialization_ops_per_sec for r in serialization_results]
    
    bars2 = ax2.bar(range(len(ser_names)), ser_ops, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'])
    ax2.set_title('Serialization Throughput (Higher is Better)', fontweight='bold')
    ax2.set_ylabel('Operations per Second')
    ax2.set_xticks(range(len(ser_names)))
    ax2.set_xticklabels(ser_names, rotation=45, ha='right')
    
    # Add value labels on bars
    for bar, ops_val in zip(bars2, ser_ops):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{ops_val:.0f}', ha='center', va='bottom', fontsize=9)
    
    # Parsing Time Comparison
    par_names = [r.name for r in parsing_results]
    par_times = [r.parsing_time for r in parsing_results]
    
    bars3 = ax3.bar(range(len(par_names)), par_times, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'])
    ax3.set_title('Parsing Time (Lower is Better)', fontweight='bold')
    ax3.set_ylabel('Time (seconds)')
    ax3.set_xticks(range(len(par_names)))
    ax3.set_xticklabels(par_names, rotation=45, ha='right')
    
    # Add value labels on bars
    for bar, time_val in zip(bars3, par_times):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{time_val:.3f}s', ha='center', va='bottom', fontsize=9)
    
    # Parsing Ops/sec Comparison
    par_ops = [r.parsing_ops_per_sec for r in parsing_results]
    
    bars4 = ax4.bar(range(len(par_names)), par_ops, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'])
    ax4.set_title('Parsing Throughput (Higher is Better)', fontweight='bold')
    ax4.set_ylabel('Operations per Second')
    ax4.set_xticks(range(len(par_names)))
    ax4.set_xticklabels(par_names, rotation=45, ha='right')
    
    # Add value labels on bars
    for bar, ops_val in zip(bars4, par_ops):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{ops_val:.0f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('json_benchmark_results.png', dpi=300, bbox_inches='tight')
    plt.show()
    print("\n📊 Graphs saved as 'json_benchmark_results.png'")

def print_summary_table(serialization_results: List[BenchmarkResult], parsing_results: List[BenchmarkResult]):
    """Print a summary table of all results"""
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE BENCHMARK SUMMARY")
    print("="*80)
    
    print("\n🚀 SERIALIZATION RESULTS:")
    print(f"{'Method':<25} {'Time (s)':<10} {'Ops/sec':<12} {'vs json.dumps':<15}")
    print("-" * 70)
    
    baseline_ser = next(r.serialization_time for r in serialization_results if r.name == "json.dumps")
    for result in serialization_results:
        speedup = baseline_ser / result.serialization_time
        print(f"{result.name:<25} {result.serialization_time:<10.4f} {result.serialization_ops_per_sec:<12.0f} {speedup:<15.2f}x")
    
    print("\n🔄 PARSING RESULTS:")
    print(f"{'Method':<25} {'Time (s)':<10} {'Ops/sec':<12} {'vs json.loads':<15}")
    print("-" * 70)
    
    baseline_par = next(r.parsing_time for r in parsing_results if r.name == "json.loads")
    for result in parsing_results:
        speedup = baseline_par / result.parsing_time
        print(f"{result.name:<25} {result.parsing_time:<10.4f} {result.parsing_ops_per_sec:<12.0f} {speedup:<15.2f}x")

def main():
    print("🔥 Comprehensive JSON/Serialization Benchmark")
    print("=" * 60)
    print(f"Python {sys.version}")
    print(f"orjson available: {HAS_ORJSON}")
    print(f"msgspec available: {HAS_MSGSPEC}")
    print(f"matplotlib available: {HAS_MATPLOTLIB}")
    
    # Configuration
    data_count = 1000
    iterations = 50
    
    print(f"\n📝 Generating {data_count} test records...")
    raw_data, satya_users, msgspec_users = generate_test_data(data_count)
    
    # Benchmark serialization
    serialization_results = benchmark_serialization(raw_data, satya_users, msgspec_users, iterations)
    
    # Generate JSON strings for parsing benchmark
    print(f"\n📝 Generating JSON strings for parsing benchmark...")
    if HAS_ORJSON:
        json_strings = [orjson.dumps(data).decode('utf-8') for data in raw_data]
    else:
        json_strings = [json.dumps(data) for data in raw_data]
    
    # Benchmark parsing
    parsing_results = benchmark_parsing(json_strings, iterations)
    
    # Print summary
    print_summary_table(serialization_results, parsing_results)
    
    # Create graphs
    create_performance_graphs(serialization_results, parsing_results)
    
    print("\n🎉 Comprehensive Benchmark Complete!")
    print("\n💡 Key Insights:")
    print("   • msgspec is typically fastest for both serialization and parsing")
    print("   • orjson provides excellent performance for general JSON operations")
    print("   • Satya Model.json() leverages orjson when available")
    print("   • Satya provides validation + performance in one package")
    print("   • Choose based on your needs: speed vs validation vs compatibility")

if __name__ == "__main__":
    main() 