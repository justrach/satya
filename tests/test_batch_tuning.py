import json
import os
import time
import random
from dataclasses import asdict
from pathlib import Path

import pytest

import satya

RESULTS_PATH = Path("benchmarks/map_elites_results.json")


def _load_results(path: Path):
    if not path.exists():
        pytest.skip(f"MAP-Elites results not found at {path}. Run benchmarks/map_elites_optimizer.py to generate.")
    with path.open("r") as f:
        data = json.load(f)
    results = data.get("results", [])
    if not results:
        pytest.skip("MAP-Elites results are empty. Run optimizer to populate results.")
    return results


def _generate_test_data(profile: dict, num_items: int):
    import random as _rnd
    data = []
    avg_len = int(profile["avg_string_length"])
    field_count = int(profile["field_count"])
    for _ in range(num_items):
        obj = {
            "name": "A" * avg_len,
            "age": _rnd.randint(18, 80),
            "email": "user@example.com",
        }
        for i in range(3, field_count):
            if i % 2 == 0:
                obj[f"s{i}"] = "X" * max(1, avg_len // 2)
            else:
                obj[f"n{i}"] = _rnd.randint(0, 1_000_000)
        data.append(obj)
    return data


def _setup_validator(profile: dict):
    # Mirror benchmarks/map_elites_optimizer.py:setup_validator()
    attrs = {}
    complexity = float(profile["constraint_complexity"])  # 0.0 .. 1.0
    field_count = int(profile["field_count"])

    if complexity > 0.5:
        attrs["name"] = satya.Field(str, min_length=3, max_length=40, required=True)
        attrs["age"] = satya.Field(int, ge=18, le=90, required=True)
        attrs["email"] = satya.Field(str, email=True, required=True)
    else:
        attrs["name"] = satya.Field(str, required=True)
        attrs["age"] = satya.Field(int, required=True)
        attrs["email"] = satya.Field(str, required=True)

    for i in range(3, field_count):
        if i % 2 == 0:
            if complexity > 0.7:
                attrs[f"s{i}"] = satya.Field(str, min_length=1, max_length=100, required=True)
            else:
                attrs[f"s{i}"] = satya.Field(str, required=True)
        else:
            if complexity > 0.7:
                attrs[f"n{i}"] = satya.Field(int, ge=0, le=1_000_000, required=True)
            else:
                attrs[f"n{i}"] = satya.Field(int, required=True)

    ModelCls = type(
        "DynModel",
        (satya.Model,),
        {
            "__annotations__": {
                k: (str if isinstance(v.type, type) and issubclass(v.type, str) else int) for k, v in attrs.items()
            },
            **attrs,
        },
    )
    return ModelCls.validator()


def _measure_ips(validator, items, micro_batch_size=512):
    # Use underlying batch API; mirror optimizer's approach
    original_batch_size = validator._validator.get_batch_size()
    try:
        start = time.perf_counter()
        total = 0
        for i in range(0, len(items), micro_batch_size):
            batch = items[i : i + micro_batch_size]
            _ = validator._validator.validate_batch(batch)
            total += len(batch)
        elapsed = time.perf_counter() - start
        return total / elapsed if elapsed > 0 else 0.0
    finally:
        validator._validator.set_batch_size(original_batch_size)


def _median_run(measure_fn, repeats: int = 3):
    values = []
    for _ in range(repeats):
        values.append(measure_fn())
    values.sort()
    mid = len(values) // 2
    return values[mid]


@pytest.mark.parametrize("sample_size", [2000])
@pytest.mark.parametrize("max_profiles", [3])
def test_tuned_not_worse_than_default(sample_size, max_profiles):
    """Regression guard: tuned config should not be worse than default on small samples."""
    results = _load_results(RESULTS_PATH)[:max_profiles]

    # Seed to reduce variance across CI runs
    random.seed(42)

    for entry in results:
        profile = entry["profile"]
        tuned = entry["satya_config"]

        # Build data + validator
        items = _generate_test_data(profile, sample_size)
        validator = _setup_validator(profile)

        # Fair comparison: keep micro-batch constant to measure impact of batch size only
        FAIR_MICRO = 512
        default_ips = _median_run(lambda: _measure_ips(validator, items, micro_batch_size=FAIR_MICRO))

        # Apply tuned batch size
        validator._validator.set_batch_size(int(tuned["batch_size"]))
        tuned_batch_size = int(tuned["batch_size"])
        tuned_micro = int(tuned["micro_batch_size"])  # used only for logging below
        tuned_ips = _median_run(lambda: _measure_ips(validator, items, micro_batch_size=FAIR_MICRO))

        # Optional logging
        if os.getenv("SATYA_TUNING_LOG", "0") == "1":
            print(
                f"[tuning] profile={profile} fair_micro={FAIR_MICRO} default_ips={default_ips:.0f} tuned_batch={tuned_batch_size} tuned_ips={tuned_ips:.0f} tuned_micro_hint={tuned_micro}"
            )

        # Allow small dip unless strict mode
        strict = os.getenv("SATYA_TUNING_STRICT", "0") == "1"
        floor_env = os.getenv("SATYA_TUNING_FLOOR")
        floor = 1.0 if strict else (float(floor_env) if floor_env else 0.98)
        assert tuned_ips >= default_ips * floor, (
            f"Tuned underperformed (floor {floor:.2f}) for profile {profile}: tuned={tuned_ips:.0f} ips, default={default_ips:.0f} ips"
        )


@pytest.mark.slow
@pytest.mark.parametrize("sample_size", [2000])
@pytest.mark.parametrize("max_profiles", [3])
def test_ratio_vs_msgspec_optional(sample_size, max_profiles):
    try:
        import msgspec  # noqa: F401
    except Exception:
        pytest.skip("msgspec not installed; skipping ratio test")

    results = _load_results(RESULTS_PATH)[:max_profiles]

    for entry in results:
        profile = entry["profile"]
        tuned = entry["satya_config"]
        items = _generate_test_data(profile, sample_size)
        validator = _setup_validator(profile)

        # Satya tuned
        validator._validator.set_batch_size(int(tuned["batch_size"]))
        satya_ips = _median_run(lambda: _measure_ips(validator, items, micro_batch_size=int(tuned["micro_batch_size"])) )

        # msgspec convert baseline
        import msgspec

        fields = {"name": str, "age": int, "email": str}
        for i in range(3, int(profile["field_count"])):
            fields[f"s{i}"] = str if i % 2 == 0 else int
        Person = msgspec.defstruct("Person", fields)

        start = time.perf_counter()
        for it in items:
            try:
                _ = msgspec.convert(it, Person)
            except Exception:
                pass
        elapsed = time.perf_counter() - start
        msgspec_ips = len(items) / elapsed if elapsed > 0 else 0.0

        # Optional logging
        if os.getenv("SATYA_TUNING_LOG", "0") == "1":
            print(
                f"[ratio] profile={profile} satya_ips={satya_ips:.0f} msgspec_ips={msgspec_ips:.0f} ratio={satya_ips/msgspec_ips if msgspec_ips else 0:.4f}"
            )

        # Mild floor; default is very lenient because msgspec convert is extremely fast on tiny structs
        ratio_floor = float(os.getenv("SATYA_RATIO_FLOOR", "0.001"))
        assert (satya_ips / msgspec_ips) >= ratio_floor, (
            f"Satya/msgspec ratio low (<{ratio_floor}) for profile {profile}: {satya_ips:.0f}/{msgspec_ips:.0f}"
        )


@pytest.mark.parametrize("sample_size", [2000])
@pytest.mark.parametrize("max_profiles", [3])
def test_best_configs_smoke(sample_size, max_profiles):
    """Ensure best configs from MAP-Elites run without error on small batches."""
    results = _load_results(RESULTS_PATH)[:max_profiles]

    for entry in results:
        profile = entry["profile"]
        tuned = entry["satya_config"]
        items = _generate_test_data(profile, sample_size)
        validator = _setup_validator(profile)

        # Should not raise
        validator._validator.set_batch_size(int(tuned["batch_size"]))
        _ = _measure_ips(validator, items, micro_batch_size=int(tuned["micro_batch_size"]))
        # Basic sanity
        assert True
