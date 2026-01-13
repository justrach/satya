"""
Benchmark: SIMD-accelerated email/URL validation vs regex

This benchmark compares:
1. New SIMD-accelerated validation (turbo_validate_email, turbo_validate_url)
2. Python regex validation
3. Overall validation performance improvements

Expected improvements:
- Email validation: 10-20x faster than regex
- URL validation: 5-10x faster than regex
- Overall throughput increase: 20-40% for models with email/URL fields
"""

import time
import re
from satya._satya import turbo_validate_email, turbo_validate_url

# Test data
TEST_EMAILS_VALID = [
    "test@example.com",
    "user.name+tag@domain.co.uk",
    "admin@localhost.org",
    "john.doe123@company-name.com",
    "support@sub.domain.example.com",
] * 1000  # 5000 valid emails

TEST_EMAILS_INVALID = [
    "invalid",
    "@domain.com",
    "user@",
    "user@domain",
    "no-at-sign",
] * 1000  # 5000 invalid emails

TEST_URLS_VALID = [
    "http://example.com",
    "https://example.com/path",
    "https://api.example.com:8080/v1/users",
    "http://localhost:3000",
    "https://subdomain.example.co.uk/path/to/resource",
] * 1000  # 5000 valid URLs

TEST_URLS_INVALID = [
    "ftp://example.com",
    "example.com",
    "//example.com",
    "htp://example.com",
    "httpx://invalid",
] * 1000  # 5000 invalid URLs

# Python regex patterns for comparison
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
URL_REGEX = re.compile(r"^https?://[A-Za-z0-9.-]+(?::\d+)?(?:/[^\s]*)?$")

def benchmark_email_regex(emails):
    """Benchmark Python regex email validation"""
    return sum(1 for email in emails if EMAIL_REGEX.match(email))

def benchmark_email_turbo(emails):
    """Benchmark SIMD-accelerated email validation"""
    return sum(1 for email in emails if turbo_validate_email(email))

def benchmark_url_regex(urls):
    """Benchmark Python regex URL validation"""
    return sum(1 for url in urls if URL_REGEX.match(url))

def benchmark_url_turbo(urls):
    """Benchmark SIMD-accelerated URL validation"""
    return sum(1 for url in urls if turbo_validate_url(url))

def run_benchmark(name, func, data, iterations=10):
    """Run a benchmark and return timing statistics"""
    times = []
    result = None

    for _ in range(iterations):
        start = time.perf_counter()
        result = func(data)
        end = time.perf_counter()
        times.append(end - start)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    ops_per_sec = len(data) / avg_time

    return {
        "name": name,
        "avg_time_ms": avg_time * 1000,
        "min_time_ms": min_time * 1000,
        "ops_per_sec": ops_per_sec,
        "result": result,
    }

def main():
    print("=" * 70)
    print("SATYA TURBO VALIDATION BENCHMARK")
    print("=" * 70)
    print()

    # Email validation benchmarks
    print("-" * 70)
    print("EMAIL VALIDATION BENCHMARKS")
    print("-" * 70)

    all_emails = TEST_EMAILS_VALID + TEST_EMAILS_INVALID

    regex_result = run_benchmark("Python Regex (email)", benchmark_email_regex, all_emails)
    turbo_result = run_benchmark("SIMD Turbo (email)", benchmark_email_turbo, all_emails)

    print(f"\nPython Regex:")
    print(f"  Average time: {regex_result['avg_time_ms']:.2f} ms")
    print(f"  Throughput:   {regex_result['ops_per_sec']:,.0f} ops/sec")
    print(f"  Valid count:  {regex_result['result']}")

    print(f"\nSIMD Turbo:")
    print(f"  Average time: {turbo_result['avg_time_ms']:.2f} ms")
    print(f"  Throughput:   {turbo_result['ops_per_sec']:,.0f} ops/sec")
    print(f"  Valid count:  {turbo_result['result']}")

    speedup = regex_result['avg_time_ms'] / turbo_result['avg_time_ms']
    print(f"\n✨ SPEEDUP: {speedup:.1f}x faster than regex!")

    # URL validation benchmarks
    print()
    print("-" * 70)
    print("URL VALIDATION BENCHMARKS")
    print("-" * 70)

    all_urls = TEST_URLS_VALID + TEST_URLS_INVALID

    regex_result = run_benchmark("Python Regex (URL)", benchmark_url_regex, all_urls)
    turbo_result = run_benchmark("SIMD Turbo (URL)", benchmark_url_turbo, all_urls)

    print(f"\nPython Regex:")
    print(f"  Average time: {regex_result['avg_time_ms']:.2f} ms")
    print(f"  Throughput:   {regex_result['ops_per_sec']:,.0f} ops/sec")
    print(f"  Valid count:  {regex_result['result']}")

    print(f"\nSIMD Turbo:")
    print(f"  Average time: {turbo_result['avg_time_ms']:.2f} ms")
    print(f"  Throughput:   {turbo_result['ops_per_sec']:,.0f} ops/sec")
    print(f"  Valid count:  {turbo_result['result']}")

    speedup = regex_result['avg_time_ms'] / turbo_result['avg_time_ms']
    print(f"\n✨ SPEEDUP: {speedup:.1f}x faster than regex!")

    # TurboValidator comparison
    print()
    print("-" * 70)
    print("TURBOVALIDATOR MODEL VALIDATION")
    print("-" * 70)

    try:
        from satya._satya import TurboValidator

        # Create validator with email and URL fields
        validator = TurboValidator()
        validator.add_field("email", "str", True)
        validator.add_field("website", "str", True)
        validator.add_field("name", "str", True)
        validator.add_field("age", "int", True)
        validator.set_constraints("email", None, None, None, None, None, None, None, True, False, None, None, None, False)
        validator.set_constraints("website", None, None, None, None, None, None, None, False, True, None, None, None, False)
        validator.compile()

        # Test data
        test_data = [
            {"email": "test@example.com", "website": "https://example.com", "name": "John", "age": 30},
        ] * 1000

        # Benchmark TurboValidator
        start = time.perf_counter()
        for item in test_data:
            validator.validate(item)
        end = time.perf_counter()

        turbo_time = (end - start) * 1000
        turbo_ops = len(test_data) / (end - start)

        print(f"\nTurboValidator (with email+URL fields):")
        print(f"  Time:       {turbo_time:.2f} ms for 1000 items")
        print(f"  Throughput: {turbo_ops:,.0f} ops/sec")

    except Exception as e:
        print(f"\nTurboValidator test failed: {e}")

    print()
    print("=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
