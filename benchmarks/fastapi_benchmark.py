#!/usr/bin/env python
"""
Benchmark comparing satya vs Pydantic performance in FastAPI.

This benchmark:
1. Sets up two FastAPI applications - one using satya, one using Pydantic
2. Tests various operations (validation, serialization, etc.)
3. Runs 1000 iterations in parallel using asyncio
4. Generates detailed performance metrics and comparisons
"""
import os
import time
import json
import asyncio
import statistics
import argparse
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import matplotlib.pyplot as plt
import numpy as np
import aiohttp

# ======================= Configuration =======================
# Define globals at the module level before use
NUM_ITERATIONS = 1000  # Number of iterations for each test
CONCURRENCY_LEVEL = 20  # Number of concurrent requests to make
BENCHMARK_PORT_PYDANTIC = 8000  # Port for Pydantic app
BENCHMARK_PORT_SATYA = 8001  # Port for satya app
WARMUP_REQUESTS = 50  # Number of warmup requests
PLOT_RESULTS = True  # Whether to generate plots
SAVE_RESULTS = True  # Whether to save results to files

try:
    import uvicorn
    from fastapi import FastAPI, Body, Query
    from fastapi.testclient import TestClient
    from pydantic import BaseModel, Field as PydanticField
    
    from satya import Model, Field
    from satya.fastapi import SatyaJSONResponse
except ImportError:
    print("Please install required packages: pip install fastapi uvicorn matplotlib aiohttp satya")
    exit(1)

# ======================= Test Data =======================
TEST_SMALL_ITEM = {
    "name": "Small Item",
    "price": 10.99,
    "is_available": True,
    "tags": ["small", "item"]
}

TEST_MEDIUM_ITEM = {
    "name": "Medium Complex Item",
    "description": "This is a medium complexity item with nested data",
    "price": 99.99,
    "is_available": True,
    "tags": ["medium", "complex", "nested"],
    "dimensions": {
        "width": 10.5,
        "height": 20.3,
        "depth": 5.0
    },
    "reviews": [
        {"user": "user1", "rating": 4, "comment": "Good product"},
        {"user": "user2", "rating": 5, "comment": "Excellent product"}
    ]
}

TEST_LARGE_ITEM = {
    "name": "Large Complex Item",
    "description": "This is a very complex item with lots of nested data",
    "price": 999.99,
    "is_available": True,
    "tags": ["large", "complex", "nested", "data-heavy"],
    "dimensions": {
        "width": 100.5,
        "height": 200.3,
        "depth": 50.0,
        "weight": 45.6,
        "additional_info": {
            "material": "steel",
            "color": "silver",
            "finish": "matte"
        }
    },
    "features": [
        "waterproof", "shockproof", "dustproof", "temperature-resistant"
    ],
    "compatibility": {
        "os": ["windows", "macos", "linux"],
        "min_requirements": {
            "ram": "8GB",
            "processor": "Intel i5",
            "storage": "256GB"
        }
    },
    "reviews": [
        {"user": "user1", "rating": 4, "comment": "Good product", "verified": True, "helpful_votes": 10},
        {"user": "user2", "rating": 5, "comment": "Excellent product", "verified": True, "helpful_votes": 20},
        {"user": "user3", "rating": 3, "comment": "Average product", "verified": False, "helpful_votes": 5},
        {"user": "user4", "rating": 5, "comment": "Best product ever", "verified": True, "helpful_votes": 15},
        {"user": "user5", "rating": 4, "comment": "Very good product", "verified": True, "helpful_votes": 8}
    ],
    "related_items": [
        {"id": 101, "name": "Related Item 1", "price": 49.99},
        {"id": 102, "name": "Related Item 2", "price": 59.99},
        {"id": 103, "name": "Related Item 3", "price": 69.99}
    ]
}

# ===================  Test Scenarios =====================
TEST_SCENARIOS = [
    {"name": "small_item", "data": TEST_SMALL_ITEM, "label": "Small Item"},
    {"name": "medium_item", "data": TEST_MEDIUM_ITEM, "label": "Medium Complex Item"},
    {"name": "large_item", "data": TEST_LARGE_ITEM, "label": "Large Complex Item"}
]

# ======================= Models =======================
# -------------- Pydantic Models --------------
class PydanticDimensions(BaseModel):
    width: float
    height: float
    depth: float
    weight: Optional[float] = None
    additional_info: Optional[Dict[str, str]] = None

