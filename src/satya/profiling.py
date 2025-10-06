"""
Performance Profiling and Benchmarking Tools for Satya

Provides built-in profiling capabilities to track validation performance,
identify bottlenecks, and compare against other validation libraries.
"""

from typing import Dict, Any, List, Optional, Callable
import time
from dataclasses import dataclass, field
from statistics import mean, median, stdev
import json


@dataclass
class FieldStats:
    """Statistics for a single field"""
    field_name: str
    validation_count: int = 0
    total_time_us: float = 0.0
    min_time_us: float = float('inf')
    max_time_us: float = 0.0
    errors: int = 0
    
    @property
    def avg_time_us(self) -> float:
        return self.total_time_us / self.validation_count if self.validation_count > 0 else 0.0
    
    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "validation_count": self.validation_count,
            "avg_time_us": round(self.avg_time_us, 2),
            "min_time_us": round(self.min_time_us, 2),
            "max_time_us": round(self.max_time_us, 2),
            "total_time_us": round(self.total_time_us, 2),
            "errors": self.errors,
        }


@dataclass
class ValidationStats:
    """Overall validation statistics"""
    total_validations: int = 0
    successful_validations: int = 0
    failed_validations: int = 0
    total_time_us: float = 0.0
    field_stats: Dict[str, FieldStats] = field(default_factory=dict)
    validation_times: List[float] = field(default_factory=list)
    
    @property
    def avg_time_us(self) -> float:
        return self.total_time_us / self.total_validations if self.total_validations > 0 else 0.0
    
    @property
    def median_time_us(self) -> float:
        return median(self.validation_times) if self.validation_times else 0.0
    
    @property
    def stddev_time_us(self) -> float:
        return stdev(self.validation_times) if len(self.validation_times) > 1 else 0.0
    
    @property
    def min_time_us(self) -> float:
        return min(self.validation_times) if self.validation_times else 0.0
    
    @property
    def max_time_us(self) -> float:
        return max(self.validation_times) if self.validation_times else 0.0
    
    @property
    def success_rate(self) -> float:
        return self.successful_validations / self.total_validations if self.total_validations > 0 else 0.0
    
    @property
    def slowest_field(self) -> Optional[str]:
        if not self.field_stats:
            return None
        return max(self.field_stats.items(), key=lambda x: x[1].avg_time_us)[0]
    
    @property
    def bottleneck(self) -> Optional[str]:
        """Identify the bottleneck field (slowest average time)"""
        return self.slowest_field
    
    def to_dict(self) -> dict:
        return {
            "total_validations": self.total_validations,
            "successful_validations": self.successful_validations,
            "failed_validations": self.failed_validations,
            "success_rate": round(self.success_rate * 100, 2),
            "avg_time_us": round(self.avg_time_us, 2),
            "median_time_us": round(self.median_time_us, 2),
            "stddev_time_us": round(self.stddev_time_us, 2),
            "min_time_us": round(self.min_time_us, 2),
            "max_time_us": round(self.max_time_us, 2),
            "slowest_field": self.slowest_field,
            "bottleneck": self.bottleneck,
            "field_stats": {name: stats.to_dict() for name, stats in self.field_stats.items()},
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class ValidationProfiler:
    """Profile validation performance"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.stats = ValidationStats()
        self._tracked_models: Dict[str, Any] = {}
    
    def track(self, model_cls):
        """Decorator to track a model class"""
        if not self.enabled:
            return model_cls
        
        self._tracked_models[model_cls.__name__] = model_cls
        
        # Wrap the model_validate method
        original_validate = model_cls.model_validate
        
        def profiled_validate(data: Dict[str, Any]):
            start = time.perf_counter()
            try:
                result = original_validate(data)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                end = time.perf_counter()
                elapsed_us = (end - start) * 1_000_000
                
                self.stats.total_validations += 1
                self.stats.total_time_us += elapsed_us
                self.stats.validation_times.append(elapsed_us)
                
                if success:
                    self.stats.successful_validations += 1
                else:
                    self.stats.failed_validations += 1
            
            return result
        
        model_cls.model_validate = classmethod(lambda cls, data: profiled_validate(data))
        return model_cls
    
    def profile_field(self, field_name: str, validation_func: Callable):
        """Profile a single field validation"""
        def wrapper(value: Any):
            start = time.perf_counter()
            try:
                result = validation_func(value)
                success = True
            except Exception:
                success = False
                raise
            finally:
                end = time.perf_counter()
                elapsed_us = (end - start) * 1_000_000
                
                if field_name not in self.stats.field_stats:
                    self.stats.field_stats[field_name] = FieldStats(field_name)
                
                field_stat = self.stats.field_stats[field_name]
                field_stat.validation_count += 1
                field_stat.total_time_us += elapsed_us
                field_stat.min_time_us = min(field_stat.min_time_us, elapsed_us)
                field_stat.max_time_us = max(field_stat.max_time_us, elapsed_us)
                
                if not success:
                    field_stat.errors += 1
            
            return result
        
        return wrapper
    
    def get_stats(self) -> ValidationStats:
        """Get current statistics"""
        return self.stats
    
    def reset(self):
        """Reset all statistics"""
        self.stats = ValidationStats()
    
    def report(self, verbose: bool = True) -> str:
        """Generate a formatted report"""
        lines = []
        lines.append("=" * 60)
        lines.append("Satya Validation Performance Report")
        lines.append("=" * 60)
        lines.append("")
        
        stats = self.stats
        lines.append(f"Total Validations: {stats.total_validations:,}")
        lines.append(f"Successful: {stats.successful_validations:,} ({stats.success_rate * 100:.2f}%)")
        lines.append(f"Failed: {stats.failed_validations:,}")
        lines.append("")
        
        lines.append("Performance Metrics:")
        lines.append(f"  Average Time: {stats.avg_time_us:.2f} μs")
        lines.append(f"  Median Time:  {stats.median_time_us:.2f} μs")
        lines.append(f"  Std Dev:      {stats.stddev_time_us:.2f} μs")
        lines.append(f"  Min Time:     {stats.min_time_us:.2f} μs")
        lines.append(f"  Max Time:     {stats.max_time_us:.2f} μs")
        lines.append("")
        
        if stats.slowest_field:
            lines.append(f"Bottleneck Field: {stats.slowest_field}")
            bottleneck = stats.field_stats[stats.slowest_field]
            lines.append(f"  Avg Time: {bottleneck.avg_time_us:.2f} μs")
            lines.append("")
        
        if verbose and stats.field_stats:
            lines.append("Per-Field Statistics:")
            for field_name, field_stat in sorted(
                stats.field_stats.items(),
                key=lambda x: x[1].avg_time_us,
                reverse=True
            ):
                lines.append(f"  {field_name}:")
                lines.append(f"    Count: {field_stat.validation_count:,}")
                lines.append(f"    Avg:   {field_stat.avg_time_us:.2f} μs")
                lines.append(f"    Min:   {field_stat.min_time_us:.2f} μs")
                lines.append(f"    Max:   {field_stat.max_time_us:.2f} μs")
                if field_stat.errors > 0:
                    lines.append(f"    Errors: {field_stat.errors}")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def print_report(self, verbose: bool = True):
        """Print the performance report"""
        print(self.report(verbose=verbose))


class BenchmarkComparison:
    """Compare Satya performance against other libraries"""
    
    def __init__(self, iterations: int = 10000):
        self.iterations = iterations
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def benchmark_satya(self, model_cls, sample_data: Dict[str, Any]):
        """Benchmark Satya validation"""
        times = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            try:
                model_cls.model_validate(sample_data)
            except Exception:
                pass
            end = time.perf_counter()
            times.append((end - start) * 1_000_000)
        
        self.results['satya'] = {
            'avg_time_us': mean(times),
            'median_time_us': median(times),
            'min_time_us': min(times),
            'max_time_us': max(times),
            'stddev_us': stdev(times) if len(times) > 1 else 0,
            'total_time_s': sum(times) / 1_000_000,
            'throughput': self.iterations / (sum(times) / 1_000_000),
        }
    
    def benchmark_pydantic(self, model_cls, sample_data: Dict[str, Any]):
        """Benchmark Pydantic validation (if available)"""
        try:
            import pydantic
        except ImportError:
            self.results['pydantic'] = {'error': 'Pydantic not installed'}
            return
        
        times = []
        for _ in range(self.iterations):
            start = time.perf_counter()
            try:
                model_cls.model_validate(sample_data)
            except Exception:
                pass
            end = time.perf_counter()
            times.append((end - start) * 1_000_000)
        
        self.results['pydantic'] = {
            'avg_time_us': mean(times),
            'median_time_us': median(times),
            'min_time_us': min(times),
            'max_time_us': max(times),
            'stddev_us': stdev(times) if len(times) > 1 else 0,
            'total_time_s': sum(times) / 1_000_000,
            'throughput': self.iterations / (sum(times) / 1_000_000),
        }
    
    def report(self) -> str:
        """Generate comparison report"""
        if not self.results:
            return "No benchmark results available"
        
        lines = []
        lines.append("=" * 70)
        lines.append("Satya vs Competition - Performance Comparison")
        lines.append("=" * 70)
        lines.append(f"Iterations: {self.iterations:,}")
        lines.append("")
        
        for lib_name, results in self.results.items():
            if 'error' in results:
                lines.append(f"{lib_name.upper()}: {results['error']}")
                continue
            
            lines.append(f"{lib_name.upper()}:")
            lines.append(f"  Average Time:  {results['avg_time_us']:.2f} μs/validation")
            lines.append(f"  Median Time:   {results['median_time_us']:.2f} μs")
            lines.append(f"  Min Time:      {results['min_time_us']:.2f} μs")
            lines.append(f"  Max Time:      {results['max_time_us']:.2f} μs")
            lines.append(f"  Throughput:    {results['throughput']:,.0f} validations/sec")
            lines.append("")
        
        # Calculate speedup if we have satya and another library
        if 'satya' in self.results and len(self.results) > 1:
            satya_time = self.results['satya']['avg_time_us']
            for lib_name, results in self.results.items():
                if lib_name != 'satya' and 'avg_time_us' in results:
                    speedup = results['avg_time_us'] / satya_time
                    lines.append(f"Satya is {speedup:.1f}x FASTER than {lib_name}")
        
        lines.append("=" * 70)
        return "\n".join(lines)
    
    def print_report(self):
        """Print the comparison report"""
        print(self.report())


__all__ = [
    "FieldStats",
    "ValidationStats",
    "ValidationProfiler",
    "BenchmarkComparison",
]
