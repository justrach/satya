#!/usr/bin/env python3
import gc
import time
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import os

# Ensure the results directory exists
os.makedirs('benchmarks/results', exist_ok=True)

# Benchmark configuration
N_ITEMS = 5_000_000  # Total number of items to validate
BATCH_SIZE = 50_000  # Process in batches of this size

def generate_test_data(num_items):
    """Generate test data for benchmarking"""
    import random
    
    # Pre-generate names, domains for faster generation
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Edward", "Fiona"]
    last_names = ["Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor"]
    domains = ["example.com", "test.com", "benchmark.org", "sample.net", "demo.io"]
    
    data = []
    for _ in range(num_items):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 80)
        email = f"{name.lower().replace(' ', '.')}@{random.choice(domains)}"
        data.append({"name": name, "age": age, "email": email})
    
    return data

def measure_memory_usage(func):
    """Simple memory measurement decorator"""
    import tracemalloc
    
    tracemalloc.start()
    func()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return peak / (1024 * 1024)  # Convert to MB

def run_pydantic_benchmark():
    """Run validation benchmark using Pydantic"""
    from pydantic import BaseModel
    
    print("\nPydantic Benchmark:")
    
    # Define model
    class Person(BaseModel):
        name: str
        age: int
        email: str
    
    # Generate test data
    test_data = generate_test_data(N_ITEMS)
    
    # Measure single item validation time
    start_time = time.time()
    Person(**test_data[0])
    single_time = time.time() - start_time
    print(f"Single item validation: {single_time*1000:.2f}ms")
    
    # Memory usage measurement
    def validation_task():
        for i in range(0, BATCH_SIZE):
            Person(**test_data[i])
    
    memory_used = measure_memory_usage(validation_task)
    
    # Time measurement for full dataset
    start_time = time.time()
    validated = 0
    for i in range(0, N_ITEMS, BATCH_SIZE):
        batch = test_data[i:i+BATCH_SIZE]
        for item in batch:
            Person(**item)
        validated += len(batch)
        if validated % 1_000_000 == 0:
            print(f"Processed {validated:,} items...")
    
    total_time = time.time() - start_time
    items_per_second = N_ITEMS / total_time
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Items per second: {int(items_per_second):,}")
    print(f"Memory usage for {BATCH_SIZE} items: {memory_used:.1f}MB")
    
    return total_time, memory_used, items_per_second

def run_satya_benchmark():
    """Run validation benchmark using Satya"""
    import satya
    
    print("\nSatya Benchmark:")
    
    # Define model
    class Person(satya.Model):
        name: str
        age: int
        email: str
    
    # Generate test data
    test_data = generate_test_data(N_ITEMS)
    
    # Create validator once
    validator = Person.validator()
    
    # Measure single item validation time
    start_time = time.time()
    validator._validator.validate_batch([test_data[0]])
    single_time = time.time() - start_time
    print(f"Single item validation: {single_time*1000:.2f}ms")
    
    # Memory usage measurement
    def validation_task():
        batch = test_data[:BATCH_SIZE]
        validator._validator.validate_batch(batch)
    
    memory_used = measure_memory_usage(validation_task)
    
    # Time measurement for full dataset
    start_time = time.time()
    validated = 0
    for i in range(0, N_ITEMS, BATCH_SIZE):
        batch = test_data[i:i+BATCH_SIZE]
        validator._validator.validate_batch(batch)
        validated += len(batch)
        if validated % 1_000_000 == 0:
            print(f"Processed {validated:,} items...")
    
    total_time = time.time() - start_time
    items_per_second = N_ITEMS / total_time
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Items per second: {int(items_per_second):,}")
    print(f"Memory usage for {BATCH_SIZE} items: {memory_used:.1f}MB")
    
    return total_time, memory_used, items_per_second

def run_msgspec_benchmark():
    """Run validation benchmark using msgspec"""
    import msgspec
    
    print("\nmsgspec Benchmark:")
    
    # Define model
    class Person(msgspec.Struct):
        name: str
        age: int
        email: str
    
    # Generate test data
    test_data = generate_test_data(N_ITEMS)
    
    # Measure single item validation time
    start_time = time.time()
    msgspec.convert(test_data[0], Person)
    single_time = time.time() - start_time
    print(f"Single item validation: {single_time*1000:.2f}ms")
    
    # Memory usage measurement
    def validation_task():
        for i in range(0, BATCH_SIZE):
            msgspec.convert(test_data[i], Person)
    
    memory_used = measure_memory_usage(validation_task)
    
    # Time measurement for full dataset
    start_time = time.time()
    validated = 0
    for i in range(0, N_ITEMS, BATCH_SIZE):
        batch = test_data[i:i+BATCH_SIZE]
        for item in batch:
            msgspec.convert(item, Person)
        validated += len(batch)
        if validated % 1_000_000 == 0:
            print(f"Processed {validated:,} items...")
    
    total_time = time.time() - start_time
    items_per_second = N_ITEMS / total_time
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Items per second: {int(items_per_second):,}")
    print(f"Memory usage for {BATCH_SIZE} items: {memory_used:.1f}MB")
    
    return total_time, memory_used, items_per_second

