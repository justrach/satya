import os
import sys
import unittest
import time
import json
from typing import List, Dict
import random

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import satya
from satya import Model, Field, StreamValidator


class Person(satya.Model):
    """Test model for performance testing"""
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=150)
    email: str = Field(email=True)
    active: bool = Field(default=True)


class TestPerformance(unittest.TestCase):
    """Test performance characteristics of the validation system"""

    def setUp(self):
        """Set up test data and validators"""
        self.validator = Person.validator()
        self.small_batch_size = 100
        self.medium_batch_size = 1000
        self.large_batch_size = 10000

    def generate_valid_data(self, count: int) -> List[dict]:
        """Generate valid test data"""
        first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Edward", "Fiona"]
        last_names = ["Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor"]
        domains = ["example.com", "test.org", "sample.net", "demo.io"]
        
        data = []
        for i in range(count):
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            data.append({
                "name": name,
                "age": random.randint(18, 80),
                "email": f"{name.lower().replace(' ', '.')}@{random.choice(domains)}",
                "active": random.choice([True, False])
            })
        return data

    def generate_mixed_data(self, count: int, invalid_ratio: float = 0.2) -> List[dict]:
        """Generate mix of valid and invalid test data"""
        valid_count = int(count * (1 - invalid_ratio))
        invalid_count = count - valid_count
        
        # Generate valid data
        data = self.generate_valid_data(valid_count)
        
        # Generate invalid data
        invalid_patterns = [
            {"name": "", "age": 25, "email": "test@example.com", "active": True},  # empty name
            {"name": "John Doe", "age": -1, "email": "test@example.com", "active": True},  # negative age
            {"name": "John Doe", "age": 200, "email": "test@example.com", "active": True},  # age too high
            {"name": "John Doe", "age": 25, "email": "invalid-email", "active": True},  # bad email
            {"age": 25, "email": "test@example.com", "active": True},  # missing name
        ]
        
        for i in range(invalid_count):
            data.append(random.choice(invalid_patterns).copy())
        
        random.shuffle(data)
        return data

    def test_single_item_validation_performance(self):
        """Test performance of single item validation"""
        data = self.generate_valid_data(1)[0]
        
        # Warm up
        for _ in range(10):
            self.validator.validate(data)
        
        # Measure performance
        start_time = time.time()
        iterations = 10000
        
        for _ in range(iterations):
            result = self.validator.validate(data)
            self.assertTrue(result.is_valid)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        # Should be very fast - less than 1ms per validation on average
        self.assertLess(avg_time, 0.001, f"Single validation took {avg_time:.6f}s on average")
        
        print(f"Single item validation: {avg_time*1000:.3f}ms per item")

    def test_small_batch_validation_performance(self):
        """Test performance with small batches"""
        data = self.generate_valid_data(self.small_batch_size)
        
        start_time = time.time()
        results = self.validator.validate_batch(data)
        end_time = time.time()
        
        # All should be valid
        self.assertTrue(all(results))
        self.assertEqual(len(results), self.small_batch_size)
        
        total_time = end_time - start_time
        per_item = total_time / self.small_batch_size
        
        print(f"Small batch ({self.small_batch_size} items): {total_time:.3f}s total, {per_item*1000:.3f}ms per item")
        
        # Should handle small batches very quickly
        self.assertLess(total_time, 1.0, f"Small batch took {total_time:.3f}s")

    def test_medium_batch_validation_performance(self):
        """Test performance with medium batches"""
        data = self.generate_valid_data(self.medium_batch_size)
        
        start_time = time.time()
        results = self.validator.validate_batch(data)
        end_time = time.time()
        
        self.assertTrue(all(results))
        self.assertEqual(len(results), self.medium_batch_size)
        
        total_time = end_time - start_time
        per_item = total_time / self.medium_batch_size
        
        print(f"Medium batch ({self.medium_batch_size} items): {total_time:.3f}s total, {per_item*1000:.3f}ms per item")
        
        # Should handle medium batches reasonably fast
        self.assertLess(total_time, 5.0, f"Medium batch took {total_time:.3f}s")

    def test_large_batch_validation_performance(self):
        """Test performance with large batches"""
        data = self.generate_valid_data(self.large_batch_size)
        
        start_time = time.time()
        results = self.validator.validate_batch(data)
        end_time = time.time()
        
        self.assertTrue(all(results))
        self.assertEqual(len(results), self.large_batch_size)
        
        total_time = end_time - start_time
        per_item = total_time / self.large_batch_size
        throughput = self.large_batch_size / total_time
        
        print(f"Large batch ({self.large_batch_size} items): {total_time:.3f}s total, {per_item*1000:.3f}ms per item")
        print(f"Throughput: {throughput:.0f} items/second")
        
        # Should maintain reasonable performance even for large batches
        self.assertLess(total_time, 30.0, f"Large batch took {total_time:.3f}s")
        self.assertGreater(throughput, 100, f"Throughput was only {throughput:.0f} items/second")

    def test_mixed_validation_performance(self):
        """Test performance with mixed valid/invalid data"""
        data = self.generate_mixed_data(self.medium_batch_size, invalid_ratio=0.3)
        
        start_time = time.time()
        results = self.validator.validate_batch(data)
        end_time = time.time()
        
        # Should have both valid and invalid results
        valid_count = sum(results)
        invalid_count = len(results) - valid_count
        
        self.assertGreater(valid_count, 0, "Should have some valid items")
        self.assertGreater(invalid_count, 0, "Should have some invalid items")
        self.assertEqual(len(results), self.medium_batch_size)
        
        total_time = end_time - start_time
        per_item = total_time / self.medium_batch_size
        
        print(f"Mixed batch ({self.medium_batch_size} items, {valid_count} valid, {invalid_count} invalid): "
              f"{total_time:.3f}s total, {per_item*1000:.3f}ms per item")

    def test_stream_validation_performance(self):
        """Test performance of stream validation"""
        data = self.generate_valid_data(self.medium_batch_size)
        
        start_time = time.time()
        valid_count = 0
        
        for result in self.validator.validate_stream(data):
            if result.is_valid:
                valid_count += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        self.assertEqual(valid_count, self.medium_batch_size)
        
        print(f"Stream validation ({self.medium_batch_size} items): {total_time:.3f}s total")

    def test_json_validation_performance(self):
        """Test JSON validation performance"""
        # Test single object validation
        data = self.generate_valid_data(1)[0]
        json_str = json.dumps(data)
        json_bytes = json_str.encode('utf-8')
        
        start_time = time.time()
        iterations = 1000
        
        for _ in range(iterations):
            result = self.validator.validate_json(json_bytes, mode="object")
            self.assertTrue(result)
        
        end_time = time.time()
        single_time = (end_time - start_time) / iterations
        
        print(f"JSON single object validation: {single_time*1000:.3f}ms per item")
        
        # Test array validation
        array_data = self.generate_valid_data(100)
        json_array = json.dumps(array_data).encode('utf-8')
        
        start_time = time.time()
        results = self.validator.validate_json(json_array, mode="array")
        end_time = time.time()
        
        array_time = end_time - start_time
        per_item = array_time / len(array_data)
        
        self.assertTrue(all(results))
        print(f"JSON array validation (100 items): {array_time:.3f}s total, {per_item*1000:.3f}ms per item")

    def test_model_instantiation_performance(self):
        """Test performance of model instantiation vs validation"""
        data = self.generate_valid_data(self.small_batch_size)
        
        # Test model instantiation (includes validation)
        start_time = time.time()
        models = []
        for item in data:
            models.append(Person(**item))
        end_time = time.time()
        
        instantiation_time = end_time - start_time
        per_item = instantiation_time / self.small_batch_size
        
        self.assertEqual(len(models), self.small_batch_size)
        print(f"Model instantiation ({self.small_batch_size} items): {instantiation_time:.3f}s total, {per_item*1000:.3f}ms per item")
        
        # Test just validation
        start_time = time.time()
        results = self.validator.validate_batch(data)
        end_time = time.time()
        
        validation_time = end_time - start_time
        
        print(f"Pure validation ({self.small_batch_size} items): {validation_time:.3f}s total")
        print(f"Instantiation overhead: {((instantiation_time - validation_time) / validation_time * 100):.1f}%")

    def test_batch_size_effect_on_performance(self):
        """Test how batch size affects performance"""
        data = self.generate_valid_data(1000)
        
        batch_sizes = [1, 10, 50, 100, 500, 1000]
        
        print("Batch size performance comparison:")
        for batch_size in batch_sizes:
            self.validator.set_batch_size(batch_size)
            
            start_time = time.time()
            results = self.validator.validate_batch(data)
            end_time = time.time()
            
            total_time = end_time - start_time
            per_item = total_time / len(data)
            
            self.assertTrue(all(results))
            print(f"Batch size {batch_size:3d}: {total_time:.3f}s total, {per_item*1000:.3f}ms per item")

    def test_memory_usage_characteristics(self):
        """Test that validation doesn't consume excessive memory"""
        import gc
        
        # Force garbage collection to get clean baseline
        gc.collect()
        
        # Generate large dataset
        data = self.generate_valid_data(self.large_batch_size)
        
        # Validate in chunks to avoid memory buildup
        chunk_size = 1000
        total_valid = 0
        
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            results = self.validator.validate_batch(chunk)
            total_valid += sum(results)
            
            # Force cleanup between chunks
            del results
            gc.collect()
        
        self.assertEqual(total_valid, self.large_batch_size)
        print(f"Processed {self.large_batch_size} items in chunks of {chunk_size}")


