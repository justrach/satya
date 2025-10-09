#!/usr/bin/env python3
"""
⚡ Satya Ultra-Fast API Showcase
=================================

Demonstrates the performance gains from using Satya's optimized APIs.
"""

from satya import BaseModel as SatyaModel
from pydantic import BaseModel as PydanticModel
import time

# Define models
class SatyaUser(SatyaModel):
    name: str
    age: int
    email: str

class PydanticUser(PydanticModel):
    name: str
    age: int
    email: str

def run_benchmarks():
    # Generate test data
    data_small = [{'name': f'User{i}', 'age': 20+i%60, 'email': f'user{i}@example.com'} for i in range(10000)]
    data_large = [{'name': f'User{i}', 'age': 20+i%60, 'email': f'user{i}@example.com'} for i in range(50000)]
    
    print("=" * 80)
    print("⚡ SATYA ULTRA-FAST API SHOWCASE")
    print("=" * 80)
    print()
    
    # ===== SINGLE OBJECT =====
    print("📊 TEST 1: Single Object Validation (10,000 records)")
    print("-" * 80)
    
    # Pydantic
    start = time.perf_counter()
    pydantic_users = [PydanticUser(**d) for d in data_small]
    pydantic_time = time.perf_counter() - start
    pydantic_speed = len(pydantic_users) / pydantic_time
    
    # Satya regular
    start = time.perf_counter()
    satya_regular = [SatyaUser(**d) for d in data_small]
    satya_regular_time = time.perf_counter() - start
    satya_regular_speed = len(satya_regular) / satya_regular_time
    
    # Satya FAST
    start = time.perf_counter()
    satya_fast = [SatyaUser.model_validate_fast(d) for d in data_small]
    satya_fast_time = time.perf_counter() - start
    satya_fast_speed = len(satya_fast) / satya_fast_time
    
    print(f"  Pydantic:           {pydantic_speed:>10,.0f} ops/sec  (baseline)")
    print(f"  Satya (regular):    {satya_regular_speed:>10,.0f} ops/sec  ({satya_regular_speed/pydantic_speed:>5.2f}×)")
    print(f"  Satya (fast):       {satya_fast_speed:>10,.0f} ops/sec  ({satya_fast_speed/pydantic_speed:>5.2f}×) ⚡")
    print()
    
    # ===== BATCH =====
    print("📊 TEST 2: Batch Validation (50,000 records)")
    print("-" * 80)
    
    # Pydantic
    start = time.perf_counter()
    pydantic_batch = [PydanticUser(**d) for d in data_large]
    pydantic_batch_time = time.perf_counter() - start
    pydantic_batch_speed = len(pydantic_batch) / pydantic_batch_time
    
    # Satya batch
    start = time.perf_counter()
    satya_batch = SatyaUser.validate_many(data_large)
    satya_batch_time = time.perf_counter() - start
    satya_batch_speed = len(satya_batch) / satya_batch_time
    
    print(f"  Pydantic:           {pydantic_batch_speed:>10,.0f} ops/sec  (baseline)")
    print(f"  Satya (batch):      {satya_batch_speed:>10,.0f} ops/sec  ({satya_batch_speed/pydantic_batch_speed:>5.2f}×) 🚀")
    print()
    
    # ===== FIELD ACCESS =====
    print("📊 TEST 3: Field Access Performance")
    print("-" * 80)
    
    pydantic_obj = pydantic_users[0]
    satya_obj = satya_fast[0]
    
    iterations = 1000000
    
    # Pydantic field access
    start = time.perf_counter()
    for _ in range(iterations):
        _ = pydantic_obj.name
        _ = pydantic_obj.age
        _ = pydantic_obj.email
    pydantic_access_time = time.perf_counter() - start
    pydantic_access_speed = (iterations * 3) / pydantic_access_time
    
    # Satya field access
    start = time.perf_counter()
    for _ in range(iterations):
        _ = satya_obj.name
        _ = satya_obj.age
        _ = satya_obj.email
    satya_access_time = time.perf_counter() - start
    satya_access_speed = (iterations * 3) / satya_access_time
    
    print(f"  Pydantic:           {pydantic_access_speed:>10,.0f} accesses/sec")
    print(f"  Satya (native):     {satya_access_speed:>10,.0f} accesses/sec  ({satya_access_speed/pydantic_access_speed:>5.2f}×)")
    print()
    
    # ===== SUMMARY =====
    print("=" * 80)
    print("🎯 SUMMARY")
    print("=" * 80)
    print()
    print(f"✅ Single-object (model_validate_fast): {satya_fast_speed/pydantic_speed:.2f}× Pydantic")
    print(f"✅ Batch validation (validate_many):    {satya_batch_speed/pydantic_batch_speed:.1f}× Pydantic")
    print(f"✅ Field access (NativeModel):          {satya_access_speed/pydantic_access_speed:.2f}× Pydantic")
    print()
    print("📖 Usage:")
    print("  # Single object - ultra fast")
    print("  user = User.model_validate_fast({'name': 'Alice', 'age': 30})")
    print()
    print("  # Batch - 10-40× faster")
    print("  users = User.validate_many(list_of_dicts)")
    print()
    print("  # Regular (backwards compatible)")
    print("  user = User(**data)")
    print()
    print("=" * 80)

if __name__ == '__main__':
    run_benchmarks()
