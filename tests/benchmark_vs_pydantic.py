"""
Head-to-head benchmark: Satya TurboValidator vs Pydantic v2

Compares:
1. Model creation/validation throughput
2. JSON serialization (model_dump_json)
3. JSON deserialization (model_validate_json)
4. Attribute access
5. Complex model with constraints
6. Batch validation
"""
import time
import json
import statistics
from typing import Optional, List

# ═══════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════
from pydantic import BaseModel as PydanticBaseModel, Field as PydanticField, field_validator

class PydanticSimple(PydanticBaseModel):
    name: str
    age: int
    email: str

class PydanticConstrained(PydanticBaseModel):
    name: str = PydanticField(min_length=1, max_length=100)
    age: int = PydanticField(ge=0, le=150)
    score: float = PydanticField(ge=0.0, le=100.0)

class PydanticComplex(PydanticBaseModel):
    username: str = PydanticField(min_length=3, max_length=50)
    email: str
    age: int = PydanticField(ge=0, le=150)
    score: float = PydanticField(ge=0.0, le=100.0)
    is_active: bool = True
    tags: List[str] = []
    nickname: Optional[str] = None
    level: int = PydanticField(ge=1, le=100, default=1)
    rating: float = PydanticField(ge=0.0, le=5.0, default=0.0)
    bio: str = PydanticField(max_length=500, default="")

class PydanticAddress(PydanticBaseModel):
    street: str
    city: str
    zip_code: str

class PydanticUser(PydanticBaseModel):
    name: str
    age: int
    address: PydanticAddress

# ═══════════════════════════════════════════════════════════════
# Satya Models
# ═══════════════════════════════════════════════════════════════
import sys
from satya import Model, Field as SatyaField

class SatyaSimple(Model):
    name: str
    age: int
    email: str

class SatyaConstrained(Model):
    name: str = SatyaField(min_length=1, max_length=100)
    age: int = SatyaField(ge=0, le=150)
    score: float = SatyaField(ge=0.0, le=100.0)

class SatyaComplex(Model):
    username: str = SatyaField(min_length=3, max_length=50)
    email: str
    age: int = SatyaField(ge=0, le=150)
    score: float = SatyaField(ge=0.0, le=100.0)
    is_active: bool = SatyaField(default=True)
    tags: list = SatyaField(default=[])
    nickname: str = SatyaField(default=None)
    level: int = SatyaField(ge=1, le=100, default=1)
    rating: float = SatyaField(ge=0.0, le=5.0, default=0.0)
    bio: str = SatyaField(max_length=500, default="")

class SatyaAddress(Model):
    street: str
    city: str
    zip_code: str

class SatyaUser(Model):
    name: str
    age: int
    address: SatyaAddress

# ═══════════════════════════════════════════════════════════════
# Benchmark Utilities
# ═══════════════════════════════════════════════════════════════

def bench(func, n_iterations=50000, warmup=5000, n_runs=5):
    """Run benchmark with warmup and multiple runs, return median ops/sec."""
    # Warmup
    for _ in range(warmup):
        func()

    results = []
    for _ in range(n_runs):
        start = time.perf_counter()
        for _ in range(n_iterations):
            func()
        elapsed = time.perf_counter() - start
        results.append(n_iterations / elapsed)

    return statistics.median(results)

def format_result(name, satya_ops, pydantic_ops):
    """Format a benchmark result line."""
    ratio = satya_ops / pydantic_ops
    winner = "SATYA" if ratio > 1 else "PYDANTIC"
    bar = "█" * min(int(ratio * 10), 50) if ratio > 1 else "░" * min(int((1/ratio) * 10), 50)
    return f"  {name:<35} {satya_ops:>12,.0f}  {pydantic_ops:>12,.0f}  {ratio:>6.2f}x  {winner:<8} {bar}"

# ═══════════════════════════════════════════════════════════════
# Benchmarks
# ═══════════════════════════════════════════════════════════════