class PydanticReview(BaseModel):
    user: str
    rating: int = PydanticField(ge=1, le=5)
    comment: Optional[str] = None
    verified: Optional[bool] = False
    helpful_votes: Optional[int] = 0

class PydanticRelatedItem(BaseModel):
    id: int
    name: str
    price: float

class PydanticCompatibility(BaseModel):
    os: List[str]
    min_requirements: Optional[Dict[str, str]] = None

class PydanticItem(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = PydanticField(gt=0)
    is_available: bool = True
    tags: List[str] = []
    dimensions: Optional[PydanticDimensions] = None
    features: Optional[List[str]] = None
    compatibility: Optional[PydanticCompatibility] = None
    reviews: Optional[List[PydanticReview]] = None
    related_items: Optional[List[PydanticRelatedItem]] = None

# -------------- Satya Models --------------
class SatyaDimensions(Model):
    width: float = Field()
    height: float = Field()
    depth: float = Field()
    weight: Optional[float] = Field(required=False)
    additional_info: Optional[Dict[str, str]] = Field(required=False)

class SatyaReview(Model):
    user: str = Field()
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(required=False)
    verified: Optional[bool] = Field(required=False, default=False)
    helpful_votes: Optional[int] = Field(required=False, default=0)

class SatyaRelatedItem(Model):
    id: int = Field()
    name: str = Field()
    price: float = Field()

class SatyaCompatibility(Model):
    os: List[str] = Field()
    min_requirements: Optional[Dict[str, str]] = Field(required=False)

class SatyaItem(Model):
    name: str = Field()
    description: Optional[str] = Field(required=False)
    price: float = Field(gt=0)
    is_available: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    dimensions: Optional[SatyaDimensions] = Field(required=False)
    features: Optional[List[str]] = Field(required=False)
    compatibility: Optional[SatyaCompatibility] = Field(required=False)
    reviews: Optional[List[SatyaReview]] = Field(required=False)
    related_items: Optional[List[SatyaRelatedItem]] = Field(required=False)

# ======================= FastAPI Apps =======================
# Create Pydantic FastAPI app
pydantic_app = FastAPI(title="Pydantic Benchmark App")

@pydantic_app.get("/")
def pydantic_root():
    return {"message": "Pydantic Benchmark App"}

@pydantic_app.post("/items")
def pydantic_create_item(item: PydanticItem):
    return item

@pydantic_app.get("/items/{item_id}")
def pydantic_get_item(item_id: int, item_size: str = "small"):
    if item_size == "small":
        data = TEST_SMALL_ITEM
    elif item_size == "medium":
        data = TEST_MEDIUM_ITEM
    else:
        data = TEST_LARGE_ITEM
    data["id"] = item_id
    return PydanticItem(**data)

# Create Satya FastAPI app
satya_app = FastAPI(title="Satya Benchmark App")

@satya_app.get("/")
def satya_root():
    return {"message": "Satya Benchmark App"}

@satya_app.post("/items", response_class=SatyaJSONResponse)
def satya_create_item(item: dict = Body(...)):
    return SatyaItem(**item)

@satya_app.get("/items/{item_id}", response_class=SatyaJSONResponse)
def satya_get_item(item_id: int, item_size: str = Query("small")):
    if item_size == "small":
        data = TEST_SMALL_ITEM
    elif item_size == "medium":
        data = TEST_MEDIUM_ITEM
    else:
        data = TEST_LARGE_ITEM
    data["id"] = item_id
    return SatyaItem(**data)

# ======================= Benchmark Logic =======================
@dataclass
class BenchmarkResult:
    framework: str
    scenario: str
    operation: str
    times: List[float]
    
    @property
    def avg_time(self) -> float:
        return statistics.mean(self.times)
    
    @property
    def median_time(self) -> float:
        return statistics.median(self.times)
    
    @property
    def min_time(self) -> float:
        return min(self.times)
    
    @property
    def max_time(self) -> float:
        return max(self.times)
    
    @property
    def stddev_time(self) -> float:
        return statistics.stdev(self.times) if len(self.times) > 1 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "framework": self.framework,
            "scenario": self.scenario,
            "operation": self.operation,
            "avg_time_ms": self.avg_time * 1000,
            "median_time_ms": self.median_time * 1000,
            "min_time_ms": self.min_time * 1000,
            "max_time_ms": self.max_time * 1000,
            "stddev_time_ms": self.stddev_time * 1000,
            "iterations": len(self.times)
        }

