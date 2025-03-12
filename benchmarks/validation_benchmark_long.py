#!/usr/bin/env python3
import gc
import time
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import os
import statistics

# Ensure the results directory exists
os.makedirs('benchmarks/results', exist_ok=True)

# Benchmark configuration
N_ITEMS = 5_000_000  # Total number of items to validate
BATCH_SIZE = 50_000  # Process in batches of this size
NUM_RUNS = 10  # Number of times to run each benchmark for averaging

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

def run_pydantic_benchmark(test_data):
    """Run validation benchmark using Pydantic"""
    from pydantic import BaseModel
    
    # Define model
    class Person(BaseModel):
        name: str
        age: int
        email: str
    
    # Measure single item validation time
    start_time = time.time()
    Person(**test_data[0])
    single_time = time.time() - start_time
    
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
            pass  # Don't print to avoid affecting timing
    
    total_time = time.time() - start_time
    items_per_second = N_ITEMS / total_time
    
    return total_time, memory_used, items_per_second, single_time

def run_satya_benchmark(test_data):
    """Run validation benchmark using Satya"""
    import satya
    
    # Define model
    class Person(satya.Model):
        name: str
        age: int
        email: str
    
    # Create validator once
    validator = Person.validator()
    
    # Measure single item validation time
    start_time = time.time()
    validator._validator.validate_batch([test_data[0]])
    single_time = time.time() - start_time
    
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
            pass  # Don't print to avoid affecting timing
    
    total_time = time.time() - start_time
    items_per_second = N_ITEMS / total_time
    
    return total_time, memory_used, items_per_second, single_time

