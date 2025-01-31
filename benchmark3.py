from typing import List, Dict, Optional
import time
import json
from pydantic import BaseModel, ConfigDict, TypeAdapter
from satya import Model, Field
import random
import gc
import psutil
import os
from itertools import islice

# Number of items to test
N_ITEMS = 5_000_000
BATCH_SIZE = 50000  # Much larger batch size for maximum throughput

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

# Define models for both libraries with optimizations
class PydanticLocation(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', validate_assignment=False)
    latitude: float
    longitude: float
    name: Optional[str] = None

class PydanticAddress(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', validate_assignment=False)
    street: str
    city: str
    country: str
    location: PydanticLocation

class PydanticPerson(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', validate_assignment=False)
    name: str
    age: int
    address: PydanticAddress
    contacts: List[str]
    metadata: Dict[str, str]
    favorite_locations: List[PydanticLocation]

class Location(Model):
    latitude: float
    longitude: float
    name: Optional[str] = Field(required=False)

class Address(Model):
    street: str
    city: str
    country: str
    location: Location

class Person(Model):
    name: str
    age: int
    address: Address
    contacts: List[str]
    metadata: Dict[str, str]
    favorite_locations: List[Location]

def generate_test_batch(size: int, start_idx: int = 0):
    """Generate a batch of test items"""
    return [
        {
            "name": f"Person_{i}",
            "age": random.randint(18, 80),
            "address": {
                "street": f"{i} Main St",
                "city": random.choice(["New York", "London", "Tokyo", "Paris"]),
                "country": random.choice(["USA", "UK", "Japan", "France"]),
                "location": {
                    "latitude": random.uniform(-90, 90),
                    "longitude": random.uniform(-180, 180),
                    "name": f"Location_{i}" if random.random() > 0.5 else None
                }
            },
            "contacts": [
                f"email_{i}@example.com",
                f"+1-555-{i:04d}"
            ],
            "metadata": {
                "id": str(i),
                "status": random.choice(["active", "inactive"]),
                "score": str(random.randint(1, 100))
            },
            "favorite_locations": [
                {
                    "latitude": random.uniform(-90, 90),
                    "longitude": random.uniform(-180, 180),
                    "name": f"Favorite_{j}" if random.random() > 0.5 else None
                }
                for j in range(random.randint(0, 3))
            ]
        }
        for i in range(start_idx, start_idx + size)
    ]

def benchmark_pydantic():
    print("\nPydantic Benchmark:")
    start_mem = get_memory_usage()
    
    # Create type adapter for maximum performance
    person_adapter = TypeAdapter(List[PydanticPerson])  # Note the List wrapper
    
    # Single item validation
    test_item = generate_test_batch(1)[0]
    start_time = time.time()
    for _ in range(1000):
        person_adapter.validate_python([test_item])  # Wrap in list
    single_time = (time.time() - start_time) / 1000
    print(f"Single item validation: {single_time*1000:.2f}ms")
    
    # Batch validation
    start_time = time.time()
    count = 0
    peak_mem = start_mem
    
    while count < N_ITEMS:
        batch_size = min(BATCH_SIZE, N_ITEMS - count)
        batch = generate_test_batch(batch_size, count)
        
        # Validate batch as a list
        person_adapter.validate_python(batch)
        
        count += batch_size
        if count % 100000 == 0:
            current_mem = get_memory_usage()
            peak_mem = max(peak_mem, current_mem)
            print(f"Processed {count:,} items...")
            gc.collect()  # Help manage memory
    
    total_time = time.time() - start_time
    memory_used = peak_mem - start_mem
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Items per second: {N_ITEMS/total_time:,.0f}")
    print(f"Peak memory usage: {memory_used:.1f}MB")
    
    gc.collect()
    return total_time, memory_used

def benchmark_satya():
    print("\nSatya Benchmark:")
    start_mem = get_memory_usage()
    
    validator = Person.validator()
    validator._validator.set_batch_size(BATCH_SIZE)
    
    # Single item validation
    test_item = generate_test_batch(1)[0]
    start_time = time.time()
    for _ in range(1000):
        validator._validator.validate_batch([test_item])
    single_time = (time.time() - start_time) / 1000
    print(f"Single item validation: {single_time*1000:.2f}ms")
    
    # Batch validation
    start_time = time.time()
    count = 0
    peak_mem = start_mem
    
    while count < N_ITEMS:
        batch_size = min(BATCH_SIZE, N_ITEMS - count)
        batch = generate_test_batch(batch_size, count)
        
        # Direct batch validation through Rust
        validator._validator.validate_batch(batch)
        
        count += batch_size
        if count % 100000 == 0:
            current_mem = get_memory_usage()
            peak_mem = max(peak_mem, current_mem)
            print(f"Processed {count:,} items...")
            gc.collect()  # Help manage memory
    
    total_time = time.time() - start_time
    memory_used = peak_mem - start_mem
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Items per second: {N_ITEMS/total_time:,.0f}")
    print(f"Peak memory usage: {memory_used:.1f}MB")
    
    gc.collect()
    return total_time, memory_used

if __name__ == "__main__":
    print(f"Benchmarking with {N_ITEMS:,} items...")
    print(f"Batch size: {BATCH_SIZE:,}")
    
    # Run benchmarks
    pydantic_time, pydantic_mem = benchmark_pydantic()
    satya_time, satya_mem = benchmark_satya()
    
    # Print comparison
    print("\nComparison:")
    print(f"{'':20} {'Pydantic':>12} {'Satya':>12} {'Improvement':>12}")
    print("-" * 58)
    print(f"{'Total time (s)':20} {pydantic_time:12.2f} {satya_time:12.2f} {pydantic_time/satya_time:11.1f}x")
    print(f"{'Memory usage (MB)':20} {pydantic_mem:12.1f} {satya_mem:12.1f} {pydantic_mem/satya_mem:11.1f}x")
    print(f"{'Items/second':20} {N_ITEMS/pydantic_time:12,.0f} {N_ITEMS/satya_time:12,.0f}") 