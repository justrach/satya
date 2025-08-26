#!/usr/bin/env python
import json
import time
import random
import statistics
from typing import Dict, List, Any, Tuple
# import matplotlib.pyplot as plt  # Comment out matplotlib
# import numpy as np  # Comment out numpy if only used for plotting

try:
    import orjson
except ImportError:
    print("orjson not found. Installing...")
    import subprocess
    subprocess.check_call(["pip", "install", "orjson"])
    import orjson

import satya


def generate_json_data(num_records: int) -> str:
    """Generate sample JSON data with the specified number of records."""
    data = []
    for i in range(num_records):
        record = {
            "id": i,
            "name": f"User {i}",
            "email": f"user{i}@example.com",
            "age": random.randint(18, 80),
            "is_active": random.choice([True, False]),
            "tags": [random.choice(["tag1", "tag2", "tag3", "tag4", "tag5"]) for _ in range(random.randint(1, 5))],
            "address": {
                "street": f"{random.randint(100, 999)} Main St",
                "city": random.choice(["New York", "San Francisco", "Seattle", "Austin", "Boston"]),
                "state": random.choice(["NY", "CA", "WA", "TX", "MA"]),
                "zip": f"{random.randint(10000, 99999)}"
            },
            "scores": [random.random() * 100 for _ in range(5)]
        }
        data.append(record)
    return json.dumps(data)


def benchmark_json_loading(json_str: str, num_iterations: int = 5) -> Dict[str, List[float]]:
    """Benchmark different JSON loading methods."""
    results = {
        "std_json": [],
        "orjson": [],
        "satya_rust": []
    }
    
    # Warm-up
    json.loads(json_str)
    orjson.loads(json_str)
    satya.load_json(json_str)
    
    for _ in range(num_iterations):
        # Standard json
        start = time.time()
        json.loads(json_str)
        end = time.time()
        results["std_json"].append(end - start)
        
        # orjson
        start = time.time()
        orjson.loads(json_str)
        end = time.time()
        results["orjson"].append(end - start)
        
        # Satya Rust implementation
        start = time.time()
        satya.load_json(json_str)
        end = time.time()
        results["satya_rust"].append(end - start)
    
    return results


def run_benchmarks() -> Dict[int, Dict[str, float]]:
    """Run benchmarks with various data sizes."""
    sizes = [10, 100, 1000, 10000]
    num_iterations = 10
    results = {}
    
    for size in sizes:
        print(f"Benchmarking with {size} records...")
        json_data = generate_json_data(size)
        data_size_mb = len(json_data) / (1024 * 1024)
        print(f"  - Generated JSON size: {data_size_mb:.2f} MB")
        
        benchmark_results = benchmark_json_loading(json_data, num_iterations)
        
        avg_results = {
            method: statistics.mean(times) 
            for method, times in benchmark_results.items()
        }
        
        results[size] = avg_results
        
        print(f"  - Average parsing times:")
        for method, avg_time in avg_results.items():
            print(f"    * {method}: {avg_time:.6f} seconds")
        print()
    
    return results


def plot_results(results: Dict[int, Dict[str, float]]) -> None:
    """Print results instead of plotting."""
    sizes = list(results.keys())
    methods = ["std_json", "orjson", "satya_rust"]
    
    print("\n===== JSON Parsing Performance =====")
    print(f"{'Size':<10} {'std_json':<15} {'orjson':<15} {'satya_rust':<15}")
    print("-" * 55)
    
    for size in sizes:
        row = f"{size:<10}"
        for method in methods:
            row += f"{results[size][method]:.6f}s      "
        print(row)
    
    print("\n===== Speedup Relative to standard json =====")
    print(f"{'Size':<10} {'orjson':<15} {'satya_rust':<15}")
    print("-" * 40)
    
    for size in sizes:
        baseline = results[size]["std_json"]
        row = f"{size:<10}"
        for method in methods[1:]:  # Skip std_json as it's the baseline
            speedup = baseline / results[size][method]
            row += f"{speedup:.2f}x           "
        print(row)


def main() -> None:
    """Main function to run benchmarks and generate plots."""
    print("Running JSON loader benchmarks...")
    results = run_benchmarks()
    
    print("\nGenerating results...")
    plot_results(results)
    
    print("\nBenchmark completed.")


if __name__ == "__main__":
    main() 