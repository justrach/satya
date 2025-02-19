import requests
import json
import time
from satya import Model, Field
from pydantic import BaseModel, Field as PydanticField
from typing import List, Dict, Optional
import os
from datetime import datetime
import dotenv
from satya.openai import OpenAISchema  # Import the new adapter

dotenv.load_dotenv()
print(os.getenv("OPENAI_API_KEY"))
# Satya Models for OpenAI API
class MathStep(Model):
    explanation: str = Field(min_length=1)
    output: str = Field(min_length=1)

class MathResponse(Model):
    steps: List[MathStep] = Field(min_length=1)
    final_answer: str = Field(min_length=1)

# Pydantic Models for OpenAI API
class PydanticMathStep(BaseModel):
    explanation: str = PydanticField(min_length=1)
    output: str = PydanticField(min_length=1)

class PydanticMathResponse(BaseModel):
    steps: List[PydanticMathStep] = PydanticField(min_items=1)
    final_answer: str = PydanticField(min_length=1)

def fetch_openai_response(prompt: str, api_key: str) -> dict:
    """Fetch response from OpenAI API using model's schema"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful math tutor. Guide the user through the solution step by step."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "response_format": OpenAISchema.response_format(MathResponse, "math_reasoning")
    }
    
    print("Request payload:", json.dumps(data, indent=2))
    
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data
    )
    
    if not response.ok:
        print("Error response:", response.text)
    response.raise_for_status()
    
    return response.json()["choices"][0]["message"]["content"]

def benchmark_validation(responses: List[dict], model_class, batch_size: int = 1):
    """Benchmark validation performance"""
    times = []
    
    # Warm-up run
    if hasattr(model_class, 'validator'):  # Satya
        validator = model_class.validator()
        validator.set_batch_size(batch_size)
        for _ in validator.validate_stream(responses[:2]):
            pass
    else:  # Pydantic
        for item in responses[:2]:
            model_class(**item)
    
    # Actual benchmark
    for _ in range(5):  # Run 5 times for average
        start = time.perf_counter()
        
        if hasattr(model_class, 'validator'):  # Satya
            validator = model_class.validator()
            validator.set_batch_size(batch_size)
            for _ in validator.validate_stream(responses):
                pass
        else:  # Pydantic
            for item in responses:
                model_class(**item)
        
        end = time.perf_counter()
        times.append(end - start)
    
    return {
        "avg_time": sum(times) / len(times),
        "ops_per_sec": len(responses) / (sum(times) / len(times))
    }

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    # Test configurations with larger datasets
    math_problems = [
        "solve 8x + 7 = -23",
        "solve 2x - 5 = 11",
        "solve 3x + 4 = 16",
        "solve 5x - 2 = 18",
        "solve 4x + 9 = -7"
    ]
    
    # Fetch initial responses
    print("Fetching responses from OpenAI API...")
    base_responses = []
    for problem in math_problems:
        response = fetch_openai_response(problem, api_key)
        base_responses.append(json.loads(response))
    
    # Create larger dataset by duplicating responses
    responses = base_responses * 200  # 1000 items total
    
    # Test configurations
    batch_sizes = [1, 10, 50, 100, 500]
    iterations = 10  # More iterations for better averaging
    
    results = {
        "satya": {},
        "pydantic": None,
        "dataset_size": len(responses)
    }
    
    # Benchmark Satya with different batch sizes
    print(f"\nBenchmarking Satya with {len(responses)} items...")
    for batch_size in batch_sizes:
        results["satya"][f"batch_{batch_size}"] = benchmark_validation(
            responses, MathResponse, batch_size
        )
    
    # Benchmark Pydantic
    print(f"\nBenchmarking Pydantic with {len(responses)} items...")
    results["pydantic"] = benchmark_validation(
        responses, PydanticMathResponse
    )
    
    # Print results
    print("\nResults:")
    print("=" * 60)
    print(f"Dataset size: {len(responses)} items")
    print("-" * 60)
    
    for batch_size, metrics in results["satya"].items():
        print(f"Satya ({batch_size})")
        print(f"  Ops/sec: {metrics['ops_per_sec']:,.2f}")
        print(f"  Avg time: {metrics['avg_time']*1000:.2f}ms")
        print(f"  Throughput: {metrics['ops_per_sec']/1000:,.2f}K items/sec")
    
    print("\nPydantic")
    print(f"  Ops/sec: {results['pydantic']['ops_per_sec']:,.2f}")
    print(f"  Avg time: {results['pydantic']['avg_time']*1000:.2f}ms")
    print(f"  Throughput: {results['pydantic']['ops_per_sec']/1000:,.2f}K items/sec")
    
    # Calculate speedup ratios
    best_satya = max(m["ops_per_sec"] for m in results["satya"].values())
    speedup = best_satya / results["pydantic"]["ops_per_sec"]
    print(f"\nBest Satya speedup vs Pydantic: {speedup:.2f}x")
    
    # Save results
    with open("openai_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main() 