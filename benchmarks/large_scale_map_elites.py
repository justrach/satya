#!/usr/bin/env python3
"""
Large-Scale MAP-Elites Optimization: up to 50M items x N runs

Runs the MAP-Elites algorithm at massive scale to discover optimal batch
configurations across different data profiles with parallel evaluation.
Now supports CLI arguments and detailed progress indicators with ETA.
"""

import json
import time
import random
import argparse
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import satya
from map_elites_optimizer import MapElitesOptimizer, DataProfile, Individual, benchmark_msgspec


def run_large_scale_evaluation(config_data: dict) -> dict:
    """Run evaluation on a single configuration with large dataset."""
    profile_data, individual_data, test_size = config_data
    
    profile = DataProfile(**profile_data)
    individual = Individual(**individual_data)
    
    # Generate large test dataset
    optimizer = MapElitesOptimizer()
    test_data = optimizer.generate_test_data(profile, test_size)
    
    # Evaluate Satya
    satya_fitness = optimizer.evaluate_individual(individual, profile, test_data)
    
    # Evaluate msgspec
    msgspec_fitness = benchmark_msgspec(profile, test_data)
    
    return {
        'profile': profile_data,
        'individual': individual_data,
        'satya_ips': satya_fitness,
        'msgspec_ips': msgspec_fitness,
        'test_size': test_size,
        'ratio': satya_fitness / msgspec_fitness if msgspec_fitness > 0 else 0.0
    }


