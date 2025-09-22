"""
Tests for schema fixing functionality
"""
import pytest
from satya import Model, Field
from enum import Enum


class TestSchemaFix:
    def test_schema_fixes_nested_types(self):
        """Test that nested type objects are flattened"""
        from satya import Model, Field

        class User(Model):
            name: str = Field(description="User name")
            age: int = Field(description="User age")

        schema = User.model_json_schema()

        # Verify type fields are strings, not objects
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"

        # Verify required fields are present
        assert "name" in schema["required"]
        assert "age" in schema["required"]

    def test_nested_model_schema_fix(self):
        """Test schema fixing for nested models"""
        class Address(Model):
            street: str
            city: str

        class User(Model):
            name: str
            address: Address

        schema = User.model_json_schema()

        # Verify nested model properties are properly handled
        assert schema["properties"]["name"]["type"] == "string"
        assert "type" in schema["properties"]["address"]  # Nested model schema should be included

    def test_schema_with_optional_fields(self):
        """Test schema fixing with Optional fields"""
        from typing import Optional

        class User(Model):
            name: str
            age: Optional[int] = None

        schema = User.model_json_schema()

        # Verify type fields are strings, not objects
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["nullable"] == True

    def test_schema_with_enums(self):
        """Test schema fixing with Enum fields"""
        class Status(Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        class User(Model):
            name: str
            status: Status

        schema = User.model_json_schema()

        # Verify enum handling
        assert schema["properties"]["status"]["type"] == "string"
        assert schema["properties"]["status"]["enum"] == ["active", "inactive"]

    def test_schema_with_lists(self):
        """Test schema fixing with list fields"""
        class User(Model):
            name: str
            tags: list[str]

        schema = User.model_json_schema()

        # Verify list handling
        assert schema["properties"]["tags"]["type"] == "array"
        assert schema["properties"]["tags"]["items"]["type"] == "string"
