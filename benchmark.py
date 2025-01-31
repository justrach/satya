from satya import StreamValidator
from pydantic import BaseModel
import time
from typing import Generator
import statistics
import psutil  # For memory tracking
import os

class Person(BaseModel):
    name: str
    age: int
    active: bool

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def generate_data(n: int, delay: float) -> Generator[dict, None, None]:
    """Generate n items with specified delay"""
    for i in range(n):
        data = {
            "name": f"Person_{i}",
            "age": 20 + i,
            "active": i % 2 == 0
        }
        time.sleep(delay)
        yield data

def benchmark_stream_validator(validator: StreamValidator, n_items: int, delay: float) -> list[float]:
    """Benchmark our streaming validator"""
    validator.add_field("name", str)
    validator.add_field("age", int)
    validator.add_field("active", bool)
    
    processing_times = []
    stream = generate_data(n_items, delay)
    
    mem_before = get_memory_usage()
    for item in validator.validate_stream(stream):
        start = time.perf_counter()
        _ = item
        processing_times.append(time.perf_counter() - start)
    mem_after = get_memory_usage()
    
    return processing_times, mem_after - mem_before

def benchmark_pydantic(n_items: int, delay: float) -> list[float]:
    """Benchmark Pydantic"""
    processing_times = []
    stream = generate_data(n_items, delay)
    
    # Measure memory before collecting data
    mem_before = get_memory_usage()
    
    # Collect all data first (as Pydantic typically works with full datasets)
    data = list(stream)
    
    # Now process each item
    for item in data:
        start = time.perf_counter()
        _ = Person(**item)
        processing_times.append(time.perf_counter() - start)
    
    mem_after = get_memory_usage()
    return processing_times, mem_after - mem_before

def run_benchmark(n_items: int = 1000, delay: float = 0.0001, batch_sizes: list[int] = [1, 1000, 10000]):
    print(f"\nRunning benchmark with {n_items:,} items and {delay}s delay per item")
    print("-" * 60)
    
    # Test different batch sizes
    for batch_size in batch_sizes:
        print(f"\nStream Validator (batch_size={batch_size:,}):")
        validator = StreamValidator(batch_size=batch_size)
        start_total = time.perf_counter()
        stream_times, mem_usage = benchmark_stream_validator(validator, n_items, delay)
        stream_total = time.perf_counter() - start_total
        
        print(f"Total time: {stream_total:.4f}s")
        print(f"Average processing time: {statistics.mean(stream_times):.8f}s")
        print(f"Max processing time: {max(stream_times):.8f}s")
        print(f"Memory usage: {mem_usage:.2f} MB")
    
    # Pydantic benchmark
    print("\nPydantic:")
    start_total = time.perf_counter()
    pydantic_times, mem_usage = benchmark_pydantic(n_items, delay)
    pydantic_total = time.perf_counter() - start_total
    
    print(f"Total time: {pydantic_total:.4f}s")
    print(f"Average processing time: {statistics.mean(pydantic_times):.8f}s")
    print(f"Max processing time: {max(pydantic_times):.8f}s")
    print(f"Memory usage: {mem_usage:.2f} MB")

if __name__ == "__main__":
    # Smaller delay for large datasets
    delay = 0.000001  # 1 microsecond
    
    # Run benchmarks with different sizes
    run_benchmark(n_items=1_000, delay=delay)
    run_benchmark(n_items=10_000, delay=delay)
    run_benchmark(n_items=100_000, delay=delay)
    run_benchmark(n_items=1_000_000, delay=delay) 