def run_benchmarks():
    print("=" * 110)
    print("  SATYA TurboValidator vs Pydantic v2 - Head-to-Head Benchmark")
    print("=" * 110)
    print(f"\n  Python: {sys.version.split()[0]}")

    import pydantic
    print(f"  Pydantic: {pydantic.__version__}")
    print(f"  Satya: TurboValidator (Rust-native)")
    print(f"  Platform: {'free-threaded' if hasattr(sys, '_is_gil_enabled') else 'standard'} CPython")
    print()

    results = []

    # ─── Test Data ───
    simple_data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
    constrained_data = {"name": "Bob", "age": 25, "score": 95.5}
    complex_data = {
        "username": "charlie",
        "email": "charlie@test.com",
        "age": 28,
        "score": 88.5,
        "is_active": True,
        "tags": ["python", "rust"],
        "nickname": "chuck",
        "level": 5,
        "rating": 4.5,
        "bio": "A software developer",
    }
    nested_data = {
        "name": "Dave",
        "age": 35,
        "address": {"street": "123 Main St", "city": "Springfield", "zip_code": "62701"},
    }

    print("─" * 110)
    print(f"  {'Benchmark':<35} {'Satya ops/s':>12}  {'Pydantic ops/s':>12}  {'Ratio':>6}   {'Winner':<8}")
    print("─" * 110)

    # ─── 1. Simple Model Creation ───
    print("\n  ▸ MODEL CREATION (validation + instantiation)")

    s = bench(lambda: SatyaSimple(**simple_data))
    p = bench(lambda: PydanticSimple(**simple_data))
    print(format_result("Simple (3 fields)", s, p))
    results.append(("Simple Model", s, p))

    s = bench(lambda: SatyaConstrained(**constrained_data))
    p = bench(lambda: PydanticConstrained(**constrained_data))
    print(format_result("Constrained (3 fields + bounds)", s, p))
    results.append(("Constrained Model", s, p))

    s = bench(lambda: SatyaComplex(**complex_data), n_iterations=20000)
    p = bench(lambda: PydanticComplex(**complex_data), n_iterations=20000)
    print(format_result("Complex (10 fields + defaults)", s, p))
    results.append(("Complex Model", s, p))

    # ─── 2. JSON Serialization ───
    print("\n  ▸ JSON SERIALIZATION (model_dump_json)")

    satya_simple = SatyaSimple(**simple_data)
    pydantic_simple = PydanticSimple(**simple_data)

    s = bench(lambda: satya_simple.model_dump_json())
    p = bench(lambda: pydantic_simple.model_dump_json())
    print(format_result("Simple model → JSON", s, p))
    results.append(("JSON Serialize Simple", s, p))

    satya_complex = SatyaComplex(**complex_data)
    pydantic_complex = PydanticComplex(**complex_data)

    s = bench(lambda: satya_complex.model_dump_json())
    p = bench(lambda: pydantic_complex.model_dump_json())
    print(format_result("Complex model → JSON", s, p))
    results.append(("JSON Serialize Complex", s, p))

    # ─── 3. JSON Deserialization ───
    print("\n  ▸ JSON DESERIALIZATION (model_validate_json)")

    simple_json = json.dumps(simple_data).encode()
    complex_json = json.dumps(complex_data).encode()

    # Both use model_validate_json (Rust-native JSON parsing)
    s = bench(lambda: SatyaSimple.model_validate_json(simple_json))
    p = bench(lambda: PydanticSimple.model_validate_json(simple_json))
    print(format_result("JSON → Simple model", s, p))
    results.append(("JSON Deserialize Simple", s, p))

    s = bench(lambda: SatyaComplex.model_validate_json(complex_json), n_iterations=20000)
    p = bench(lambda: PydanticComplex.model_validate_json(complex_json), n_iterations=20000)
    print(format_result("JSON → Complex model", s, p))
    results.append(("JSON Deserialize Complex", s, p))

    # ─── 4. Attribute Access ───
    print("\n  ▸ ATTRIBUTE ACCESS")

    s = bench(lambda: (satya_simple.name, satya_simple.age, satya_simple.email), n_iterations=100000)
    p = bench(lambda: (pydantic_simple.name, pydantic_simple.age, pydantic_simple.email), n_iterations=100000)
    print(format_result("3 attribute reads", s, p))
    results.append(("Attribute Access", s, p))

    # ─── 5. model_dump (dict serialization) ───
    print("\n  ▸ DICT SERIALIZATION (model_dump)")

    s = bench(lambda: satya_simple.model_dump())
    p = bench(lambda: pydantic_simple.model_dump())
    print(format_result("Simple model_dump()", s, p))
    results.append(("Dict Serialize Simple", s, p))

    s = bench(lambda: satya_complex.model_dump())
    p = bench(lambda: pydantic_complex.model_dump())
    print(format_result("Complex model_dump()", s, p))
    results.append(("Dict Serialize Complex", s, p))

    # ─── 6. Nested Model ───
    print("\n  ▸ NESTED MODEL")

    s = bench(lambda: SatyaUser(**nested_data), n_iterations=20000)
    p = bench(lambda: PydanticUser(**nested_data), n_iterations=20000)
    print(format_result("Nested model creation", s, p))
    results.append(("Nested Model", s, p))

    # ─── 7. Validation Errors (invalid data) ───
    print("\n  ▸ VALIDATION ERRORS (reject invalid data)")

    invalid_simple = {"name": 123, "age": "not_int", "email": "test@test.com"}

    def satya_reject():
        try:
            SatyaSimple(**invalid_simple)
        except Exception:
            pass

    def pydantic_reject():
        try:
            PydanticSimple(**invalid_simple)
        except Exception:
            pass

    s = bench(satya_reject, n_iterations=20000)
    p = bench(pydantic_reject, n_iterations=20000)
    print(format_result("Reject invalid data", s, p))
    results.append(("Validation Error", s, p))

    # ─── 8. Raw Validator (no Model overhead) ───
    print("\n  ▸ RAW VALIDATOR (Rust-only, no Python Model layer)")

    from satya._satya import TurboValidatorPy
    turbo = TurboValidatorPy()
    turbo.add_field("name", "str", True)
    turbo.add_field("age", "int", True)
    turbo.add_field("email", "str", True)
    turbo.compile()

    s = bench(lambda: turbo.validate_check(simple_data), n_iterations=100000)
    p = bench(lambda: PydanticSimple(**simple_data), n_iterations=100000)
    print(format_result("Raw Rust validate_check vs Pydantic", s, p))
    results.append(("Raw Rust Validate", s, p))

    # ─── Summary ───
    print("\n" + "═" * 110)
    print("  SUMMARY")
    print("═" * 110)

    wins_satya = sum(1 for _, s, p in results if s > p)
    wins_pydantic = sum(1 for _, s, p in results if p > s)
    avg_ratio = statistics.geometric_mean([s/p for _, s, p in results])

    print(f"\n  Satya wins: {wins_satya}/{len(results)} benchmarks")
    print(f"  Pydantic wins: {wins_pydantic}/{len(results)} benchmarks")
    print(f"  Geometric mean speedup (Satya/Pydantic): {avg_ratio:.2f}x")

    if avg_ratio > 1:
        print(f"\n  → Satya is {avg_ratio:.2f}x faster than Pydantic v2 on average")
    else:
        print(f"\n  → Pydantic v2 is {1/avg_ratio:.2f}x faster than Satya on average")

    print(f"\n  NOTE: msgspec could not be benchmarked (incompatible with Python 3.13 free-threaded)")
    print("=" * 110)


if __name__ == "__main__":
    run_benchmarks()
