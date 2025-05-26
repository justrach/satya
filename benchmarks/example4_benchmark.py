#!/usr/bin/env python3
import gc
import time
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from memory_profiler import memory_usage
import os
from typing import List, Dict, Optional, Union, Literal, Any
from datetime import datetime
from enum import Enum
from uuid import UUID
import random

# Ensure the results directory exists
os.makedirs('benchmarks/results', exist_ok=True)

# Benchmark configuration
N_ITEMS = 500_000  # Total number of items to validate (increased for more meaningful timing)
BATCH_SIZE = 10_000  # Process in batches of this size

class PublicationStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

def generate_complex_test_data(num_items):
    """
    Generate complex test data matching the User model from example4.py
    """
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Edward", "Fiona", "George", "Helen"]
    last_names = ["Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Thomas"]
    domains = ["example.com", "test.com", "benchmark.org", "sample.net", "demo.io"]
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego"]
    streets = ["Main Street", "Oak Avenue", "Park Road", "First Street", "Second Avenue", "Third Street", "Fourth Avenue"]
    platforms = ["twitter", "facebook", "linkedin", "github"]
    interests_pool = ["coding", "music", "sports", "reading", "gaming", "cooking", "travel", "photography", "art", "science"]
    
    data = []
    for i in range(num_items):
        # Generate basic user info
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        username = f"{first_name.lower()}_{last_name.lower()}_{i}"
        email = f"{username}@{random.choice(domains)}"
        
        # Generate address
        address = {
            "street": f"{random.randint(100, 9999)} {random.choice(streets)}",
            "city": random.choice(cities),
            "postal_code": f"{random.randint(10000, 99999)}",
            "country": "US",
            "location": {
                "latitude": round(random.uniform(-90, 90), 6),
                "longitude": round(random.uniform(-180, 180), 6)
            }
        }
        
        # Generate social profiles
        num_profiles = random.randint(1, 3)
        social_profiles = []
        selected_platforms = random.sample(platforms, num_profiles)
        for platform in selected_platforms:
            social_profiles.append({
                "platform": platform,
                "username": f"@{username}" if platform == "twitter" else username,
                "url": f"https://{platform}.com/{username}"
            })
        
        # Generate interests
        num_interests = random.randint(1, 5)
        interests = random.sample(interests_pool, num_interests)
        
        # Generate user data
        user_data = {
            "id": f"123e4567-e89b-12d3-a456-42661417{i:04d}",
            "username": username[:20],  # Ensure max length
            "email": email,
            "status": random.choice(["draft", "published", "archived"]),
            "age": random.randint(18, 65),
            "score": round(random.uniform(0, 100), 2),
            "address": address,
            "social_profiles": social_profiles,
            "interests": interests,
            "metadata": {
                "language": random.choice(["en", "es", "fr", "de"]),
                "theme": random.choice(["light", "dark"]),
                "notifications": random.choice([True, False])
            },
            "last_login": "2024-01-01T12:00:00Z" if random.choice([True, False]) else None
        }
        
        data.append(user_data)
    
    return data

