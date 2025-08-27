#!/usr/bin/env python3
"""
MAP-Elites Optimization for Satya Batch Size Selection

This implements a MAP-Elites evolutionary algorithm to discover optimal batch sizes
for different data characteristics (object size, field count, constraint complexity).
The algorithm builds an archive of elite solutions across different behavioral dimensions.
"""

import json
import time
import random
import argparse
import sys
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import satya


@dataclass
class DataProfile:
    """Characterizes a dataset for MAP-Elites behavioral dimensions."""
    field_count: int          # Number of fields per object
    avg_string_length: float  # Average string field length
    constraint_complexity: float  # 0.0 = simple types, 1.0 = complex constraints
    object_size_kb: float     # Average object size in KB
    
    def behavioral_descriptor(self) -> Tuple[int, int, int]:
        """Map to discrete behavioral dimensions for MAP-Elites archive."""
        # Dimension 1: Field count (0-4: 1-5 fields, 5-9: 6-15 fields, 10-14: 16+ fields)
        field_dim = min(14, max(0, (self.field_count - 1) // 3))
        
        # Dimension 2: Object complexity (0-9: simple to complex)
        complexity_dim = min(9, int(self.constraint_complexity * 10))
        
        # Dimension 3: Object size (0-9: small to large)
        size_dim = min(9, int(self.object_size_kb * 2))  # 0.5KB increments
        
        return (field_dim, complexity_dim, size_dim)


@dataclass
class Individual:
    """A candidate solution in the MAP-Elites population."""
    batch_size: int
    micro_batch_size: int
    streaming_threshold: int
    fitness: float = 0.0
    
    def mutate(self) -> 'Individual':
        """Create a mutated copy of this individual."""
        new_individual = Individual(
            batch_size=max(100, self.batch_size + random.randint(-5000, 5000)),
            micro_batch_size=max(64, self.micro_batch_size + random.randint(-1024, 1024)),
            streaming_threshold=max(1000, self.streaming_threshold + random.randint(-5000, 5000))
        )
        return new_individual


class MapElitesOptimizer:
    """MAP-Elites algorithm for optimizing Satya batch parameters."""
    
    def __init__(self, archive_dims: Tuple[int, int, int] = (15, 10, 10), verbose: int = 1):
        self.archive_dims = archive_dims
        self.archive: Dict[Tuple[int, int, int], Individual] = {}
        self.generation = 0
        self.best_fitness = 0.0
        self.verbose = verbose
        
    def generate_test_data(self, profile: DataProfile, num_items: int) -> List[dict]:
        """Generate test data matching the given profile."""
        data = []
        
        for _ in range(num_items):
            obj = {}
            
            # Base fields
            obj['name'] = 'A' * int(profile.avg_string_length)
            obj['age'] = random.randint(18, 80)
            obj['email'] = f"user@example.com"
            
            # Add extra fields based on profile
            for i in range(3, profile.field_count):
                if i % 2 == 0:
                    obj[f's{i}'] = 'X' * int(profile.avg_string_length // 2)
                else:
                    obj[f'n{i}'] = random.randint(0, 1000000)
                    
            data.append(obj)
            
        return data
    
    def setup_validator(self, profile: DataProfile):
        """Create a validator matching the profile's constraint complexity."""
        attrs = {}
        
        # Base fields with complexity based on profile
        if profile.constraint_complexity > 0.5:
            attrs['name'] = satya.Field(str, min_length=3, max_length=40, required=True)
            attrs['age'] = satya.Field(int, ge=18, le=90, required=True)
            attrs['email'] = satya.Field(str, email=True, required=True)
        else:
            attrs['name'] = satya.Field(str, required=True)
            attrs['age'] = satya.Field(int, required=True)
            attrs['email'] = satya.Field(str, required=True)
        
        # Add extra fields
        for i in range(3, profile.field_count):
            if i % 2 == 0:
                if profile.constraint_complexity > 0.7:
                    attrs[f's{i}'] = satya.Field(str, min_length=1, max_length=100, required=True)
                else:
                    attrs[f's{i}'] = satya.Field(str, required=True)
            else:
                if profile.constraint_complexity > 0.7:
                    attrs[f'n{i}'] = satya.Field(int, ge=0, le=1000000, required=True)
                else:
                    attrs[f'n{i}'] = satya.Field(int, required=True)
        
        ModelCls = type('DynModel', (satya.Model,), {
            '__annotations__': {k: (str if 'str' in str(v.type) else int) for k, v in attrs.items()}, 
            **attrs
        })
        return ModelCls.validator()
    
    def evaluate_individual(self, individual: Individual, profile: DataProfile, 
                          test_data: List[dict]) -> float:
        """Evaluate an individual's fitness on the given data profile."""
        validator = self.setup_validator(profile)
        
        # Temporarily modify the validator's batch parameters
        original_batch_size = validator._validator.get_batch_size()
        validator._validator.set_batch_size(individual.batch_size)
        
        try:
            start = time.perf_counter()
            
            # Use the individual's micro-batch size
            micro_batch_size = individual.micro_batch_size
            total = 0
            
            for i in range(0, len(test_data), micro_batch_size):
                batch = test_data[i : i + micro_batch_size]
                _ = validator._validator.validate_batch(batch)
                total += len(batch)
            
            elapsed = time.perf_counter() - start
            
            # Fitness = items per second (higher is better)
            fitness = total / elapsed if elapsed > 0 else 0.0
            
        except Exception as e:
            fitness = 0.0
        finally:
            # Restore original batch size
            validator._validator.set_batch_size(original_batch_size)
            
        return fitness
    
    def random_individual(self) -> Individual:
        """Generate a random individual."""
        return Individual(
            batch_size=random.randint(1000, 100000),
            micro_batch_size=random.choice([64, 128, 256, 512, 1024, 2048, 4096, 8192]),
            streaming_threshold=random.randint(5000, 50000)
        )
    
    def run_generation(self, profiles: List[DataProfile], test_datasets: Dict[str, List[dict]]):
        """Run one generation of MAP-Elites with progress reporting."""
        self.generation += 1
        
        # Generate new individuals
        new_individuals = []
        
        if len(self.archive) < 100:  # Initial random population
            new_individuals = [self.random_individual() for _ in range(50)]
        else:
            # Mutation-based generation
            for _ in range(30):
                parent = random.choice(list(self.archive.values()))
                child = parent.mutate()
                new_individuals.append(child)
            
            # Some random individuals for exploration
            new_individuals.extend([self.random_individual() for _ in range(10)])
        
        total_evals = len(new_individuals) * len(profiles)
        eval_count = 0
        start_time = time.perf_counter()
        next_report = 0.1  # 10% increments
        
        # Evaluate each individual on each profile
        for individual in new_individuals:
            for profile in profiles:
                profile_key = f"{profile.field_count}_{profile.constraint_complexity:.1f}"
                test_data = test_datasets[profile_key]
                
                fitness = self.evaluate_individual(individual, profile, test_data)
                individual.fitness = max(individual.fitness, fitness)
                
                # Get behavioral descriptor
                bd = profile.behavioral_descriptor()
                
                # Check if this individual should be added to archive
                if bd not in self.archive or individual.fitness > self.archive[bd].fitness:
                    self.archive[bd] = Individual(
                        batch_size=individual.batch_size,
                        micro_batch_size=individual.micro_batch_size,
                        streaming_threshold=individual.streaming_threshold,
                        fitness=individual.fitness
                    )
                    
                    if individual.fitness > self.best_fitness:
                        self.best_fitness = individual.fitness
                
                eval_count += 1
                if self.verbose >= 2 and total_evals > 0:
                    progress = eval_count / total_evals
                    if progress >= next_report or eval_count == total_evals:
                        elapsed = time.perf_counter() - start_time
                        ips = eval_count / elapsed if elapsed > 0 else 0
                        remaining = (total_evals - eval_count) / ips if ips > 0 else 0
                        print(f"  Gen {self.generation} progress: {progress*100:5.1f}% | "
                              f"evals {eval_count}/{total_evals} | ETA {remaining:6.1f}s")
                        next_report += 0.1
        
        if self.verbose >= 1:
            print(f"Generation {self.generation}: Archive size={len(self.archive)}, "
                  f"Best fitness={self.best_fitness:.0f} items/s")
    
    def get_best_config(self, profile: DataProfile) -> Individual:
        """Get the best configuration for a given data profile."""
        bd = profile.behavioral_descriptor()
        
        if bd in self.archive:
            return self.archive[bd]
        
        # Find nearest neighbor in archive
        best_individual = None
        best_distance = float('inf')
        
        for archive_bd, individual in self.archive.items():
            distance = sum((a - b) ** 2 for a, b in zip(bd, archive_bd)) ** 0.5
            if distance < best_distance:
                best_distance = distance
                best_individual = individual
        
        return best_individual or self.random_individual()
    
    def save_archive(self, filename: str):
        """Save the current archive to a file."""
        archive_data = {
            'generation': self.generation,
            'best_fitness': self.best_fitness,
            'archive': {
                str(bd): asdict(individual) 
                for bd, individual in self.archive.items()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(archive_data, f, indent=2)
    
    def load_archive(self, filename: str):
        """Load an archive from a file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            self.generation = data['generation']
            self.best_fitness = data['best_fitness']
            self.archive = {
                eval(bd): Individual(**individual_data)
                for bd, individual_data in data['archive'].items()
            }
            print(f"Loaded archive with {len(self.archive)} individuals from generation {self.generation}")
        except FileNotFoundError:
            print(f"Archive file {filename} not found, starting fresh")


def benchmark_msgspec(profile: DataProfile, test_data: List[dict]) -> float:
    """Benchmark msgspec for comparison."""
    try:
        import msgspec
        
        # Create msgspec struct matching profile
        fields = {
            'name': str,
            'age': int,
            'email': str
        }
        
        for i in range(3, profile.field_count):
            if i % 2 == 0:
                fields[f's{i}'] = str
            else:
                fields[f'n{i}'] = int
        
        Person = msgspec.defstruct('Person', fields)
        
        start = time.perf_counter()
        
        for item in test_data:
            try:
                _ = msgspec.convert(item, Person)
            except:
                pass  # Count invalid items
        
        elapsed = time.perf_counter() - start
        return len(test_data) / elapsed if elapsed > 0 else 0.0
        
    except ImportError:
        return 0.0


def main():
    """Run the MAP-Elites optimization experiment with CLI controls."""
    parser = argparse.ArgumentParser(description="MAP-Elites optimizer for Satya batch sizes")
    parser.add_argument("--generations", type=int, default=50, help="Number of generations to run")
    parser.add_argument("--test-size", type=int, default=100_000, help="Number of items per profile dataset")
    parser.add_argument("--save-every", type=int, default=10, help="Save archive every N generations (0=never)")
    parser.add_argument("--archive", type=str, default="map_elites_archive.json", help="Archive file path")
    parser.add_argument("--results", type=str, default="map_elites_results.json", help="Results JSON output path")
    parser.add_argument("--verbose", type=int, default=1, choices=[0,1,2], help="Verbosity level: 0,1,2")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--no-msgspec", action="store_true", help="Skip msgspec comparison in final evaluation")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed % (2**32 - 1))

    if args.verbose >= 1:
        print("🧬 Starting MAP-Elites Optimization for Satya Batch Sizes")
    
    # Define test profiles covering different data characteristics
    profiles = [
        DataProfile(field_count=3, avg_string_length=10, constraint_complexity=0.0, object_size_kb=0.1),
        DataProfile(field_count=3, avg_string_length=20, constraint_complexity=0.5, object_size_kb=0.2),
        DataProfile(field_count=3, avg_string_length=30, constraint_complexity=1.0, object_size_kb=0.3),
        DataProfile(field_count=8, avg_string_length=15, constraint_complexity=0.3, object_size_kb=0.4),
        DataProfile(field_count=8, avg_string_length=25, constraint_complexity=0.7, object_size_kb=0.6),
        DataProfile(field_count=15, avg_string_length=20, constraint_complexity=0.5, object_size_kb=0.8),
        DataProfile(field_count=20, avg_string_length=30, constraint_complexity=0.9, object_size_kb=1.2),
    ]
    
    optimizer = MapElitesOptimizer(verbose=args.verbose)
    
    # Try to load existing archive
    optimizer.load_archive(args.archive)
    
    # Generate test datasets (smaller for development, will scale up)
    test_datasets = {}
    test_size = args.test_size
    
    if args.verbose >= 1:
        print(f"📊 Generating test datasets ({test_size} items each)...")
    for profile in profiles:
        profile_key = f"{profile.field_count}_{profile.constraint_complexity:.1f}"
        test_datasets[profile_key] = optimizer.generate_test_data(profile, test_size)
    
    # Run MAP-Elites for multiple generations
    if args.verbose >= 1:
        print("🚀 Running MAP-Elites optimization...")
    
    for generation in range(args.generations):
        optimizer.run_generation(profiles, test_datasets)
        
        # Save archive every N generations
        if args.save_every and (generation % args.save_every == args.save_every - 1):
            optimizer.save_archive(args.archive)
            if args.verbose >= 1:
                print(f"💾 Saved archive at generation {optimizer.generation}")
    
    # Final evaluation against msgspec
    if not args.no_msgspec:
        if args.verbose >= 1:
            print("\n🏁 Final Evaluation vs msgspec:")
            print("=" * 80)
        
        results = []
        for profile in profiles:
            profile_key = f"{profile.field_count}_{profile.constraint_complexity:.1f}"
            test_data = test_datasets[profile_key]
            
            # Get optimized Satya config
            best_config = optimizer.get_best_config(profile)
            satya_fitness = optimizer.evaluate_individual(best_config, profile, test_data)
            
            # Benchmark msgspec
            msgspec_fitness = benchmark_msgspec(profile, test_data)
            
            ratio = satya_fitness / msgspec_fitness if msgspec_fitness > 0 else float('inf')
            
            results.append({
                'profile': asdict(profile),
                'satya_config': asdict(best_config),
                'satya_ips': satya_fitness,
                'msgspec_ips': msgspec_fitness,
                'ratio': ratio
            })
            
            if args.verbose >= 1:
                print(f"Profile: {profile.field_count} fields, {profile.constraint_complexity:.1f} complexity")
                print(f"  Satya (optimized): {satya_fitness:,.0f} items/s")
                print(f"  msgspec:          {msgspec_fitness:,.0f} items/s")
                print(f"  Ratio:            {ratio:.2f}x")
                print(f"  Best config:      batch={best_config.batch_size}, micro={best_config.micro_batch_size}")
                print()
    else:
        results = []
        for profile in profiles:
            best_config = optimizer.get_best_config(profile)
            results.append({
                'profile': asdict(profile),
                'satya_config': asdict(best_config),
                'satya_ips': None,
                'msgspec_ips': None,
                'ratio': None
            })
    
    # Save final results
    with open(args.results, 'w') as f:
        json.dump({
            'archive_size': len(optimizer.archive),
            'generations': optimizer.generation,
            'best_fitness': optimizer.best_fitness,
            'results': results
        }, f, indent=2)
    
    optimizer.save_archive(args.archive.replace('.json', '_final.json'))
    
    if args.verbose >= 1:
        print(f"✅ MAP-Elites optimization complete!")
        print(f"   Archive size: {len(optimizer.archive)} elite solutions")
        print(f"   Best fitness: {optimizer.best_fitness:,.0f} items/s")
        print(f"   Results saved to: {args.results}")


if __name__ == "__main__":
    main()
