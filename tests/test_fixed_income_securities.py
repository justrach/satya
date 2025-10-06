"""
Test cases for fixed income securities validation example.

Tests the List[Model] nested structure support added in v0.3.84.
"""

import os
import sys
import unittest

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from satya import Model, Field, ModelValidationError
from typing import List, Optional


class Bond(Model):
    """Simplified Bond model for testing"""
    isin: str = Field(
        pattern=r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$',
        min_length=12,
        max_length=12
    )
    issuer_name: str = Field(min_length=2, max_length=200)
    issuer_type: str = Field(enum=["Government", "Corporate", "Municipal", "Agency"])
    face_value: float = Field(min_value=100.0, max_value=1000000000.0)
    current_price: float = Field(min_value=0.01, max_value=200.0)
    coupon_rate: float = Field(min_value=0.0, max_value=20.0)
    credit_rating: str = Field(
        enum=["AAA", "AA+", "AA", "AA-", "A+", "A", "A-", 
              "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-"]
    )
    yield_to_maturity: float = Field(min_value=-2.0, max_value=30.0)
    duration: float = Field(min_value=0.01, max_value=30.0)


class BondIndex(Model):
    """Bond index containing List[Bond]"""
    index_name: str = Field(min_length=3, max_length=100)
    index_type: str = Field(enum=["Government", "Corporate", "Municipal", "Aggregate"])
    total_market_value: float = Field(min_value=0.0)
    average_duration: float = Field(min_value=0.0, max_value=30.0)
    average_yield: float = Field(min_value=-2.0, max_value=30.0)
    securities: List[Bond] = Field(description="List of bonds", min_items=1)


class TestBondValidation(unittest.TestCase):
    """Test individual bond validation"""
    
    def test_valid_bond(self):
        """Test creating a valid bond"""
        bond_data = {
            "isin": "US0378331005",
            "issuer_name": "Apple Inc",
            "issuer_type": "Corporate",
            "face_value": 1000.0,
            "current_price": 102.5,
            "coupon_rate": 3.5,
            "credit_rating": "AA+",
            "yield_to_maturity": 3.2,
            "duration": 5.5
        }
        bond = Bond(**bond_data)
        self.assertEqual(bond.isin, "US0378331005")
        self.assertEqual(bond.issuer_name, "Apple Inc")
        self.assertEqual(bond.coupon_rate, 3.5)
    
    def test_invalid_isin_format(self):
        """Test that invalid ISIN format is rejected"""
        bond_data = {
            "isin": "INVALID123",  # Wrong format
            "issuer_name": "Test Corp",
            "issuer_type": "Corporate",
            "face_value": 1000.0,
            "current_price": 100.0,
            "coupon_rate": 3.0,
            "credit_rating": "A",
            "yield_to_maturity": 3.0,
            "duration": 5.0
        }
        with self.assertRaises(ModelValidationError):
            Bond(**bond_data)
    
    def test_invalid_coupon_rate(self):
        """Test that negative coupon rate is rejected"""
        bond_data = {
            "isin": "US0378331005",
            "issuer_name": "Test Corp",
            "issuer_type": "Corporate",
            "face_value": 1000.0,
            "current_price": 100.0,
            "coupon_rate": -1.0,  # Invalid negative
            "credit_rating": "A",
            "yield_to_maturity": 3.0,
            "duration": 5.0
        }
        with self.assertRaises(ModelValidationError):
            Bond(**bond_data)
    
    def test_invalid_credit_rating(self):
        """Test that invalid credit rating is rejected"""
        bond_data = {
            "isin": "US0378331005",
            "issuer_name": "Test Corp",
            "issuer_type": "Corporate",
            "face_value": 1000.0,
            "current_price": 100.0,
            "coupon_rate": 3.0,
            "credit_rating": "ZZZ",  # Not a valid rating
            "yield_to_maturity": 3.0,
            "duration": 5.0
        }
        with self.assertRaises(ModelValidationError):
            Bond(**bond_data)
    
    def test_price_out_of_range(self):
        """Test that price above 200% is rejected"""
        bond_data = {
            "isin": "US0378331005",
            "issuer_name": "Test Corp",
            "issuer_type": "Corporate",
            "face_value": 1000.0,
            "current_price": 250.0,  # Above max of 200
            "coupon_rate": 3.0,
            "credit_rating": "A",
            "yield_to_maturity": 3.0,
            "duration": 5.0
        }
        with self.assertRaises(ModelValidationError):
            Bond(**bond_data)