async def benchmark_http_client(base_url: str, operation: str, scenario: Dict) -> List[float]:
    """Run benchmark using HTTP client (aiohttp)."""
    times = []
    data = scenario["data"]
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Warmup requests
        warmup_tasks = []
        for _ in range(WARMUP_REQUESTS):
            if operation == "create":
                warmup_tasks.append(session.post(f"{base_url}/items", json=data))
            elif operation == "get":
                warmup_tasks.append(session.get(f"{base_url}/items/1?item_size={scenario['name']}"))
        
        await asyncio.gather(*warmup_tasks)
        
        # Benchmark tasks
        tasks = []
        for i in range(NUM_ITERATIONS):
            if operation == "create":
                tasks.append(benchmark_single_request(session, "POST", f"{base_url}/items", json=data))
            elif operation == "get":
                tasks.append(benchmark_single_request(session, "GET", f"{base_url}/items/{i % 100 + 1}?item_size={scenario['name']}"))
        
        # Execute in parallel with controlled concurrency
        chunked_times = []
        for i in range(0, len(tasks), CONCURRENCY_LEVEL):
            chunk = tasks[i:i + CONCURRENCY_LEVEL]
            chunk_times = await asyncio.gather(*chunk)
            chunked_times.extend(chunk_times)
        
        times.extend(chunked_times)
    
    return times

async def benchmark_single_request(session, method: str, url: str, **kwargs) -> float:
    """Benchmark a single HTTP request and return the time taken."""
    start_time = time.time()
    if method == "GET":
        async with session.get(url, **kwargs) as response:
            await response.text()
    elif method == "POST":
        async with session.post(url, **kwargs) as response:
            await response.text()
    end_time = time.time()
    return end_time - start_time

def start_server(app, port: int):
    """Start a FastAPI server in a separate process."""
    config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config=config)
    return server.serve()

async def run_server_and_benchmark(framework: str, scenarios: List[Dict], operations: List[str], port: int, app):
    """Run the benchmark for a given framework."""
    # Start the server in a separate process
    server_task = asyncio.create_task(start_server(app, port))
    
    # Give the server a moment to start
    await asyncio.sleep(2)
    
    base_url = f"http://127.0.0.1:{port}"
    results = []
    
    try:
        # Run benchmarks for each scenario and operation
        for scenario in scenarios:
            for operation in operations:
                print(f"Benchmarking {framework} - {scenario['label']} - {operation}...")
                times = await benchmark_http_client(base_url, operation, scenario)
                result = BenchmarkResult(
                    framework=framework,
                    scenario=scenario["name"],
                    operation=operation,
                    times=times
                )
                results.append(result)
                print(f"  Avg time: {result.avg_time * 1000:.2f}ms | Median: {result.median_time * 1000:.2f}ms")
    finally:
        # Stop the server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
    
    return results

