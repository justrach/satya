import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from satya.json_loader import load_json


class TestJSONLoader(unittest.TestCase):
    """Test JSON loader functionality"""

    def test_load_valid_json_dict(self):
        """Test loading valid JSON dictionary"""
        json_str = '{"name": "John", "age": 30, "active": true}'
        result = load_json(json_str)
        
        expected = {"name": "John", "age": 30, "active": True}
        self.assertEqual(result, expected)

    def test_load_valid_json_list(self):
        """Test loading valid JSON list"""
        json_str = '[1, 2, 3, "test", true, null]'
        result = load_json(json_str)
        
        expected = [1, 2, 3, "test", True, None]
        self.assertEqual(result, expected)

    def test_load_valid_json_primitives(self):
        """Test loading JSON primitives"""
        # String
        result = load_json('"hello world"')
        self.assertEqual(result, "hello world")
        
        # Number
        result = load_json('42')
        self.assertEqual(result, 42)
        
        # Float
        result = load_json('3.14')
        self.assertEqual(result, 3.14)
        
        # Boolean
        result = load_json('true')
        self.assertEqual(result, True)
        result = load_json('false')
        self.assertEqual(result, False)
        
        # Null
        result = load_json('null')
        self.assertEqual(result, None)

    def test_load_nested_json(self):
        """Test loading nested JSON structures"""
        json_str = '''
        {
            "user": {
                "name": "John Doe",
                "age": 30,
                "addresses": [
                    {
                        "type": "home",
                        "street": "123 Main St",
                        "city": "Anytown"
                    },
                    {
                        "type": "work",
                        "street": "456 Office Blvd",
                        "city": "Business City"
                    }
                ],
                "active": true,
                "balance": null
            },
            "metadata": {
                "created": "2023-01-01",
                "tags": ["user", "premium", "verified"]
            }
        }
        '''
        result = load_json(json_str)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["user"]["name"], "John Doe")
        self.assertEqual(len(result["user"]["addresses"]), 2)
        self.assertEqual(result["user"]["addresses"][0]["type"], "home")
        self.assertEqual(len(result["metadata"]["tags"]), 3)

    def test_load_invalid_json(self):
        """Test loading invalid JSON raises ValueError"""
        invalid_jsons = [
            '{"name": "John", "age":}',  # Missing value
            '{"name": "John" "age": 30}',  # Missing comma
            '{name: "John", "age": 30}',  # Unquoted key
            '{"name": "John", "age": 30,}',  # Trailing comma
            '[1, 2, 3,]',  # Trailing comma in array
            '{"name": "John", "age": 30',  # Unclosed brace
            'undefined',  # Invalid literal
            '',  # Empty string
            '   ',  # Whitespace only
        ]
        
        for invalid_json in invalid_jsons:
            with self.subTest(json_str=invalid_json):
                with self.assertRaises(ValueError):
                    load_json(invalid_json)

    def test_load_empty_structures(self):
        """Test loading empty JSON structures"""
        # Empty object
        result = load_json('{}')
        self.assertEqual(result, {})
        
        # Empty array
        result = load_json('[]')
        self.assertEqual(result, [])

    def test_load_unicode_json(self):
        """Test loading JSON with Unicode characters"""
        json_str = '{"name": "José", "city": "São Paulo", "emoji": "🚀", "chinese": "你好"}'
        result = load_json(json_str)
        
        self.assertEqual(result["name"], "José")
        self.assertEqual(result["city"], "São Paulo")
        self.assertEqual(result["emoji"], "🚀")
        self.assertEqual(result["chinese"], "你好")

    def test_load_escaped_characters(self):
        """Test loading JSON with escaped characters"""
        json_str = '{"quote": "He said \\"Hello\\"", "newline": "Line 1\\nLine 2", "backslash": "Path\\\\to\\\\file"}'
        result = load_json(json_str)
        
        self.assertEqual(result["quote"], 'He said "Hello"')
        self.assertEqual(result["newline"], "Line 1\nLine 2")
        self.assertEqual(result["backslash"], "Path\\to\\file")

    def test_load_large_numbers(self):
        """Test loading JSON with large numbers"""
        json_str = '{"small": -1000000, "large": 9007199254740991, "scientific": 1.23e10, "negative_exp": 1.23e-10}'
        result = load_json(json_str)
        
        self.assertEqual(result["small"], -1000000)
        self.assertEqual(result["large"], 9007199254740991)
        self.assertEqual(result["scientific"], 1.23e10)
        self.assertEqual(result["negative_exp"], 1.23e-10)

    @patch('satya.json_loader._HAVE_ORJSON', True)
    @patch('satya.json_loader.orjson')
    def test_uses_orjson_when_available(self, mock_orjson):
        """Test that orjson is used when available"""
        mock_orjson.loads.return_value = {"test": "data"}
        
        json_str = '{"test": "data"}'
        result = load_json(json_str)
        
        mock_orjson.loads.assert_called_once_with(json_str)
        self.assertEqual(result, {"test": "data"})

    @patch('satya.json_loader._HAVE_ORJSON', True)
    @patch('satya.json_loader.orjson')
    def test_orjson_exception_handling(self, mock_orjson):
        """Test that orjson exceptions are properly converted to ValueError"""
        mock_orjson.loads.side_effect = Exception("orjson parse error")
        
        json_str = '{"test": "data"}'
        with self.assertRaises(ValueError) as context:
            load_json(json_str)
        
        self.assertIn("Failed to parse JSON", str(context.exception))
        self.assertIn("orjson parse error", str(context.exception))

    @patch('satya.json_loader._HAVE_ORJSON', False)
    def test_fallback_to_json_module(self):
        """Test fallback to standard json module when orjson is not available"""
        json_str = '{"name": "John", "age": 30}'
        result = load_json(json_str)
        
        expected = {"name": "John", "age": 30}
        self.assertEqual(result, expected)

    @patch('satya.json_loader._HAVE_ORJSON', False)
    @patch('json.loads')
    def test_json_module_exception_handling(self, mock_json_loads):
        """Test that json.JSONDecodeError is properly converted to ValueError"""
        mock_json_loads.side_effect = json.JSONDecodeError("test error", "doc", 0)
        
        json_str = '{"invalid": json}'
        with self.assertRaises(ValueError) as context:
            load_json(json_str)
        
        self.assertIn("Failed to parse JSON", str(context.exception))

    def test_whitespace_handling(self):
        """Test JSON with various whitespace"""
        json_strs = [
            '  {"name": "John"}  ',  # Leading and trailing spaces
            '\n{\n  "name": "John"\n}\n',  # Newlines
            '\t{\t"name":\t"John"\t}\t',  # Tabs
            '{\r\n  "name": "John"\r\n}',  # Windows line endings
        ]
        
        expected = {"name": "John"}
        for json_str in json_strs:
            with self.subTest(json_str=repr(json_str)):
                result = load_json(json_str)
                self.assertEqual(result, expected)

    def test_performance_characteristics(self):
        """Test that the loader can handle reasonably large JSON"""
        # Create a moderately large JSON structure
        large_data = {
            "users": [
                {
                    "id": i,
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "active": i % 2 == 0,
                    "metadata": {
                        "created": "2023-01-01",
                        "updated": "2023-12-01",
                        "tags": [f"tag{j}" for j in range(5)]
                    }
                }
                for i in range(1000)  # 1000 users
            ],
            "pagination": {
                "total": 1000,
                "page": 1,
                "per_page": 1000
            }
        }
        
        json_str = json.dumps(large_data)
        
        # This should complete without issues
        result = load_json(json_str)
        self.assertEqual(len(result["users"]), 1000)
        self.assertEqual(result["pagination"]["total"], 1000)
        self.assertEqual(result["users"][0]["name"], "User 0")
        self.assertEqual(result["users"][999]["name"], "User 999")


if __name__ == '__main__':
    unittest.main()
