#!/usr/bin/env python3
"""
Run all benchmarks in sequence and save results to a file.
"""

import os
import sys
import subprocess
import datetime

def run_benchmark(benchmark_file):
    """Run a benchmark script and capture its output"""
    print(f"\n{'='*80}")
    print(f"Running benchmark: {benchmark_file}")
    print(f"{'='*80}\n")
    
    # Run the benchmark and capture output
    result = subprocess.run(
        [sys.executable, benchmark_file],
        capture_output=True,
        text=True
    )
    
    # Print output
    print(result.stdout)
    if result.stderr:
        print("ERRORS:")
        print(result.stderr)
    
    return result.stdout

def main():
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(script_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Get timestamp for results file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"benchmark_results_{timestamp}.txt")
    
    # List of benchmarks to run
    benchmarks = [
        os.path.join(script_dir, "benchmark3.py"),
        os.path.join(script_dir, "benchmark_msgspec.py"),
    ]
    
    # Run each benchmark and save results
    with open(results_file, "w") as f:
        f.write(f"Benchmark Results - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for benchmark in benchmarks:
            output = run_benchmark(benchmark)
            
            # Write to results file
            f.write(f"\n{'='*80}\n")
            f.write(f"Results for {os.path.basename(benchmark)}\n")
            f.write(f"{'='*80}\n\n")
            f.write(output)
            f.write("\n\n")
    
    print(f"\nAll benchmarks completed. Results saved to: {results_file}")

if __name__ == "__main__":
    main() 