class TestScalability(unittest.TestCase):
    """Test scalability characteristics"""

    def test_validator_reuse(self):
        """Test that validators can be reused efficiently"""
        validator = Person.validator()
        
        # Use the same validator for multiple operations
        data1 = {"name": "John Doe", "age": 30, "email": "john@example.com"}
        data2 = {"name": "Jane Smith", "age": 25, "email": "jane@example.com"}
        
        # Multiple validations with same validator
        for _ in range(100):
            result1 = validator.validate(data1)
            result2 = validator.validate(data2)
            
            self.assertTrue(result1.is_valid)
            self.assertTrue(result2.is_valid)

    def test_concurrent_validation_safety(self):
        """Test that validation is safe for concurrent use patterns"""
        import threading
        import queue
        
        validator = Person.validator()
        data = {"name": "Test User", "age": 30, "email": "test@example.com"}
        results = queue.Queue()
        
        def validate_worker():
            for _ in range(100):
                result = validator.validate(data)
                results.put(result.is_valid)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=validate_worker)
            t.start()
            threads.append(t)
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Check all results were valid
        total_results = []
        while not results.empty():
            total_results.append(results.get())
        
        self.assertEqual(len(total_results), 500)  # 5 threads * 100 validations
        self.assertTrue(all(total_results))


if __name__ == '__main__':
    # Run with more verbose output for performance metrics
    unittest.main(verbosity=2)
