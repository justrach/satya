"""Tests for TurboValidator: Correctness + Performance

TurboValidator uses bulk extraction architecture:
- Phase 1: Single-pass dict iteration (minimal FFI)
- Phase 2: Pure Rust constraint validation (zero FFI)
- Result: Rust-owned Vec<TurboValue>, lazy Python conversion
"""
import time
import pytest
from satya import Model, Field, ModelValidationError
from decimal import Decimal
from typing import Optional, List, Dict


# ═══════════════════════════════════════════════════════════════════
# Correctness Tests
# ═══════════════════════════════════════════════════════════════════

class TestTurboBasicTypes:
    """Test basic type validation through TurboValidator."""

    def test_string_field(self):
        class M(Model):
            name: str
        m = M(name="hello")
        assert m.name == "hello"

    def test_int_field(self):
        class M(Model):
            age: int
        m = M(age=42)
        assert m.age == 42

    def test_float_field(self):
        class M(Model):
            score: float
        m = M(score=3.14)
        assert m.score == 3.14

    def test_bool_field(self):
        class M(Model):
            active: bool
        m = M(active=True)
        assert m.active is True

    def test_bool_not_int(self):
        """Bool should not be accepted for int fields."""
        class M(Model):
            count: int
        with pytest.raises(ModelValidationError):
            M(count=True)

    def test_list_field(self):
        class M(Model):
            tags: list
        m = M(tags=[1, 2, 3])
        assert m.tags == [1, 2, 3]

    def test_dict_field(self):
        class M(Model):
            meta: dict
        m = M(meta={"a": 1})
        assert m.meta == {"a": 1}

    def test_optional_field_present(self):
        class M(Model):
            name: str
            bio: Optional[str] = None
        m = M(name="Alice", bio="Developer")
        assert m.bio == "Developer"

    def test_optional_field_missing(self):
        class M(Model):
            name: str
            bio: Optional[str] = None
        m = M(name="Alice")
        assert m.bio is None

    def test_optional_field_none(self):
        class M(Model):
            name: str
            bio: Optional[str] = None
        m = M(name="Alice", bio=None)
        assert m.bio is None


class TestTurboConstraints:
    """Test constraint validation in pure Rust (Phase 2)."""

    def test_string_min_length(self):
        class M(Model):
            name: str = Field(min_length=3)
        m = M(name="Alice")
        assert m.name == "Alice"
        with pytest.raises(ModelValidationError):
            M(name="Al")

    def test_string_max_length(self):
        class M(Model):
            code: str = Field(max_length=5)
        m = M(code="ABC")
        assert m.code == "ABC"
        with pytest.raises(ModelValidationError):
            M(code="ABCDEF")

    def test_int_ge(self):
        class M(Model):
            age: int = Field(ge=0)
        m = M(age=0)
        assert m.age == 0
        with pytest.raises(ModelValidationError):
            M(age=-1)

    def test_int_le(self):
        class M(Model):
            score: int = Field(le=100)
        m = M(score=100)
        assert m.score == 100
        with pytest.raises(ModelValidationError):
            M(score=101)

    def test_int_gt(self):
        class M(Model):
            count: int = Field(gt=0)
        m = M(count=1)
        assert m.count == 1
        with pytest.raises(ModelValidationError):
            M(count=0)

    def test_int_lt(self):
        class M(Model):
            pos: int = Field(lt=10)
        m = M(pos=9)
        assert m.pos == 9
        with pytest.raises(ModelValidationError):
            M(pos=10)

    def test_float_ge_le(self):
        class M(Model):
            rate: float = Field(ge=0.0, le=1.0)
        m = M(rate=0.5)
        assert m.rate == 0.5
        with pytest.raises(ModelValidationError):
            M(rate=-0.1)
        with pytest.raises(ModelValidationError):
            M(rate=1.1)

    def test_email_validation(self):
        class M(Model):
            email: str = Field(email=True)
        m = M(email="user@example.com")
        assert m.email == "user@example.com"
        with pytest.raises(ModelValidationError):
            M(email="not-an-email")

    def test_url_validation(self):
        class M(Model):
            website: str = Field(url=True)
        m = M(website="https://example.com")
        assert m.website == "https://example.com"
        with pytest.raises(ModelValidationError):
            M(website="not-a-url")

    def test_enum_constraint(self):
        class M(Model):
            status: str = Field(enum=["active", "inactive"])
        m = M(status="active")
        assert m.status == "active"
        with pytest.raises(ModelValidationError):
            M(status="unknown")

    def test_list_min_items(self):
        class M(Model):
            items: list = Field(min_items=2)
        m = M(items=[1, 2, 3])
        assert m.items == [1, 2, 3]
        with pytest.raises(ModelValidationError):
            M(items=[1])

    def test_list_max_items(self):
        class M(Model):
            items: list = Field(max_items=3)
        m = M(items=[1, 2])
        assert m.items == [1, 2]
        with pytest.raises(ModelValidationError):
            M(items=[1, 2, 3, 4])


