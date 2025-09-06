import json
import os
import random
import sys
from typing import List

import pytest

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import satya


class Person(satya.Model):
    name: str
    age: int
    email: str


def make_batch(n: int) -> List[dict]:
    first_names = ["John","Jane","Bob","Alice","Charlie","Diana","Edward","Fiona"]
    last_names = ["Smith","Johnson","Brown","Davis","Miller","Wilson","Moore","Taylor"]
    domains = ["example.com","test.com","benchmark.org","sample.net","demo.io"]
    out = []
    for _ in range(n):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        out.append({
            "name": name,
            "age": random.randint(18, 80),
            "email": f"{name.lower().replace(' ', '.')}@{random.choice(domains)}",
        })
    return out


def test_validate_json_object_bytes():
    v = Person.validator()
    item = {"name": "John Doe", "age": 30, "email": "john@example.com"}
    data = json.dumps(item).encode()
    ok = v.validate_json(data, mode="object")
    assert ok is True

    bad_data = b'{"name": 123, "age": "x", "email": false}'
    ok2 = v.validate_json(bad_data, mode="object")
    assert ok2 is False


def test_validate_json_array_bytes_matches_batch():
    v = Person.validator()
    batch = make_batch(200)
    arr_bytes = json.dumps(batch).encode()

    # JSON array path
    res_json = v.validate_json(arr_bytes, mode="array")
    assert isinstance(res_json, list)
    assert len(res_json) == len(batch)

    # Dict path
    res_dict = v.validate_batch(batch)
    assert res_dict == res_json


def test_validate_ndjson_bytes():
    v = Person.validator()
    batch = make_batch(100)
    ndjson = "\n".join(json.dumps(x) for x in batch).encode()
    res = v.validate_json(ndjson, mode="ndjson")
    assert isinstance(res, list)
    assert len(res) == len(batch)
    assert all(res)


def test_validate_json_requires_correct_top_level():
    v = Person.validator()
    # Array provided to object mode -> error
    arr = json.dumps([{"a":1}]).encode()
    with pytest.raises(ValueError):
        # Python wrapper checks mode name; core raises ValueError for wrong top-level
        v.validate_json(arr, mode="object")

    # Object provided to array mode -> should raise
    obj = json.dumps({"a": 1}).encode()
    with pytest.raises(Exception):
        v.validate_json(obj, mode="array")
