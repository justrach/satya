import os
import sys
import unittest
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from uuid import uuid4

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import satya
from satya import Model, Field, ValidationError, ModelValidationError


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""

    def test_empty_model(self):
        """Test model with no fields"""
        class EmptyModel(Model):
            pass
        
        # Should be able to create empty model
        empty = EmptyModel()
        self.assertIsInstance(empty, EmptyModel)
        
        # Should work with empty dict
        empty2 = EmptyModel(**{})
        self.assertIsInstance(empty2, EmptyModel)

    def test_model_with_only_optional_fields(self):
        """Test model with all optional fields"""
        class OptionalModel(Model):
            name: Optional[str] = Field(required=False, default=None)
            age: Optional[int] = Field(required=False, default=None)
        
        # Should work with no data
        model = OptionalModel()
        self.assertIsNone(model.name)
        self.assertIsNone(model.age)
        
        # Should work with partial data
        model2 = OptionalModel(name="John")
        self.assertEqual(model2.name, "John")
        self.assertIsNone(model2.age)

    def test_model_with_complex_defaults(self):
        """Test model with complex default values"""
        class DefaultModel(Model):
            tags: List[str] = Field(default=[])
            metadata: Dict[str, str] = Field(default={})
            active: bool = Field(default=True)
        
        model = DefaultModel()
        self.assertEqual(model.tags, [])
        self.assertEqual(model.metadata, {})
        self.assertEqual(model.active, True)
        
        # Defaults should not be shared between instances
        model1 = DefaultModel()
        model2 = DefaultModel()
        
        model1.tags.append("test")
        self.assertEqual(len(model1.tags), 1)
        self.assertEqual(len(model2.tags), 0)

    def test_none_values_handling(self):
        """Test handling of None values"""
        class TestModel(Model):
            required_field: str = Field(description="Required")
            optional_field: Optional[str] = Field(required=False, default=None)
        
        # None in required field should fail
        with self.assertRaises(ModelValidationError):
            TestModel(required_field=None, optional_field="test")
        
        # None in optional field should work
        model = TestModel(required_field="test", optional_field=None)
        self.assertEqual(model.required_field, "test")
        self.assertIsNone(model.optional_field)

    def test_deeply_nested_models(self):
        """Test deeply nested model structures"""
        class Level3(Model):
            value: str = Field(description="Deep value")
        
        class Level2(Model):
            level3: Level3 = Field(description="Level 3 data")
            items: List[Level3] = Field(default=[], description="List of level 3")
        
        class Level1(Model):
            level2: Level2 = Field(description="Level 2 data")
        
        # Valid nested structure
        data = {
            "level2": {
                "level3": {"value": "deep"},
                "items": [
                    {"value": "item1"},
                    {"value": "item2"}
                ]
            }
        }
        
        model = Level1(**data)
        self.assertEqual(model.level2.level3.value, "deep")
        self.assertEqual(len(model.level2.items), 2)
        self.assertEqual(model.level2.items[0].value, "item1")

    def test_circular_reference_prevention(self):
        """Test that circular references are handled appropriately"""
        # This tests the system's ability to handle self-referential structures
        class Node(Model):
            name: str = Field(description="Node name")
            # Note: We can't easily test true circular references without
            # more complex model definition, but we can test self-contained structures
        
        data = {
            "name": "root"
        }
        
        node = Node(**data)
        self.assertEqual(node.name, "root")

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters"""
        class UnicodeModel(Model):
            name: str = Field(description="Unicode name")
            emoji: str = Field(description="Emoji field")
        
        # Test various Unicode characters
        test_cases = [
            {"name": "José María", "emoji": "🚀"},
            {"name": "北京", "emoji": "🇨🇳"}, 
            {"name": "Москва", "emoji": "🇷🇺"},
            {"name": "العربية", "emoji": "🕌"},
            {"name": "Test\nNewline", "emoji": "📝"},
            {"name": "Tab\tSeparated", "emoji": "📋"}
        ]
        
        for test_data in test_cases:
            with self.subTest(data=test_data):
                model = UnicodeModel(**test_data)
                self.assertEqual(model.name, test_data["name"])
                self.assertEqual(model.emoji, test_data["emoji"])

    def test_very_large_strings(self):
        """Test handling of very large string values"""
        class LargeStringModel(Model):
            content: str = Field(max_length=100000, description="Large content")
        
        # Test with large but valid string
        large_content = "x" * 50000
        model = LargeStringModel(content=large_content)
        self.assertEqual(len(model.content), 50000)
        
        # Test with string exceeding limit
        too_large = "x" * 100001
        with self.assertRaises(ModelValidationError):
            LargeStringModel(content=too_large)

    def test_numeric_edge_cases(self):
        """Test numeric edge cases"""
        class NumericModel(Model):
            int_field: int = Field(description="Integer field")
            float_field: float = Field(description="Float field")
        
        # Test extreme values
        edge_cases = [
            {"int_field": 0, "float_field": 0.0},
            {"int_field": -1, "float_field": -1.0},
            {"int_field": 2**31 - 1, "float_field": 1e10},  # Large positive
            {"int_field": -2**31, "float_field": -1e10},     # Large negative
        ]
        
        for case in edge_cases:
            with self.subTest(case=case):
                model = NumericModel(**case)
                self.assertEqual(model.int_field, case["int_field"])
                self.assertEqual(model.float_field, case["float_field"])

    def test_boolean_edge_cases(self):
        """Test boolean field edge cases"""
        class BoolModel(Model):
            flag: bool = Field(description="Boolean flag")
        
        # Test various truthy/falsy values that should be converted
        test_cases = [
            (True, True),
            (False, False),
            # Note: Type coercion behavior depends on validator implementation
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                model = BoolModel(flag=input_val)
                self.assertEqual(model.flag, expected)

    def test_empty_and_whitespace_strings(self):
        """Test handling of empty and whitespace-only strings"""
        class StringModel(Model):
            name: str = Field(min_length=1, description="Name")
            optional_name: Optional[str] = Field(required=False, description="Optional")
        
        # Empty string should fail min_length validation
        with self.assertRaises(ModelValidationError):
            StringModel(name="")
        
        # Whitespace-only string behavior
        with self.assertRaises(ModelValidationError):
            StringModel(name="   ")  # Should fail if trimmed to empty
        
        # Optional field with empty string
        model = StringModel(name="valid", optional_name="")
        self.assertEqual(model.name, "valid")

    def test_list_edge_cases(self):
        """Test list field edge cases"""
        class ListModel(Model):
            items: List[str] = Field(default=[], description="String list")
            numbers: List[int] = Field(min_items=0, max_items=5, description="Number list")
        
        # Empty lists
        model = ListModel(items=[], numbers=[])
        self.assertEqual(model.items, [])
        self.assertEqual(model.numbers, [])
        
        # Single item lists
        model2 = ListModel(items=["single"], numbers=[42])
        self.assertEqual(len(model2.items), 1)
        self.assertEqual(model2.numbers[0], 42)

    def test_dict_edge_cases(self):
        """Test dictionary field edge cases"""
        class DictModel(Model):
            metadata: Dict[str, str] = Field(default={}, description="Metadata")
        
        # Empty dict
        model = DictModel(metadata={})
        self.assertEqual(model.metadata, {})
        
        # Dict with various key types (as strings)
        test_dict = {
            "key1": "value1",
            "key_with_underscore": "value2", 
            "key-with-dash": "value3",
            "123": "numeric_key"
        }
        
        model2 = DictModel(metadata=test_dict)
        self.assertEqual(model2.metadata, test_dict)

    def test_model_construction_edge_cases(self):
        """Test edge cases in model construction"""
        class TestModel(Model):
            name: str = Field(description="Name")
            age: int = Field(default=0, description="Age")
        
        # Test with extra fields in strict mode
        data_with_extra = {
            "name": "John",
            "age": 30,
            "extra_field": "should_be_ignored"
        }
        
        # Should work (extra fields ignored by default)
        model = TestModel(**data_with_extra)
        self.assertEqual(model.name, "John")
        self.assertEqual(model.age, 30)
        
        # Test model_construct with invalid data (bypasses validation)
        invalid_data = {"name": "", "age": -1}  # Would normally fail validation
        model2 = TestModel.model_construct(**invalid_data)
        self.assertEqual(model2.name, "")
        self.assertEqual(model2.age, -1)

    def test_json_edge_cases(self):
        """Test JSON serialization/deserialization edge cases"""
        class JsonModel(Model):
            text: str = Field(description="Text field")
            number: float = Field(description="Number field")
        
        # Test with special JSON values
        special_cases = [
            {"text": "normal", "number": 3.14},
            {"text": '{"nested": "json"}', "number": 0.0},
            {"text": "newline\ntext", "number": -0.0},
            {"text": "", "number": float('inf')},  # May not work depending on JSON handling
        ]
        
        for case in special_cases[:2]:  # Skip infinite values for now
            with self.subTest(case=case):
                model = JsonModel(**case)
                json_str = model.model_dump_json()
                self.assertIsInstance(json_str, str)
                
                # Should be able to parse back
                model2 = JsonModel.model_validate_json(json_str)
                self.assertEqual(model2.text, case["text"])

    def test_validation_error_accumulation(self):
        """Test that multiple validation errors are properly accumulated"""
        class MultiConstraintModel(Model):
            name: str = Field(min_length=5, max_length=10, description="Name")
            age: int = Field(ge=0, le=100, description="Age")
            email: str = Field(email=True, description="Email")
        
        # Data with multiple validation failures
        invalid_data = {
            "name": "x",  # Too short
            "age": -5,    # Too low
            "email": "not-an-email"  # Invalid format
        }
        
        try:
            MultiConstraintModel(**invalid_data)
            self.fail("Expected ModelValidationError")
        except ModelValidationError as e:
            # Should have multiple errors
            self.assertGreater(len(e.errors), 1)
            
            # Check that different field errors are captured
            error_fields = {error.field for error in e.errors}
            # Should have errors for different fields
            self.assertGreater(len(error_fields), 1)


class TestModelInheritance(unittest.TestCase):
    """Test model inheritance scenarios"""

    def test_simple_inheritance(self):
        """Test basic model inheritance"""
        class BaseModel(Model):
            id: str = Field(description="Base ID")
            created_at: str = Field(description="Creation time")
        
        class ExtendedModel(BaseModel):
            name: str = Field(description="Extended name")
            active: bool = Field(default=True, description="Active flag")
        
        # Should inherit fields from base
        data = {
            "id": "123",
            "created_at": "2023-01-01",
            "name": "Test",
            "active": False
        }
        
        model = ExtendedModel(**data)
        self.assertEqual(model.id, "123")
        self.assertEqual(model.created_at, "2023-01-01")
        self.assertEqual(model.name, "Test")
        self.assertEqual(model.active, False)

    def test_inheritance_with_override(self):
        """Test field override in inheritance"""
        class BaseModel(Model):
            name: str = Field(description="Base name")
        
        class ExtendedModel(BaseModel):
            name: str = Field(min_length=5, description="Extended name with constraints")
        
        # Should use extended field constraints
        with self.assertRaises(ModelValidationError):
            ExtendedModel(name="x")  # Should fail min_length=5 from extended model


if __name__ == '__main__':
    unittest.main()
