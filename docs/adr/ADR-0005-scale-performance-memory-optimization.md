# ADR-0005: Scale Performance Analysis and Memory Optimization Strategy

## Status
Accepted

## Context
After optimizing Satya's validation performance (ADR-0003), we discovered significant performance variance based on dataset scale and memory pressure. Performance testing revealed different characteristics at different scales that affect competitive positioning against msgspec and Pydantic.

## Performance Analysis by Scale

### Small Scale (100k items, 10k batches)
**Command:** `python3 benchmarks/streaming_validation_benchmark.py --items 100000 --batch 10000 --mode object --compare-libs`

**Results:**
- **Satya dict-path: 8.20M items/s** 🥇 (beats msgspec)
- msgspec+json: 7.50M items/s 🥈
- Satya json-stream: 3.54M items/s 
- orjson.loads+dict: 3.41M items/s
- Pydantic+orjson: 1.62M items/s

**Memory usage:** 1.4MB (dict-path), 0.1MB (streaming)

### Large Scale (5M items, 50k batches)  
**Command:** `python3 benchmarks/streaming_validation_benchmark.py --items 5000000 --batch 50000 --mode object --compare-libs`

**Results:**
- msgspec+json: 7.62M items/s 🥇 (regains lead)
- **Satya dict-path: 6.20M items/s** 🥈 (24% slower than small scale)
- Satya json-stream: 3.18M items/s
- orjson.loads+dict: 2.66M items/s  
- Pydantic+orjson: 0.76M items/s

**Memory usage:** 7.2MB (dict-path), 0.4MB (streaming), 21.5MB (orjson+dict)

### Production Scale (validation_benchmark_long.py: 5M items, 50k batches, 10 runs)
**Command:** `python3 benchmarks/validation_benchmark_long.py`

**Results (10-run average):**
- msgspec: 10.8M items/s 🥇 (42% faster than single-run)
- **Satya: 6.1M items/s** 🥈 (consistent with single-run)
- Pydantic: 2.4M items/s

## Problem Analysis

### Memory Pressure Impact
At scale, Satya's performance degrades due to:
1. **Increased memory allocation**: 7.2MB vs 1.4MB (5x increase)
2. **CPU cache misses**: Larger working sets exceed L3 cache
3. **GC pressure**: More Python objects trigger garbage collection
4. **Memory fragmentation**: Large batch processing creates fragmented heap

### msgspec's Scale Advantage
msgspec maintains performance at scale because:
1. **Zero-copy parsing**: Direct C struct creation, no Python dict overhead
2. **Minimal allocations**: Validates during parsing, no intermediate objects
3. **Cache-friendly**: Compact memory layout, better cache utilization
4. **No GC pressure**: C-level validation avoids Python object creation

## Decision: Memory Optimization Strategy

Implement aggressive memory optimizations to maintain Satya's competitive edge:

### 1. Streaming-First Architecture
- Default to streaming validation for large datasets
- Automatic fallback: use streaming when batch size > threshold
- Memory-bounded processing: limit working set size

### 2. Object Pool Optimization
- Pre-allocate validation result vectors
- Reuse Python object references across batches
- Minimize heap allocations in hot paths

### 3. Cache-Aware Batch Processing
- Optimize batch sizes for CPU cache (L3: ~8-32MB)
- Implement adaptive batching based on memory pressure
- Process in cache-friendly chunks

### 4. Zero-Copy Validation Paths
- Direct PyDict field access without intermediate copies
- Minimize string allocations in constraint checking
- Reuse error objects for common validation failures

## Implementation Plan

### Phase 1: Streaming Optimization
```rust
// Auto-select streaming for large datasets
fn validate_batch_adaptive(&self, items: Vec<&PyAny>) -> PyResult<Vec<bool>> {
    if items.len() > STREAMING_THRESHOLD {
        self.validate_batch_streaming(items)
    } else {
        self.validate_batch_direct(items)
    }
}
```

### Phase 2: Memory Pool Implementation  
```rust
// Pre-allocated result vectors
struct ValidationPool {
    result_buffers: Vec<Vec<bool>>,
    string_cache: HashMap<String, String>,
}
```

### Phase 3: Cache-Aware Processing
```rust
// Process in cache-friendly chunks
const CACHE_FRIENDLY_BATCH: usize = 16384; // ~64KB working set
```

## Success Metrics

### Target Performance (5M items, 50k batches)
- **Satya dict-path: >8M items/s** (maintain small-scale performance)
- **Memory usage: <4MB** (reduce from 7.2MB)
- **Consistent performance**: <10% variance across scales

### Competitive Positioning
- Match or exceed msgspec at all scales
- Maintain 3x+ advantage over Pydantic
- Preserve streaming memory efficiency (0.4MB target)

## Commands for Testing

```bash
# Small scale baseline
python3 benchmarks/streaming_validation_benchmark.py --items 100000 --batch 10000 --mode object --compare-libs

# Large scale test  
python3 benchmarks/streaming_validation_benchmark.py --items 5000000 --batch 50000 --mode object --compare-libs

# Production benchmark
python3 benchmarks/validation_benchmark_long.py

# Memory profiling
python3 -m memory_profiler benchmarks/streaming_validation_benchmark.py --items 1000000 --batch 25000 --mode object
```

## Future Considerations
- SIMD vectorization for constraint checking
- Parallel validation for multi-core utilization  
- JIT compilation for hot validation paths
- Custom allocator for validation-specific memory patterns
