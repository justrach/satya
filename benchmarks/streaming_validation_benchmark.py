#!/usr/bin/env python3
import argparse
import gc
import json
import os
import sys
import time
from typing import List

# Resolve project root for output paths only (do not modify sys.path)
THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))

# Ensure the results directory exists
os.makedirs(os.path.join(PROJECT_ROOT, 'benchmarks', 'results'), exist_ok=True)

# Defaults (can be overridden by CLI)
N_ITEMS = 500_000
BATCH_SIZE = 50_000
MODES = ("object", "array", "ndjson")


def generate_test_data(
    num_items: int,
    *,
    fields: int,
    string_constraints: bool,
    number_constraints: bool,
    invalid_rate: float,
    use_regex: bool,
) -> List[dict]:
    """Generate synthetic test data with optional constraints and invalid-rate injection."""
    import random

    random.seed(42)
    first_names = [
        "John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Edward", "Fiona",
    ]
    last_names = [
        "Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
    ]
    domains = ["example.com", "test.com", "benchmark.org", "sample.net", "demo.io"]

    def make_record() -> dict:
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 80)
        email = f"{name.lower().replace(' ', '.')}@{random.choice(domains)}"
        rec = {"name": name, "age": age, "email": email}
        # Add extra fields up to 'fields'
        # Start from 3 base fields; add pairs s{i} (str) and n{i} (int)
        extra_needed = max(0, fields - 3)
        for i in range(extra_needed):
            if i % 2 == 0:
                rec[f"s{i}"] = f"val{i}-{random.randint(0, 999)}"
            else:
                rec[f"n{i}"] = random.randint(0, 1_000_000)
        return rec

    data = [make_record() for _ in range(num_items)]

    # Inject invalids per rate by breaking a constraint at random
    if invalid_rate > 0.0:
        n_bad = int(num_items * invalid_rate)
        bad_idx = random.sample(range(num_items), n_bad)
        for idx in bad_idx:
            rec = data[idx]
            # Prefer breaking strongest constraints first
            if number_constraints and "age" in rec:
                rec["age"] = 5  # violates ge=18
                continue
            if string_constraints and "name" in rec:
                rec["name"] = "x"  # too short and likely fails regex
                continue
            if "email" in rec:
                rec["email"] = "not-an-email"
                continue
            # Fallback: remove a required key
            rec.pop("name", None)
    return data


def measure_memory_usage(func) -> float:
    """Return peak memory in MB while executing func using tracemalloc."""
    import tracemalloc

    tracemalloc.start()
    func()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / (1024 * 1024)


def setup_validator(fields: int, string_constraints: bool, number_constraints: bool, use_regex: bool):
    import satya

    # Dynamically build a Model subclass with N fields and constraints
    attrs = {}
    # Base fields
    attrs['name'] = satya.Field(
        str,
        min_length=3 if string_constraints else None,
        max_length=40 if string_constraints else None,
        pattern=r"^[A-Za-z]+\s+[A-Za-z]+$" if (string_constraints and use_regex) else None,
        required=True,
    )
    attrs['age'] = satya.Field(
        int,
        ge=18 if number_constraints else None,
        le=90 if number_constraints else None,
        required=True,
    )
    attrs['email'] = satya.Field(
        str,
        email=True if string_constraints else False,
        required=True,
    )

    # Add extra fields alternating str/int to reach 'fields'
    extra_needed = max(0, fields - 3)
    for i in range(extra_needed):
        if i % 2 == 0:
            attrs[f"s{i}"] = satya.Field(
                str,
                min_length=2 if string_constraints else None,
                max_length=64 if string_constraints else None,
                required=True,
            )
        else:
            attrs[f"n{i}"] = satya.Field(
                int,
                ge=0 if number_constraints else None,
                le=1_000_000 if number_constraints else None,
                required=True,
            )

    ModelCls = type('DynModel', (satya.Model,), {'__annotations__': {k: (str if isinstance(v, satya.Field) and v.type is str else int) for k, v in attrs.items()}, **attrs})
    return ModelCls.validator()


