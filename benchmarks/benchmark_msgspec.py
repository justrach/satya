from typing import List, Dict, Optional
import time
import json
from pydantic import BaseModel, ConfigDict, TypeAdapter
from satya import Model, Field
import msgspec
import random
import gc
import psutil
import os
from itertools import islice
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
import matplotlib as mpl

# Number of items to test
N_ITEMS = 5_000_000
BATCH_SIZE = 50000  # Much larger batch size for maximum throughput

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

# Define models for all three libraries with optimizations
# Pydantic models
class PydanticLocation(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', validate_assignment=False)
    latitude: float
    longitude: float
    name: Optional[str] = None

class PydanticAddress(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', validate_assignment=False)
    street: str
    city: str
    country: str
    location: PydanticLocation

class PydanticPerson(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', validate_assignment=False)
    name: str
    age: int
    address: PydanticAddress
    contacts: List[str]
    metadata: Dict[str, str]
    favorite_locations: List[PydanticLocation]

# Satya models
class Location(Model):
    latitude: float
    longitude: float
    name: Optional[str] = Field(required=False)

class Address(Model):
    street: str
    city: str
    country: str
    location: Location

class Person(Model):
    name: str
    age: int
    address: Address
    contacts: List[str]
    metadata: Dict[str, str]
    favorite_locations: List[Location]

# msgspec models
class MsgspecLocation(msgspec.Struct):
    latitude: float
    longitude: float
    name: Optional[str] = None

class MsgspecAddress(msgspec.Struct):
    street: str
    city: str
    country: str
    location: MsgspecLocation

class MsgspecPerson(msgspec.Struct):
    name: str
    age: int
    address: MsgspecAddress
    contacts: List[str]
    metadata: Dict[str, str]
    favorite_locations: List[MsgspecLocation]

def generate_test_batch(size: int, start_idx: int = 0):
    """Generate a batch of test items"""
    return [
        {
            "name": f"Person_{i}",
            "age": random.randint(18, 80),
            "address": {
                "street": f"{i} Main St",
                "city": random.choice(["New York", "London", "Tokyo", "Paris"]),
                "country": random.choice(["USA", "UK", "Japan", "France"]),
                "location": {
                    "latitude": random.uniform(-90, 90),
                    "longitude": random.uniform(-180, 180),
                    "name": f"Location_{i}" if random.random() > 0.5 else None
                }
            },
            "contacts": [
                f"email_{i}@example.com",
                f"+1-555-{i:04d}"
            ],
            "metadata": {
                "id": str(i),
                "status": random.choice(["active", "inactive"]),
                "score": str(random.randint(1, 100))
            },
            "favorite_locations": [
                {
                    "latitude": random.uniform(-90, 90),
                    "longitude": random.uniform(-180, 180),
                    "name": f"Favorite_{j}" if random.random() > 0.5 else None
                }
                for j in range(random.randint(0, 3))
            ]
        }
        for i in range(start_idx, start_idx + size)
    ]

def benchmark_pydantic():
    print("\nPydantic Benchmark:")
    start_mem = get_memory_usage()
    
    # Create type adapter for maximum performance
    person_adapter = TypeAdapter(List[PydanticPerson])  # Note the List wrapper
    
    # Single item validation
    test_item = generate_test_batch(1)[0]
    start_time = time.time()
    for _ in range(1000):
        person_adapter.validate_python([test_item])  # Wrap in list
    single_time = (time.time() - start_time) / 1000
    print(f"Single item validation: {single_time*1000:.2f}ms")
    
    # Batch validation
    start_time = time.time()
    count = 0
    peak_mem = start_mem
    
    while count < N_ITEMS:
        batch_size = min(BATCH_SIZE, N_ITEMS - count)
        batch = generate_test_batch(batch_size, count)
        
        # Validate batch as a list
        person_adapter.validate_python(batch)
        
        count += batch_size
        if count % 1000000 == 0:
            current_mem = get_memory_usage()
            peak_mem = max(peak_mem, current_mem)
            print(f"Processed {count:,} items...")
            gc.collect()  # Help manage memory
    
    total_time = time.time() - start_time
    memory_used = peak_mem - start_mem
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Items per second: {N_ITEMS/total_time:,.0f}")
    print(f"Peak memory usage: {memory_used:.1f}MB")
    
    gc.collect()
    return total_time, memory_used

def benchmark_satya():
    print("\nSatya Benchmark:")
    start_mem = get_memory_usage()
    
    validator = Person.validator()
    validator._validator.set_batch_size(BATCH_SIZE)
    
    # Single item validation
    test_item = generate_test_batch(1)[0]
    start_time = time.time()
    for _ in range(1000):
        validator._validator.validate_batch([test_item])
    single_time = (time.time() - start_time) / 1000
    print(f"Single item validation: {single_time*1000:.2f}ms")
    
    # Batch validation
    start_time = time.time()
    count = 0
    peak_mem = start_mem
    
    while count < N_ITEMS:
        batch_size = min(BATCH_SIZE, N_ITEMS - count)
        batch = generate_test_batch(batch_size, count)
        
        # Direct batch validation through Rust
        validator._validator.validate_batch(batch)
        
        count += batch_size
        if count % 1000000 == 0:
            current_mem = get_memory_usage()
            peak_mem = max(peak_mem, current_mem)
            print(f"Processed {count:,} items...")
            gc.collect()  # Help manage memory
    
    total_time = time.time() - start_time
    memory_used = peak_mem - start_mem
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Items per second: {N_ITEMS/total_time:,.0f}")
    print(f"Peak memory usage: {memory_used:.1f}MB")
    
    gc.collect()
    return total_time, memory_used

def benchmark_msgspec():
    print("\nMsgspec Benchmark:")
    start_mem = get_memory_usage()
    
    # Create decoder for maximum performance
    decoder = msgspec.json.Decoder(List[MsgspecPerson])
    
    # For direct Python dict validation, we can use msgspec.convert
    # This is more comparable to how Pydantic and Satya are being used
    
    # Single item validation
    test_item = generate_test_batch(1)[0]
    start_time = time.time()
    for _ in range(1000):
        # Use msgspec.convert for direct Python dict validation
        msgspec.convert(test_item, MsgspecPerson)
    single_time = (time.time() - start_time) / 1000
    print(f"Single item validation: {single_time*1000:.2f}ms")
    
    # Batch validation
    start_time = time.time()
    count = 0
    peak_mem = start_mem
    
    while count < N_ITEMS:
        batch_size = min(BATCH_SIZE, N_ITEMS - count)
        batch = generate_test_batch(batch_size, count)
        
        # Use msgspec.convert for direct Python dict validation
        # We need to convert each item individually as msgspec doesn't have a batch API
        for item in batch:
            msgspec.convert(item, MsgspecPerson)
        
        count += batch_size
        if count % 1000000 == 0:
            current_mem = get_memory_usage()
            peak_mem = max(peak_mem, current_mem)
            print(f"Processed {count:,} items...")
            gc.collect()  # Help manage memory
    
    total_time = time.time() - start_time
    memory_used = peak_mem - start_mem
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Items per second: {N_ITEMS/total_time:,.0f}")
    print(f"Peak memory usage: {memory_used:.1f}MB")
    
    gc.collect()
    return total_time, memory_used

def benchmark_serialization():
    """
    Benchmark JSON serialization and deserialization performance
    This is where msgspec typically excels
    """
    print("\nSerialization Benchmark (JSON):")
    
    # Generate a batch of test data
    test_batch = generate_test_batch(10000)
    
    # Pydantic serialization
    print("\nPydantic Serialization:")
    # Convert to Pydantic objects first
    person_adapter = TypeAdapter(List[PydanticPerson])
    pydantic_objects = person_adapter.validate_python(test_batch)
    
    # Measure serialization
    start_time = time.time()
    for _ in range(10):
        json_str = json.dumps([obj.model_dump() for obj in pydantic_objects])
    pydantic_ser_time = (time.time() - start_time) / 10
    
    # Measure deserialization
    start_time = time.time()
    for _ in range(10):
        person_adapter.validate_json(json_str.encode())
    pydantic_deser_time = (time.time() - start_time) / 10
    
    print(f"Serialization time: {pydantic_ser_time:.4f}s")
    print(f"Deserialization time: {pydantic_deser_time:.4f}s")
    
    # Satya serialization
    print("\nSatya Serialization:")
    # Convert to Satya objects first
    validator = Person.validator()
    satya_results = validator.validate_batch(test_batch)
    satya_objects = [result.value for result in satya_results]
    
    # Measure serialization
    start_time = time.time()
    for _ in range(10):
        json_str = json.dumps([obj.dict() for obj in satya_objects])
    satya_ser_time = (time.time() - start_time) / 10
    
    # Measure deserialization
    start_time = time.time()
    for _ in range(10):
        validator.validate_json_batch(json_str)
    satya_deser_time = (time.time() - start_time) / 10
    
    print(f"Serialization time: {satya_ser_time:.4f}s")
    print(f"Deserialization time: {satya_deser_time:.4f}s")
    
    # msgspec serialization
    print("\nmsgspec Serialization:")
    # Convert to msgspec objects first
    msgspec_objects = [msgspec.convert(item, MsgspecPerson) for item in test_batch]
    
    # Measure serialization
    encoder = msgspec.json.Encoder()
    start_time = time.time()
    for _ in range(10):
        json_bytes = encoder.encode(msgspec_objects)
    msgspec_ser_time = (time.time() - start_time) / 10
    
    # Measure deserialization
    decoder = msgspec.json.Decoder(List[MsgspecPerson])
    start_time = time.time()
    for _ in range(10):
        decoder.decode(json_bytes)
    msgspec_deser_time = (time.time() - start_time) / 10
    
    print(f"Serialization time: {msgspec_ser_time:.4f}s")
    print(f"Deserialization time: {msgspec_deser_time:.4f}s")
    
    # Print comparison
    print("\nSerialization Comparison:")
    print(f"{'':20} {'Pydantic':>12} {'Satya':>12} {'msgspec':>12}")
    print("-" * 58)
    print(f"{'Serialization (s)':20} {pydantic_ser_time:12.4f} {satya_ser_time:12.4f} {msgspec_ser_time:12.4f}")
    print(f"{'Deserialization (s)':20} {pydantic_deser_time:12.4f} {satya_deser_time:12.4f} {msgspec_deser_time:12.4f}")
    
    # Print relative performance
    print("\nRelative Serialization Performance (higher is better):")
    print(f"{'':20} {'vs Pydantic':>12} {'vs Satya':>12}")
    print("-" * 46)
    print(f"{'msgspec ser':20} {pydantic_ser_time/msgspec_ser_time:12.1f}x {satya_ser_time/msgspec_ser_time:12.1f}x")
    print(f"{'msgspec deser':20} {pydantic_deser_time/msgspec_deser_time:12.1f}x {satya_deser_time/msgspec_deser_time:12.1f}x")
    
    return {
        'pydantic': (pydantic_ser_time, pydantic_deser_time),
        'satya': (satya_ser_time, satya_deser_time),
        'msgspec': (msgspec_ser_time, msgspec_deser_time)
    }

def benchmark_strict_validation():
    """
    Benchmark validation with type coercion disabled (strict mode)
    This tests the performance of strict type checking
    """
    print("\nStrict Validation Benchmark:")
    
    # Generate a smaller batch for strict validation
    test_batch = generate_test_batch(10000)
    
    # Pydantic strict validation
    print("\nPydantic Strict Validation:")
    # Create a strict model
    class StrictPydanticPerson(BaseModel):
        model_config = ConfigDict(frozen=True, extra='forbid', validate_assignment=False, strict=True)
        name: str
        age: int
        address: PydanticAddress
        contacts: List[str]
        metadata: Dict[str, str]
        favorite_locations: List[PydanticLocation]
    
    strict_adapter = TypeAdapter(List[StrictPydanticPerson])
    
    start_time = time.time()
    try:
        strict_adapter.validate_python(test_batch)
    except Exception as e:
        print(f"Error during validation: {e}")
    pydantic_strict_time = time.time() - start_time
    
    print(f"Validation time: {pydantic_strict_time:.4f}s")
    
    # Satya strict validation
    print("\nSatya Strict Validation:")
    # Satya is strict by default
    validator = Person.validator()
    
    start_time = time.time()
    results = validator.validate_batch(test_batch)
    satya_strict_time = time.time() - start_time
    
    print(f"Validation time: {satya_strict_time:.4f}s")
    
    # msgspec strict validation
    print("\nmsgspec Strict Validation:")
    # msgspec is strict by default
    
    start_time = time.time()
    for item in test_batch:
        try:
            msgspec.convert(item, MsgspecPerson)
        except Exception:
            pass
    msgspec_strict_time = time.time() - start_time
    
    print(f"Validation time: {msgspec_strict_time:.4f}s")
    
    # Print comparison
    print("\nStrict Validation Comparison:")
    print(f"{'':20} {'Pydantic':>12} {'Satya':>12} {'msgspec':>12}")
    print("-" * 58)
    print(f"{'Time (s)':20} {pydantic_strict_time:12.4f} {satya_strict_time:12.4f} {msgspec_strict_time:12.4f}")
    
    return {
        'pydantic': pydantic_strict_time,
        'satya': satya_strict_time,
        'msgspec': msgspec_strict_time
    }

def create_performance_visualization(results):
    """
    Create a flashy horizontal bar chart visualization of the benchmark results
    
    Args:
        results: Dictionary containing benchmark results
    """
    # Set a modern, appealing style
    plt.style.use('ggplot')
    mpl.rcParams['font.family'] = 'sans-serif'
    mpl.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif']
    
    # Extract data from results
    categories = ['Validation\n(items/sec)', 'Memory\nEfficiency', 'Serialization\n(speed)', 'Deserialization\n(speed)', 'Strict Validation\n(speed)']
    
    # Calculate relative performance (higher is better)
    pydantic_rel = [
        results['validation']['pydantic_ips'] / results['validation']['satya_ips'],
        results['memory']['pydantic'] / results['memory']['satya'],
        results['serialization']['pydantic'][0] / results['serialization']['satya'][0],
        results['serialization']['pydantic'][1] / results['serialization']['satya'][1],
        results['strict']['pydantic'] / results['strict']['satya']
    ]
    
    msgspec_rel = [
        results['validation']['msgspec_ips'] / results['validation']['satya_ips'],
        results['memory']['msgspec'] / results['memory']['satya'],
        results['serialization']['msgspec'][0] / results['serialization']['satya'][0],
        results['serialization']['msgspec'][1] / results['serialization']['satya'][1],
        results['strict']['msgspec'] / results['strict']['satya']
    ]
    
    # Satya is always 1.0 (the baseline)
    satya_rel = [1.0, 1.0, 1.0, 1.0, 1.0]
    
    # Invert values where lower is better (all of them in this case)
    # For all metrics, we want higher bars to mean "better"
    pydantic_rel = [1/x for x in pydantic_rel]
    msgspec_rel = [1/x for x in msgspec_rel]
    
    # Create figure with a specific size
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Set up positions for bars
    y_pos = np.arange(len(categories))
    bar_width = 0.25
    
    # Create a vibrant color palette
    satya_color = '#FF5757'  # Bright red for Satya
    pydantic_color = '#4D4DFF'  # Blue for Pydantic
    msgspec_color = '#4CAF50'  # Green for msgspec
    
    # Create gradient effect for Satya bars
    satya_cmap = mcolors.LinearSegmentedColormap.from_list("", ["#FF8A8A", "#FF5757", "#B71C1C"])
    satya_colors = [satya_cmap(i/len(satya_rel)) for i in range(len(satya_rel))]
    
    # Plot horizontal bars with a slight shadow effect for depth
    ax.barh(y_pos - bar_width, satya_rel, bar_width, color=satya_colors, 
            label='Satya', edgecolor='white', linewidth=1, alpha=0.9, zorder=3)
    ax.barh(y_pos, pydantic_rel, bar_width, color=pydantic_color, 
            label='Pydantic', edgecolor='white', linewidth=1, alpha=0.7, zorder=2)
    ax.barh(y_pos + bar_width, msgspec_rel, bar_width, color=msgspec_color, 
            label='msgspec', edgecolor='white', linewidth=1, alpha=0.7, zorder=1)
    
    # Add value labels on the bars
    for i, v in enumerate(satya_rel):
        ax.text(v + 0.1, i - bar_width, f"{v:.1f}x", 
                va='center', fontweight='bold', color=satya_color)
    
    for i, v in enumerate(pydantic_rel):
        ax.text(v + 0.1, i, f"{v:.1f}x", 
                va='center', fontweight='bold', color=pydantic_color)
    
    for i, v in enumerate(msgspec_rel):
        ax.text(v + 0.1, i + bar_width, f"{v:.1f}x", 
                va='center', fontweight='bold', color=msgspec_color)
    
    # Customize the plot
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=12, fontweight='bold')
    ax.set_xlabel('Relative Performance (higher is better)', fontsize=14, fontweight='bold')
    ax.set_title('Satya Performance Benchmark', fontsize=20, fontweight='bold', pad=20)
    
    # Add a subtitle explaining the chart
    plt.figtext(0.5, 0.01, 
                'Bar height represents relative performance.\nSatya (1.0x) is the baseline. Higher bars mean better performance.', 
                ha='center', fontsize=12, fontstyle='italic')
    
    # Add a grid for better readability (only horizontal lines)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add legend with custom styling
    legend = ax.legend(loc='upper right', fontsize=12, frameon=True, framealpha=0.9)
    frame = legend.get_frame()
    frame.set_facecolor('white')
    frame.set_edgecolor('#CCCCCC')
    
    # Add a watermark-style text
    fig.text(0.95, 0.05, 'Powered by Satya', 
             fontsize=12, color='gray', alpha=0.5,
             ha='right', va='bottom', rotation=0)
    
    # Adjust layout and save
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    plt.savefig('benchmarks/results/satya_performance.png', dpi=300, bbox_inches='tight')
    plt.savefig('benchmarks/results/satya_performance.pdf', bbox_inches='tight')
    
    print("\nVisualization saved to 'benchmarks/results/satya_performance.png' and 'satya_performance.pdf'")
    
    # Show the plot if running in an interactive environment
    plt.show()

if __name__ == "__main__":
    print(f"Benchmarking with {N_ITEMS:,} items...")
    print(f"Batch size: {BATCH_SIZE:,}")
    
    # Run validation benchmarks
    pydantic_time, pydantic_mem = benchmark_pydantic()
    satya_time, satya_mem = benchmark_satya()
    msgspec_time, msgspec_mem = benchmark_msgspec()
    
    # Print validation comparison
    print("\nValidation Comparison:")
    print(f"{'':20} {'Pydantic':>12} {'Satya':>12} {'msgspec':>12}")
    print("-" * 58)
    print(f"{'Total time (s)':20} {pydantic_time:12.2f} {satya_time:12.2f} {msgspec_time:12.2f}")
    print(f"{'Memory usage (MB)':20} {pydantic_mem:12.1f} {satya_mem:12.1f} {msgspec_mem:12.1f}")
    print(f"{'Items/second':20} {N_ITEMS/pydantic_time:12,.0f} {N_ITEMS/satya_time:12,.0f} {N_ITEMS/msgspec_time:12,.0f}")
    
    # Print relative validation performance
    print("\nRelative Validation Performance (higher is better):")
    print(f"{'':20} {'vs Pydantic':>12} {'vs msgspec':>12}")
    print("-" * 46)
    print(f"{'Satya speed':20} {pydantic_time/satya_time:12.1f}x {msgspec_time/satya_time:12.1f}x")
    print(f"{'Satya memory':20} {pydantic_mem/satya_mem:12.1f}x {msgspec_mem/satya_mem:12.1f}x")
    
    # Run serialization benchmark
    print("\n" + "="*60)
    print("Running serialization benchmarks...")
    serialization_results = benchmark_serialization()
    
    # Run strict validation benchmark
    print("\n" + "="*60)
    print("Running strict validation benchmarks...")
    strict_results = benchmark_strict_validation()
    
    # Print overall summary
    print("\n" + "="*60)
    print("OVERALL BENCHMARK SUMMARY")
    print("="*60)
    
    print("\nValidation Performance (items/second):")
    print(f"{'':20} {'Pydantic':>12} {'Satya':>12} {'msgspec':>12}")
    print("-" * 58)
    print(f"{'Standard validation':20} {N_ITEMS/pydantic_time:12,.0f} {N_ITEMS/satya_time:12,.0f} {N_ITEMS/msgspec_time:12,.0f}")
    
    print("\nSerialization Performance (seconds for 10000 items, lower is better):")
    print(f"{'':20} {'Pydantic':>12} {'Satya':>12} {'msgspec':>12}")
    print("-" * 58)
    print(f"{'Serialization':20} {serialization_results['pydantic'][0]:12.4f} {serialization_results['satya'][0]:12.4f} {serialization_results['msgspec'][0]:12.4f}")
    print(f"{'Deserialization':20} {serialization_results['pydantic'][1]:12.4f} {serialization_results['satya'][1]:12.4f} {serialization_results['msgspec'][1]:12.4f}")
    
    print("\nStrict Validation Performance (seconds for 10000 items, lower is better):")
    print(f"{'':20} {'Pydantic':>12} {'Satya':>12} {'msgspec':>12}")
    print("-" * 58)
    print(f"{'Strict validation':20} {strict_results['pydantic']:12.4f} {strict_results['satya']:12.4f} {strict_results['msgspec']:12.4f}")
    
    print("\nRelative Performance (Satya vs others, higher is better):")
    print(f"{'':20} {'vs Pydantic':>12} {'vs msgspec':>12}")
    print("-" * 46)
    print(f"{'Validation speed':20} {pydantic_time/satya_time:12.1f}x {msgspec_time/satya_time:12.1f}x")
    print(f"{'Memory efficiency':20} {pydantic_mem/satya_mem:12.1f}x {msgspec_mem/satya_mem:12.1f}x")
    print(f"{'Serialization':20} {serialization_results['pydantic'][0]/serialization_results['satya'][0]:12.1f}x {serialization_results['msgspec'][0]/serialization_results['satya'][0]:12.1f}x")
    print(f"{'Deserialization':20} {serialization_results['pydantic'][1]/serialization_results['satya'][1]:12.1f}x {serialization_results['msgspec'][1]/serialization_results['satya'][1]:12.1f}x")
    print(f"{'Strict validation':20} {strict_results['pydantic']/strict_results['satya']:12.1f}x {strict_results['msgspec']/strict_results['satya']:12.1f}x")
    
    # Prepare results for visualization
    benchmark_results = {
        'validation': {
            'pydantic_ips': N_ITEMS/pydantic_time,
            'satya_ips': N_ITEMS/satya_time,
            'msgspec_ips': N_ITEMS/msgspec_time
        },
        'memory': {
            'pydantic': pydantic_mem,
            'satya': satya_mem,
            'msgspec': msgspec_mem
        },
        'serialization': {
            'pydantic': serialization_results['pydantic'],
            'satya': serialization_results['satya'],
            'msgspec': serialization_results['msgspec']
        },
        'strict': {
            'pydantic': strict_results['pydantic'],
            'satya': strict_results['satya'],
            'msgspec': strict_results['msgspec']
        }
    }
    
    # Create visualization
    create_performance_visualization(benchmark_results) 