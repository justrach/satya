#!/usr/bin/env python3
"""
Comprehensive Benchmark: Satya vs msgspec using Ultra-Complex Model
===================================================================

This benchmark compares Satya and msgspec using the most comprehensive validation
model (ComprehensiveEntity) from example5.py, which includes:

- 25+ top-level fields with deep nesting (4+ levels)
- All validation types: email, URL, patterns, ranges, enums, literals
- Complex nested models with UUID validation, datetime handling
- Arrays with constraints (min/max items, unique items)
- Decimal precision handling
- Multiple enum types and literal constraints
- Optional fields and Union types
- Healthcare, financial, and security data validation

This represents the most comprehensive validation scenario possible with Satya.
"""

import time
import json
import sys
import os
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime, date
from uuid import uuid4
import random
import string

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import Satya
from examples.example5 import ComprehensiveEntity, Priority, Status, Currency, Protocol

# Import msgspec for comparison
try:
    import msgspec
    from msgspec import Struct
    MSGSPEC_AVAILABLE = True
except ImportError:
    print("⚠️  msgspec not available. Install with: pip install msgspec")
    MSGSPEC_AVAILABLE = False

# Memory profiling
try:
    from memory_profiler import profile, memory_usage
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    print("⚠️  memory_profiler not available. Install with: pip install memory-profiler")
    MEMORY_PROFILER_AVAILABLE = False

# Plotting
try:
    import matplotlib.pyplot as plt
    import numpy as np
    PLOTTING_AVAILABLE = True
except ImportError:
    print("⚠️  matplotlib not available. Install with: pip install matplotlib")
    PLOTTING_AVAILABLE = False


class MsgspecComprehensiveEntity(Struct):
    """Simplified msgspec version of ComprehensiveEntity for comparison"""
    # Note: msgspec doesn't support the same level of validation as Satya
    # This is a basic structure comparison only
    
    entity_id: str
    entity_type: str
    created_timestamp: str
    last_updated: str
    
    # Simplified nested structures (msgspec doesn't support deep validation)
    personal_info: Dict[str, Any]
    primary_address: Dict[str, Any]
    secondary_addresses: List[Dict[str, Any]]
    contact_methods: List[Dict[str, Any]]
    security: Dict[str, Any]
    financial_profiles: List[Dict[str, Any]]
    system_configs: Dict[str, Dict[str, Any]]
    documents: List[Dict[str, Any]]
    projects: List[Dict[str, Any]]
    healthcare_records: List[Dict[str, Any]]
    
    nested_metadata: Dict[str, Dict[str, List[Dict[str, Any]]]]
    priority_scores: List[float]
    related_entity_ids: List[str]
    verification_codes: List[str]
    status_history: List[str]
    advanced_settings: Dict[str, Any]
    coordinates_3d: List[float]
    theme_colors: List[str]
    schema_version: str
    compliance_flags: Dict[str, bool]
    performance_metrics: Dict[str, float]