def generate_plots(results: List[BenchmarkResult], output_dir: str = "benchmarks/results"):
    """Generate plots comparing the benchmark results."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Group results by scenario and operation
    grouped_results = {}
    for result in results:
        key = (result.scenario, result.operation)
        if key not in grouped_results:
            grouped_results[key] = []
        grouped_results[key].append(result)
    
    # Generate comparison bar charts
    for (scenario, operation), group_results in grouped_results.items():
        plt.figure(figsize=(12, 8))
        
        # Extract data for plotting
        frameworks = [r.framework for r in group_results]
        avg_times = [r.avg_time * 1000 for r in group_results]  # Convert to ms
        median_times = [r.median_time * 1000 for r in group_results]
        min_times = [r.min_time * 1000 for r in group_results]
        max_times = [r.max_time * 1000 for r in group_results]
        
        # Set up bar positions
        bar_width = 0.2
        r1 = np.arange(len(frameworks))
        r2 = [x + bar_width for x in r1]
        r3 = [x + bar_width for x in r2]
        r4 = [x + bar_width for x in r3]
        
        # Create bars
        plt.bar(r1, avg_times, width=bar_width, label='Avg Time', color='skyblue')
        plt.bar(r2, median_times, width=bar_width, label='Median Time', color='lightgreen')
        plt.bar(r3, min_times, width=bar_width, label='Min Time', color='yellow')
        plt.bar(r4, max_times, width=bar_width, label='Max Time', color='salmon')
        
        # Add labels and title
        plt.xlabel('Framework')
        plt.ylabel('Time (ms)')
        plt.title(f'Performance Comparison - {scenario.capitalize()} - {operation.capitalize()}')
        plt.xticks([r + bar_width * 1.5 for r in range(len(frameworks))], frameworks)
        plt.legend()
        
        # Add value labels on bars
        for i, v in enumerate(avg_times):
            plt.text(r1[i], v + 0.1, f'{v:.2f}', ha='center', va='bottom', fontsize=8, rotation=45)
        for i, v in enumerate(median_times):
            plt.text(r2[i], v + 0.1, f'{v:.2f}', ha='center', va='bottom', fontsize=8, rotation=45)
        for i, v in enumerate(min_times):
            plt.text(r3[i], v + 0.1, f'{v:.2f}', ha='center', va='bottom', fontsize=8, rotation=45)
        for i, v in enumerate(max_times):
            plt.text(r4[i], v + 0.1, f'{v:.2f}', ha='center', va='bottom', fontsize=8, rotation=45)
        
        # Add improvement percentage if satya is faster than pydantic
        if len(frameworks) == 2 and "satya" in frameworks and "pydantic" in frameworks:
            pydantic_idx = frameworks.index("pydantic")
            satya_idx = frameworks.index("satya")
            pydantic_avg = avg_times[pydantic_idx]
            satya_avg = avg_times[satya_idx]
            
            improvement_pct = ((pydantic_avg - satya_avg) / pydantic_avg) * 100
            if improvement_pct > 0:
                plt.figtext(0.5, 0.01, f"satya is {improvement_pct:.2f}% faster than pydantic (avg time)", 
                           ha="center", fontsize=10, bbox={"facecolor":"lightgreen", "alpha":0.5, "pad":5})
            else:
                plt.figtext(0.5, 0.01, f"pydantic is {-improvement_pct:.2f}% faster than satya (avg time)", 
                           ha="center", fontsize=10, bbox={"facecolor":"salmon", "alpha":0.5, "pad":5})
        
        # Save the plot
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{scenario}_{operation}_comparison.png")
        plt.close()
    
    # Generate summary plot
    generate_summary_plot(results, output_dir)

def generate_summary_plot(results: List[BenchmarkResult], output_dir: str):
    """Generate a summary plot comparing pydantic vs satya across all tests."""
    # Group results by framework
    pydantic_results = [r for r in results if r.framework == "pydantic"]
    satya_results = [r for r in results if r.framework == "satya"]
    
    if not pydantic_results or not satya_results:
        return
    
    # Prepare data for plotting
    scenarios = sorted(set(r.scenario for r in results))
    operations = sorted(set(r.operation for r in results))
    
    # Create one subplot for each operation
    fig, axs = plt.subplots(len(operations), 1, figsize=(12, 8 * len(operations)))
    if len(operations) == 1:
        axs = [axs]
    
    for i, operation in enumerate(operations):
        op_pydantic = [r for r in pydantic_results if r.operation == operation]
        op_satya = [r for r in satya_results if r.operation == operation]
        
        # Create dictionary to easily find results by scenario
        pydantic_dict = {r.scenario: r for r in op_pydantic}
        satya_dict = {r.scenario: r for r in op_satya}
        
        # Prepare bar data
        pydantic_avgs = []
        satya_avgs = []
        labels = []
        
        for scenario in scenarios:
            if scenario in pydantic_dict and scenario in satya_dict:
                pydantic_avgs.append(pydantic_dict[scenario].avg_time * 1000)  # ms
                satya_avgs.append(satya_dict[scenario].avg_time * 1000)  # ms
                # Make scenario label more readable
                label = scenario.replace('_', ' ').title()
                labels.append(label)
        
        # Plot bars
        x = np.arange(len(labels))
        width = 0.35
        
        axs[i].bar(x - width/2, pydantic_avgs, width, label='Pydantic')
        axs[i].bar(x + width/2, satya_avgs, width, label='satya')
        
        # Configure subplot
        axs[i].set_xlabel('Scenario')
        axs[i].set_ylabel('Average time (ms)')
        axs[i].set_title(f'{operation.capitalize()} Operation Performance')
        axs[i].set_xticks(x)
        axs[i].set_xticklabels(labels)
        axs[i].legend()
        
        # Add value labels
        for j, v in enumerate(pydantic_avgs):
            axs[i].text(j - width/2, v + 0.1, f'{v:.2f}', ha='center', fontsize=8)
        for j, v in enumerate(satya_avgs):
            axs[i].text(j + width/2, v + 0.1, f'{v:.2f}', ha='center', fontsize=8)
            
        # Calculate and display improvement percentages
        for j in range(len(labels)):
            pydantic_val = pydantic_avgs[j]
            satya_val = satya_avgs[j]
            if pydantic_val > 0:  # Avoid division by zero
                improvement = ((pydantic_val - satya_val) / pydantic_val) * 100
                if improvement > 0:
                    axs[i].text(j, max(pydantic_val, satya_val) * 1.1, 
                                f'{improvement:.1f}% faster', ha='center', 
                                color='green', fontweight='bold')
                else:
                    axs[i].text(j, max(pydantic_val, satya_val) * 1.1, 
                                f'{-improvement:.1f}% slower', ha='center', 
                                color='red', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/summary_comparison.png")
    plt.close()

def save_results_to_file(results: List[BenchmarkResult], output_dir: str = "benchmarks/results"):
    """Save benchmark results to a JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert results to dictionaries
    result_dicts = [r.to_dict() for r in results]
    
    # Save to JSON file
    with open(f"{output_dir}/benchmark_results.json", "w") as f:
        json.dump(result_dicts, f, indent=2)
    
    # Also save a summary CSV
    with open(f"{output_dir}/benchmark_summary.csv", "w") as f:
        # Write header
        f.write("Framework,Scenario,Operation,Avg Time (ms),Median Time (ms),Min Time (ms),Max Time (ms),StdDev (ms)\n")
        
        # Write data rows
        for r in results:
            f.write(f"{r.framework},{r.scenario},{r.operation},{r.avg_time * 1000:.4f},{r.median_time * 1000:.4f},{r.min_time * 1000:.4f},{r.max_time * 1000:.4f},{r.stddev_time * 1000:.4f}\n")