class TestBondIndexValidation(unittest.TestCase):
    """Test bond index with List[Bond] nested structure"""
    
    def test_valid_bond_index_with_list_of_bonds(self):
        """Test creating a valid bond index with nested bonds"""
        index_data = {
            "index_name": "US Corporate Bond Index",
            "index_type": "Corporate",
            "total_market_value": 1000000.0,
            "average_duration": 7.5,
            "average_yield": 4.2,
            "securities": [
                {
                    "isin": "US0378331005",
                    "issuer_name": "Apple Inc",
                    "issuer_type": "Corporate",
                    "face_value": 1000.0,
                    "current_price": 102.5,
                    "coupon_rate": 3.5,
                    "credit_rating": "AA+",
                    "yield_to_maturity": 3.2,
                    "duration": 5.5
                },
                {
                    "isin": "US5949181045",
                    "issuer_name": "Microsoft Corp",
                    "issuer_type": "Corporate",
                    "face_value": 1000.0,
                    "current_price": 98.0,
                    "coupon_rate": 4.0,
                    "credit_rating": "AAA",
                    "yield_to_maturity": 4.5,
                    "duration": 8.0
                }
            ]
        }
        
        index = BondIndex(**index_data)
        self.assertEqual(index.index_name, "US Corporate Bond Index")
        self.assertEqual(len(index.securities), 2)
        self.assertIsInstance(index.securities[0], Bond)
        self.assertEqual(index.securities[0].issuer_name, "Apple Inc")
        self.assertEqual(index.securities[1].issuer_name, "Microsoft Corp")
    
    def test_empty_securities_list_rejected(self):
        """Test that empty securities list is rejected"""
        index_data = {
            "index_name": "Empty Index",
            "index_type": "Corporate",
            "total_market_value": 0.0,
            "average_duration": 0.0,
            "average_yield": 0.0,
            "securities": []  # Empty list, should fail min_items=1
        }
        with self.assertRaises(ModelValidationError):
            BondIndex(**index_data)
    
    def test_invalid_bond_in_list_rejected(self):
        """Test that invalid bond in list causes validation error"""
        index_data = {
            "index_name": "Test Index",
            "index_type": "Corporate",
            "total_market_value": 1000.0,
            "average_duration": 5.0,
            "average_yield": 3.0,
            "securities": [
                {
                    "isin": "INVALID",  # Invalid ISIN
                    "issuer_name": "Test Corp",
                    "issuer_type": "Corporate",
                    "face_value": 1000.0,
                    "current_price": 100.0,
                    "coupon_rate": 3.0,
                    "credit_rating": "A",
                    "yield_to_maturity": 3.0,
                    "duration": 5.0
                }
            ]
        }
        with self.assertRaises(ModelValidationError):
            BondIndex(**index_data)
    
    def test_large_bond_index(self):
        """Test index with many bonds"""
        securities = []
        for i in range(50):
            securities.append({
                "isin": f"US{i:010d}",
                "issuer_name": f"Company {i}",
                "issuer_type": "Corporate",
                "face_value": 1000.0,
                "current_price": 100.0 + i * 0.1,
                "coupon_rate": 3.0 + i * 0.01,
                "credit_rating": "A",
                "yield_to_maturity": 3.5,
                "duration": 5.0 + i * 0.1
            })
        
        index_data = {
            "index_name": "Large Corporate Index",
            "index_type": "Corporate",
            "total_market_value": 50000000.0,
            "average_duration": 7.5,
            "average_yield": 3.75,
            "securities": securities
        }
        
        index = BondIndex(**index_data)
        self.assertEqual(len(index.securities), 50)
        self.assertIsInstance(index.securities[0], Bond)
        self.assertIsInstance(index.securities[49], Bond)


class TestBatchValidation(unittest.TestCase):
    """Test batch validation performance"""
    
    def test_batch_bond_validation(self):
        """Test batch validation of multiple bonds"""
        bonds_data = []
        for i in range(100):
            bonds_data.append({
                "isin": f"US{i:010d}",
                "issuer_name": f"Company {i}",
                "issuer_type": "Corporate",
                "face_value": 1000.0,
                "current_price": 100.0,
                "coupon_rate": 3.0,
                "credit_rating": "A",
                "yield_to_maturity": 3.5,
                "duration": 5.0
            })
        
        validator = Bond.validator()
        validator.set_batch_size(100)
        results = validator.validate_batch(bonds_data)
        
        # Results are booleans
        self.assertEqual(len(results), 100)
        self.assertIsInstance(results[0], bool)


if __name__ == '__main__':
    unittest.main()