def generate_comprehensive_test_data(count: int) -> List[Dict[str, Any]]:
    """Generate comprehensive test data matching the ComprehensiveEntity schema"""
    
    def random_string(length: int, pattern: str = None) -> str:
        if pattern == "alpha":
            return ''.join(random.choices(string.ascii_letters, k=length))
        elif pattern == "alnum":
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        elif pattern == "hex":
            return ''.join(random.choices('0123456789abcdef', k=length))
        else:
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def random_email() -> str:
        domains = ["example.com", "test.org", "demo.net", "sample.io"]
        return f"{random_string(8, 'alnum').lower()}@{random.choice(domains)}"
    
    def random_phone() -> str:
        return f"+1{random.randint(1000000000, 9999999999)}"
    
    def random_uuid() -> str:
        return str(uuid4())
    
    def random_datetime() -> str:
        base = datetime(2020, 1, 1)
        random_days = random.randint(0, 1460)  # 4 years
        return (base + timedelta(days=random_days)).isoformat() + "Z"
    
    def random_date() -> str:
        base = date(1980, 1, 1)
        random_days = random.randint(0, 15000)  # ~40 years
        return (base + timedelta(days=random_days)).isoformat()
    
    from datetime import timedelta
    
    data = []
    for i in range(count):
        entity = {
            "entity_id": random_uuid(),
            "entity_type": random.choice(["person", "organization", "system", "project"]),
            "created_timestamp": random_datetime(),
            "last_updated": random_datetime(),
            
            "personal_info": {
                "first_name": random_string(random.randint(3, 20), "alpha"),
                "middle_name": random_string(random.randint(3, 15), "alpha") if random.random() > 0.3 else None,
                "last_name": random_string(random.randint(3, 25), "alpha"),
                "date_of_birth": random_date(),
                "social_security_number": f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}" if random.random() > 0.2 else None,
                "passport_number": random_string(random.randint(6, 12), "alnum").upper() if random.random() > 0.4 else None,
                "driver_license": random_string(random.randint(8, 20), "alnum").upper() if random.random() > 0.3 else None,
                "nationality": random.choice(["US", "CA", "GB", "DE", "FR", "JP", "AU"]),
                "gender": random.choice(["M", "F", "O", "N"]),
                "emergency_contacts": [
                    {
                        "email": random_email(),
                        "phone": random_phone(),
                        "website": f"https://{random_string(10, 'alnum').lower()}.com"
                    }
                ]
            },
            
            "primary_address": {
                "street_address": f"{random.randint(1, 9999)} {random_string(10, 'alpha')} Street",
                "apartment": f"Apt {random.randint(1, 999)}" if random.random() > 0.5 else None,
                "city": random_string(random.randint(5, 20), "alpha"),
                "state_province": random_string(random.randint(5, 15), "alpha"),
                "postal_code": f"{random.randint(10000, 99999)}",
                "country_code": random.choice(["US", "CA", "GB", "DE", "FR"]),
                "latitude": round(random.uniform(-90, 90), 6) if random.random() > 0.3 else None,
                "longitude": round(random.uniform(-180, 180), 6) if random.random() > 0.3 else None
            },
            
            "secondary_addresses": [],
            
            "contact_methods": [
                {
                    "email": random_email(),
                    "phone": random_phone(),
                    "website": f"https://{random_string(12, 'alnum').lower()}.com"
                }
            ],
            
            "security": {
                "username": random_string(random.randint(5, 20), "alnum").lower(),
                "password_hash": random_string(64, "hex"),
                "salt": random_string(32, "hex"),
                "api_key": random_string(random.randint(32, 64), "alnum") if random.random() > 0.4 else None,
                "two_factor_enabled": random.choice([True, False]),
                "security_questions": [
                    f"Question {i}?" for i in range(random.randint(2, 5))
                ],
                "allowed_ip_ranges": [
                    f"192.168.{random.randint(1, 255)}.0/24" for _ in range(random.randint(0, 3))
                ]
            },
            
            "financial_profiles": [
                {
                    "account_number": str(random.randint(10**10, 10**16)),
                    "routing_number": str(random.randint(100000000, 999999999)),
                    "credit_card": f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}" if random.random() > 0.3 else None,
                    "cvv": str(random.randint(100, 999)) if random.random() > 0.3 else None,
                    "currency": random.choice(["USD", "EUR", "GBP", "JPY"]),
                    "balance": str(Decimal(f"{random.randint(0, 100000)}.{random.randint(0, 99):02d}")),
                    "credit_limit": str(Decimal(f"{random.randint(1000, 50000)}.00")) if random.random() > 0.4 else None,
                    "transaction_history": []
                }
            ] if random.random() > 0.2 else [],
            
            "system_configs": {
                "production": {
                    "hostname": f"{random_string(8, 'alnum').lower()}.example.com",
                    "ip_address": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
                    "ipv6_address": f"2001:0db8:85a3:0000:0000:8a2e:0370:{random.randint(1000, 9999):04x}" if random.random() > 0.5 else None,
                    "mac_address": f"{random_string(2, 'hex').upper()}:{random_string(2, 'hex').upper()}:{random_string(2, 'hex').upper()}:{random_string(2, 'hex').upper()}:{random_string(2, 'hex').upper()}:{random_string(2, 'hex').upper()}",
                    "port_number": random.randint(1, 65535),
                    "protocol": random.choice(["http", "https", "ftp", "sftp"]),
                    "ssl_enabled": random.choice([True, False]),
                    "timeout_seconds": random.randint(1, 300),
                    "max_connections": random.randint(10, 5000),
                    "environment_variables": {
                        "ENV": random.choice(["production", "staging", "development"]),
                        "DEBUG": str(random.choice([True, False])).lower()
                    }
                }
            },
            
            "documents": [
                {
                    "filename": f"document_{i}.{random.choice(['pdf', 'docx', 'txt', 'json'])}",
                    "file_size_bytes": random.randint(1024, 10485760),
                    "mime_type": random.choice(["application/pdf", "application/json", "text/plain"]),
                    "checksum_md5": random_string(32, "hex"),
                    "checksum_sha256": random_string(64, "hex"),
                    "created_at": random_datetime(),
                    "modified_at": random_datetime(),
                    "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                    "tags": [f"tag{j}" for j in range(random.randint(0, 5))],
                    "permissions": {
                        "admin": ["read", "write"],
                        "user": ["read"]
                    }
                }
            ] if random.random() > 0.3 else [],
            
            "projects": [
                {
                    "project_id": random_uuid(),
                    "project_name": f"Project {random_string(8, 'alpha')}",
                    "description": f"This is a sample project description with {random.randint(50, 200)} characters of text.",
                    "priority": random.choice(["low", "medium", "high", "critical"]),
                    "status": random.choice(["active", "inactive", "pending", "suspended"]),
                    "start_date": random_date(),
                    "end_date": random_date() if random.random() > 0.3 else None,
                    "budget": str(Decimal(f"{random.randint(1000, 1000000)}.00")),
                    "team_members": [random_uuid() for _ in range(random.randint(1, 10))],
                    "milestones": [{"name": f"Milestone {j}", "date": random_date()} for j in range(random.randint(0, 5))],
                    "dependencies": [random_uuid() for _ in range(random.randint(0, 3))],
                    "risk_assessment": {
                        "overall_risk": random.choice(["low", "medium", "high"]),
                        "score": round(random.uniform(1.0, 10.0), 2)
                    }
                }
            ] if random.random() > 0.4 else [],
            
            "healthcare_records": [
                {
                    "patient_id": random_uuid(),
                    "medical_record_number": f"MRN{random.randint(10**8, 10**12)}",
                    "blood_type": random.choice(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]),
                    "height_cm": round(random.uniform(150.0, 200.0), 1),
                    "weight_kg": round(random.uniform(50.0, 120.0), 1),
                    "allergies": [f"allergy_{j}" for j in range(random.randint(0, 5))],
                    "medications": [{"name": f"Med{j}", "dosage": f"{random.randint(1, 500)}mg"} for j in range(random.randint(0, 5))],
                    "medical_conditions": [f"condition_{j}" for j in range(random.randint(0, 3))],
                    "emergency_contact": {
                        "email": random_email(),
                        "phone": random_phone(),
                        "website": f"https://emergency{random.randint(1, 1000)}.com"
                    },
                    "insurance_policy_number": random_string(random.randint(10, 15), "alnum").upper(),
                    "last_visit": random_datetime(),
                    "next_appointment": random_datetime() if random.random() > 0.4 else None
                }
            ] if random.random() > 0.6 else [],
            
            "nested_metadata": {
                "level1": {
                    "level2": [
                        {"level3": {"key": f"value_{j}"}} for j in range(random.randint(1, 3))
                    ]
                }
            },
            
            "priority_scores": [round(random.uniform(1.0, 10.0), 2) for _ in range(random.randint(1, 5))],
            "related_entity_ids": [random_uuid() for _ in range(random.randint(0, 5))],
            "verification_codes": [random_string(6, "alnum").upper() for _ in range(random.randint(0, 3))],
            "status_history": [random.choice(["pending", "active", "inactive", "suspended"]) for _ in range(random.randint(1, 5))],
            "advanced_settings": {
                "feature_flags": {f"feature_{j}": random.choice([True, False]) for j in range(3)},
                "thresholds": {"warning": random.randint(70, 90), "critical": random.randint(90, 99)}
            } if random.random() > 0.3 else None,
            "coordinates_3d": [round(random.uniform(-100, 100), 2) for _ in range(3)],
            "theme_colors": [f"#{random_string(6, 'hex').upper()}" for _ in range(random.randint(1, 5))],
            "schema_version": f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "compliance_flags": {
                "gdpr": random.choice([True, False]),
                "hipaa": random.choice([True, False]),
                "sox": random.choice([True, False])
            },
            "performance_metrics": {
                "response_time": round(random.uniform(0.1, 2.0), 3),
                "throughput": round(random.uniform(100, 5000), 1),
                "error_rate": round(random.uniform(0.001, 0.1), 4)
            }
        }
        data.append(entity)
    
    return data