def bench_dict_path(mode: str, items: List[dict], batch_size: int, validator):
    """Optimized dict validation: balance speed and memory with micro-batching."""
    
    start = time.perf_counter()
    total = 0
    
    # Use small micro-batches for optimal speed/memory balance
    micro_batch_size = min(4096, batch_size)  # 4K items per micro-batch
    
    if mode == "object":
        # Process in micro-batches for optimal cache performance
        for i in range(0, len(items), micro_batch_size):
            batch = items[i : i + micro_batch_size]
            _ = validator._validator.validate_batch(batch)
            total += len(batch)
    else:
        # array/ndjson: micro-batch validate all dicts
        for i in range(0, len(items), micro_batch_size):
            batch = items[i : i + micro_batch_size]
            _ = validator._validator.validate_batch(batch)
            total += len(batch)
            
    elapsed = time.perf_counter() - start

    # Memory measurement for micro-batch approach
    def mem_task():
        # Measure memory for processing a micro-batch
        test_batch = items[:micro_batch_size]
        _ = validator._validator.validate_batch(test_batch)

    mem_mb = measure_memory_usage(mem_task)
    ips = total / elapsed if elapsed > 0 else float('inf')
    return elapsed, mem_mb, ips


def bench_jsonloads_plus_dict(mode: str, items: List[dict], batch_size: int, validator):
    """Baseline: bytes -> json.loads -> dict-path validation.
    This measures end-to-end ingestion from bytes while still using dict-path validation.
    Uses orjson if available, falls back to standard json.
    """
    # Try to use orjson for faster parsing, fall back to json
    try:
        import orjson
        json_loads = orjson.loads
        json_dumps = lambda obj: orjson.dumps(obj).decode("utf-8")
        parser_name = "orjson"
    except ImportError:
        json_loads = json.loads
        json_dumps = json.dumps
        parser_name = "json"
    
    # Build payload(s)
    if mode == "object":
        payloads = [json_dumps(obj).encode("utf-8") for obj in items]
    elif mode == "array":
        payload = json_dumps(items).encode("utf-8")
    elif mode == "ndjson":
        payload = ("\n".join(json_dumps(obj) for obj in items)).encode("utf-8")
    else:
        raise ValueError(f"Unknown mode: {mode}")

    start = time.perf_counter()
    total = 0
    if mode == "object":
        # Decode each object and validate in batches
        decoded_batch = []
        for p in payloads:
            decoded_batch.append(json_loads(p))
            if len(decoded_batch) >= batch_size:
                _ = validator._validator.validate_batch(decoded_batch)
                total += len(decoded_batch)
                decoded_batch.clear()
        if decoded_batch:
            _ = validator._validator.validate_batch(decoded_batch)
            total += len(decoded_batch)
    elif mode == "array":
        decoded = json_loads(payload)
        _ = validator._validator.validate_batch(decoded)
        total = len(decoded)
    else:  # ndjson
        decoded_batch = []
        for line in payload.decode("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            decoded_batch.append(json_loads(line))
            if len(decoded_batch) >= batch_size:
                _ = validator._validator.validate_batch(decoded_batch)
                total += len(decoded_batch)
                decoded_batch.clear()
        if decoded_batch:
            _ = validator._validator.validate_batch(decoded_batch)
            total += len(decoded_batch)
    elapsed = time.perf_counter() - start

    # Memory for a single batch-sized workload
    def mem_task():
        if mode == "object":
            decoded = [json_loads(p) for p in payloads[:batch_size]]
            _ = validator._validator.validate_batch(decoded)
        elif mode == "array":
            part = json_dumps(items[:batch_size]).encode("utf-8")
            decoded = json_loads(part)
            _ = validator._validator.validate_batch(decoded)
        else:
            lines = ("\n".join(json_dumps(obj) for obj in items[:batch_size])).encode("utf-8").decode("utf-8").splitlines()
            decoded = [json_loads(line) for line in lines if line.strip()]
            _ = validator._validator.validate_batch(decoded)

    mem_mb = measure_memory_usage(mem_task)
    ips = total / elapsed if elapsed > 0 else float('inf')
    return elapsed, mem_mb, ips, parser_name


def bench_json_bytes(mode: str, items: List[dict], batch_size: int, streaming: bool, validator):
    """Validate using JSON bytes path (non-streaming or streaming)."""

    # Prepare payload(s)
    if mode == "object":
        payloads = [json.dumps(obj).encode("utf-8") for obj in items]
    elif mode == "array":
        payload = json.dumps(items).encode("utf-8")
    elif mode == "ndjson":
        payload = ("\n".join(json.dumps(obj) for obj in items)).encode("utf-8")
    else:
        raise ValueError(f"Unknown mode: {mode}")

    start = time.perf_counter()
    total = 0
    if mode == "object":
        for p in payloads:
            _ = validator.validate_json(p, mode="object", streaming=streaming)
            total += 1
    elif mode == "array":
        _ = validator.validate_json(payload, mode="array", streaming=streaming)
        total = len(items)
    elif mode == "ndjson":
        _ = validator.validate_json(payload, mode="ndjson", streaming=streaming)
        total = len(items)
    elapsed = time.perf_counter() - start

    # Memory for a single batch-sized workload
    def mem_task():
        if mode == "object":
            for p in payloads[:batch_size]:
                _ = validator.validate_json(p, mode="object", streaming=streaming)
        elif mode == "array":
            part = json.dumps(items[:batch_size]).encode("utf-8")
            _ = validator.validate_json(part, mode="array", streaming=streaming)
        else:  # ndjson
            part = ("\n".join(json.dumps(obj) for obj in items[:batch_size])).encode("utf-8")
            _ = validator.validate_json(part, mode="ndjson", streaming=streaming)

    mem_mb = measure_memory_usage(mem_task)
    ips = total / elapsed if elapsed > 0 else float('inf')
    return elapsed, mem_mb, ips


def bench_pydantic_orjson(mode: str, items: List[dict], batch_size: int):
    """Benchmark Pydantic with orjson parsing for fair comparison."""
    try:
        from pydantic import BaseModel
        import orjson
    except ImportError as e:
        print(f"Skipping Pydantic benchmark: {e}")
        return 0, 0, 0
    
    # Define Pydantic model matching Satya schema
    class Person(BaseModel):
        name: str
        age: int
        email: str
        # Add extra fields dynamically if needed - for now assume 3 base fields
    
    # Build payloads
    if mode == "object":
        payloads = [orjson.dumps(obj) for obj in items]
    elif mode == "array":
        payload = orjson.dumps(items)
    elif mode == "ndjson":
        payload = ("\n".join(orjson.dumps(obj).decode("utf-8") for obj in items)).encode("utf-8")
    else:
        raise ValueError(f"Unknown mode: {mode}")

    start = time.perf_counter()
    total = 0
    if mode == "object":
        for p in payloads:
            decoded = orjson.loads(p)
            Person(**decoded)
            total += 1
    elif mode == "array":
        decoded = orjson.loads(payload)
        for item in decoded:
            Person(**item)
        total = len(decoded)
    else:  # ndjson
        for line in payload.decode("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            decoded = orjson.loads(line)
            Person(**decoded)
            total += 1
    elapsed = time.perf_counter() - start

    # Memory measurement
    def mem_task():
        if mode == "object":
            for p in payloads[:batch_size]:
                decoded = orjson.loads(p)
                Person(**decoded)
        elif mode == "array":
            part = orjson.dumps(items[:batch_size])
            decoded = orjson.loads(part)
            for item in decoded:
                Person(**item)
        else:
            lines = ("\n".join(orjson.dumps(obj).decode("utf-8") for obj in items[:batch_size])).encode("utf-8").decode("utf-8").splitlines()
            for line in lines:
                if line.strip():
                    decoded = orjson.loads(line)
                    Person(**decoded)

    mem_mb = measure_memory_usage(mem_task)
    ips = total / elapsed if elapsed > 0 else float('inf')
    return elapsed, mem_mb, ips


def bench_msgspec_json(mode: str, items: List[dict], batch_size: int):
    """Benchmark msgspec with its own JSON parsing."""
    try:
        import msgspec
    except ImportError as e:
        print(f"Skipping msgspec benchmark: {e}")
        return 0, 0, 0
    
    # Define msgspec model
    class Person(msgspec.Struct):
        name: str
        age: int
        email: str
    
    # Build payloads using standard json for encoding (msgspec will decode)
    if mode == "object":
        payloads = [json.dumps(obj).encode("utf-8") for obj in items]
    elif mode == "array":
        payload = json.dumps(items).encode("utf-8")
    elif mode == "ndjson":
        payload = ("\n".join(json.dumps(obj) for obj in items)).encode("utf-8")
    else:
        raise ValueError(f"Unknown mode: {mode}")

    start = time.perf_counter()
    total = 0
    if mode == "object":
        for p in payloads:
            msgspec.json.decode(p, type=Person)
            total += 1
    elif mode == "array":
        decoded = msgspec.json.decode(payload, type=list[Person])
        total = len(decoded)
    else:  # ndjson
        for line in payload.decode("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            msgspec.json.decode(line.encode("utf-8"), type=Person)
            total += 1
    elapsed = time.perf_counter() - start

    # Memory measurement
    def mem_task():
        if mode == "object":
            for p in payloads[:batch_size]:
                msgspec.json.decode(p, type=Person)
        elif mode == "array":
            part = json.dumps(items[:batch_size]).encode("utf-8")
            msgspec.json.decode(part, type=list[Person])
        else:
            lines = ("\n".join(json.dumps(obj) for obj in items[:batch_size])).encode("utf-8").decode("utf-8").splitlines()
            for line in lines:
                if line.strip():
                    msgspec.json.decode(line.encode("utf-8"), type=Person)

    mem_mb = measure_memory_usage(mem_task)
    ips = total / elapsed if elapsed > 0 else float('inf')
    return elapsed, mem_mb, ips


def create_visualization(results, mode: str):
    """Create simple bars comparing dict-path vs JSON (non-streaming vs streaming)."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib as mpl
    except Exception:
        print("matplotlib not available; skipping plots")
        return

    plt.style.use('ggplot')
    mpl.rcParams['font.family'] = 'sans-serif'
    mpl.rcParams['font.sans-serif'] = [
        'Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif'
    ]

    parser_name = results.get('parser_name', 'json')
    
    # Base libraries
    libs = ["dict-path", f"{parser_name}.loads+dict", "json-nonstream", "json-stream"]
    ips_vals = [
        results['dict_ips'],
        results['json_loads_ips'],
        results['json_ips'],
        results['json_stream_ips'],
    ]
    mem_vals = [
        results['dict_mem'],
        results['json_loads_mem'],
        results['json_mem'],
        results['json_stream_mem'],
    ]
    colors = ['#7f8c8d', '#8e44ad', '#2980b9', '#27ae60']
    
    # Add comparison libraries if enabled
    if results.get('compare_libs', False):
        if results.get('pydantic_ips', 0) > 0:
            libs.append("pydantic+orjson")
            ips_vals.append(results['pydantic_ips'])
            mem_vals.append(results['pydantic_mem'])
            colors.append('#e74c3c')
        if results.get('msgspec_ips', 0) > 0:
            libs.append("msgspec+json")
            ips_vals.append(results['msgspec_ips'])
            mem_vals.append(results['msgspec_mem'])
            colors.append('#f39c12')

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.bar(libs, ips_vals, color=colors, width=0.6, edgecolor='white', linewidth=1)
    for bar, speed in zip(bars, ips_vals):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() * 1.01,
                f"{int(speed):,} items/s", ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.set_title(f"Satya validation throughput by mode = {mode}", fontsize=16, fontweight='bold')
    ax.set_ylabel('Items per second', fontsize=13, fontweight='bold')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    out1 = os.path.join(PROJECT_ROOT, 'benchmarks', 'results', f'streaming_ips_{mode}.png')
    plt.savefig(out1, dpi=300, bbox_inches='tight')
    print(f"Saved throughput chart to {out1}")

    # Memory plot
    plt.figure(figsize=(12, 7))
    bars2 = plt.bar(libs, mem_vals, color=colors, width=0.6, edgecolor='white', linewidth=1)
    for bar, mem in zip(bars2, mem_vals):
        ax = plt.gca()
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() * 1.01,
                f"{mem:.1f} MB", ha='center', va='bottom', fontsize=11, fontweight='bold')
    plt.title(f"Satya memory usage (peak tracemalloc) by mode = {mode}", fontsize=16, fontweight='bold')
    plt.ylabel('MB (peak)', fontsize=13, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.gca().set_axisbelow(True)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.tight_layout()
    out2 = os.path.join(PROJECT_ROOT, 'benchmarks', 'results', f'streaming_mem_{mode}.png')
    plt.savefig(out2, dpi=300, bbox_inches='tight')
    print(f"Saved memory chart to {out2}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Satya dict-path vs JSON-bytes (streaming and non-streaming)")
    parser.add_argument("--items", type=int, default=N_ITEMS, help="Total number of items")
    parser.add_argument("--batch", type=int, default=BATCH_SIZE, help="Batch size for dict-path and memory tasks")
    parser.add_argument("--mode", type=str, choices=list(MODES), default="array", help="Top-level JSON mode")
    parser.add_argument("--fields", type=int, default=3, help="Total number of fields in the model (>=3)")
    parser.add_argument("--string-constraints", action="store_true", help="Enable string constraints (min/max length, email, regex)")
    parser.add_argument("--number-constraints", action="store_true", help="Enable numeric constraints (ge/le)")
    parser.add_argument("--regex", action="store_true", help="Add a regex constraint to 'name'")
    parser.add_argument("--invalid-rate", type=float, default=0.0, help="Fraction of items to make invalid (0.0-1.0)")
    parser.add_argument("--no-plot", action="store_true", help="Skip matplotlib plots")
    parser.add_argument("--compare-libs", action="store_true", help="Include Pydantic and msgspec benchmarks for comparison")
    args = parser.parse_args()

    # Override globals
    N = int(args.items)
    BATCH = int(args.batch)
    MODE = args.mode

    print(f"Benchmarking mode='{MODE}' with items={N:,}, batch={BATCH:,}, fields={args.fields}, string_constraints={args.string_constraints}, number_constraints={args.number_constraints}, regex={args.regex}, invalid_rate={args.invalid_rate}")

    # Prepare data
    items = generate_test_data(
        N,
        fields=args.fields,
        string_constraints=args.string_constraints,
        number_constraints=args.number_constraints,
        invalid_rate=args.invalid_rate,
        use_regex=args.regex,
    )

    # Build validator matching the same schema/constraints
    validator = setup_validator(args.fields, args.string_constraints, args.number_constraints, args.regex)

    # dict-path baseline
    gc.collect()
    dict_time, dict_mem, dict_ips = bench_dict_path(MODE, items, BATCH, validator)
    print(f"dict-path: time={dict_time:.2f}s, ips={int(dict_ips):,}, mem={dict_mem:.1f}MB")

    # bytes -> json.loads -> dict-path
    gc.collect()
    json_loads_time, json_loads_mem, json_loads_ips, parser_name = bench_jsonloads_plus_dict(MODE, items, BATCH, validator)
    print(f"{parser_name}.loads+dict: time={json_loads_time:.2f}s, ips={int(json_loads_ips):,}, mem={json_loads_mem:.1f}MB")

    # JSON non-streaming
    gc.collect()
    json_time, json_mem, json_ips = bench_json_bytes(MODE, items, BATCH, streaming=False, validator=validator)
    print(f"json-nonstream: time={json_time:.2f}s, ips={int(json_ips):,}, mem={json_mem:.1f}MB")

    # JSON streaming
    gc.collect()
    json_stream_time, json_stream_mem, json_stream_ips = bench_json_bytes(MODE, items, BATCH, streaming=True, validator=validator)
    print(f"json-stream: time={json_stream_time:.2f}s, ips={int(json_stream_ips):,}, mem={json_stream_mem:.1f}MB")

    # Optional library comparisons
    pydantic_time = pydantic_mem = pydantic_ips = 0
    msgspec_time = msgspec_mem = msgspec_ips = 0
    
    if args.compare_libs:
        print("\n--- Library Comparisons ---")
        
        # Pydantic with orjson
        gc.collect()
        pydantic_time, pydantic_mem, pydantic_ips = bench_pydantic_orjson(MODE, items, BATCH)
        if pydantic_ips > 0:
            print(f"pydantic+orjson: time={pydantic_time:.2f}s, ips={int(pydantic_ips):,}, mem={pydantic_mem:.1f}MB")
        
        # msgspec with its own JSON
        gc.collect()
        msgspec_time, msgspec_mem, msgspec_ips = bench_msgspec_json(MODE, items, BATCH)
        if msgspec_ips > 0:
            print(f"msgspec+json: time={msgspec_time:.2f}s, ips={int(msgspec_ips):,}, mem={msgspec_mem:.1f}MB")

    # Save summary
    summary = {
        "mode": MODE,
        "items": N,
        "batch": BATCH,
        "fields": args.fields,
        "string_constraints": args.string_constraints,
        "number_constraints": args.number_constraints,
        "regex": args.regex,
        "invalid_rate": args.invalid_rate,
        "parser_name": parser_name,
        "dict_time": dict_time,
        "dict_mem": dict_mem,
        "dict_ips": dict_ips,
        "json_loads_time": json_loads_time,
        "json_loads_mem": json_loads_mem,
        "json_loads_ips": json_loads_ips,
        "json_time": json_time,
        "json_mem": json_mem,
        "json_ips": json_ips,
        "json_stream_time": json_stream_time,
        "json_stream_mem": json_stream_mem,
        "json_stream_ips": json_stream_ips,
        "compare_libs": args.compare_libs,
        "pydantic_time": pydantic_time,
        "pydantic_mem": pydantic_mem,
        "pydantic_ips": pydantic_ips,
        "msgspec_time": msgspec_time,
        "msgspec_mem": msgspec_mem,
        "msgspec_ips": msgspec_ips,
    }
    outpath = os.path.join(PROJECT_ROOT, 'benchmarks', 'results', f'streaming_benchmark_{MODE}.json')
    with open(outpath, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary to {outpath}")

    if not args.no_plot:
        create_visualization(summary, MODE)
    else:
        print("Skipping plots (--no-plot)")
