# Example4 Benchmark: Satya vs msgspec

This benchmark compares the performance of Satya against msgspec using the complex User model from `examples/example4.py`.

## Model Complexity

The benchmark uses a highly complex nested model structure that includes:

- **User Model** with 11 fields including:
  - UUID validation with regex pattern
  - Email validation
  - Enum validation (PublicationStatus)
  - Numeric range validation (age: 13-120, score: 0-100)
  - Complex nested objects (Address, SocialMedia profiles)
  - Lists with length constraints
  - Optional datetime fields

- **Address Model** with:
  - String length validation
  - Regex pattern validation for city names and postal codes
  - Nested GeoLocation with latitude/longitude range validation

- **SocialMedia Model** with:
  - Literal type validation for platforms
  - Regex pattern validation for usernames
  - URL validation

## Benchmark Configuration

- **Dataset Size**: 500,000 complex user records
- **Batch Size**: 10,000 items per batch
- **Validation Features**: Full field validation including patterns, ranges, and nested object validation

## Results

### Performance Comparison

| Metric | Satya | msgspec | Winner |
|--------|-------|---------|---------|
| **Total Time** | 0.30s | 0.29s | msgspec (1.0x faster) |
| **Items/Second** | 1,642,209 | 1,715,283 | msgspec |
| **Memory Usage** | 0.6MB | 0.3MB | msgspec (2.2x less) |
| **Single Item Validation** | 0.02ms | 0.11ms | Satya (5.5x faster) |

### Key Findings

1. **Overall Performance**: msgspec is slightly faster for bulk validation (1.0x faster)
2. **Memory Efficiency**: msgspec uses significantly less memory (2.2x less)
3. **Single Item Performance**: Satya is much faster for individual validations (5.5x faster)
4. **Validation Depth**: Satya provides much more comprehensive validation:
   - Regex pattern validation
   - Range validation
   - Email validation
   - URL validation
   - Custom field constraints

### Trade-offs

**Satya Advantages:**
- Much more comprehensive validation rules
- Better single-item validation performance
- Rich validation error reporting
- More expressive field constraints

**msgspec Advantages:**
- Slightly faster bulk processing
- Lower memory usage
- Simpler model definitions
- Faster for basic type checking

## Running the Benchmark

```bash
cd benchmarks
python example4_benchmark.py
```

## Generated Files

- `benchmarks/results/example4_benchmark_results.json` - Raw benchmark data
- `benchmarks/results/example4_satya_vs_msgspec.png` - Performance comparison chart
- `benchmarks/results/example4_memory_comparison.png` - Memory usage comparison chart

## Conclusion

While msgspec shows slight advantages in bulk processing speed and memory usage, Satya provides significantly more comprehensive validation capabilities. The choice between them depends on whether you prioritize raw speed (msgspec) or comprehensive validation features (Satya).

For applications requiring detailed validation rules, error reporting, and data integrity, Satya's comprehensive validation makes it the better choice despite the small performance trade-off. 