class LargeScaleMapElites:
    """Large-scale MAP-Elites with parallel evaluation."""
    
    def __init__(self, verbose: int = 1, archive_path: str = 'large_scale_archive.json',
                 results_prefix: str = 'large_scale_results', runs: int = 5,
                 max_workers: int | None = None, evolve_gens: int = 20,
                 task_timeout: int = 300):
        self.base_optimizer = MapElitesOptimizer(verbose=verbose)
        self.elite_archive = {}
        self.scale_results = []
        self.verbose = verbose
        self.archive_path = archive_path
        self.results_prefix = results_prefix
        self.runs = runs
        self.max_workers = max_workers
        self.evolve_gens = evolve_gens
        self.task_timeout = task_timeout
    
    def run_progressive_scaling(self, profiles, scales, sample_size: int | None = None):
        """Run MAP-Elites with progressively larger datasets."""
        if self.verbose >= 1:
            print("🚀 Large-Scale MAP-Elites: Progressive Scaling")
        
        # Load existing archive if available
        self.base_optimizer.load_archive(self.archive_path)
        
        for scale in scales:
            if self.verbose >= 1:
                print(f"\n📊 Running at {scale:,} items scale...")
            
            # First, evolve the archive with smaller samples
            if scale <= 5_000_000:
                sample = sample_size if sample_size is not None else min(100_000, scale // 10)
                self.evolve_archive_at_scale(profiles, sample)
            
            # Then evaluate best configurations at full scale
            scale_results = self.evaluate_at_scale(profiles, scale)
            self.scale_results.extend(scale_results)
            
            # Save intermediate results
            self.save_results(f'{self.results_prefix}_{scale}.json')
            self.base_optimizer.save_archive(self.archive_path)
            
            if self.verbose >= 1:
                print(f"✅ Completed {scale:,} items scale")
    
    def evolve_archive_at_scale(self, profiles: List[DataProfile], sample_size: int):
        """Evolve the MAP-Elites archive using samples."""
        if self.verbose >= 1:
            print(f"🧬 Evolving archive with {sample_size:,} item samples...")
        
        # Generate sample datasets
        test_datasets = {}
        for profile in profiles:
            profile_key = f"{profile.field_count}_{profile.constraint_complexity:.1f}"
            test_datasets[profile_key] = self.base_optimizer.generate_test_data(profile, sample_size)
        
        # Run evolution for multiple generations
        for gen in range(self.evolve_gens):
            self.base_optimizer.run_generation(profiles, test_datasets)
            
            if self.verbose >= 1 and gen % 5 == 4:
                print(f"  Generation {self.base_optimizer.generation}: "
                      f"Archive={len(self.base_optimizer.archive)}, "
                      f"Best={self.base_optimizer.best_fitness:.0f} items/s")
    
    def evaluate_at_scale(self, profiles: List[DataProfile], scale: int) -> List[dict]:
        """Evaluate best configurations at full scale using parallel processing."""
        if self.verbose >= 1:
            print(f"⚡ Evaluating at {scale:,} items with parallel processing...")
        
        # Prepare evaluation tasks
        tasks = []
        for profile in profiles:
            best_config = self.base_optimizer.get_best_config(profile)
            
            # Run multiple times for statistical significance
            for run in range(self.runs):
                tasks.append((asdict(profile), asdict(best_config), scale))
        
        results = []
        
        # Use process pool for parallel evaluation
        max_workers = self.max_workers or min(mp.cpu_count(), 8)  # Limit to avoid memory issues
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(run_large_scale_evaluation, task): task 
                for task in tasks
            }
            
            # Collect results as they complete
            total = len(tasks)
            completed = 0
            start = time.perf_counter()
            next_report = 0.1
            for future in as_completed(future_to_task):
                try:
                    result = future.result(timeout=self.task_timeout)  # timeout per task
                    results.append(result)
                    
                    profile_desc = f"{result['profile']['field_count']}f-{result['profile']['constraint_complexity']:.1f}c"
                    if self.verbose >= 2:
                        print(f"  ✓ {profile_desc}: Satya={result['satya_ips']:,.0f}, "
                              f"msgspec={result['msgspec_ips']:,.0f}, "
                              f"ratio={result['ratio']:.2f}x")
                    completed += 1
                    if self.verbose >= 1:
                        progress = completed / total if total else 1.0
                        if progress >= next_report or completed == total:
                            elapsed = time.perf_counter() - start
                            rps = completed / elapsed if elapsed > 0 else 0
                            eta = (total - completed) / rps if rps > 0 else 0
                            print(f"  Progress: {progress*100:5.1f}% | tasks {completed}/{total} | ETA {eta:6.1f}s")
                            next_report += 0.1
                except Exception as e:
                    if self.verbose >= 1:
                        print(f"  ✗ Task failed: {e}")
        
        return results
    
    def save_results(self, filename: str):
        """Save current results to file."""
        summary = self.analyze_results()
        
        data = {
            'archive_size': len(self.base_optimizer.archive),
            'total_evaluations': len(self.scale_results),
            'summary': summary,
            'detailed_results': self.scale_results
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        if self.verbose >= 1:
            print(f"💾 Results saved to {filename}")
    
    def analyze_results(self) -> dict:
        """Analyze results across all scales and profiles."""
        if not self.scale_results:
            return {}
        
        # Group by scale and profile
        by_scale = {}
        by_profile = {}
        
        for result in self.scale_results:
            scale = result['test_size']
            profile_key = f"{result['profile']['field_count']}f_{result['profile']['constraint_complexity']:.1f}c"
            
            if scale not in by_scale:
                by_scale[scale] = []
            by_scale[scale].append(result)
            
            if profile_key not in by_profile:
                by_profile[profile_key] = []
            by_profile[profile_key].append(result)
        
        # Calculate statistics
        summary = {
            'scales_tested': list(by_scale.keys()),
            'profiles_tested': list(by_profile.keys()),
            'scale_performance': {},
            'profile_performance': {},
            'overall_stats': {}
        }
        
        # Scale performance
        for scale, results in by_scale.items():
            satya_speeds = [r['satya_ips'] for r in results]
            msgspec_speeds = [r['msgspec_ips'] for r in results]
            ratios = [r['ratio'] for r in results if r['ratio'] > 0]
            
            summary['scale_performance'][scale] = {
                'satya_avg': np.mean(satya_speeds),
                'satya_std': np.std(satya_speeds),
                'msgspec_avg': np.mean(msgspec_speeds),
                'msgspec_std': np.std(msgspec_speeds),
                'ratio_avg': np.mean(ratios) if ratios else 0,
                'ratio_std': np.std(ratios) if ratios else 0,
                'samples': len(results)
            }
        
        # Profile performance
        for profile_key, results in by_profile.items():
            satya_speeds = [r['satya_ips'] for r in results]
            ratios = [r['ratio'] for r in results if r['ratio'] > 0]
            
            summary['profile_performance'][profile_key] = {
                'satya_avg': np.mean(satya_speeds),
                'ratio_avg': np.mean(ratios) if ratios else 0,
                'best_ratio': max(ratios) if ratios else 0,
                'samples': len(results)
            }
        
        # Overall statistics
        all_ratios = [r['ratio'] for r in self.scale_results if r['ratio'] > 0]
        all_satya_speeds = [r['satya_ips'] for r in self.scale_results]
        
        summary['overall_stats'] = {
            'total_evaluations': len(self.scale_results),
            'avg_ratio': np.mean(all_ratios) if all_ratios else 0,
            'best_ratio': max(all_ratios) if all_ratios else 0,
            'avg_satya_speed': np.mean(all_satya_speeds),
            'max_satya_speed': max(all_satya_speeds),
            'competitive_profiles': len([r for r in all_ratios if r >= 0.9])  # Within 10% of msgspec
        }
        
        return summary


def main():
    """Run the large-scale MAP-Elites experiment (CLI)."""
    parser = argparse.ArgumentParser(description="Large-scale MAP-Elites optimizer")
    parser.add_argument("--verbose", type=int, default=1, choices=[0,1,2], help="Verbosity level: 0,1,2")
    parser.add_argument("--runs", type=int, default=5, help="Parallel evaluation runs per profile")
    parser.add_argument("--workers", type=int, default=None, help="Max process workers (default=min(cpu,8))")
    parser.add_argument("--evolve-gens", type=int, default=20, help="Generations when evolving archive at sample scale")
    parser.add_argument("--sample-size", type=int, default=None, help="Sample size for evolution when scale <= 5M")
    parser.add_argument("--archive", type=str, default="large_scale_archive.json", help="Archive path")
    parser.add_argument("--results-prefix", type=str, default="large_scale_results", help="Prefix for results files")
    parser.add_argument("--timeout", type=int, default=300, help="Per-task timeout in seconds")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--scales", type=str, default="1000000,5000000,10000000,25000000,50000000", help="Comma-separated scales")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed % (2**32 - 1))

    if args.verbose >= 1:
        print("🌟 Large-Scale MAP-Elites")
        print("=" * 60)
    
    optimizer = LargeScaleMapElites(
        verbose=args.verbose,
        archive_path=args.archive,
        results_prefix=args.results_prefix,
        runs=args.runs,
        max_workers=args.workers,
        evolve_gens=args.evolve_gens,
        task_timeout=args.timeout,
    )

    # Define comprehensive test profiles (same defaults as before)
    profiles = [
        # Small objects, varying complexity
        DataProfile(field_count=3, avg_string_length=8, constraint_complexity=0.0, object_size_kb=0.08),
        DataProfile(field_count=3, avg_string_length=12, constraint_complexity=0.3, object_size_kb=0.12),
        DataProfile(field_count=3, avg_string_length=16, constraint_complexity=0.6, object_size_kb=0.16),
        DataProfile(field_count=3, avg_string_length=20, constraint_complexity=1.0, object_size_kb=0.20),
        
        # Medium objects
        DataProfile(field_count=8, avg_string_length=10, constraint_complexity=0.0, object_size_kb=0.25),
        DataProfile(field_count=8, avg_string_length=15, constraint_complexity=0.4, object_size_kb=0.35),
        DataProfile(field_count=8, avg_string_length=20, constraint_complexity=0.8, object_size_kb=0.45),
        
        # Large objects
        DataProfile(field_count=15, avg_string_length=15, constraint_complexity=0.2, object_size_kb=0.6),
        DataProfile(field_count=15, avg_string_length=25, constraint_complexity=0.6, object_size_kb=0.9),
        DataProfile(field_count=20, avg_string_length=20, constraint_complexity=0.5, object_size_kb=1.0),
        DataProfile(field_count=25, avg_string_length=30, constraint_complexity=0.9, object_size_kb=1.5),
    ]
    scales = [int(s.strip()) for s in args.scales.split(',') if s.strip()]

    try:
        optimizer.run_progressive_scaling(profiles, scales, sample_size=args.sample_size)
        
        if args.verbose >= 1:
            print("\n🏆 Final Analysis:")
            print("=" * 60)
        
        summary = optimizer.analyze_results()
        
        if args.verbose >= 1 and summary:
            print(f"Total evaluations: {summary['overall_stats']['total_evaluations']:,}")
            print(f"Average performance ratio: {summary['overall_stats']['avg_ratio']:.3f}x msgspec")
            print(f"Best performance ratio: {summary['overall_stats']['best_ratio']:.3f}x msgspec")
            print(f"Max Satya speed: {summary['overall_stats']['max_satya_speed']:,.0f} items/s")
            print(f"Competitive profiles: {summary['overall_stats']['competitive_profiles']}")
            
            print("\n📊 Scale Performance:")
            for scale, stats in summary['scale_performance'].items():
                print(f"  {scale:>10,} items: {stats['ratio_avg']:.3f}x ± {stats['ratio_std']:.3f}")
        
        optimizer.save_results(f"{args.results_prefix}_final_results.json")
        optimizer.base_optimizer.save_archive(args.archive.replace('.json', '_final.json'))
        
        if args.verbose >= 1:
            print("\n✅ Large-scale optimization complete!")
        
    except KeyboardInterrupt:
        if args.verbose >= 1:
            print("\n⚠️  Interrupted by user, saving current progress...")
        optimizer.save_results(f"{args.results_prefix}_interrupted_results.json")
        optimizer.base_optimizer.save_archive(args.archive.replace('.json', '_interrupted.json'))


if __name__ == "__main__":
    main()
