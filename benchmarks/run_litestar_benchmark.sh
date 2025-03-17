#!/bin/bash
# This script runs the Litestar benchmark comparing satya and Pydantic

# Install required packages if needed
pip install litestar pydantic matplotlib aiohttp

# Set the number of iterations and concurrency
ITERATIONS=200
CONCURRENCY=10

# Run the benchmark
python benchmarks/litestar_benchmark.py --iterations $ITERATIONS --concurrency $CONCURRENCY

echo "Benchmark completed! Check the results in benchmarks/results/ directory."
