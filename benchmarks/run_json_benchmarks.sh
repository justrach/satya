#!/bin/bash

# Ensure we're in the right directory
cd "$(dirname "$0")"

echo "===================================================="
echo "Running JSON loader benchmarks..."
echo "===================================================="
python json_loader_benchmark.py

echo ""
echo "===================================================="
echo "Running Satya JSON pipeline benchmarks..."
echo "===================================================="
python satya_json_pipeline_benchmark.py

echo ""
echo "===================================================="
echo "All benchmarks completed!"
echo "====================================================" 