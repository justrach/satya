#!/usr/bin/env python
import time
import json
import random

# Try direct import from the module
from src.satya.json_loader import load_json

# Try to import orjson for comparison
try:
    import orjson
    have_orjson = True
except ImportError:
    have_orjson = False
    print("orjson not installed, skipping comparison")

# Generate a larger JSON payload
def generate_test_data(records=10000):
    data = []
    for i in range(records):
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

print(f"Generating test data with 10,000 records...")
json_str = generate_test_data()
print(f"Test data size: {len(json_str) / 1024 / 1024:.2f} MB")

# Run multiple iterations to get more accurate timing
iterations = 5
print(f"\nRunning {iterations} iterations for each parser...")

# Test satya.json_loader.load_json
satya_times = []
for i in range(iterations):
    start = time.time()
    parsed_data = load_json(json_str)
    end = time.time()
    satya_times.append((end - start) * 1000)  # Convert to ms

# Test standard json
json_times = []
for i in range(iterations):
    start = time.time()
    standard_parsed = json.loads(json_str)
    end = time.time()
    json_times.append((end - start) * 1000)  # Convert to ms

# Test orjson if available
if have_orjson:
    orjson_times = []
    for i in range(iterations):
        start = time.time()
        orjson_parsed = orjson.loads(json_str)
        end = time.time()
        orjson_times.append((end - start) * 1000)  # Convert to ms

# Print results
print("\nResults (in milliseconds):")
print(f"satya.json_loader: avg={sum(satya_times)/len(satya_times):.2f}ms, min={min(satya_times):.2f}ms, max={max(satya_times):.2f}ms")
print(f"standard json: avg={sum(json_times)/len(json_times):.2f}ms, min={min(json_times):.2f}ms, max={max(json_times):.2f}ms")
if have_orjson:
    print(f"orjson: avg={sum(orjson_times)/len(orjson_times):.2f}ms, min={min(orjson_times):.2f}ms, max={max(orjson_times):.2f}ms")

# Compare speed (relative to standard json)
avg_json = sum(json_times)/len(json_times)
avg_satya = sum(satya_times)/len(satya_times)
print(f"\nSpeed comparison:")
print(f"satya.json_loader vs standard json: {avg_json/avg_satya:.2f}x")

if have_orjson:
    avg_orjson = sum(orjson_times)/len(orjson_times)
    print(f"orjson vs standard json: {avg_json/avg_orjson:.2f}x")
    print(f"satya.json_loader vs orjson: {avg_orjson/avg_satya:.2f}x") 