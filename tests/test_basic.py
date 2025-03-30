import unittest
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