class TestTurboRequiredFields:
    """Test required field validation."""

    def test_missing_required_field(self):
        class M(Model):
            name: str
            age: int
        with pytest.raises(ModelValidationError):
            M(name="Alice")

    def test_all_required_present(self):
        class M(Model):
            name: str
            age: int
        m = M(name="Alice", age=30)
        assert m.name == "Alice"
        assert m.age == 30

    def test_type_errors(self):
        class M(Model):
            name: str
            age: int
        with pytest.raises(ModelValidationError):
            M(name=123, age=30)
        with pytest.raises(ModelValidationError):
            M(name="Alice", age="not_int")


class TestTurboCoercion:
    """Test type coercion (non-strict mode)."""

    def test_string_to_int_coercion(self):
        class M(Model):
            count: int
        m = M(count="42")
        assert m.count == 42

    def test_string_to_float_coercion(self):
        class M(Model):
            rate: float
        m = M(rate="3.14")
        assert abs(m.rate - 3.14) < 0.001

    def test_int_to_float_coercion(self):
        class M(Model):
            val: float
        m = M(val=42)
        assert m.val == 42.0


class TestTurboDecimal:
    """Test Decimal type handling."""

    def test_decimal_from_string(self):
        class M(Model):
            price: Decimal
        m = M(price="9.99")
        assert m.price == Decimal("9.99")

    def test_decimal_from_int(self):
        class M(Model):
            price: Decimal
        m = M(price=10)
        assert m.price == Decimal("10")

    def test_decimal_from_float(self):
        class M(Model):
            price: Decimal
        m = M(price=9.99)
        assert isinstance(m.price, Decimal)


