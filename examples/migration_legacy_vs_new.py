"""
Side-by-side examples to help migrate from legacy Satya bindings (v0.2) to v0.3+ model-first DX.

Run this file to see both patterns (they do not require a running server). The legacy
section uses the low-level core for illustrative purposes; prefer the new DX below.
"""

# --- Legacy (pre-v0.3): manual schema on core ---
# Note: This remains for reference. Prefer the model-first API below.

def legacy_example():
    try:
        from satya._satya import StreamValidatorCore
    except Exception as e:
        print("Legacy core not available:", e)
        return

    core = StreamValidatorCore()
    core.add_field('id', 'int', True)
    core.add_field('email', 'str', True)
    core.set_field_constraints('email', email=True)

    items = [{"id": 1, "email": "a@b.com"}, {"id": "x", "email": "bad"}]
    oks = core.validate_batch(items)
    print("Legacy validate_batch ->", oks)

    ok_json = core.validate_json_bytes(b'{"id": 123, "email": "a@b.com"}')
    print("Legacy validate_json_bytes ->", ok_json)


# --- New (v0.3+): model-first DX ---

def new_example():
    from typing import List
    from satya import Model, Field, ModelValidationError

    class User(Model):
        id: int
        email: str = Field(email=True)
        tags: List[str] = Field(default=[], min_items=0)

    # 1) Validate on init (raises on error)
    try:
        u = User(id=1, email="a@b.com", tags=["alpha"])  # ok
        print("New init ->", u.model_dump())
        User(id="x", email="not-an-email")  # will raise
    except ModelValidationError as e:
        print("New init error ->", [str(err) for err in e.errors])

    # 2) Explicit validate
    u2 = User.model_validate({"id": 2, "email": "c@d.com"})
    print("New model_validate ->", u2.model_dump())

    # 3) Batch/stream
    oks = User.validator().validate_batch([
        {"id": 3, "email": "ok@e.com"},
        {"id": "x", "email": "bad"},
    ])
    print("New validate_batch ->", oks)

    # 4) JSON bytes helpers (streaming)
    ok = User.model_validate_json_bytes(b'{"id": 10, "email":"a@b.com"}', streaming=True)
    print("New model_validate_json_bytes(streaming) ->", ok)
    oks = User.model_validate_json_array_bytes(b'[{"id":1,"email":"a@b.com"},{"id":"x"}]', streaming=True)
    print("New model_validate_json_array_bytes(streaming) ->", oks)


if __name__ == "__main__":
    print("--- Legacy example ---")
    legacy_example()
    print("\n--- New example ---")
    new_example()