def benchmark_satya(data: List[Dict[str, Any]], batch_size: int = 10000) -> Dict[str, Any]:
    """Benchmark Satya validation performance using batching"""
    print(f"🔍 Benchmarking Satya with {len(data)} comprehensive entities...")
    print(f"   📦 Using batch processing with batch_size={batch_size}")
    
    # Create validator
    validator = ComprehensiveEntity.validator()
    validator.set_batch_size(batch_size)
    
    # Warm up with a small batch
    validator.validate(data[0])
    
    # Benchmark validation using streaming with batching
    start_time = time.time()
    
    valid_count = 0
    error_count = 0
    
    # Use validate_stream for efficient batch processing
    for result in validator.validate_stream(iter(data), collect_errors=True):
        if hasattr(result, 'is_valid'):  # ValidationResult object
            if result.is_valid:
                valid_count += 1
            else:
                error_count += 1
        else:  # Direct valid item
            valid_count += 1
    
    end_time = time.time()
    total_time = end_time - start_time
    
    return {
        'total_time': total_time,
        'items_per_second': len(data) / total_time,
        'valid_count': valid_count,
        'error_count': error_count,
        'avg_time_per_item': total_time / len(data) * 1000,  # milliseconds
        'library': 'Satya (Batched)',
        'batch_size': batch_size
    }