def run_msgspec_benchmark(test_data):
    """Run validation benchmark using msgspec"""
    import msgspec
    
    # Define model
    class Person(msgspec.Struct):
        name: str
        age: int
        email: str
    
    # Measure single item validation time
    start_time = time.time()
    msgspec.convert(test_data[0], Person)
    single_time = time.time() - start_time
    
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
            pass  # Don't print to avoid affecting timing
    
    total_time = time.time() - start_time
    items_per_second = N_ITEMS / total_time
    
    return total_time, memory_used, items_per_second, single_time

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
        results['pydantic_ips_mean'],
        results['satya_ips_mean'],
        results['msgspec_ips_mean']
    ]
    
    std_devs = [
        results['pydantic_ips_std'],
        results['satya_ips_std'],
        results['msgspec_ips_std']
    ]
    
    # Create a color palette
    colors = ['#4D4DFF', '#FF5757', '#4CAF50']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create bars
    bars = ax.bar(libraries, validation_speeds, color=colors, width=0.6, 
                 edgecolor='white', linewidth=1, yerr=std_devs, capsize=10)
    
    # Add values on bars
    for bar, speed in zip(bars, validation_speeds):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + max(std_devs) + 1000000,
                f'{int(speed):,} items/s',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Customize plot
    ax.set_title('Validation Speed Comparison (10-run average)', fontsize=18, fontweight='bold', pad=20)
    ax.set_ylabel('Items per second', fontsize=14, fontweight='bold')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add comparison text
    satya_vs_pydantic = results['satya_ips_mean'] / results['pydantic_ips_mean']
    satya_vs_msgspec = results['satya_ips_mean'] / results['msgspec_ips_mean']
    
    textstr = '\n'.join((
        f'Satya vs Pydantic: {satya_vs_pydantic:.1f}x faster',
        f'Satya vs msgspec: {satya_vs_msgspec:.1f}x faster',
        f'Run count: {NUM_RUNS}'
    ))
    
    props = dict(boxstyle='round', facecolor='white', alpha=0.5)
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=12,
            verticalalignment='top', bbox=props)
    
    # Adjust layout and save
    plt.tight_layout()
    output_path = 'benchmarks/results/validation_speed_long.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nValidation speed chart saved to '{output_path}'")
    
    # Create a second chart showing relative performance with Pydantic as baseline
    plt.figure(figsize=(10, 6))
    
    # Calculate relative speeds (Pydantic = 1.0)
    rel_speeds = [
        1.0,  # Pydantic baseline
        results['satya_ips_mean'] / results['pydantic_ips_mean'],
        results['msgspec_ips_mean'] / results['pydantic_ips_mean']
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
    plt.title('Relative Validation Performance\n(Pydantic = 1.0x baseline, 10-run average)', fontsize=16, fontweight='bold')
    plt.ylabel('Performance Multiple', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.gca().set_axisbelow(True)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Adjust layout and save
    plt.tight_layout()
    rel_output_path = 'benchmarks/results/validation_relative_performance_long.png'
    plt.savefig(rel_output_path, dpi=300, bbox_inches='tight')
    print(f"Relative performance chart saved to '{rel_output_path}'")

if __name__ == "__main__":
    print(f"Running validation benchmark with {N_ITEMS:,} items...")
    print(f"Batch size: {BATCH_SIZE:,}")
    print(f"Number of runs per benchmark: {NUM_RUNS}")
    
    # Generate test data once to ensure all benchmarks use the same data
    print("Generating test data...")
    test_data = generate_test_data(N_ITEMS)
    print("Test data generated.")
    
    # Store results for each run
    pydantic_times = []
    pydantic_mems = []
    pydantic_ips = []
    pydantic_single_times = []
    
    satya_times = []
    satya_mems = []
    satya_ips = []
    satya_single_times = []
    
    msgspec_times = []
    msgspec_mems = []
    msgspec_ips = []
    msgspec_single_times = []
    
    # Run benchmarks multiple times
    for run in range(1, NUM_RUNS + 1):
        print(f"\n=== Run {run}/{NUM_RUNS} ===")
        
        # Force garbage collection before each benchmark
        gc.collect()
        
        # Run Pydantic benchmark
        print("\nPydantic Benchmark:")
        time_result, mem_result, ips_result, single_time = run_pydantic_benchmark(test_data)
        print(f"Total time: {time_result:.2f}s")
        print(f"Items per second: {int(ips_result):,}")
        print(f"Memory usage for {BATCH_SIZE} items: {mem_result:.1f}MB")
        print(f"Single item validation: {single_time*1000:.2f}ms")
        
        pydantic_times.append(time_result)
        pydantic_mems.append(mem_result)
        pydantic_ips.append(ips_result)
        pydantic_single_times.append(single_time)
        
        # Force garbage collection before each benchmark
        gc.collect()
        
        # Run Satya benchmark
        print("\nSatya Benchmark:")
        time_result, mem_result, ips_result, single_time = run_satya_benchmark(test_data)
        print(f"Total time: {time_result:.2f}s")
        print(f"Items per second: {int(ips_result):,}")
        print(f"Memory usage for {BATCH_SIZE} items: {mem_result:.1f}MB")
        print(f"Single item validation: {single_time*1000:.2f}ms")
        
        satya_times.append(time_result)
        satya_mems.append(mem_result)
        satya_ips.append(ips_result)
        satya_single_times.append(single_time)
        
        # Force garbage collection before each benchmark
        gc.collect()
        
        # Run msgspec benchmark
        print("\nmsgspec Benchmark:")
        time_result, mem_result, ips_result, single_time = run_msgspec_benchmark(test_data)
        print(f"Total time: {time_result:.2f}s")
        print(f"Items per second: {int(ips_result):,}")
        print(f"Memory usage for {BATCH_SIZE} items: {mem_result:.1f}MB")
        print(f"Single item validation: {single_time*1000:.2f}ms")
        
        msgspec_times.append(time_result)
        msgspec_mems.append(mem_result)
        msgspec_ips.append(ips_result)
        msgspec_single_times.append(single_time)
    
    # Calculate statistics
    pydantic_time_mean = statistics.mean(pydantic_times)
    pydantic_time_std = statistics.stdev(pydantic_times) if len(pydantic_times) > 1 else 0
    pydantic_mem_mean = statistics.mean(pydantic_mems)
    pydantic_ips_mean = statistics.mean(pydantic_ips)
    pydantic_ips_std = statistics.stdev(pydantic_ips) if len(pydantic_ips) > 1 else 0
    pydantic_single_mean = statistics.mean(pydantic_single_times) * 1000  # Convert to ms
    
    satya_time_mean = statistics.mean(satya_times)
    satya_time_std = statistics.stdev(satya_times) if len(satya_times) > 1 else 0
    satya_mem_mean = statistics.mean(satya_mems)
    satya_ips_mean = statistics.mean(satya_ips)
    satya_ips_std = statistics.stdev(satya_ips) if len(satya_ips) > 1 else 0
    satya_single_mean = statistics.mean(satya_single_times) * 1000  # Convert to ms
    
    msgspec_time_mean = statistics.mean(msgspec_times)
    msgspec_time_std = statistics.stdev(msgspec_times) if len(msgspec_times) > 1 else 0
    msgspec_mem_mean = statistics.mean(msgspec_mems)
    msgspec_ips_mean = statistics.mean(msgspec_ips)
    msgspec_ips_std = statistics.stdev(msgspec_ips) if len(msgspec_ips) > 1 else 0
    msgspec_single_mean = statistics.mean(msgspec_single_times) * 1000  # Convert to ms
    
    # Print final statistics
    print("\n=== FINAL RESULTS ({} RUNS) ===".format(NUM_RUNS))
    print("\nValidation Comparison (Mean ± Std Dev):")
    print("                         Pydantic        Satya          msgspec")
    print("------------------------------------------------------------")
    print(f"Total time (s)          {pydantic_time_mean:.2f} ± {pydantic_time_std:.2f}    {satya_time_mean:.2f} ± {satya_time_std:.2f}    {msgspec_time_mean:.2f} ± {msgspec_time_std:.2f}")
    print(f"Memory usage (MB)       {pydantic_mem_mean:.1f}            {satya_mem_mean:.1f}            {msgspec_mem_mean:.1f}")
    print(f"Items/second           {int(pydantic_ips_mean):,}     {int(satya_ips_mean):,}     {int(msgspec_ips_mean):,}")
    print(f"Single item val. (ms)   {pydantic_single_mean:.3f}          {satya_single_mean:.3f}          {msgspec_single_mean:.3f}")
    
    # Print relative performance
    print("\nRelative Validation Performance (higher is better):")
    print("                      vs Pydantic   vs msgspec")
    print("----------------------------------------------")
    print(f"Satya speed                   {satya_ips_mean/pydantic_ips_mean:.1f}x          {satya_ips_mean/msgspec_ips_mean:.1f}x")
    print(f"Satya memory                  {pydantic_mem_mean/satya_mem_mean if satya_mem_mean > 0 else 'N/A'}x          {msgspec_mem_mean/satya_mem_mean if satya_mem_mean > 0 else 'N/A'}x")
    
    # Save results
    results = {
        'pydantic_times': pydantic_times,
        'pydantic_time_mean': pydantic_time_mean,
        'pydantic_time_std': pydantic_time_std,
        'pydantic_mem_mean': pydantic_mem_mean,
        'pydantic_ips_mean': pydantic_ips_mean,
        'pydantic_ips_std': pydantic_ips_std,
        'pydantic_single_mean': pydantic_single_mean,
        
        'satya_times': satya_times,
        'satya_time_mean': satya_time_mean,
        'satya_time_std': satya_time_std,
        'satya_mem_mean': satya_mem_mean,
        'satya_ips_mean': satya_ips_mean,
        'satya_ips_std': satya_ips_std,
        'satya_single_mean': satya_single_mean,
        
        'msgspec_times': msgspec_times,
        'msgspec_time_mean': msgspec_time_mean,
        'msgspec_time_std': msgspec_time_std,
        'msgspec_mem_mean': msgspec_mem_mean,
        'msgspec_ips_mean': msgspec_ips_mean,
        'msgspec_ips_std': msgspec_ips_std,
        'msgspec_single_mean': msgspec_single_mean,
    }
    
    # Save the raw results to JSON
    results_path = 'benchmarks/results/validation_benchmark_long_results.json'
    with open(results_path, 'w') as f:
        json.dump({k: v for k, v in results.items() if not isinstance(v, list)}, f, indent=2)
    print(f"\nRaw results saved to '{results_path}'")
    
    # Create visualizations
    create_visualization(results)
