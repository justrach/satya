// SIMD-friendly batch validation functions
// Structured for LLVM auto-vectorization with opt-level=3 + codegen-units=1
// Inspired by emergentDB's batch normalization patterns (chunked, unrolled, interleaved)

/// L2-cache-friendly chunk size for batch processing
/// 64 items * ~232 bytes per Python dict header = ~15KB (fits L1 data cache)
pub const BATCH_CHUNK_SIZE: usize = 64;

/// Batch-validate a >= constraint across many f64 values
/// This loop auto-vectorizes into NEON (aarch64) or AVX2 (x86_64)
#[inline]
pub fn batch_check_ge(values: &[f64], threshold: f64, results: &mut [bool]) {
    for (val, result) in values.iter().zip(results.iter_mut()) {
        *result = *result && (*val >= threshold);
    }
}

/// Batch-validate a <= constraint
#[inline]
pub fn batch_check_le(values: &[f64], threshold: f64, results: &mut [bool]) {
    for (val, result) in values.iter().zip(results.iter_mut()) {
        *result = *result && (*val <= threshold);
    }
}

/// Batch-validate a > constraint
#[inline]
pub fn batch_check_gt(values: &[f64], threshold: f64, results: &mut [bool]) {
    for (val, result) in values.iter().zip(results.iter_mut()) {
        *result = *result && (*val > threshold);
    }
}

/// Batch-validate a < constraint
#[inline]
pub fn batch_check_lt(values: &[f64], threshold: f64, results: &mut [bool]) {
    for (val, result) in values.iter().zip(results.iter_mut()) {
        *result = *result && (*val < threshold);
    }
}

/// Batch-validate finite constraint (no NaN or Inf)
#[inline]
pub fn batch_check_finite(values: &[f64], results: &mut [bool]) {
    for (val, result) in values.iter().zip(results.iter_mut()) {
        *result = *result && val.is_finite();
    }
}

/// Batch-validate string minimum length
#[inline]
pub fn batch_check_min_length(lengths: &[usize], min_len: usize, results: &mut [bool]) {
    for (len, result) in lengths.iter().zip(results.iter_mut()) {
        *result = *result && (*len >= min_len);
    }
}

/// Batch-validate string maximum length
#[inline]
pub fn batch_check_max_length(lengths: &[usize], max_len: usize, results: &mut [bool]) {
    for (len, result) in lengths.iter().zip(results.iter_mut()) {
        *result = *result && (*len <= max_len);
    }
}

/// Batch-validate multiple_of constraint
#[inline]
pub fn batch_check_multiple_of(values: &[f64], multiple: f64, results: &mut [bool]) {
    if multiple == 0.0 { return; }
    for (val, result) in values.iter().zip(results.iter_mut()) {
        *result = *result && ((*val % multiple).abs() <= f64::EPSILON);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_batch_check_ge() {
        let values = vec![1.0, 2.0, 3.0, 0.5, 5.0];
        let mut results = vec![true; 5];
        batch_check_ge(&values, 1.0, &mut results);
        assert_eq!(results, vec![true, true, true, false, true]);
    }

    #[test]
    fn test_batch_check_le() {
        let values = vec![1.0, 2.0, 3.0, 0.5, 5.0];
        let mut results = vec![true; 5];
        batch_check_le(&values, 3.0, &mut results);
        assert_eq!(results, vec![true, true, true, true, false]);
    }

    #[test]
    fn test_batch_check_finite() {
        let values = vec![1.0, f64::NAN, 3.0, f64::INFINITY, 5.0];
        let mut results = vec![true; 5];
        batch_check_finite(&values, &mut results);
        assert_eq!(results, vec![true, false, true, false, true]);
    }

    #[test]
    fn test_batch_check_min_length() {
        let lengths = vec![3, 5, 1, 10, 2];
        let mut results = vec![true; 5];
        batch_check_min_length(&lengths, 3, &mut results);
        assert_eq!(results, vec![true, true, false, true, false]);
    }
}
