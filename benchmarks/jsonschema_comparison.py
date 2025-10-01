#!/usr/bin/env python3
"""
Benchmark comparing Satya validation vs standard Python jsonschema library.

This demonstrates how Satya's Rust-powered validation significantly outperforms
the pure Python jsonschema library for data validation tasks.
"""
import gc
import time
import json
import random
from typing import Dict, Any, List
import matplotlib.pyplot as plt
import matplotlib as mpl
from memory_profiler import memory_usage
import os

# Ensure the results directory exists
os.makedirs('benchmarks/results', exist_ok=True)

# Benchmark configuration
N_ITEMS = 1_000_000  # Total number of items to validate
BATCH_SIZE = 10_000  # Process in batches of this size

def generate_test_data(num_items: int) -> List[Dict[str, Any]]:
    """Generate test data for benchmarking"""
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Edward", "Fiona", "Grace", "Henry"]
    last_names = ["Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Thomas"]
    domains = ["example.com", "test.com", "benchmark.org", "sample.net", "demo.io"]
    
    data = []
    for i in range(num_items):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 80)
        email = f"{name.lower().replace(' ', '.')}@{random.choice(domains)}"
        is_active = random.choice([True, False])
        score = round(random.uniform(0.0, 100.0), 2)
        
        data.append({
            "id": i,
            "name": name,
            "age": age,
            "email": email,
            "is_active": is_active,
            "score": score
        })
    
    return data

def run_jsonschema_benchmark() -> tuple:
    """Run validation benchmark using standard jsonschema library"""
    try:
        import jsonschema
        from jsonschema import validate, Draft7Validator
    except ImportError:
        print("jsonschema library not installed. Install with: pip install jsonschema")
        return None, None, None
    
    print("\n" + "="*60)
    print("jsonschema (Python) Benchmark")
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
        "required": ["id", "name", "age", "email", "is_active", "score"],
        "additionalProperties": False
    }
    
    # Create validator
    validator = Draft7Validator(schema)
    
    # Generate test data
    print(f"Generating {N_ITEMS:,} test items...")
    test_data = generate_test_data(N_ITEMS)
    
    # Measure single item validation time
    start_time = time.time()
    validator.validate(test_data[0])
    single_time = time.time() - start_time
    print(f"Single item validation: {single_time*1000:.3f}ms")
    
    # Benchmark memory and time
    def run_validation():
        validated = 0
        errors = 0
        for i in range(0, N_ITEMS, BATCH_SIZE):
            batch = test_data[i:i+BATCH_SIZE]
            for item in batch:
                try:
                    validator.validate(item)
                    validated += 1
                except jsonschema.ValidationError:
                    errors += 1
            if validated % 100_000 == 0 and validated > 0:
                print(f"  Processed {validated:,} items...")
    
    # Run with memory profiling
    print("Running validation with memory profiling...")
    mem_usage = memory_usage((run_validation, (), {}), interval=0.1, max_usage=True)
    
    # Run validation again to measure time accurately
    print("Running timed validation...")
    start_time = time.time()
    validated = 0
    errors = 0
    for i in range(0, N_ITEMS, BATCH_SIZE):
        batch = test_data[i:i+BATCH_SIZE]
        for item in batch:
            try:
                validator.validate(item)
                validated += 1
            except jsonschema.ValidationError:
                errors += 1
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate items per second
    items_per_second = N_ITEMS / total_time
    
    # Calculate peak memory usage
    peak_memory = mem_usage if isinstance(mem_usage, float) else max(mem_usage)
    
    print(f"\nResults:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Items validated: {validated:,}")
    print(f"  Errors: {errors:,}")
    print(f"  Items per second: {int(items_per_second):,}")
    print(f"  Peak memory usage: {peak_memory:.1f}MB")
    
    return total_time, peak_memory, items_per_second