def run_satya_benchmark():
    """Run validation benchmark using Satya with the complex User model"""
    from satya import Model, Field
    
    print("\nSatya Benchmark (Complex User Model):")
    
    # Define models (from example4.py)
    class GeoLocation(Model):
        latitude: float = Field(
            min_value=-90.0,
            max_value=90.0,
            description="Latitude coordinate"
        )
        longitude: float = Field(
            min_value=-180.0,
            max_value=180.0,
            description="Longitude coordinate"
        )

    class Address(Model):
        street: str = Field(
            min_length=5, 
            max_length=100,
            description="Street address"
        )
        city: str = Field(
            pattern=r'^[A-Za-z\s]+$',
            description="City name (letters only)"
        )
        postal_code: str = Field(
            pattern=r'^\d{5}(-\d{4})?$',
            description="US postal code format"
        )
        country: str = Field(
            min_length=2,
            max_length=2,
            description="Two-letter country code"
        )
        location: Optional[GeoLocation] = Field(
            required=False,
            description="Geographic coordinates"
        )

    class SocialMedia(Model):
        platform: Literal["twitter", "facebook", "linkedin", "github"] = Field(
            description="Social media platform"
        )
        username: str = Field(
            pattern=r'^@?[a-zA-Z0-9_]+$',
            description="Social media handle"
        )
        url: str = Field(
            url=True,
            description="Profile URL"
        )

    class User(Model):
        id: str = Field(
            pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            description="User UUID v4"
        )
        username: str = Field(
            min_length=3,
            max_length=20,
            pattern=r'^[a-zA-Z0-9_]+$',
            description="Username (alphanumeric and underscore)"
        )
        email: str = Field(
            email=True,
            description="Valid email address"
        )
        status: PublicationStatus = Field(
            description="User account status"
        )
        age: int = Field(
            min_value=13,
            max_value=120,
            description="User age (13-120)"
        )
        score: float = Field(
            min_value=0.0,
            max_value=100.0,
            description="User score (0-100)"
        )
        address: Address = Field(
            description="User's address"
        )
        social_profiles: List[SocialMedia] = Field(
            min_length=0,
            max_length=5,
            description="Social media profiles"
        )
        interests: List[str] = Field(
            min_length=1,
            max_length=5,
            description="List of interests (1-5 items)"
        )
        metadata: Dict[str, Any] = Field(
            description="Additional user metadata"
        )
        last_login: Optional[datetime] = Field(
            required=False,
            description="Last login timestamp"
        )
    
    # Generate test data
    test_data = generate_complex_test_data(N_ITEMS)
    
    # Measure single item validation time
    start_time = time.time()
    User(**test_data[0])
    single_time = time.time() - start_time
    print(f"Single item validation: {single_time*1000:.2f}ms")
    
    # Benchmark memory and time
    def run_validation():
        validator = User.validator()
        validated = 0
        for i in range(0, N_ITEMS, BATCH_SIZE):
            batch = test_data[i:i+BATCH_SIZE]
            for item in batch:
                result = validator.validate(item)
                if not result.is_valid:
                    print(f"Validation failed: {result.errors}")
            validated += len(batch)
            if validated % 100_000 == 0:
                print(f"Processed {validated:,} items...")
    
    # Run with memory profiling
    mem_usage = memory_usage((run_validation, (), {}), interval=0.1)
    
    # Run validation again to measure time accurately
    start_time = time.time()
    validator = User.validator()
    validated = 0
    for i in range(0, N_ITEMS, BATCH_SIZE):
        batch = test_data[i:i+BATCH_SIZE]
        for item in batch:
            validator.validate(item)
        validated += len(batch)
        if validated % 100_000 == 0:
            pass  # don't print to avoid affecting time measurement
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate items per second
    items_per_second = N_ITEMS / total_time
    
    # Calculate peak memory usage
    peak_memory = max(mem_usage)
    base_memory = min(mem_usage)
    memory_used = peak_memory - base_memory
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Items per second: {int(items_per_second):,}")
    print(f"Peak memory usage: {memory_used:.1f}MB")
    
    return total_time, memory_used, items_per_second

def run_msgspec_benchmark():
    """Run validation benchmark using msgspec with the complex User model"""
    import msgspec
    from typing import Optional
    
    print("\nmsgspec Benchmark (Complex User Model):")
    
    # Define models for msgspec
    class GeoLocation(msgspec.Struct):
        latitude: float
        longitude: float

    class Address(msgspec.Struct):
        street: str
        city: str
        postal_code: str
        country: str
        location: Optional[GeoLocation] = None

    class SocialMedia(msgspec.Struct):
        platform: Literal["twitter", "facebook", "linkedin", "github"]
        username: str
        url: str

    class User(msgspec.Struct):
        id: str
        username: str
        email: str
        status: str  # msgspec doesn't have built-in enum validation
        age: int
        score: float
        address: Address
        social_profiles: List[SocialMedia]
        interests: List[str]
        metadata: Dict[str, Any]
        last_login: Optional[str] = None  # msgspec handles datetime as string
    
    # Generate test data
    test_data = generate_complex_test_data(N_ITEMS)
    
    # Measure single item validation time
    start_time = time.time()
    msgspec.convert(test_data[0], User)
    single_time = time.time() - start_time
    print(f"Single item validation: {single_time*1000:.2f}ms")
    
    # Benchmark memory and time
    def run_validation():
        validated = 0
        for i in range(0, N_ITEMS, BATCH_SIZE):
            batch = test_data[i:i+BATCH_SIZE]
            for item in batch:
                try:
                    msgspec.convert(item, User)
                except Exception as e:
                    print(f"Validation failed: {e}")
            validated += len(batch)
            if validated % 100_000 == 0:
                print(f"Processed {validated:,} items...")
    
    # Run with memory profiling
    mem_usage = memory_usage((run_validation, (), {}), interval=0.1)
    
    # Run validation again to measure time accurately
    start_time = time.time()
    validated = 0
    for i in range(0, N_ITEMS, BATCH_SIZE):
        batch = test_data[i:i+BATCH_SIZE]
        for item in batch:
            msgspec.convert(item, User)
        validated += len(batch)
        if validated % 100_000 == 0:
            pass  # don't print to avoid affecting time measurement
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate items per second
    items_per_second = N_ITEMS / total_time
    
    # Calculate peak memory usage
    peak_memory = max(mem_usage)
    base_memory = min(mem_usage)
    memory_used = peak_memory - base_memory
    
    print(f"Total time: {total_time:.2f}s")
    print(f"Items per second: {int(items_per_second):,}")
    print(f"Peak memory usage: {memory_used:.1f}MB")
    
    return total_time, memory_used, items_per_second

