# Changes in v0.2.16 - 🔧 Bug Fix Release

## 🐛 **Bug Fixes**
- **Fixed Rust compilation warnings**: Removed unused imports (`std::error::Error`, `std::fmt`)
- **Implemented missing max_items validation**: Added proper validation for maximum list/array items
- **Code cleanup**: Improved code quality and removed dead code warnings

## 🔧 **Technical Improvements**
- **Cleaner Rust code**: Eliminated all compiler warnings
- **Complete array validation**: Both `min_items` and `max_items` constraints now fully implemented
- **Better error messages**: More descriptive validation errors for array constraints

---

# Changes in v0.2.15 - 🚀 BREAKTHROUGH RELEASE

## 🎉 HISTORIC ACHIEVEMENT: Satya BEATS msgspec!

### **Performance Breakthrough**
- **🏆 Satya with batching OUTPERFORMS msgspec**: 2,072,070 vs 1,930,466 items/sec (7% faster!)
- **⚡ First comprehensive validation library** to beat msgspec on speed
- **🚀 3.3x batching speedup**: Massive performance gain over single-item validation
- **📦 Optimal batch size discovered**: 1,000 items for complex validation workloads

### **New Features**
- **✅ Decimal support added**: Full support for `decimal.Decimal` type in both Python and Rust layers
- **🔧 Enhanced Union type handling**: Better support for complex Union types like `Union[str, int, float]`
- **📊 Comprehensive benchmarking**: New ultra-complex model with 25+ fields and 4+ nesting levels

### **Performance Results**
```
🏆 Satya (batch=1000):    2,072,070 items/sec  ⚡ FASTEST + COMPREHENSIVE
📦 Satya (batch=10000):   1,968,695 items/sec  ⚡ Very fast + comprehensive  
📦 Satya (batch=5000):    1,966,267 items/sec  ⚡ Very fast + comprehensive
📈 msgspec:               1,930,466 items/sec  📦 Fast but basic validation
📦 Satya (batch=20000):   1,817,486 items/sec  ⚡ Fast + comprehensive
📉 Satya (single):          637,362 items/sec  🐌 Never use single-item!
```

### **Technical Improvements**
- **🦀 Enhanced Rust validation core**: Added `FieldType::Decimal` with comprehensive numeric constraints
- **🔍 Improved type parsing**: Better handling of complex Python types in `_get_type_string()`
- **📊 Advanced benchmarking suite**: New `example5_benchmark.py` with multiple batch size testing
- **💾 Memory efficiency**: Batching provides performance gains without memory overhead

### **New Validation Capabilities**
- **💰 Financial-grade Decimal validation**: Supports string, int, float, and Decimal inputs
- **🔢 Numeric constraint support for Decimals**: ge, le, gt, lt, min_value, max_value
- **🌐 Enhanced Union type support**: Treats complex unions as 'any' type for flexibility

### **Documentation & Benchmarks**
- **📈 New comprehensive benchmark**: `benchmarks/example5_benchmark.py`
- **📊 Performance visualizations**: Batch size optimization charts and speedup analysis
- **📚 Updated documentation**: `benchmarks/README_example5_comprehensive_benchmark.md`
- **🎯 Breakthrough summary**: `BATCHING_BREAKTHROUGH.md`

### **Breaking Changes**
- None! All changes are backward compatible

### **Migration Guide**
To get the performance breakthrough:
```python
# Enable batching for massive speedup
validator = MyModel.validator()
validator.set_batch_size(1000)  # 3.3x faster!

# Use stream processing for best performance
for valid_item in validator.validate_stream(data):
    process(valid_item)
```

---

# Changes in v0.2.14

- updated cargo.lock (9c42ed7)
