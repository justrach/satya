#!/usr/bin/env python
import json
import sys
import time

def main() -> int:
    try:
        # Import Satya module
        from satya import load_json
        
        # Print available functions
        print("Testing JSON parsing with StreamValidatorCore.parse_json")
        
        # Try the function
        json_str = '{"name": "example", "value": 123, "items": [1, 2, 3]}'
        
        # Time the Satya JSON parsing
        start = time.time()
        parsed_data = load_json(json_str)
        end = time.time()
        
        print(f"\nSatya parsing successful: {parsed_data}")
        print(f"Parsing time: {(end - start)*1000:.6f} ms")
        
        # Compare with Python's json
        start = time.time()
        parsed_py = json.loads(json_str)
        end = time.time()
        
        print(f"\nPython json parsing time: {(end - start)*1000:.6f} ms")
        
        # Verify the results match
        print(f"Results match: {parsed_data == parsed_py}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())