#!/bin/bash
# This script runs the Starlette benchmark comparing satya and Pydantic

# Install required packages if needed
pip install starlette uvicorn pydantic aiohttp matplotlib

# Set the number of iterations and concurrency
ITERATIONS=200
CONCURRENCY=10

# Run the benchmark
python benchmarks/starlette_benchmark.py --iterations $ITERATIONS --concurrency $CONCURRENCY

echo "Benchmark completed! Check the results in benchmarks/results/ directory."
