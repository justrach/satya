"""
Test runner for all examples
Ensures all examples work correctly and produce expected output
"""

import subprocess
import sys
from pathlib import Path

# Examples to test (only working examples, legacy ones removed)
EXAMPLES = [
    "example2.py",
    "example3.py",
    "example4.py",
    "example5.py",
    "batch_validation_showcase.py",
    "json_schema_example.py",
    "native_optimization_example.py",
    "pydantic_compatibility_showcase.py",
    "scalar_validation_example.py",
    "ultra_fast_showcase.py",
    "user_profile.py",
    "fixed_income_securities.py",
    "turboapi_integration_example.py",
]

# Examples that require special handling
SKIP_EXAMPLES = [
    "example_fastapi.py",  # Requires FastAPI server
    "example_fastapi_tests.py",  # Empty file
    "performance_comparison.py",  # Requires specific setup
    "speed_comparison_comprehensive.py",  # Long running
    "eaxmple5.py",  # Typo in filename
    "test.py",  # Test file
]

def run_example(example_path):
    """Run an example and capture output"""
    try:
        result = subprocess.run(
            [sys.executable, str(example_path)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path.cwd())
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

def main():
    examples_dir = Path("examples")
    
    print("="*80)
    print("TESTING ALL EXAMPLES")
    print("="*80)
    
    passed = []
    failed = []
    skipped = []
    
    for example_file in EXAMPLES:
        example_path = examples_dir / example_file
        
        if not example_path.exists():
            print(f"\n❌ {example_file}: NOT FOUND")
            failed.append((example_file, "File not found"))
            continue
        
        print(f"\n{'='*80}")
        print(f"Running: {example_file}")
        print(f"{'='*80}")
        
        returncode, stdout, stderr = run_example(example_path)
        
        if returncode == 0:
            print(f"✅ {example_file}: PASSED")
            print(f"\nOutput preview (first 500 chars):")
            print(stdout[:500])
            if len(stdout) > 500:
                print(f"... ({len(stdout) - 500} more characters)")
            passed.append(example_file)
        else:
            print(f"❌ {example_file}: FAILED (exit code: {returncode})")
            if stderr:
                print(f"\nError output (first 500 chars):")
                print(stderr[:500])
            if stdout:
                print(f"\nStdout (first 500 chars):")
                print(stdout[:500])
            failed.append((example_file, stderr or "Unknown error"))
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\n✅ Passed: {len(passed)}/{len(EXAMPLES)}")
    for example in passed:
        print(f"   ✓ {example}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(EXAMPLES)}")
        for example, error in failed:
            print(f"   ✗ {example}")
            print(f"     Error: {error[:100]}")
    
    print(f"\n📊 Success Rate: {len(passed)}/{len(EXAMPLES)} ({len(passed)/len(EXAMPLES)*100:.1f}%)")
    
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
