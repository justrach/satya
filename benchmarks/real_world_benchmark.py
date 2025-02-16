import requests
import time
from satya import Model, Field
from pydantic import BaseModel, Field as PydanticField
from typing import List, Dict, Optional
from datetime import datetime
import statistics
import concurrent.futures
from ratelimit import limits, sleep_and_retry
import json

# Models for GitHub API
class SatyaGitHubUser(Model):
    login: str = Field()
    id: int = Field()
    type: str = Field()
    site_admin: bool = Field()
    name: Optional[str] = Field(required=False)
    company: Optional[str] = Field(required=False)
    blog: Optional[str] = Field(required=False)
    location: Optional[str] = Field(required=False)
    email: Optional[str] = Field(required=False, email=True)
    bio: Optional[str] = Field(required=False)
    public_repos: int = Field(min_value=0)
    followers: int = Field(min_value=0)
    following: int = Field(min_value=0)
    created_at: datetime = Field()
    updated_at: datetime = Field()

class PydanticGitHubUser(BaseModel):
    login: str
    id: int
    type: str
    site_admin: bool
    name: Optional[str] = None
    company: Optional[str] = None
    blog: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    public_repos: int = PydanticField(ge=0)
    followers: int = PydanticField(ge=0)
    following: int = PydanticField(ge=0)
    created_at: datetime
    updated_at: datetime

# Models for JSONPlaceholder API
class SatyaPost(Model):
    userId: int = Field(min_value=1)
    id: int = Field(min_value=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)

class PydanticPost(BaseModel):
    userId: int = PydanticField(gt=0)
    id: int = PydanticField(gt=0)
    title: str = PydanticField(min_length=1)
    body: str = PydanticField(min_length=1)

# Rate limiting decorators
@sleep_and_retry
@limits(calls=30, period=60)  # GitHub API limit
def fetch_github_user(username: str) -> dict:
    response = requests.get(f"https://api.github.com/users/{username}")
    response.raise_for_status()
    return response.json()

@sleep_and_retry
@limits(calls=100, period=60)  # JSONPlaceholder limit
def fetch_post(post_id: int) -> dict:
    response = requests.get(f"https://jsonplaceholder.typicode.com/posts/{post_id}")
    response.raise_for_status()
    return response.json()

def benchmark_github_validation(usernames: List[str], model_class, batch_size: int = 1):
    """Benchmark validation of GitHub user data"""
    times = []
    data = []
    
    # Fetch data first
    print(f"Fetching {len(usernames)} GitHub profiles...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        data = list(executor.map(fetch_github_user, usernames))
    
    # Validation benchmark
    if hasattr(model_class, 'validator'):  # Satya
        validator = model_class.validator()
        validator.set_batch_size(batch_size)
        
        start = time.perf_counter()
        for _ in validator.validate_stream(data):
            pass
        end = time.perf_counter()
        times.append(end - start)
    else:  # Pydantic
        start = time.perf_counter()
        for item in data:
            model_class(**item)
        end = time.perf_counter()
        times.append(end - start)
    
    return {
        "avg_time": statistics.mean(times),
        "data_size": len(data),
        "ops_per_sec": len(data) / statistics.mean(times)
    }

def benchmark_posts_validation(post_count: int, model_class, batch_size: int = 1):
    """Benchmark validation of JSONPlaceholder posts"""
    times = []
    data = []
    
    # Fetch data first
    print(f"Fetching {post_count} posts...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        data = list(executor.map(fetch_post, range(1, post_count + 1)))
    
    # Validation benchmark
    if hasattr(model_class, 'validator'):  # Satya
        validator = model_class.validator()
        validator.set_batch_size(batch_size)
        
        start = time.perf_counter()
        for _ in validator.validate_stream(data):
            pass
        end = time.perf_counter()
        times.append(end - start)
    else:  # Pydantic
        start = time.perf_counter()
        for item in data:
            model_class(**item)
        end = time.perf_counter()
        times.append(end - start)
    
    return {
        "avg_time": statistics.mean(times),
        "data_size": len(data),
        "ops_per_sec": len(data) / statistics.mean(times)
    }

def main():
    # Test configurations
    github_usernames = [
        "torvalds", "gvanrossum", "antirez", "fabpot", "dhh",
        "wycats", "tenderlove", "defunkt", "mojombo", "matz"
    ]
    post_counts = [10, 50, 100]
    batch_sizes = [1, 5, 10]
    
    results = {
        "github": {},
        "posts": {}
    }
    
    # GitHub API benchmarks
    print("\nRunning GitHub API Benchmarks...")
    for batch_size in batch_sizes:
        results["github"][f"satya_{batch_size}"] = benchmark_github_validation(
            github_usernames, SatyaGitHubUser, batch_size
        )
    
    results["github"]["pydantic"] = benchmark_github_validation(
        github_usernames, PydanticGitHubUser
    )
    
    # JSONPlaceholder API benchmarks
    print("\nRunning Posts API Benchmarks...")
    for count in post_counts:
        results["posts"][f"count_{count}"] = {
            "satya": {},
            "pydantic": None
        }
        
        for batch_size in batch_sizes:
            results["posts"][f"count_{count}"]["satya"][f"batch_{batch_size}"] = \
                benchmark_posts_validation(count, SatyaPost, batch_size)
        
        results["posts"][f"count_{count}"]["pydantic"] = \
            benchmark_posts_validation(count, PydanticPost)
    
    # Print results
    print("\nGitHub API Results:")
    print("=" * 80)
    for key, value in results["github"].items():
        print(f"{key:>20}: {value['ops_per_sec']:>10.2f} ops/sec "
              f"(avg: {value['avg_time']*1000:>8.2f}ms)")
    
    print("\nPosts API Results:")
    print("=" * 80)
    for count_key, count_data in results["posts"].items():
        print(f"\n{count_key}:")
        for framework, framework_data in count_data.items():
            if framework == "satya":
                for batch_key, batch_data in framework_data.items():
                    print(f"{framework} {batch_key:>12}: "
                          f"{batch_data['ops_per_sec']:>10.2f} ops/sec "
                          f"(avg: {batch_data['avg_time']*1000:>8.2f}ms)")
            else:
                print(f"{framework:>20}: "
                      f"{framework_data['ops_per_sec']:>10.2f} ops/sec "
                      f"(avg: {framework_data['avg_time']*1000:>8.2f}ms)")
    
    # Save results
    with open("real_world_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main() 