#!/usr/bin/env python
import sys
import os
import json
import time

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))

def main() -> int:
    try:
        # Now import from our local version of satya
        from satya.json_loader import load_json
        
        # Try the function
        json_str = '{"name": "example", "value": 123, "items": [1, 2, 3]}'
        
        # Time the Satya JSON parsing
        start = time.time()
        parsed_data = load_json(json_str)
        end = time.time()
        
        print(f"Satya parsing successful: {parsed_data}")
        print(f"Parsing time: {(end - start)*1000:.6f} ms")
        
        # Compare with Python's json
        start = time.time()
        parsed_py = json.loads(json_str)
        end = time.time()
        
        print(f"Python json parsing time: {(end - start)*1000:.6f} ms")
        
        # Verify the results match
        print(f"Results match: {parsed_data == parsed_py}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())