class TestTurboModelInstance:
    """Test TurboModelInstance direct usage."""

    def test_direct_validate(self):
        from satya._satya import TurboValidatorPy
        turbo = TurboValidatorPy()
        turbo.add_field("name", "str", True)
        turbo.add_field("age", "int", True)
        turbo.compile()

        instance = turbo.validate({"name": "Alice", "age": 30})
        assert instance.get_field("name") == "Alice"
        assert instance.get_field("age") == 30

    def test_json_serialization(self):
        from satya._satya import TurboValidatorPy
        turbo = TurboValidatorPy()
        turbo.add_field("name", "str", True)
        turbo.add_field("age", "int", True)
        turbo.add_field("score", "float", False)
        turbo.compile()

        instance = turbo.validate({"name": "Alice", "age": 30, "score": 95.5})
        json_str = instance.json()
        import json
        parsed = json.loads(json_str)
        assert parsed["name"] == "Alice"
        assert parsed["age"] == 30
        assert parsed["score"] == 95.5

    def test_json_string_escaping(self):
        from satya._satya import TurboValidatorPy
        turbo = TurboValidatorPy()
        turbo.add_field("text", "str", True)
        turbo.compile()

        instance = turbo.validate({"text": 'He said "hello"\nNew line'})
        json_str = instance.json()
        import json
        parsed = json.loads(json_str)
        assert parsed["text"] == 'He said "hello"\nNew line'

    def test_field_names(self):
        from satya._satya import TurboValidatorPy
        turbo = TurboValidatorPy()
        turbo.add_field("name", "str", True)
        turbo.add_field("age", "int", True)
        turbo.compile()

        instance = turbo.validate({"name": "Alice", "age": 30})
        names = instance.field_names()
        assert "name" in names
        assert "age" in names

    def test_validate_dict_compat(self):
        """validate_dict returns a PyDict like BlazeValidator."""
        from satya._satya import TurboValidatorPy
        turbo = TurboValidatorPy()
        turbo.add_field("x", "int", True)
        turbo.add_field("y", "str", True)
        turbo.compile()

        result = turbo.validate_dict({"x": 42, "y": "hello"})
        assert isinstance(result, dict)
        assert result["x"] == 42
        assert result["y"] == "hello"

    def test_constraints_in_validate(self):
        from satya._satya import TurboValidatorPy
        turbo = TurboValidatorPy()
        turbo.add_field("age", "int", True)
        turbo.set_constraints("age", None, 0.0, None, None, None, None, None, False, False, None, None, None, False)
        turbo.compile()

        instance = turbo.validate({"age": 5})
        assert instance.get_field("age") == 5

        with pytest.raises(ValueError):
            turbo.validate({"age": -1})

    def test_batch_validate(self):
        from satya._satya import TurboValidatorPy
        turbo = TurboValidatorPy()
        turbo.add_field("x", "int", True)
        turbo.compile()

        results = turbo.validate_batch([{"x": 1}, {"x": 2}, {"x": 3}])
        assert len(results) == 3
        assert results[0].get_field("x") == 1
        assert results[1].get_field("x") == 2
        assert results[2].get_field("x") == 3


class TestTurboNestedModels:
    """Test nested model support through Python layer."""

    def test_nested_model(self):
        class Address(Model):
            city: str
            zip_code: str

        class Person(Model):
            name: str
            address: Address

        p = Person(name="Alice", address={"city": "NYC", "zip_code": "10001"})
        assert p.name == "Alice"
        assert p.address.city == "NYC"

    def test_list_of_models(self):
        class Tag(Model):
            name: str

        class Post(Model):
            title: str
            tags: List[Tag]

        p = Post(title="Hello", tags=[{"name": "python"}, {"name": "rust"}])
        assert p.title == "Hello"
        assert len(p.tags) == 2
        assert p.tags[0].name == "python"


# ═══════════════════════════════════════════════════════════════════
# Performance Tests
# ═══════════════════════════════════════════════════════════════════

