#!/usr/bin/env python
import time
import json

# Try direct import from the module
from src.satya.json_loader import load_json

print("Testing JSON loading...")

# Test data
json_str = '{"name": "example", "value": 123, "items": [1, 2, 3]}'

# Time the Satya JSON parsing
start = time.time()
parsed_data = load_json(json_str)
end = time.time()

print(f"Parsed data: {parsed_data}")
print(f"Parsing time: {(end - start)*1000:.6f} ms")

# Compare with standard json
start = time.time()
standard_parsed = json.loads(json_str)
end = time.time()

print(f"Standard json parsing time: {(end - start)*1000:.6f} ms")
print(f"Results match: {parsed_data == standard_parsed}") 