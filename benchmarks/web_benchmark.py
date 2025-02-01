from typing import List, Dict, Optional
import time
import json
import asyncio
import aiohttp
from pydantic import BaseModel, ConfigDict, TypeAdapter
from satya import Model, Field
import random
import gc
import psutil
import os
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import uvicorn
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor
import math
import matplotlib.pyplot as plt

# Increase batch size for better performance
BATCH_SIZE = 1000  # Process requests in larger batches
N_REQUESTS = 10_000
CONCURRENT_REQUESTS = 1000  # Reduced to avoid overwhelming
SIMULATED_LATENCY = 0.0001  # 0.1ms network latency

# Models for both libraries
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

def generate_payload():
    """Generate a realistic API payload"""
    i = random.randint(0, 1000000)
    return {
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

# FastAPI apps
app_pydantic = FastAPI()
app_satya = FastAPI()

# Pre-create validators
person_adapter = TypeAdapter(PydanticPerson)
satya_validator = Person.validator()

@app_pydantic.post("/validate")
async def validate_pydantic(data: dict):
    await asyncio.sleep(SIMULATED_LATENCY)  # Simulate network/DB latency
    try:
        person_adapter.validate_python(data)
        return {"status": "valid"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app_satya.post("/validate-batch")
async def validate_satya_batch(data: List[dict]):
    """Batch validation endpoint for Satya"""
    await asyncio.sleep(SIMULATED_LATENCY)
    results = satya_validator._validator.validate_batch(data)
    valid_items = [item for item, is_valid in zip(data, results) if is_valid]
    return {"valid_count": len(valid_items), "total": len(data)}

def percentile(data, p):
    """Calculate percentile value from a list of numbers"""
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1

async def run_benchmark(client: TestClient, n_requests: int):
    """Run benchmark with concurrent requests"""
    latencies = []
    valid_count = 0
    
    async def make_request():
        nonlocal valid_count, latencies
        payload = generate_payload()
        start_time = time.time()
        response = client.post("/validate", json=payload)
        latency = time.time() - start_time
        latencies.append(latency)
        if response.status_code == 200:
            valid_count += 1
        return response.status_code
    
    # Process requests in batches
    pending = set()
    completed = 0
    
    while completed < n_requests:
        # Add new tasks up to concurrent limit
        while len(pending) < CONCURRENT_REQUESTS and completed + len(pending) < n_requests:
            task = asyncio.create_task(make_request())
            pending.add(task)
        
        if not pending:
            break
            
        # Wait for some tasks to complete
        done, pending = await asyncio.wait(
            pending,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Process completed tasks
        for task in done:
            await task
            completed += 1
            
        if completed % 1000 == 0:
            print(f"Completed {completed:,} requests...")
    
    return {
        "valid_count": valid_count,
        "avg_latency": statistics.mean(latencies),
        "p95_latency": percentile(latencies, 0.95),
        "p99_latency": percentile(latencies, 0.99),
        "min_latency": min(latencies),
        "max_latency": max(latencies),
        "latencies": latencies
    }

async def run_benchmark_satya(client: TestClient, n_requests: int):
    """Run benchmark with batched requests for Satya"""
    latencies = []
    valid_count = 0
    
    async def make_batch_request(batch_data):
        nonlocal valid_count, latencies
        start_time = time.time()
        response = client.post("/validate-batch", json=batch_data)
        latency = (time.time() - start_time) / len(batch_data)  # Per-item latency
        
        if response.status_code == 200:
            result = response.json()
            valid_count += result["valid_count"]
            latencies.extend([latency] * len(batch_data))
        return response.status_code
    
    # Process requests in batches
    completed = 0
    while completed < n_requests:
        # Generate batch of payloads
        batch_size = min(BATCH_SIZE, n_requests - completed)
        batch_data = [generate_payload() for _ in range(batch_size)]
        
        # Process batch
        await make_batch_request(batch_data)
        completed += batch_size
        
        if completed % 1000 == 0:
            print(f"Completed {completed:,} requests...")
    
    return {
        "valid_count": valid_count,
        "avg_latency": statistics.mean(latencies),
        "p95_latency": percentile(latencies, 0.95),
        "p99_latency": percentile(latencies, 0.99),
        "min_latency": min(latencies),
        "max_latency": max(latencies),
        "latencies": latencies
    }

def print_results(name: str, results: dict):
    print(f"\n{name} Results:")
    print(f"Valid requests: {results['valid_count']:,} / {N_REQUESTS:,}")
    print(f"Average latency: {results['avg_latency']*1000:.2f}ms")
    print(f"P95 latency: {results['p95_latency']*1000:.2f}ms")
    print(f"P99 latency: {results['p99_latency']*1000:.2f}ms")
    print(f"Min latency: {results['min_latency']*1000:.2f}ms")
    print(f"Max latency: {results['max_latency']*1000:.2f}ms")
    print(f"Requests/second: {N_REQUESTS/sum(results['latencies']):.0f}")

async def main():
    print(f"Running web benchmark with {N_REQUESTS:,} requests")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Concurrent requests: {CONCURRENT_REQUESTS}")
    print(f"Simulated latency: {SIMULATED_LATENCY*1000:.1f}ms")
    
    # Run Pydantic benchmark
    client_pydantic = TestClient(app_pydantic)
    pydantic_results = await run_benchmark(client_pydantic, N_REQUESTS)
    print_results("Pydantic", pydantic_results)
    
    # Run Satya benchmark with batching
    client_satya = TestClient(app_satya)
    satya_results = await run_benchmark_satya(client_satya, N_REQUESTS)
    print_results("Satya (Batched)", satya_results)
    
    # Create visualization
    metrics = ['Average', 'P95', 'P99', 'Max']
    pydantic_values = [
        pydantic_results['avg_latency'] * 1000,
        pydantic_results['p95_latency'] * 1000,
        pydantic_results['p99_latency'] * 1000,
        pydantic_results['max_latency'] * 1000
    ]
    satya_values = [
        satya_results['avg_latency'] * 1000,
        satya_results['p95_latency'] * 1000,
        satya_results['p99_latency'] * 1000,
        satya_results['max_latency'] * 1000
    ]
    
    x = range(len(metrics))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar([i - width/2 for i in x], pydantic_values, width, label='Pydantic', color='#FF6B6B')
    ax.bar([i + width/2 for i in x], satya_values, width, label='Satya', color='#4ECDC4')
    
    ax.set_ylabel('Latency (ms)')
    ax.set_title('Validation Performance: Pydantic vs Satya')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    
    # Add value labels on top of each bar
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}ms',
                       xy=(rect.get_x() + rect.get_width() / 2, height),
                       xytext=(0, 3),  # 3 points vertical offset
                       textcoords="offset points",
                       ha='center', va='bottom', rotation=0)
    
    autolabel(ax.patches[:len(metrics)])
    autolabel(ax.patches[len(metrics):])
    
    plt.tight_layout()
    plt.savefig('benchmark_results.png')
    plt.close()
    
    # Print comparison
    print("\nComparison (Satya vs Pydantic):")
    print(f"Latency improvement: {pydantic_results['avg_latency']/satya_results['avg_latency']:.1f}x")
    print(f"Throughput improvement: {(N_REQUESTS/sum(satya_results['latencies']))/(N_REQUESTS/sum(pydantic_results['latencies'])):.1f}x")

if __name__ == "__main__":
    asyncio.run(main()) 