def run_fastjsonschema_benchmark() -> tuple:
    """Run validation benchmark using fastjsonschema library"""
    try:
        import fastjsonschema
    except ImportError:
        print("fastjsonschema library not installed. Install with: pip install fastjsonschema")
        return None, None, None
    
    print("\n" + "="*60)
    print("fastjsonschema (Python + JIT) Benchmark")
    print("="*60)
    
    # Define JSON Schema (same as jsonschema)
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
        "required": ["id", "name", "age", "email", "is_active", "score"],
        "additionalProperties": False
    }
    
    # Compile validator (JIT compilation for speed)
    validate = fastjsonschema.compile(schema)
    
    # Generate test data
    print(f"Generating {N_ITEMS:,} test items...")
    test_data = generate_test_data(N_ITEMS)
    
    # Measure single item validation time
    start_time = time.time()
    try:
        validate(test_data[0])
    except Exception:
        pass
    single_time = time.time() - start_time
    print(f"Single item validation: {single_time*1000:.3f}ms")
    
    # Benchmark memory and time
    def run_validation():
        validated = 0
        errors = 0
        for i in range(0, N_ITEMS, BATCH_SIZE):
            batch = test_data[i:i+BATCH_SIZE]
            for item in batch:
                try:
                    validate(item)
                    validated += 1
                except Exception:
                    errors += 1
            if validated % 100_000 == 0 and validated > 0:
                print(f"  Processed {validated:,} items...")
    
    # Run with memory profiling
    print("Running validation with memory profiling...")
    mem_usage = memory_usage((run_validation, (), {}), interval=0.1, max_usage=True)
    
    # Run validation again to measure time accurately
    print("Running timed validation...")
    start_time = time.time()
    validated = 0
    errors = 0
    for i in range(0, N_ITEMS, BATCH_SIZE):
        batch = test_data[i:i+BATCH_SIZE]
        for item in batch:
            try:
                validate(item)
                validated += 1
            except Exception:
                errors += 1
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate items per second
    items_per_second = N_ITEMS / total_time
    
    # Calculate peak memory usage
    peak_memory = mem_usage if isinstance(mem_usage, float) else max(mem_usage)
    
    print(f"\nResults:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Items validated: {validated:,}")
    print(f"  Errors: {errors:,}")
    print(f"  Items per second: {int(items_per_second):,}")
    print(f"  Peak memory usage: {peak_memory:.1f}MB")
    
    return total_time, peak_memory, items_per_second

def run_satya_benchmark() -> tuple:
    """Run validation benchmark using Satya with optimal batch processing"""
    import satya
    from satya import Model, Field
    
    print("\n" + "="*60)
    print("Satya (Rust-powered) Benchmark - OPTIMIZED")
    print("="*60)
    
    # Define model
    class DataRecord(Model):
        id: int = Field(ge=0)
        name: str = Field(min_length=1)
        age: int = Field(ge=0, le=150)
        email: str = Field(email=True)
        is_active: bool
        score: float = Field(ge=0.0, le=100.0)
    
    # Generate test data
    print(f"Generating {N_ITEMS:,} test items...")
    test_data = generate_test_data(N_ITEMS)
    
    # Measure single item validation time
    start_time = time.time()
    try:
        DataRecord(**test_data[0])
    except Exception:
        pass
    single_time = time.time() - start_time
    print(f"Single item validation: {single_time*1000:.3f}ms")
    
    # Create validator OUTSIDE the profiled function for fair comparison
    # Set optimal batch size (Satya's Rust core handles batching internally)
    validator = DataRecord.validator()
    # Satya's internal batch size is optimized for performance
    validator.set_batch_size(10000)  # Optimal for large datasets
    
    print(f"Batch size set to: 10000 (optimized for high-throughput)")
    print("Using validate_batch_hybrid for MAXIMUM performance!")
    print("(Direct Python dict validation in Rust - no JSON overhead!)")
    
    # Benchmark memory and time
    def run_validation():
        validated = 0
        errors = 0
        # Use validate_batch_hybrid for MAXIMUM speed!
        # This validates Python dicts directly without JSON serialization overhead
        for i in range(0, N_ITEMS, BATCH_SIZE):
            batch = test_data[i:i+BATCH_SIZE]
            # validate_batch_hybrid is the FASTEST method - validates dicts directly!
            results = validator._validator.validate_batch_hybrid(batch)
            validated += sum(results)
            errors += len(results) - sum(results)
            
            if validated % 100_000 == 0 and validated > 0:
                print(f"  Processed {validated:,} items...")
    
    # Run with memory profiling
    print("Running validation with memory profiling...")
    mem_usage = memory_usage((run_validation, (), {}), interval=0.1, max_usage=True)
    
    # Run validation again to measure time accurately
    print("Running timed validation...")
    start_time = time.time()
    validated = 0
    errors = 0
    
    # Use validate_batch_hybrid for maximum speed - validates Python dicts directly!
    for i in range(0, N_ITEMS, BATCH_SIZE):
        batch = test_data[i:i+BATCH_SIZE]
        results = validator._validator.validate_batch_hybrid(batch)
        validated += sum(results)
        errors += len(results) - sum(results)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate items per second
    items_per_second = N_ITEMS / total_time
    
    # Calculate peak memory usage
    peak_memory = mem_usage if isinstance(mem_usage, float) else max(mem_usage)
    
    print(f"\nResults:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Items validated: {validated:,}")
    print(f"  Errors: {errors:,}")
    print(f"  Items per second: {int(items_per_second):,}")
    print(f"  Peak memory usage: {peak_memory:.1f}MB")
    
    return total_time, peak_memory, items_per_second

