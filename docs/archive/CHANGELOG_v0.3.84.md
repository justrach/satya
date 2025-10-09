# Changelog for Satya v0.3.84

## Release Date: 2025-10-04

## 🎯 Major Feature: Enhanced List[Model] Support

### New Capabilities
- **Complete `List[Model]` Validation**: Full support for nested list structures containing Model instances
- **Automatic Nested Validation**: Lists of custom models are now validated recursively during construction
- **Seamless Integration**: Works alongside existing `Dict[str, Model]` support

### What's Fixed
✅ `List[Model]` fields are now properly handled in Model construction  
✅ Nested validation occurs automatically for all list elements  
✅ Validator registration correctly skips `List[Model]` and `Dict[str, Model]` fields  
✅ Optional wrapped types (`Optional[List[Model]]`) now work correctly  

### Technical Changes

**Modified Files:**
- `src/satya/__init__.py`:
  - Enhanced `Model.__init__()` to detect and skip `List[Model]` fields from validator (lines 212-242)
  - Updated `_register_model()` to skip `List[Model]` fields during validator registration (lines 960-989)
  - Proper unwrapping of `Optional[T]` types before checking for nested models
  - Consistent handling across both validation and registration phases

### New Example & Tests

**Added Files:**
1. **`examples/fixed_income_securities.py`** (505 lines)
   - Comprehensive fixed income securities validation example
   - Demonstrates `List[Bond]` in `BondIndex` model
   - Shows real-world financial data validation use case
   - Includes 5 complete examples:
     - Single bond validation
     - Batch validation (3.6M bonds/second!)
     - Nested bond index validation
     - Constraint validation & error handling
     - Performance analysis across dataset sizes

2. **`tests/test_fixed_income_securities.py`** (318 lines, 10 tests)
   - Complete test coverage for `List[Model]` functionality
   - Tests for valid and invalid bond data
   - Tests for nested bond index structures
   - Batch validation tests
   - All 10 tests passing ✅

### Use Cases Enabled

```python
from satya import Model, Field
from typing import List

class Security(Model):
    symbol: str = Field(pattern=r'^[A-Z]{1,5}$')
    price: float = Field(min_value=0.0)
    rating: str = Field(enum=["AAA", "AA", "A", "BBB"])

class Portfolio(Model):
    name: str
    holdings: List[Security]  # Now fully supported!
    
# Validates entire structure including all nested securities
portfolio = Portfolio(
    name="Growth Portfolio",
    holdings=[
        {"symbol": "AAPL", "price": 175.50, "rating": "AAA"},
        {"symbol": "MSFT", "price": 380.25, "rating": "AA"}
    ]
)
```

### Performance

- **No performance regression**: List validation maintains Satya's high performance
- **Efficient nested validation**: Each model in the list is validated once during construction
- **Batch processing compatible**: Works seamlessly with existing batch validation APIs
- **Example performance**: 2.4M - 3.6M bonds/second in fixed income example

### Benefits

1. **Complete Pydantic-like Experience**: Now supports all common nested structure patterns
2. **Financial Data Validation**: Perfect for validating portfolios, indices, and complex instruments
3. **Zero Breaking Changes**: Existing code continues to work unchanged
4. **Type Safety**: Full Python type hint compatibility with `List[Model]`

### Migration Notes

**No migration required!** This is a pure enhancement. If you have existing code that worked around `List[Model]` limitations, it will now work natively.

### Example Scenarios

**Before v0.3.84** (workaround needed):
```python
# Had to validate list elements manually
class Index(Model):
    name: str
    # securities: List[Bond]  # Didn't work properly
```

**After v0.3.84** (native support):
```python
# Works perfectly out of the box!
class BondIndex(Model):
    name: str
    securities: List[Bond] = Field(min_items=1)  # Fully supported!
```

## Testing

- ✅ All 10 new tests passing
- ✅ All 178 existing tests still passing
- ✅ Zero breaking changes
- ✅ Full backward compatibility

## Documentation

- New comprehensive example: `examples/fixed_income_securities.py`
- Demonstrates real-world financial data validation
- Shows nested structure patterns
- Includes performance benchmarks

## What's Next

This enhancement completes the core nested structure support in Satya, enabling:
- Portfolio management systems
- Financial index construction
- Complex hierarchical data models
- Multi-level configuration systems

## Summary

v0.3.84 adds production-ready `List[Model]` support, making Satya even more powerful for validating complex, nested data structures. Perfect for financial applications, configuration management, and any scenario requiring hierarchical model validation.

**Satya (सत्य) - Truth and Integrity in Data Validation** 🚀
