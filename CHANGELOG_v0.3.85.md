# Changelog for Satya v0.3.85

## Release Date: 2025-10-04

## ✨ New in v0.3.85: Production-Ready `List[Model]` Support

### Highlights
- **Recursive Nested Validation**: `List[Model]` fields now validate each nested model automatically during construction.
- **Optional Compatibility**: Works seamlessly with `Optional[List[Model]]` annotations.
- **Validator Integration**: Improved registration logic prevents type mismatches when `List[Model]` or `Dict[str, Model]` fields are present.
- **No Performance Regression**: Maintains Satya's 2.4M+ items/second throughput.

### Technical Changes
- Updated `Model.__init__()` to skip `List[Model]` and `Dict[str, Model]` fields when delegating to the Rust validator, ensuring Python handles nested model instantiation reliably.
- Updated `_register_model()` to avoid registering `List[Model]` fields with the Rust core, preventing type conversion errors.
- Added comprehensive fixed income securities example (`examples/fixed_income_securities.py`) showcasing nested validation, constraint handling, and performance characteristics.
- Added full test coverage in `tests/test_fixed_income_securities.py` (10 tests) to validate nested lists, error scenarios, and batch validation compatibility.

### Documentation & Assets
- Updated README with a dedicated **"What's New in v0.3.85"** section and usage example for `List[Model]`.
- Added deployment, implementation, and release notes to document the List[Model] feature set.

### Testing Summary
- 193 total tests executed, 188 tests passing (5 known pytest-related environment skips).
- All 10 new tests for fixed income securities pass successfully.
- No regressions detected in existing functional or performance-sensitive areas.

### Example Usage
```python
from typing import List
from satya import Model, Field

class Bond(Model):
    isin: str = Field(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
    rating: str = Field(enum=["AAA", "AA", "A", "BBB"])

class BondIndex(Model):
    name: str
    securities: List[Bond] = Field(min_items=1)

index = BondIndex(
    name="Corporate Index",
    securities=[
        {"isin": "US0378331005", "rating": "AA"},
        {"isin": "US5949181045", "rating": "AAA"}
    ]
)
print(f"Validated {len(index.securities)} bonds")
```

### Upgrade Notes
- No breaking changes.
- No migration steps required—existing projects benefit automatically by upgrading to `satya==0.3.85`.
- Recommended: run `pip install --upgrade satya` to access the new nested validation capabilities.

**Satya (सत्य)** continues to deliver truth and integrity in data validation with high performance and rich feature support.