async def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Benchmark FastAPI with satya vs Pydantic")
    parser.add_argument("--iterations", type=int, default=NUM_ITERATIONS, help="Number of iterations")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY_LEVEL, help="Concurrency level")
    parser.add_argument("--output-dir", default="benchmarks/results", help="Output directory for results")
    parser.add_argument("--no-plot", action="store_true", help="Disable plot generation")
    parser.add_argument("--no-save", action="store_true", help="Disable saving results to file")
    args = parser.parse_args()
    
    # Update global parameters (without using global keyword here)
    # Variables are already defined at the module level
    NUM_ITERATIONS = args.iterations
    CONCURRENCY_LEVEL = args.concurrency
    PLOT_RESULTS = not args.no_plot
    SAVE_RESULTS = not args.no_save
    
    # Define operations to benchmark
    operations = ["create", "get"]
    
    print(f"Starting benchmark with {NUM_ITERATIONS} iterations and {CONCURRENCY_LEVEL} concurrency level")
    
    # Run benchmarks for both frameworks
    pydantic_results = await run_server_and_benchmark(
        "pydantic", TEST_SCENARIOS, operations, 
        BENCHMARK_PORT_PYDANTIC, f"{pydantic_app.__module__}:{pydantic_app.__name__}"
    )
    
    satya_results = await run_server_and_benchmark(
        "satya", TEST_SCENARIOS, operations, 
        BENCHMARK_PORT_SATYA, f"{satya_app.__module__}:{satya_app.__name__}"
    )
    
    # Combine results
    all_results = pydantic_results + satya_results
    
    # Generate plots if enabled
    if PLOT_RESULTS:
        print("Generating plots...")
        generate_plots(all_results, args.output_dir)
    
    # Save results to file if enabled
    if SAVE_RESULTS:
        print("Saving results to file...")
        save_results_to_file(all_results, args.output_dir)
    
    print("Benchmark completed!")
    print(f"Results saved to: {args.output_dir}")

if __name__ == "__main__":
    asyncio.run(main())