def create_visualization(results):
    """
    Create bar charts showing validation speed comparison.
    """
    # Set style
    plt.style.use('ggplot')
    mpl.rcParams['font.family'] = 'sans-serif'
    mpl.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif']
    
    # Extract data
    libraries = ['Pydantic', 'Satya', 'msgspec']
    validation_speeds = [
        results['pydantic_ips'],
        results['satya_ips'],
        results['msgspec_ips']
    ]
    
    # Create a color palette
    colors = ['#4D4DFF', '#FF5757', '#4CAF50']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create bars
    bars = ax.bar(libraries, validation_speeds, color=colors, width=0.6, edgecolor='white', linewidth=1)
    
    # Add values on bars
    for bar, speed in zip(bars, validation_speeds):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 5000,
                f'{int(speed):,} items/s',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Customize plot
    ax.set_title('Validation Speed Comparison', fontsize=18, fontweight='bold', pad=20)
    ax.set_ylabel('Items per second', fontsize=14, fontweight='bold')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add comparison text
    satya_vs_pydantic = results['satya_ips'] / results['pydantic_ips']
    satya_vs_msgspec = results['satya_ips'] / results['msgspec_ips']
    
    textstr = '\n'.join((
        f'Satya vs Pydantic: {satya_vs_pydantic:.1f}x faster',
        f'Satya vs msgspec: {satya_vs_msgspec:.1f}x faster'
    ))
    
    props = dict(boxstyle='round', facecolor='white', alpha=0.5)
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=12,
            verticalalignment='top', bbox=props)
    
    # Adjust layout and save
    plt.tight_layout()
    output_path = 'benchmarks/results/validation_speed_only.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nValidation speed chart saved to '{output_path}'")
    
    # Create a second chart showing relative performance with Pydantic as baseline
    plt.figure(figsize=(10, 6))
    
    # Calculate relative speeds (Pydantic = 1.0)
    rel_speeds = [
        1.0,  # Pydantic baseline
        results['satya_ips'] / results['pydantic_ips'],
        results['msgspec_ips'] / results['pydantic_ips']
    ]
    
    # Create bars for relative performance
    bars = plt.bar(libraries, rel_speeds, color=colors, width=0.6, edgecolor='white', linewidth=1)
    
    # Add values on bars
    for bar, speed in zip(bars, rel_speeds):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{speed:.1f}x',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Customize plot
    plt.title('Relative Validation Performance\n(Pydantic = 1.0x baseline)', fontsize=16, fontweight='bold')
    plt.ylabel('Performance Multiple', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.gca().set_axisbelow(True)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Adjust layout and save
    plt.tight_layout()
    rel_output_path = 'benchmarks/results/validation_relative_performance.png'
    plt.savefig(rel_output_path, dpi=300, bbox_inches='tight')
    print(f"Relative performance chart saved to '{rel_output_path}'")

if __name__ == "__main__":
    print(f"Running validation benchmark with {N_ITEMS:,} items...")
    print(f"Batch size: {BATCH_SIZE:,}")
    
    # Force garbage collection before each benchmark
    gc.collect()
    
    # Run benchmarks
    pydantic_time, pydantic_mem, pydantic_ips = run_pydantic_benchmark()
    
    gc.collect()
    satya_time, satya_mem, satya_ips = run_satya_benchmark()
    
    gc.collect()
    msgspec_time, msgspec_mem, msgspec_ips = run_msgspec_benchmark()
    
    # Print comparison table
    print("\nValidation Comparison:")
    print("                         Pydantic        Satya      msgspec")
    print("----------------------------------------------------------")
    print(f"Total time (s)              {pydantic_time:.2f}        {satya_time:.2f}        {msgspec_time:.2f}")
    print(f"Memory usage (MB)           {pydantic_mem:.1f}        {satya_mem:.1f}        {msgspec_mem:.1f}")
    print(f"Items/second               {int(pydantic_ips):,}      {int(satya_ips):,}      {int(msgspec_ips):,}")
    
    # Print relative performance
    print("\nRelative Validation Performance (higher is better):")
    print("                      vs Pydantic   vs msgspec")
    print("----------------------------------------------")
    print(f"Satya speed                   {satya_ips/pydantic_ips:.1f}x          {satya_ips/msgspec_ips:.1f}x")
    print(f"Satya memory                  {pydantic_mem/satya_mem:.1f}x          {msgspec_mem/satya_mem:.1f}x")
    
    # Save results
    results = {
        'pydantic_time': pydantic_time,
        'pydantic_mem': pydantic_mem,
        'pydantic_ips': pydantic_ips,
        'satya_time': satya_time,
        'satya_mem': satya_mem,
        'satya_ips': satya_ips,
        'msgspec_time': msgspec_time,
        'msgspec_mem': msgspec_mem,
        'msgspec_ips': msgspec_ips
    }
    
    # Create visualizations
    create_visualization(results)
