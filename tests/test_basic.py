import os
import sys
import unittest

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import satya

class TestBasicFunctionality(unittest.TestCase):
    def test_import(self):
        """Test that the module can be imported successfully."""
        self.assertTrue(hasattr(satya, '__version__'))
        
    def test_model_creation(self):
        """Test that basic Model class exists."""
        self.assertTrue(hasattr(satya, 'Model'))

if __name__ == '__main__':
    unittest.main() 