def benchmark_satya_single(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Benchmark Satya validation performance using single-item validation for comparison"""
    print(f"🔍 Benchmarking Satya (single-item) with {len(data)} comprehensive entities...")
    
    # Create validator
    validator = ComprehensiveEntity.validator()
    
    # Warm up
    validator.validate(data[0])
    
    # Benchmark validation item by item
    start_time = time.time()
    
    valid_count = 0
    error_count = 0
    
    for item in data:
        result = validator.validate(item)
        if result.is_valid:
            valid_count += 1
        else:
            error_count += 1
    
    end_time = time.time()
    total_time = end_time - start_time
    
    return {
        'total_time': total_time,
        'items_per_second': len(data) / total_time,
        'valid_count': valid_count,
        'error_count': error_count,
        'avg_time_per_item': total_time / len(data) * 1000,  # milliseconds
        'library': 'Satya (Single)',
        'batch_size': 1
    }


def benchmark_msgspec(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Benchmark msgspec validation performance"""
    if not MSGSPEC_AVAILABLE:
        return None
        
    print(f"🔍 Benchmarking msgspec with {len(data)} comprehensive entities...")
    
    # Warm up
    try:
        MsgspecComprehensiveEntity(**data[0])
    except Exception:
        pass
    
    # Benchmark validation
    start_time = time.time()
    
    valid_count = 0
    error_count = 0
    
    for item in data:
        try:
            MsgspecComprehensiveEntity(**item)
            valid_count += 1
        except Exception:
            error_count += 1
    
    end_time = time.time()
    total_time = end_time - start_time
    
    return {
        'total_time': total_time,
        'items_per_second': len(data) / total_time,
        'valid_count': valid_count,
        'error_count': error_count,
        'avg_time_per_item': total_time / len(data) * 1000,  # milliseconds
        'library': 'msgspec'
    }


def measure_memory_usage(func, *args, **kwargs):
    """Measure memory usage of a function"""
    if not MEMORY_PROFILER_AVAILABLE:
        return None
    
    def wrapper():
        return func(*args, **kwargs)
    
    mem_usage = memory_usage(wrapper, interval=0.1, timeout=None)
    return {
        'max_memory_mb': max(mem_usage),
        'min_memory_mb': min(mem_usage),
        'avg_memory_mb': sum(mem_usage) / len(mem_usage),
        'memory_samples': len(mem_usage)
    }


def create_visualizations(results: Dict[str, Any], output_dir: str = "benchmarks/results"):
    """Create performance visualization charts"""
    if not PLOTTING_AVAILABLE:
        print("⚠️  Skipping visualizations (matplotlib not available)")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Prepare data
    libraries = [r['library'] for r in results['benchmarks']]
    items_per_sec = [r['items_per_second'] for r in results['benchmarks']]
    avg_time_ms = [r['avg_time_per_item'] for r in results['benchmarks']]
    
    # Create comprehensive performance comparison
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 12))
    
    # 1. Items per second comparison
    colors = ['#2E86AB' if 'Satya' in lib else '#A23B72' for lib in libraries]
    bars1 = ax1.bar(range(len(libraries)), items_per_sec, color=colors)
    ax1.set_title('Validation Performance Comparison\n(Higher is Better)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Items per Second')
    ax1.set_xticks(range(len(libraries)))
    ax1.set_xticklabels(libraries, rotation=45, ha='right')
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bar, value in zip(bars1, items_per_sec):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{value:,.0f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # 2. Average time per item
    bars2 = ax2.bar(range(len(libraries)), avg_time_ms, color=colors)
    ax2.set_title('Average Time per Item\n(Lower is Better)', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Milliseconds per Item')
    ax2.set_xticks(range(len(libraries)))
    ax2.set_xticklabels(libraries, rotation=45, ha='right')
    ax2.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bar, value in zip(bars2, avg_time_ms):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{value:.3f}ms', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # 3. Batch size performance analysis
    batch_results = [r for r in results['benchmarks'] if 'batch=' in r['library']]
    if batch_results:
        batch_sizes = [r['batch_size'] for r in batch_results]
        batch_performance = [r['items_per_second'] for r in batch_results]
        
        ax3.plot(batch_sizes, batch_performance, 'o-', linewidth=3, markersize=8, color='#2E86AB')
        ax3.set_title('Satya Batch Size Performance\n(Optimal Batch Size Analysis)', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Batch Size')
        ax3.set_ylabel('Items per Second')
        ax3.grid(True, alpha=0.3)
        
        # Highlight best performance
        best_idx = batch_performance.index(max(batch_performance))
        ax3.scatter(batch_sizes[best_idx], batch_performance[best_idx], 
                   color='red', s=100, zorder=5, label=f'Best: {batch_sizes[best_idx]:,}')
        ax3.legend()
        
        # Add value labels
        for x, y in zip(batch_sizes, batch_performance):
            ax3.annotate(f'{y:,.0f}', (x, y), textcoords="offset points", 
                        xytext=(0,10), ha='center', fontweight='bold')
    
    # 4. Speedup comparison (Batched vs Single vs msgspec)
    single_result = next((r for r in results['benchmarks'] if r['library'] == 'Satya (Single)'), None)
    msgspec_result = next((r for r in results['benchmarks'] if r['library'] == 'msgspec'), None)
    
    if single_result and batch_results:
        best_batch = max(batch_results, key=lambda x: x['items_per_second'])
        
        speedup_data = {
            'Single Item': 1.0,
            f'Best Batch\n({best_batch["batch_size"]:,})': best_batch['items_per_second'] / single_result['items_per_second']
        }
        
        if msgspec_result:
            speedup_data['msgspec'] = msgspec_result['items_per_second'] / single_result['items_per_second']
        
        bars4 = ax4.bar(speedup_data.keys(), speedup_data.values(), 
                       color=['#FF6B6B', '#2E86AB', '#A23B72'])
        ax4.set_title('Performance Speedup vs Single-Item Validation\n(Relative Performance)', 
                     fontsize=14, fontweight='bold')
        ax4.set_ylabel('Speedup Factor (x)')
        ax4.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars4, speedup_data.values()):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{value:.1f}x', ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/example5_comprehensive_performance.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Memory usage comparison (if available)
    if results.get('memory_usage'):
        memory_data = results['memory_usage']
        valid_memory = {k: v for k, v in memory_data.items() if v and v.get('max_memory_mb')}
        
        if valid_memory:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
            
            # Peak memory usage
            libraries_mem = list(valid_memory.keys())
            max_memory = [valid_memory[lib]['max_memory_mb'] for lib in libraries_mem]
            avg_memory = [valid_memory[lib]['avg_memory_mb'] for lib in libraries_mem]
            
            colors_mem = ['#2E86AB' if 'Satya' in lib else '#A23B72' for lib in libraries_mem]
            
            bars1 = ax1.bar(range(len(libraries_mem)), max_memory, color=colors_mem)
            ax1.set_title('Peak Memory Usage Comparison\n(Lower is Better)', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Memory Usage (MB)')
            ax1.set_xticks(range(len(libraries_mem)))
            ax1.set_xticklabels(libraries_mem, rotation=45, ha='right')
            ax1.grid(axis='y', alpha=0.3)
            
            # Add value labels
            for bar, value in zip(bars1, max_memory):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{value:.1f}MB', ha='center', va='bottom', fontweight='bold')
            
            # Average memory usage
            bars2 = ax2.bar(range(len(libraries_mem)), avg_memory, color=colors_mem)
            ax2.set_title('Average Memory Usage Comparison\n(Lower is Better)', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Memory Usage (MB)')
            ax2.set_xticks(range(len(libraries_mem)))
            ax2.set_xticklabels(libraries_mem, rotation=45, ha='right')
            ax2.grid(axis='y', alpha=0.3)
            
            # Add value labels
            for bar, value in zip(bars2, avg_memory):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{value:.1f}MB', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/example5_memory_comparison.png", dpi=300, bbox_inches='tight')
            plt.close()
    
    print(f"📊 Visualizations saved to {output_dir}/")
    print(f"   📈 Performance charts: example5_comprehensive_performance.png")
    print(f"   💾 Memory charts: example5_memory_comparison.png")


def main():
    """Run comprehensive benchmark comparing Satya vs msgspec"""
    print("🚀 Comprehensive Validation Benchmark: Satya vs msgspec")
    print("=" * 60)
    print("📋 Using Ultra-Complex ComprehensiveEntity Model")
    print("   • 25+ fields with deep nesting (4+ levels)")
    print("   • All validation types: email, URL, patterns, ranges")
    print("   • Decimal precision, UUID validation, datetime handling")
    print("   • Complex arrays, enums, literals, optional fields")
    print("   • Healthcare, financial, security data validation")
    print("=" * 60)
    
    # Configuration
    dataset_size = 100000  # Large dataset for comprehensive testing
    batch_sizes = [1000, 5000, 10000, 20000]  # Test different batch sizes
    
    print(f"📊 Dataset: {dataset_size:,} comprehensive entities")
    print(f"📦 Testing batch sizes: {batch_sizes}")
    print()
    
    # Generate test data
    print("🔄 Generating comprehensive test data...")
    test_data = generate_comprehensive_test_data(dataset_size)
    print(f"✅ Generated {len(test_data):,} comprehensive entities")
    
    # Calculate data complexity
    sample_json = json.dumps(test_data[0])
    avg_entity_size = len(sample_json)
    total_data_size = avg_entity_size * len(test_data) / (1024 * 1024)  # MB
    
    print(f"📏 Average entity size: {avg_entity_size:,} characters")
    print(f"💾 Total dataset size: {total_data_size:.1f} MB")
    print()
    
    # Run benchmarks
    results = {
        'dataset_size': dataset_size,
        'avg_entity_size': avg_entity_size,
        'total_data_size_mb': total_data_size,
        'benchmarks': [],
        'memory_usage': {}
    }
    
    # Benchmark Satya with different batch sizes
    print("🔍 Testing Satya with different batch sizes...")
    for batch_size in batch_sizes:
        print(f"\n📦 Testing batch size: {batch_size:,}")
        
        if MEMORY_PROFILER_AVAILABLE:
            print(f"📊 Measuring Satya (batch={batch_size}) memory usage...")
            satya_memory = measure_memory_usage(benchmark_satya, test_data, batch_size)
            results['memory_usage'][f'Satya (batch={batch_size})'] = satya_memory
        
        satya_results = benchmark_satya(test_data, batch_size)
        satya_results['library'] = f"Satya (batch={batch_size})"
        results['benchmarks'].append(satya_results)
    
    # Benchmark Satya single-item for comparison
    print(f"\n🔍 Testing Satya single-item validation...")
    if MEMORY_PROFILER_AVAILABLE:
        print("📊 Measuring Satya (single) memory usage...")
        satya_single_memory = measure_memory_usage(benchmark_satya_single, test_data)
        results['memory_usage']['Satya (Single)'] = satya_single_memory
    
    satya_single_results = benchmark_satya_single(test_data)
    results['benchmarks'].append(satya_single_results)
    
    # Benchmark msgspec
    if MSGSPEC_AVAILABLE:
        print(f"\n🔍 Testing msgspec...")
        if MEMORY_PROFILER_AVAILABLE:
            print("📊 Measuring msgspec memory usage...")
            msgspec_memory = measure_memory_usage(benchmark_msgspec, test_data)
            results['memory_usage']['msgspec'] = msgspec_memory
        
        msgspec_results = benchmark_msgspec(test_data)
        if msgspec_results:
            results['benchmarks'].append(msgspec_results)
    
    # Display results
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE BENCHMARK RESULTS")
    print("=" * 80)
    
    for result in results['benchmarks']:
        print(f"\n🔍 {result['library']} Results:")
        print(f"   ⏱️  Total time: {result['total_time']:.2f} seconds")
        print(f"   🚀 Items/second: {result['items_per_second']:,.0f}")
        print(f"   ⚡ Avg time/item: {result['avg_time_per_item']:.3f} ms")
        print(f"   ✅ Valid items: {result['valid_count']:,}")
        print(f"   ❌ Invalid items: {result['error_count']:,}")
        if 'batch_size' in result:
            print(f"   📦 Batch size: {result['batch_size']:,}")
        
        lib_key = result['library']
        if lib_key in results['memory_usage'] and results['memory_usage'][lib_key]:
            mem = results['memory_usage'][lib_key]
            print(f"   💾 Peak memory: {mem['max_memory_mb']:.1f} MB")
            print(f"   📊 Avg memory: {mem['avg_memory_mb']:.1f} MB")
    
    # Batching performance analysis
    print(f"\n🚀 BATCHING PERFORMANCE ANALYSIS")
    print("=" * 50)
    
    # Find best performing batch size
    batch_results = [r for r in results['benchmarks'] if 'batch=' in r['library']]
    single_result = next(r for r in results['benchmarks'] if r['library'] == 'Satya (Single)')
    
    if batch_results:
        best_batch = max(batch_results, key=lambda x: x['items_per_second'])
        worst_batch = min(batch_results, key=lambda x: x['items_per_second'])
        
        print(f"🏆 Best batch size: {best_batch['batch_size']:,}")
        print(f"   🚀 Performance: {best_batch['items_per_second']:,.0f} items/sec")
        print(f"   ⚡ Time per item: {best_batch['avg_time_per_item']:.3f} ms")
        
        print(f"\n📉 Worst batch size: {worst_batch['batch_size']:,}")
        print(f"   🚀 Performance: {worst_batch['items_per_second']:,.0f} items/sec")
        print(f"   ⚡ Time per item: {worst_batch['avg_time_per_item']:.3f} ms")
        
        # Compare best batch vs single
        batch_vs_single_ratio = best_batch['items_per_second'] / single_result['items_per_second']
        print(f"\n⚡ Batching speedup: {batch_vs_single_ratio:.1f}x faster than single-item")
        print(f"   📈 Best batch: {best_batch['items_per_second']:,.0f} items/sec")
        print(f"   📉 Single item: {single_result['items_per_second']:,.0f} items/sec")
    
    # Performance comparison with msgspec
    if MSGSPEC_AVAILABLE and any(r['library'] == 'msgspec' for r in results['benchmarks']):
        msgspec_perf = next(r for r in results['benchmarks'] if r['library'] == 'msgspec')
        best_satya = max([r for r in results['benchmarks'] if 'Satya' in r['library']], 
                        key=lambda x: x['items_per_second'])
        
        speed_ratio = msgspec_perf['items_per_second'] / best_satya['items_per_second']
        time_ratio = best_satya['avg_time_per_item'] / msgspec_perf['avg_time_per_item']
        
        print(f"\n🏁 SATYA vs MSGSPEC COMPARISON")
        print("=" * 40)
        print(f"   📈 msgspec is {speed_ratio:.1f}x faster than best Satya")
        print(f"   ⚡ Best Satya takes {time_ratio:.1f}x longer per item")
        print(f"   🔍 msgspec: {msgspec_perf['items_per_second']:,.0f} items/sec")
        print(f"   🔍 Best Satya: {best_satya['items_per_second']:,.0f} items/sec ({best_satya['library']})")
        
        if results['memory_usage'].get(best_satya['library']) and results['memory_usage'].get('msgspec'):
            satya_mem = results['memory_usage'][best_satya['library']]['max_memory_mb']
            msgspec_mem = results['memory_usage']['msgspec']['max_memory_mb']
            if msgspec_mem > 0:
                memory_ratio = satya_mem / msgspec_mem
                print(f"   💾 Best Satya uses {memory_ratio:.1f}x more memory than msgspec")
    
    # Validation depth comparison
    print(f"\n🎯 VALIDATION DEPTH ANALYSIS")
    print("=" * 40)
    print(f"   🔍 Satya: Comprehensive validation")
    print(f"      • Email format validation (RFC 5322)")
    print(f"      • URL format validation") 
    print(f"      • Regex pattern matching")
    print(f"      • Numeric range validation")
    print(f"      • Decimal precision handling")
    print(f"      • UUID format validation")
    print(f"      • Enum value checking")
    print(f"      • Array constraints (min/max, unique)")
    print(f"      • Deep nested object validation (4+ levels)")
    print(f"      • Optional field handling")
    print(f"      • Custom error reporting")
    print(f"      • ⚡ EFFICIENT BATCH PROCESSING")
    print(f"   📦 msgspec: Basic type checking only")
    print(f"      • Struct field type validation")
    print(f"      • No format validation")
    print(f"      • No constraint checking")
    print(f"      • Limited error details")
    
    # Save results
    output_dir = "benchmarks/results"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/example5_comprehensive_benchmark_results.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Create visualizations
    create_visualizations(results, output_dir)
    
    print(f"\n💾 Results saved to {output_dir}/example5_comprehensive_benchmark_results.json")
    print("\n🎉 Comprehensive benchmark completed!")
    print("\n💡 KEY INSIGHTS:")
    print("   🚀 Satya's batching provides significant performance improvements")
    print("   📦 Optimal batch size depends on data complexity and memory")
    print("   🔍 msgspec optimized for speed with basic validation")
    print("   ⚖️  Satya provides comprehensive validation at reasonable performance cost")
    print("   🎯 Trade-off: Speed vs Validation Depth")
    print("   🏢 Satya ideal for applications requiring robust data validation")
    print("   ⚡ msgspec suitable for high-throughput scenarios with trusted data")
    print("   📈 Batching is KEY to Satya's performance - use it!")


if __name__ == "__main__":
    main() 