#!/usr/bin/env python
import json
import time
import random
import statistics
from typing import Dict, List, Any, Tuple, Iterator
# import matplotlib.pyplot as plt  # Comment out matplotlib
# import numpy as np  # Comment out numpy if only used for plotting

try:
    import orjson
except ImportError:
    print("orjson not found. Installing...")
    import subprocess
    subprocess.check_call(["pip", "install", "orjson"])
    import orjson

from satya import StreamValidator
import satya


def generate_test_data(num_records: int) -> str:
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


def create_validator() -> StreamValidator:
    """Create a StreamValidator with a schema that matches our test data."""
    validator = StreamValidator()
    
    # Define address type
    validator.define_type("Address", {
        "street": str,
        "city": str,
        "state": str,
        "zip": str
    })
    
    # Add fields to the validator
    validator.add_field("id", int)
    validator.add_field("name", str)
    validator.add_field("email", str)
    validator.add_field("age", int)
    validator.add_field("is_active", bool)
    validator.add_field("tags", List[str])
    validator.add_field("address", "Address")
    validator.add_field("scores", List[float])
    
    return validator


class Pipeline1:
    """Pipeline using Python's json.loads() followed by Satya validation."""
    def __init__(self, validator: StreamValidator):
        self.validator = validator
    
    def process(self, json_str: str) -> Iterator[Dict]:
        # Parse JSON using standard Python json module
        data = json.loads(json_str)
        # Validate using Satya
        for item in data:
            yield from self.validator.validate_stream([item])


class Pipeline2:
    """Pipeline using orjson.loads() followed by Satya validation."""
    def __init__(self, validator: StreamValidator):
        self.validator = validator
    
    def process(self, json_str: str) -> Iterator[Dict]:
        # Parse JSON using orjson
        data = orjson.loads(json_str)
        # Validate using Satya
        for item in data:
            yield from self.validator.validate_stream([item])


class Pipeline3:
    """Pipeline using Satya's Rust-based JSON loading followed by validation."""
    def __init__(self, validator: StreamValidator):
        self.validator = validator
    
    def process(self, json_str: str) -> Iterator[Dict]:
        # Parse JSON using Satya's Rust implementation
        data = satya.load_json(json_str)
        # Validate using Satya
        for item in data:
            yield from self.validator.validate_stream([item])


def benchmark_pipelines(json_str: str, num_iterations: int = 5) -> Dict[str, List[float]]:
    """Benchmark different JSON loading pipelines."""
    validator = create_validator()
    
    pipeline1 = Pipeline1(validator)
    pipeline2 = Pipeline2(validator)
    pipeline3 = Pipeline3(validator)
    
    results = {
        "std_json_pipeline": [],
        "orjson_pipeline": [],
        "satya_rust_pipeline": []
    }
    
    # Warm-up
    list(pipeline1.process(json_str))
    list(pipeline2.process(json_str))
    list(pipeline3.process(json_str))
    
    for _ in range(num_iterations):
        # Standard json pipeline
        start = time.time()
        list(pipeline1.process(json_str))
        end = time.time()
        results["std_json_pipeline"].append(end - start)
        
        # orjson pipeline
        start = time.time()
        list(pipeline2.process(json_str))
        end = time.time()
        results["orjson_pipeline"].append(end - start)
        
        # Satya Rust implementation pipeline
        start = time.time()
        list(pipeline3.process(json_str))
        end = time.time()
        results["satya_rust_pipeline"].append(end - start)
    
    return results


def run_benchmarks() -> Dict[int, Dict[str, float]]:
    """Run benchmarks with various data sizes."""
    sizes = [10, 100, 1000, 5000]
    num_iterations = 5
    results = {}
    
    for size in sizes:
        print(f"Benchmarking pipeline with {size} records...")
        json_data = generate_test_data(size)
        data_size_mb = len(json_data) / (1024 * 1024)
        print(f"  - Generated JSON size: {data_size_mb:.2f} MB")
        
        benchmark_results = benchmark_pipelines(json_data, num_iterations)
        
        avg_results = {
            method: statistics.mean(times) 
            for method, times in benchmark_results.items()
        }
        
        results[size] = avg_results
        
        print(f"  - Average processing times:")
        for method, avg_time in avg_results.items():
            print(f"    * {method}: {avg_time:.6f} seconds")
        print()
    
    return results


def plot_results(results: Dict[int, Dict[str, float]]) -> None:
    """Print results instead of plotting."""
    sizes = list(results.keys())
    methods = ["std_json_pipeline", "orjson_pipeline", "satya_rust_pipeline"]
    
    # Create nice labels for the plot
    method_labels = {
        "std_json_pipeline": "Python json + Satya",
        "orjson_pipeline": "orjson + Satya",
        "satya_rust_pipeline": "Satya Rust JSON"
    }
    
    print("\n===== JSON Parsing and Validation Pipeline Performance =====")
    print(f"{'Size':<10} {'Python json':<15} {'orjson':<15} {'Satya Rust':<15}")
    print("-" * 60)
    
    for size in sizes:
        row = f"{size:<10}"
        for method in methods:
            row += f"{results[size][method]:.6f}s      "
        print(row)
    
    print("\n===== Pipeline Speedup Relative to Standard json =====")
    print(f"{'Size':<10} {'orjson':<15} {'Satya Rust':<15}")
    print("-" * 40)
    
    for size in sizes:
        baseline = results[size]["std_json_pipeline"]
        row = f"{size:<10}"
        for method in methods[1:]:  # Skip std_json as it's the baseline
            speedup = baseline / results[size][method]
            row += f"{speedup:.2f}x           "
        print(row)


def main() -> None:
    """Main function to run benchmarks and generate plots."""
    print("Running Satya JSON pipeline benchmarks...")
    results = run_benchmarks()
    
    print("\nGenerating results...")
    plot_results(results)
    
    print("\nBenchmark completed.")


if __name__ == "__main__":
    main() 