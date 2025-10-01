#!/bin/bash
# Runner script for jsonschema comparison benchmark

set -e

echo "============================================"
echo "Satya vs jsonschema Benchmark Runner"
echo "============================================"
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  No virtual environment detected."
    echo ""
    echo "It's recommended to run this in a virtual environment:"
    echo ""
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install jsonschema memory-profiler matplotlib numpy"
    echo "  pip install -e ."
    echo "  ./benchmarks/run_jsonschema_comparison.sh"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for required packages
echo "Checking dependencies..."

python3 -c "import jsonschema" 2>/dev/null || {
    echo "❌ jsonschema not installed"
    echo "   Install with: pip install jsonschema"
    exit 1
}

python3 -c "import memory_profiler" 2>/dev/null || {
    echo "❌ memory-profiler not installed"
    echo "   Install with: pip install memory-profiler"
    exit 1
}

python3 -c "import matplotlib" 2>/dev/null || {
    echo "❌ matplotlib not installed"
    echo "   Install with: pip install matplotlib"
    exit 1
}

python3 -c "import satya" 2>/dev/null || {
    echo "❌ satya not installed"
    echo "   Install with: pip install -e ."
    exit 1
}

echo "✅ All dependencies found"
echo ""

# Run the benchmark
echo "Running benchmark..."
python3 benchmarks/jsonschema_comparison.py

echo ""
echo "✅ Benchmark complete!"
echo "📊 Check benchmarks/results/ for charts and data"