def create_visualization(results):
    """
    Create a bar chart showing validation speed comparison between Satya and msgspec.
    
    Args:
        results: Dictionary containing benchmark results
    """
    # Set style
    plt.style.use('ggplot')
    mpl.rcParams['font.family'] = 'sans-serif'
    mpl.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif']
    
    # Extract data
    libraries = ['Satya', 'msgspec']
    validation_speeds = [
        results['satya_ips'],
        results['msgspec_ips']
    ]
    
    # Create a color palette
    colors = ['#FF5757', '#4CAF50']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Create bars
    bars = ax.bar(libraries, validation_speeds, color=colors, width=0.5, edgecolor='white', linewidth=1)
    
    # Add values on bars
    for bar, speed in zip(bars, validation_speeds):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + max(validation_speeds) * 0.01,
                f'{int(speed):,} items/s',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Customize plot
    ax.set_title('Complex Model Validation Speed: Satya vs msgspec\n(User Model from example4.py)', 
                fontsize=16, fontweight='bold', pad=20)
    ax.set_ylabel('Items per second', fontsize=14, fontweight='bold')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add comparison text
    satya_vs_msgspec = results['satya_ips'] / results['msgspec_ips']
    
    textstr = f'Satya vs msgspec: {satya_vs_msgspec:.1f}x {"faster" if satya_vs_msgspec > 1 else "slower"}'
    
    props = dict(boxstyle='round', facecolor='white', alpha=0.8)
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=12,
            verticalalignment='top', bbox=props)
    
    # Adjust layout and save
    plt.tight_layout()
    output_path = 'benchmarks/results/example4_satya_vs_msgspec.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nValidation speed chart saved to '{output_path}'")
    
    # Create memory usage comparison
    plt.figure(figsize=(10, 6))
    
    memory_usage_values = [results['satya_mem'], results['msgspec_mem']]
    bars = plt.bar(libraries, memory_usage_values, color=colors, width=0.5, edgecolor='white', linewidth=1)
    
    # Add values on bars
    for bar, mem in zip(bars, memory_usage_values):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + max(memory_usage_values) * 0.01,
                f'{mem:.1f}MB',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Customize plot
    plt.title('Memory Usage Comparison: Satya vs msgspec\n(Complex User Model)', 
             fontsize=16, fontweight='bold')
    plt.ylabel('Memory Usage (MB)', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.gca().set_axisbelow(True)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Adjust layout and save
    plt.tight_layout()
    mem_output_path = 'benchmarks/results/example4_memory_comparison.png'
    plt.savefig(mem_output_path, dpi=300, bbox_inches='tight')
    print(f"Memory usage chart saved to '{mem_output_path}'")

if __name__ == "__main__":
    print(f"Running complex model validation benchmark with {N_ITEMS:,} items...")
    print(f"Batch size: {BATCH_SIZE:,}")
    print("Using the complex User model from example4.py")
    
    # Force garbage collection before each benchmark
    gc.collect()
    
    # Run benchmarks
    satya_time, satya_mem, satya_ips = run_satya_benchmark()
    
    gc.collect()
    msgspec_time, msgspec_mem, msgspec_ips = run_msgspec_benchmark()
    
    # Print comparison table
    print("\nComplex Model Validation Comparison:")
    print("                         Satya      msgspec")
    print("------------------------------------------")
    print(f"Total time (s)           {satya_time:.2f}        {msgspec_time:.2f}")
    print(f"Memory usage (MB)        {satya_mem:.1f}        {msgspec_mem:.1f}")
    print(f"Items/second            {int(satya_ips):,}      {int(msgspec_ips):,}")
    
    # Print relative performance
    print("\nRelative Performance:")
    print("-------------------------------")
    if satya_ips > msgspec_ips:
        print(f"Satya is {satya_ips/msgspec_ips:.1f}x faster than msgspec")
    else:
        print(f"msgspec is {msgspec_ips/satya_ips:.1f}x faster than Satya")
    
    # Handle memory comparison more carefully
    if satya_mem > 0 and msgspec_mem > 0:
        if satya_mem < msgspec_mem:
            print(f"Satya uses {msgspec_mem/satya_mem:.1f}x less memory than msgspec")
        else:
            print(f"msgspec uses {satya_mem/msgspec_mem:.1f}x less memory than Satya")
    elif satya_mem > 0 and msgspec_mem == 0:
        print(f"msgspec uses minimal memory compared to Satya ({satya_mem:.1f}MB)")
    elif msgspec_mem > 0 and satya_mem == 0:
        print(f"Satya uses minimal memory compared to msgspec ({msgspec_mem:.1f}MB)")
    else:
        print("Both libraries use minimal memory for this benchmark")
    
    # Save results
    results = {
        'satya_time': satya_time,
        'satya_mem': satya_mem,
        'satya_ips': satya_ips,
        'msgspec_time': msgspec_time,
        'msgspec_mem': msgspec_mem,
        'msgspec_ips': msgspec_ips
    }
    
    # Save results to JSON
    with open('benchmarks/results/example4_benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to 'benchmarks/results/example4_benchmark_results.json'")
    
    # Create visualizations
    create_visualization(results) 