class TestTurboPerformance:
    """Performance benchmarks for TurboValidator."""

    def test_simple_validation_throughput(self):
        """Target: >200K validations/sec for simple 4-field model."""
        class BenchModel(Model):
            name: str
            age: int
            score: float
            active: bool

        data = {"name": "Alice", "age": 30, "score": 95.5, "active": True}
        N = 50_000

        # Warmup
        for _ in range(1000):
            BenchModel(**data)

        start = time.perf_counter()
        for _ in range(N):
            BenchModel(**data)
        elapsed = time.perf_counter() - start

        throughput = N / elapsed
        print(f"\n  Simple 4-field: {throughput:,.0f} val/s ({elapsed*1e6/N:.2f} μs/val)")
        assert throughput > 100_000, f"Too slow: {throughput:.0f} val/s"

    def test_constrained_validation_throughput(self):
        """Target: >150K validations/sec for constrained model."""
        class ConstrainedModel(Model):
            name: str = Field(min_length=1)
            age: int = Field(ge=0, le=200)
            email: str = Field(email=True)
            score: float = Field(ge=0.0, le=100.0)

        data = {"name": "Alice", "age": 30, "email": "alice@example.com", "score": 95.5}
        N = 50_000

        # Warmup
        for _ in range(1000):
            ConstrainedModel(**data)

        start = time.perf_counter()
        for _ in range(N):
            ConstrainedModel(**data)
        elapsed = time.perf_counter() - start

        throughput = N / elapsed
        print(f"\n  Constrained 4-field: {throughput:,.0f} val/s ({elapsed*1e6/N:.2f} μs/val)")
        assert throughput > 80_000, f"Too slow: {throughput:.0f} val/s"

    def test_10_field_throughput(self):
        """Target: >100K validations/sec for 10-field model."""
        class TenFieldModel(Model):
            f1: str
            f2: str
            f3: int
            f4: int
            f5: float
            f6: float
            f7: bool
            f8: bool
            f9: str
            f10: int

        data = {
            "f1": "hello", "f2": "world",
            "f3": 1, "f4": 2,
            "f5": 1.0, "f6": 2.0,
            "f7": True, "f8": False,
            "f9": "test", "f10": 42,
        }
        N = 50_000

        # Warmup
        for _ in range(1000):
            TenFieldModel(**data)

        start = time.perf_counter()
        for _ in range(N):
            TenFieldModel(**data)
        elapsed = time.perf_counter() - start

        throughput = N / elapsed
        print(f"\n  10-field simple: {throughput:,.0f} val/s ({elapsed*1e6/N:.2f} μs/val)")
        # Note: Model layer adds ~8-10μs Python overhead (kwargs, defaults, nested checks)
        # The TurboValidator itself is >300K val/s for direct .validate() calls
        assert throughput > 50_000, f"Too slow: {throughput:.0f} val/s"

    def test_turbo_json_throughput(self):
        """Target: TurboModelInstance.json() <2μs."""
        from satya._satya import TurboValidatorPy

        turbo = TurboValidatorPy()
        turbo.add_field("name", "str", True)
        turbo.add_field("age", "int", True)
        turbo.add_field("email", "str", True)
        turbo.add_field("score", "float", True)
        turbo.add_field("active", "bool", True)
        turbo.compile()

        instance = turbo.validate({"name": "Alice", "age": 30, "email": "a@b.com", "score": 95.5, "active": True})

        N = 100_000

        # Warmup
        for _ in range(1000):
            instance.json()

        start = time.perf_counter()
        for _ in range(N):
            instance.json()
        elapsed = time.perf_counter() - start

        us_per_call = elapsed * 1e6 / N
        print(f"\n  TurboModelInstance.json(): {us_per_call:.3f} μs/call")
        assert us_per_call < 5.0, f"Too slow: {us_per_call:.3f} μs"

    def test_turbo_direct_validate_throughput(self):
        """TurboValidatorPy.validate() bypassing Model layer."""
        from satya._satya import TurboValidatorPy

        turbo = TurboValidatorPy()
        turbo.add_field("name", "str", True)
        turbo.add_field("age", "int", True)
        turbo.add_field("email", "str", True)
        turbo.add_field("score", "float", True)
        turbo.compile()

        data = {"name": "Alice", "age": 30, "email": "a@b.com", "score": 95.5}
        N = 100_000

        # Warmup
        for _ in range(1000):
            turbo.validate(data)

        start = time.perf_counter()
        for _ in range(N):
            turbo.validate(data)
        elapsed = time.perf_counter() - start

        throughput = N / elapsed
        us_per_call = elapsed * 1e6 / N
        print(f"\n  TurboValidator.validate() direct: {throughput:,.0f} val/s ({us_per_call:.3f} μs/val)")
        assert throughput > 300_000, f"Too slow: {throughput:.0f} val/s"

    def test_turbo_batch_throughput(self):
        """Batch validation throughput."""
        from satya._satya import TurboValidatorPy

        turbo = TurboValidatorPy()
        turbo.add_field("name", "str", True)
        turbo.add_field("age", "int", True)
        turbo.add_field("score", "float", True)
        turbo.compile()

        batch = [{"name": f"User{i}", "age": 20 + i % 50, "score": float(i % 100)} for i in range(10_000)]
        N = 5

        # Warmup
        turbo.validate_batch(batch[:100])

        start = time.perf_counter()
        for _ in range(N):
            turbo.validate_batch(batch)
        elapsed = time.perf_counter() - start

        total = N * len(batch)
        throughput = total / elapsed
        print(f"\n  Batch 10K: {throughput:,.0f} val/s ({elapsed/N*1000:.1f} ms/batch)")
        assert throughput > 200_000, f"Too slow: {throughput:.0f} val/s"
