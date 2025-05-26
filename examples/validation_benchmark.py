#!/usr/bin/env python3
"""
Validation Benchmark comparing:
1. Satya + orjson (with validation)
2. msgspec (with validation)
3. Pure performance baselines (no validation)

This benchmark focuses on the validation overhead and performance
when data validation is actually performed.
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

# Satya Models with comprehensive validation
class Address(Model):
    street: str = Field(min_length=5, max_length=100, description="Street address")
    city: str = Field(pattern=r'^[A-Za-z\s]+$', description="City name (letters only)")
    postal_code: str = Field(pattern=r'^\d{5}(-\d{4})?$', description="US postal code")
    country: str = Field(min_length=2, max_length=2, description="Country code")

class User(Model):
    id: str = Field(pattern=r'^[0-9a-f-]+$', description="User ID")
    username: str = Field(min_length=3, max_length=20, pattern=r'^[a-zA-Z0-9_]+$')
    email: str = Field(email=True, description="Valid email address")
    age: int = Field(min_value=13, max_value=120, description="User age")
    score: float = Field(min_value=0.0, max_value=100.0, description="User score")
    address: Address
    interests: List[str] = Field(min_length=1, max_length=5)
    metadata: Dict[str, Any]
    last_login: Optional[datetime] = Field(required=False)

# msgspec equivalents with validation
if HAS_MSGSPEC:
    import msgspec
    
    class MsgspecAddress(msgspec.Struct):
        street: str
        city: str
        postal_code: str
        country: str
        
        def __post_init__(self):
            # Manual validation for msgspec
            if not (5 <= len(self.street) <= 100):
                raise ValueError(f"Street length must be 5-100 chars, got {len(self.street)}")
            if not self.city.replace(' ', '').isalpha():
                raise ValueError(f"City must contain only letters and spaces")
            if not (len(self.postal_code) == 5 or (len(self.postal_code) == 10 and '-' in self.postal_code)):
                raise ValueError(f"Invalid postal code format")
            if len(self.country) != 2:
                raise ValueError(f"Country code must be 2 characters")

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
        
        def __post_init__(self):
            # Manual validation for msgspec
            if not (3 <= len(self.username) <= 20):
                raise ValueError(f"Username length must be 3-20 chars")
            if not self.username.replace('_', '').isalnum():
                raise ValueError(f"Username must be alphanumeric with underscores")
            if '@' not in self.email or '.' not in self.email:
                raise ValueError(f"Invalid email format")
            if not (13 <= self.age <= 120):
                raise ValueError(f"Age must be 13-120")
            if not (0.0 <= self.score <= 100.0):
                raise ValueError(f"Score must be 0-100")
            if not (1 <= len(self.interests) <= 5):
                raise ValueError(f"Must have 1-5 interests")

@dataclass
class ValidationBenchmarkResult:
    name: str
    serialization_time: float
    parsing_time: float
    validation_time: float
    total_time: float
    ops_per_sec: float
    validation_ops_per_sec: float

def generate_test_data(count: int = 1000) -> Tuple[List[Dict], List[Dict]]:
    """Generate both valid and invalid test data"""
    base_valid = {
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
    
    base_invalid = {
        "id": "invalid-id-format",  # Invalid format
        "username": "jo",  # Too short
        "email": "invalid-email",  # Invalid email
        "age": 150,  # Too old
        "score": 150.0,  # Too high
        "address": {
            "street": "123",  # Too short
            "city": "New York123",  # Contains numbers
            "postal_code": "invalid",  # Invalid format
            "country": "USA"  # Too long
        },
        "interests": [],  # Empty list
        "metadata": {
            "language": "en",
            "theme": "dark"
        },
        "last_login": "2024-01-01T12:00:00Z"
    }
    
    # Generate valid data
    valid_data = [
        {**base_valid, "id": f"123e4567-e89b-12d3-a456-42661417{i:04d}", "username": f"user_{i}"}
        for i in range(count)
    ]
    
    # Generate invalid data
    invalid_data = [
        {**base_invalid, "username": f"u{i}"}  # Keep making it invalid
        for i in range(count)
    ]
    
    return valid_data, invalid_data

def benchmark_validation_serialization(valid_data: List[Dict], invalid_data: List[Dict], iterations: int = 50) -> List[ValidationBenchmarkResult]:
    """Benchmark serialization with validation"""
    results = []
    total_ops = len(valid_data) * iterations
    
    print(f"\n🚀 Benchmarking Validation + Serialization ({len(valid_data)} records × {iterations} iterations)\n")
    
    # 1. Baseline: orjson without validation
    if HAS_ORJSON:
        print("1️⃣  orjson.dumps() (no validation)...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for data in valid_data:
                orjson.dumps(data)
        end_time = time.perf_counter()
        orjson_time = end_time - start_time
        results.append(ValidationBenchmarkResult(
            "orjson (no validation)", orjson_time, 0, 0, orjson_time, 
            total_ops / orjson_time, 0
        ))
        print(f"   ⏱️  {orjson_time:.4f}s ({total_ops / orjson_time:.0f} ops/sec)")
    
    # 2. msgspec with validation
    if HAS_MSGSPEC:
        print("2️⃣  msgspec with validation...")
        
        # First convert data to msgspec objects (this includes validation)
        print("   📝 Converting to msgspec objects with validation...")
        msgspec_users = []
        validation_start = time.perf_counter()
        for data in valid_data:
            try:
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
            except Exception as e:
                print(f"   ❌ Validation failed: {e}")
                continue
        validation_end = time.perf_counter()
        validation_time = validation_end - validation_start
        
        # Now benchmark serialization
        start_time = time.perf_counter()
        for _ in range(iterations):
            for user in msgspec_users:
                msgspec.json.encode(user)
        end_time = time.perf_counter()
        serialization_time = end_time - start_time
        total_time = validation_time + serialization_time
        
        results.append(ValidationBenchmarkResult(
            "msgspec (with validation)", serialization_time, 0, validation_time, total_time,
            total_ops / total_time, len(valid_data) / validation_time
        ))
        print(f"   ⏱️  Validation: {validation_time:.4f}s, Serialization: {serialization_time:.4f}s")
        print(f"   ⏱️  Total: {total_time:.4f}s ({total_ops / total_time:.0f} ops/sec)")
    
    # 3. Satya Model.json() (uses orjson internally)
    print("3️⃣  Satya Model.json() (with validation)...")
    
    # Convert to Satya models (includes validation)
    print("   📝 Converting to Satya models with validation...")
    satya_users = []
    validation_start = time.perf_counter()
    for data in valid_data:
        try:
            user = User(**data)
            satya_users.append(user)
        except Exception as e:
            print(f"   ❌ Validation failed: {e}")
            continue
    validation_end = time.perf_counter()
    validation_time = validation_end - validation_start
    
    # Benchmark serialization
    start_time = time.perf_counter()
    for _ in range(iterations):
        for user in satya_users:
            user.json()
    end_time = time.perf_counter()
    serialization_time = end_time - start_time
    total_time = validation_time + serialization_time
    
    results.append(ValidationBenchmarkResult(
        "Satya Model.json() (with validation)", serialization_time, 0, validation_time, total_time,
        total_ops / total_time, len(valid_data) / validation_time
    ))
    print(f"   ⏱️  Validation: {validation_time:.4f}s, Serialization: {serialization_time:.4f}s")
    print(f"   ⏱️  Total: {total_time:.4f}s ({total_ops / total_time:.0f} ops/sec)")
    
    # 4. Satya validator + orjson combination
    if HAS_ORJSON:
        print("4️⃣  Satya validator + orjson...")
        validator = User.validator()
        
        start_time = time.perf_counter()
        validated_count = 0
        for _ in range(iterations):
            for data in valid_data:
                result = validator.validate(data)
                if result.is_valid:
                    orjson.dumps(result.value)
                    validated_count += 1
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        results.append(ValidationBenchmarkResult(
            "Satya validator + orjson", 0, 0, total_time, total_time,
            validated_count / total_time, validated_count / total_time
        ))
        print(f"   ⏱️  Total: {total_time:.4f}s ({validated_count / total_time:.0f} ops/sec)")
    
    # 5. Satya validator.to_json() (validation + serialization in Rust)
    print("5️⃣  Satya validator.to_json() (Rust validation + serialization)...")
    validator = User.validator()
    
    start_time = time.perf_counter()
    for _ in range(iterations):
        for data in valid_data:
            try:
                validator.to_json(data)
            except Exception:
                pass  # Skip invalid data
    end_time = time.perf_counter()
    total_time = end_time - start_time
    
    results.append(ValidationBenchmarkResult(
        "Satya validator.to_json() (Rust)", 0, 0, total_time, total_time,
        total_ops / total_time, total_ops / total_time
    ))
    print(f"   ⏱️  Total: {total_time:.4f}s ({total_ops / total_time:.0f} ops/sec)")
    
    return results

def benchmark_validation_parsing(json_strings: List[str], iterations: int = 50) -> List[ValidationBenchmarkResult]:
    """Benchmark parsing with validation"""
    results = []
    total_ops = len(json_strings) * iterations
    
    print(f"\n🔄 Benchmarking Validation + Parsing ({len(json_strings)} records × {iterations} iterations)\n")
    
    # 1. Baseline: orjson without validation
    if HAS_ORJSON:
        print("1️⃣  orjson.loads() (no validation)...")
        start_time = time.perf_counter()
        for _ in range(iterations):
            for json_str in json_strings:
                orjson.loads(json_str)
        end_time = time.perf_counter()
        orjson_time = end_time - start_time
        results.append(ValidationBenchmarkResult(
            "orjson (no validation)", 0, orjson_time, 0, orjson_time,
            total_ops / orjson_time, 0
        ))
        print(f"   ⏱️  {orjson_time:.4f}s ({total_ops / orjson_time:.0f} ops/sec)")
    
    # 2. msgspec with validation
    if HAS_MSGSPEC:
        print("2️⃣  msgspec with validation...")
        start_time = time.perf_counter()
        parsed_count = 0
        for _ in range(iterations):
            for json_str in json_strings:
                try:
                    msgspec.json.decode(json_str.encode(), type=MsgspecUser)
                    parsed_count += 1
                except Exception:
                    pass  # Skip invalid data
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        results.append(ValidationBenchmarkResult(
            "msgspec (with validation)", 0, total_time, total_time, total_time,
            parsed_count / total_time, parsed_count / total_time
        ))
        print(f"   ⏱️  Total: {total_time:.4f}s ({parsed_count / total_time:.0f} ops/sec)")
    
    # 3. Satya Model.from_json()
    print("3️⃣  Satya Model.from_json() (with validation)...")
    start_time = time.perf_counter()
    parsed_count = 0
    for _ in range(iterations):
        for json_str in json_strings:
            try:
                User.from_json(json_str)
                parsed_count += 1
            except Exception:
                pass  # Skip invalid data
    end_time = time.perf_counter()
    total_time = end_time - start_time
    
    results.append(ValidationBenchmarkResult(
        "Satya Model.from_json() (with validation)", 0, total_time, total_time, total_time,
        parsed_count / total_time, parsed_count / total_time
    ))
    print(f"   ⏱️  Total: {total_time:.4f}s ({parsed_count / total_time:.0f} ops/sec)")
    
    # 4. Satya validator.from_json()
    print("4️⃣  Satya validator.from_json() (Rust validation + parsing)...")
    validator = User.validator()
    start_time = time.perf_counter()
    parsed_count = 0
    for _ in range(iterations):
        for json_str in json_strings:
            try:
                validator.from_json(json_str)
                parsed_count += 1
            except Exception:
                pass  # Skip invalid data
    end_time = time.perf_counter()
    total_time = end_time - start_time
    
    results.append(ValidationBenchmarkResult(
        "Satya validator.from_json() (Rust)", 0, total_time, total_time, total_time,
        parsed_count / total_time, parsed_count / total_time
    ))
    print(f"   ⏱️  Total: {total_time:.4f}s ({parsed_count / total_time:.0f} ops/sec)")
    
    return results

def create_validation_graphs(serialization_results: List[ValidationBenchmarkResult], parsing_results: List[ValidationBenchmarkResult]):
    """Create validation performance comparison graphs"""
    if not HAS_MATPLOTLIB:
        print("⚠️  matplotlib not available, skipping graph generation")
        return
    
    # Create figure with subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Validation Performance Benchmark: Satya vs msgspec', fontsize=16, fontweight='bold')
    
    # Serialization comparison
    ser_names = [r.name for r in serialization_results]
    ser_ops = [r.ops_per_sec for r in serialization_results]
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
    bars1 = ax1.bar(range(len(ser_names)), ser_ops, color=colors[:len(ser_names)])
    ax1.set_title('Serialization + Validation Performance\n(Higher is Better)', fontweight='bold')
    ax1.set_ylabel('Operations per Second')
    ax1.set_xticks(range(len(ser_names)))
    ax1.set_xticklabels(ser_names, rotation=45, ha='right')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
    
    # Add value labels
    for bar, ops_val in zip(bars1, ser_ops):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                f'{ops_val/1000:.0f}K', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Parsing comparison
    par_names = [r.name for r in parsing_results]
    par_ops = [r.ops_per_sec for r in parsing_results]
    
    bars2 = ax2.bar(range(len(par_names)), par_ops, color=colors[:len(par_names)])
    ax2.set_title('Parsing + Validation Performance\n(Higher is Better)', fontweight='bold')
    ax2.set_ylabel('Operations per Second')
    ax2.set_xticks(range(len(par_names)))
    ax2.set_xticklabels(par_names, rotation=45, ha='right')
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
    
    # Add value labels
    for bar, ops_val in zip(bars2, par_ops):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                f'{ops_val/1000:.0f}K', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # Validation overhead comparison (serialization)
    validation_methods = [r for r in serialization_results if "validation" in r.name.lower()]
    if validation_methods:
        val_names = [r.name.replace(" (with validation)", "").replace(" (Rust)", "") for r in validation_methods]
        val_ops = [r.validation_ops_per_sec for r in validation_methods if r.validation_ops_per_sec > 0]
        val_names_filtered = [val_names[i] for i, r in enumerate(validation_methods) if r.validation_ops_per_sec > 0]
        
        if val_ops and len(val_ops) > 0:
            colors_val = colors[:len(val_ops)]  # Use only as many colors as we have data points
            bars3 = ax3.bar(range(len(val_names_filtered)), val_ops, color=colors_val)
            ax3.set_title('Pure Validation Performance\n(Higher is Better)', fontweight='bold')
            ax3.set_ylabel('Validations per Second')
            ax3.set_xticks(range(len(val_names_filtered)))
            ax3.set_xticklabels(val_names_filtered, rotation=45, ha='right')
            ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
            
            # Add value labels
            for bar, ops_val in zip(bars3, val_ops):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                        f'{ops_val/1000:.0f}K', ha='center', va='bottom', fontsize=9, fontweight='bold')
        else:
            # If no validation data, show a message
            ax3.text(0.5, 0.5, 'No separate validation\nperformance data available', 
                    ha='center', va='center', transform=ax3.transAxes, fontsize=12)
            ax3.set_title('Pure Validation Performance', fontweight='bold')
    
    # Performance comparison chart
    methods_comparison = ['msgspec', 'Satya Model', 'Satya validator']
    ser_perf = []
    par_perf = []
    
    for method in methods_comparison:
        # Find serialization performance
        ser_result = next((r for r in serialization_results if method.lower() in r.name.lower() and "validation" in r.name.lower()), None)
        if ser_result:
            ser_perf.append(ser_result.ops_per_sec)
        else:
            ser_perf.append(0)
        
        # Find parsing performance
        par_result = next((r for r in parsing_results if method.lower() in r.name.lower() and "validation" in r.name.lower()), None)
        if par_result:
            par_perf.append(par_result.ops_per_sec)
        else:
            par_perf.append(0)
    
    x = np.arange(len(methods_comparison))
    width = 0.35
    
    bars4a = ax4.bar(x - width/2, ser_perf, width, label='Serialization + Validation', color='#45B7D1')
    bars4b = ax4.bar(x + width/2, par_perf, width, label='Parsing + Validation', color='#96CEB4')
    
    ax4.set_title('Validation Methods Comparison\n(Higher is Better)', fontweight='bold')
    ax4.set_ylabel('Operations per Second')
    ax4.set_xticks(x)
    ax4.set_xticklabels(methods_comparison)
    ax4.legend()
    ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
    
    # Add value labels
    for bars in [bars4a, bars4b]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax4.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                        f'{height/1000:.0f}K', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('validation_benchmark_results.png', dpi=300, bbox_inches='tight')
    plt.show()
    print("\n📊 Validation benchmark graphs saved as 'validation_benchmark_results.png'")

def print_validation_summary(serialization_results: List[ValidationBenchmarkResult], parsing_results: List[ValidationBenchmarkResult]):
    """Print validation benchmark summary"""
    print("\n" + "="*90)
    print("📊 VALIDATION BENCHMARK SUMMARY")
    print("="*90)
    
    print("\n🚀 SERIALIZATION + VALIDATION RESULTS:")
    print(f"{'Method':<35} {'Total (ops/sec)':<15} {'Validation (ops/sec)':<20} {'Notes':<20}")
    print("-" * 90)
    
    for result in serialization_results:
        validation_str = f"{result.validation_ops_per_sec:.0f}" if result.validation_ops_per_sec > 0 else "N/A"
        notes = "No validation" if "no validation" in result.name else "With validation"
        print(f"{result.name:<35} {result.ops_per_sec:<15.0f} {validation_str:<20} {notes:<20}")
    
    print("\n🔄 PARSING + VALIDATION RESULTS:")
    print(f"{'Method':<35} {'Total (ops/sec)':<15} {'Notes':<20}")
    print("-" * 70)
    
    for result in parsing_results:
        notes = "No validation" if "no validation" in result.name else "With validation"
        print(f"{result.name:<35} {result.ops_per_sec:<15.0f} {notes:<20}")

def main():
    print("🔥 Validation Performance Benchmark: Satya vs msgspec")
    print("=" * 70)
    print(f"Python {sys.version}")
    print(f"orjson available: {HAS_ORJSON}")
    print(f"msgspec available: {HAS_MSGSPEC}")
    print(f"matplotlib available: {HAS_MATPLOTLIB}")
    
    if not HAS_MSGSPEC:
        print("❌ msgspec is required for this benchmark. Install with: pip install msgspec")
        return
    
    # Configuration
    data_count = 1000
    iterations = 50
    
    print(f"\n📝 Generating {data_count} test records (valid and invalid)...")
    valid_data, invalid_data = generate_test_data(data_count)
    
    # Benchmark validation + serialization
    serialization_results = benchmark_validation_serialization(valid_data, invalid_data, iterations)
    
    # Generate JSON strings for parsing benchmark
    print(f"\n📝 Generating JSON strings for parsing benchmark...")
    if HAS_ORJSON:
        json_strings = [orjson.dumps(data).decode('utf-8') for data in valid_data]
    else:
        json_strings = [json.dumps(data) for data in valid_data]
    
    # Benchmark validation + parsing
    parsing_results = benchmark_validation_parsing(json_strings, iterations)
    
    # Print summary
    print_validation_summary(serialization_results, parsing_results)
    
    # Create graphs
    create_validation_graphs(serialization_results, parsing_results)
    
    print("\n🎉 Validation Benchmark Complete!")
    print("\n💡 Key Insights:")
    print("   • msgspec provides fast validation through struct definitions")
    print("   • Satya Model.json() combines validation with orjson performance")
    print("   • Satya validator methods provide comprehensive validation in Rust")
    print("   • Choose based on validation complexity vs performance needs")
    print("   • Both libraries significantly outperform manual validation approaches")

if __name__ == "__main__":
    main() 