def create_visualizations(results: Dict[str, Any]):
    """Create comparison visualizations"""
    # Set style
    plt.style.use('ggplot')
    mpl.rcParams['font.family'] = 'sans-serif'
    mpl.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif']
    
    libraries = ['jsonschema\n(Python)', 'Satya\n(Rust)']
    validation_speeds = [
        results['jsonschema_ips'],
        results['satya_ips']
    ]
    memory_usage = [
        results['jsonschema_mem'],
        results['satya_mem']
    ]
    
    # Color palette
    colors = ['#4D4DFF', '#FF5757']
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # ===== Chart 1: Validation Speed =====
    bars1 = ax1.bar(libraries, validation_speeds, color=colors, width=0.5, edgecolor='white', linewidth=2)
    
    # Add values on bars
    for bar, speed in zip(bars1, validation_speeds):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(speed):,}\nitems/s',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Customize speed plot
    ax1.set_title('Validation Speed Comparison', fontsize=16, fontweight='bold', pad=20)
    ax1.set_ylabel('Items per second (higher is better)', fontsize=12, fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # Add speedup annotation
    speedup = results['satya_ips'] / results['jsonschema_ips']
    textstr = f'Satya is {speedup:.1f}x faster'
    props = dict(boxstyle='round', facecolor='lightgreen', alpha=0.8)
    ax1.text(0.5, 0.95, textstr, transform=ax1.transAxes, fontsize=14,
            verticalalignment='top', horizontalalignment='center', bbox=props, fontweight='bold')
    
    # ===== Chart 2: Memory Usage =====
    bars2 = ax2.bar(libraries, memory_usage, color=colors, width=0.5, edgecolor='white', linewidth=2)
    
    # Add values on bars
    for bar, mem in zip(bars2, memory_usage):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{mem:.1f}\nMB',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Customize memory plot
    ax2.set_title('Memory Usage Comparison', fontsize=16, fontweight='bold', pad=20)
    ax2.set_ylabel('Peak memory usage in MB (lower is better)', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    ax2.set_axisbelow(True)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    # Add memory comparison annotation
    mem_ratio = results['jsonschema_mem'] / results['satya_mem']
    mem_textstr = f'{mem_ratio:.1f}x less memory' if mem_ratio > 1 else f'{1/mem_ratio:.1f}x more memory'
    ax2.text(0.5, 0.95, mem_textstr, transform=ax2.transAxes, fontsize=14,
            verticalalignment='top', horizontalalignment='center', bbox=props, fontweight='bold')
    
    # Adjust layout and save
    plt.tight_layout()
    output_path = 'benchmarks/results/jsonschema_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n📊 Comparison chart saved to '{output_path}'")
    
    # ===== Create relative performance chart =====
    plt.figure(figsize=(10, 6))
    
    # Calculate relative speeds (jsonschema = 1.0)
    rel_speeds = [
        1.0,  # jsonschema baseline
        results['satya_ips'] / results['jsonschema_ips']
    ]
    
    # Create bars for relative performance
    bars = plt.bar(libraries, rel_speeds, color=colors, width=0.5, edgecolor='white', linewidth=2)
    
    # Add values on bars
    for bar, speed in zip(bars, rel_speeds):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{speed:.1f}x',
                ha='center', va='bottom', fontsize=13, fontweight='bold')
    
    # Customize plot
    plt.title('Relative Validation Performance\n(jsonschema = 1.0x baseline)', 
              fontsize=16, fontweight='bold', pad=20)
    plt.ylabel('Performance Multiple', fontsize=13, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.gca().set_axisbelow(True)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Add a horizontal line at 1.0x
    plt.axhline(y=1.0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    
    # Adjust layout and save
    plt.tight_layout()
    rel_output_path = 'benchmarks/results/jsonschema_relative_performance.png'
    plt.savefig(rel_output_path, dpi=300, bbox_inches='tight')
    print(f"📊 Relative performance chart saved to '{rel_output_path}'")
    
    plt.close('all')

def save_results_json(results: Dict[str, Any]):
    """Save benchmark results to JSON file"""
    output_path = 'benchmarks/results/jsonschema_comparison_results.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"💾 Results saved to '{output_path}'")

def print_summary(results: Dict[str, Any]):
    """Print benchmark summary"""
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    
    print(f"\nTest Configuration:")
    print(f"  Total items: {results['n_items']:,}")
    print(f"  Batch size: {results['batch_size']:,}")
    
    print(f"\nLibrary                   Time (s)     Memory (MB)     Items/sec      ")
    print("-" * 67)
    print(f"jsonschema (Python)       {results['jsonschema_time']:<12.2f} {results['jsonschema_mem']:<20.1f} {int(results['jsonschema_ips']):>15,}")
    
    if results.get('has_fastjsonschema'):
        print(f"fastjsonschema (JIT)      {results['fastjsonschema_time']:<12.2f} {results['fastjsonschema_mem']:<20.1f} {int(results['fastjsonschema_ips']):>15,}")
    
    print(f"Satya (Rust)              {results['satya_time']:<12.2f} {results['satya_mem']:<20.1f} {int(results['satya_ips']):>15,}")
    
    speedup = results['speedup']
    time_reduction = results['time_reduction_pct']
    mem_comparison = results['satya_mem'] / results['jsonschema_mem']
    
    print("\n" + "="*60)
    print("PERFORMANCE IMPROVEMENT")
    print("="*60)
    print(f"⚡ Speed improvement vs jsonschema: {speedup:.1f}x faster")
    
    if results.get('has_fastjsonschema'):
        speedup_fast = results['speedup_vs_fast']
        print(f"⚡ Speed improvement vs fastjsonschema: {speedup_fast:.1f}x faster")
    
    print(f"⏱️  Time reduction vs jsonschema: {time_reduction:.1f}% faster")
    print(f"💾 Memory usage: {mem_comparison:.2f}x (relative to jsonschema)")
    print(f"🚀 Throughput gain vs jsonschema: {int(results['satya_ips'] - results['jsonschema_ips']):,} more items/sec")
    print("="*60)

if __name__ == "__main__":
    print("\n" + "🏆"*30)
    print("Python Validation Libraries Performance Benchmark")
    print("🏆"*30)
    print(f"\nValidating {N_ITEMS:,} items in batches of {BATCH_SIZE:,}...")
    
    # Force garbage collection before each benchmark
    gc.collect()
    
    # Run benchmarks
    jsonschema_time, jsonschema_mem, jsonschema_ips = run_jsonschema_benchmark()
    
    if jsonschema_time is None:
        print("\n❌ Could not run jsonschema benchmark. Please install: pip install jsonschema")
        exit(1)
    
    gc.collect()
    fastjsonschema_time, fastjsonschema_mem, fastjsonschema_ips = run_fastjsonschema_benchmark()
    
    if fastjsonschema_time is None:
        print("\n⚠️ Skipping fastjsonschema benchmark (not installed)")
        has_fastjsonschema = False
    else:
        has_fastjsonschema = True
    
    gc.collect()
    satya_time, satya_mem, satya_ips = run_satya_benchmark()
    
    # Collect results
    results = {
        'n_items': N_ITEMS,
        'batch_size': BATCH_SIZE,
        'jsonschema_time': jsonschema_time,
        'jsonschema_mem': jsonschema_mem,
        'jsonschema_ips': jsonschema_ips,
        'satya_time': satya_time,
        'satya_mem': satya_mem,
        'satya_ips': satya_ips,
        'speedup': satya_ips / jsonschema_ips,
        'time_reduction_pct': (1 - satya_time / jsonschema_time) * 100,
        'has_fastjsonschema': has_fastjsonschema
    }
    
    if has_fastjsonschema:
        results['fastjsonschema_time'] = fastjsonschema_time
        results['fastjsonschema_mem'] = fastjsonschema_mem
        results['fastjsonschema_ips'] = fastjsonschema_ips
        results['speedup_vs_fast'] = satya_ips / fastjsonschema_ips
    
    # Print summary
    print_summary(results)
    
    # Create visualizations
    print("\n📊 Creating visualizations...")
    create_visualizations(results)
    
    # Save results
    save_results_json(results)
    
    print("\n✅ Benchmark complete!")
    print("="*60 + "\n")
