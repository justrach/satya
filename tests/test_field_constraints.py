import os
import sys
import unittest
from typing import List, Optional
from datetime import datetime
from uuid import UUID
import re

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import satya
from satya import Model, Field, ValidationError, ModelValidationError


class TestFieldConstraints(unittest.TestCase):
    """Test various field constraint validations"""

    def test_string_length_constraints(self):
        """Test string min/max length constraints"""
        class TestModel(Model):
            short_name: str = Field(min_length=2, max_length=5)

        # Valid length
        valid = TestModel(short_name="test")
        self.assertEqual(valid.short_name, "test")

        # Too short
        with self.assertRaises(ModelValidationError):
            TestModel(short_name="x")

        # Too long  
        with self.assertRaises(ModelValidationError):
            TestModel(short_name="toolong")

        # Edge cases - exactly at limits
        edge_min = TestModel(short_name="ab")
        self.assertEqual(edge_min.short_name, "ab")
        
        edge_max = TestModel(short_name="abcde")
        self.assertEqual(edge_max.short_name, "abcde")

    def test_integer_constraints(self):
        """Test integer value constraints"""
        class TestModel(Model):
            age: int = Field(ge=0, le=150)
            score: int = Field(gt=0, lt=100)

        # Valid values
        valid = TestModel(age=25, score=85)
        self.assertEqual(valid.age, 25)
        self.assertEqual(valid.score, 85)

        # Age constraints (ge/le - inclusive)
        edge_age_min = TestModel(age=0, score=50)
        self.assertEqual(edge_age_min.age, 0)
        
        edge_age_max = TestModel(age=150, score=50)
        self.assertEqual(edge_age_max.age, 150)

        # Score constraints (gt/lt - exclusive)
        with self.assertRaises(ModelValidationError):
            TestModel(age=25, score=0)  # score must be > 0

        with self.assertRaises(ModelValidationError):
            TestModel(age=25, score=100)  # score must be < 100

        # Age violations
        with self.assertRaises(ModelValidationError):
            TestModel(age=-1, score=50)

        with self.assertRaises(ModelValidationError):
            TestModel(age=151, score=50)

    def test_float_constraints(self):
        """Test float value constraints"""
        class TestModel(Model):
            price: float = Field(gt=0.0, description="Product price")
            discount: float = Field(ge=0.0, le=1.0, description="Discount percentage")

        # Valid values
        valid = TestModel(price=99.99, discount=0.15)
        self.assertEqual(valid.price, 99.99)
        self.assertEqual(valid.discount, 0.15)

        # Edge cases
        edge_discount = TestModel(price=1.0, discount=0.0)
        self.assertEqual(edge_discount.discount, 0.0)

        edge_max_discount = TestModel(price=1.0, discount=1.0)
        self.assertEqual(edge_max_discount.discount, 1.0)

        # Violations
        with self.assertRaises(ModelValidationError):
            TestModel(price=0.0, discount=0.5)  # price must be > 0

        with self.assertRaises(ModelValidationError):
            TestModel(price=10.0, discount=-0.1)  # discount must be >= 0

        with self.assertRaises(ModelValidationError):
            TestModel(price=10.0, discount=1.1)  # discount must be <= 1

    def test_pattern_constraints(self):
        """Test regex pattern constraints"""
        class TestModel(Model):
            username: str = Field(pattern=r"^[a-zA-Z0-9_]+$", description="Username")
            phone: str = Field(pattern=r"^\+\d{1,3}-\d{3}-\d{3}-\d{4}$", description="Phone number")

        # Valid patterns
        valid = TestModel(
            username="john_doe123", 
            phone="+1-555-123-4567"
        )
        self.assertEqual(valid.username, "john_doe123")
        self.assertEqual(valid.phone, "+1-555-123-4567")

        # Invalid username patterns
        with self.assertRaises(ModelValidationError):
            TestModel(username="john-doe", phone="+1-555-123-4567")  # hyphen not allowed

        with self.assertRaises(ModelValidationError):
            TestModel(username="john doe", phone="+1-555-123-4567")  # space not allowed

        with self.assertRaises(ModelValidationError):
            TestModel(username="john@doe", phone="+1-555-123-4567")  # @ not allowed

        # Invalid phone patterns
        with self.assertRaises(ModelValidationError):
            TestModel(username="johndoe", phone="555-123-4567")  # missing country code

        with self.assertRaises(ModelValidationError):
            TestModel(username="johndoe", phone="+1-555-1234567")  # wrong format

    def test_email_constraint(self):
        """Test email validation constraint"""
        class TestModel(Model):
            email: str = Field(email=True, description="Email address")

        # Valid emails
        valid_emails = [
            "user@example.com",
            "test.email@domain.org", 
            "user+tag@example.co.uk",
            "firstname.lastname@company.io"
        ]

        for email in valid_emails:
            with self.subTest(email=email):
                model = TestModel(email=email)
                self.assertEqual(model.email, email)

        # Invalid emails
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user.name",
            "user@.com",
            "user@domain",
            "user space@domain.com"
        ]

        for email in invalid_emails:
            with self.subTest(email=email):
                with self.assertRaises(ModelValidationError):
                    TestModel(email=email)

    def test_url_constraint(self):
        """Test URL validation constraint"""
        class TestModel(Model):
            website: str = Field(url=True, description="Website URL")

        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://test.org",
            "https://subdomain.example.com/path",
            "https://example.com:8080/path?query=value"
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                model = TestModel(website=url)
                self.assertEqual(model.website, url)

        # Invalid URLs
        invalid_urls = [
            "not-a-url",
            "example.com",  # missing protocol
            "ftp://example.com",  # wrong protocol
            "https://",  # incomplete
        ]

        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ModelValidationError):
                    TestModel(website=url)

    def test_list_constraints(self):
        """Test list field constraints"""
        class TestModel(Model):
            tags: List[str] = Field(min_items=1, max_items=5, description="Tags")
            scores: List[int] = Field(min_items=0, max_items=3, unique_items=True, description="Unique scores")

        # Valid lists
        valid = TestModel(
            tags=["python", "validation"],
            scores=[85, 92, 78]
        )
        self.assertEqual(len(valid.tags), 2)
        self.assertEqual(len(valid.scores), 3)

        # Edge cases
        edge_min_tags = TestModel(tags=["single"], scores=[])
        self.assertEqual(len(edge_min_tags.tags), 1)
        self.assertEqual(len(edge_min_tags.scores), 0)

        edge_max_tags = TestModel(tags=["a", "b", "c", "d", "e"], scores=[100])
        self.assertEqual(len(edge_max_tags.tags), 5)

        # Violations - too few items
        with self.assertRaises(ModelValidationError):
            TestModel(tags=[], scores=[])  # tags must have at least 1 item

        # Violations - too many items  
        with self.assertRaises(ModelValidationError):
            TestModel(tags=["a", "b", "c", "d", "e", "f"], scores=[])  # tags max 5 items

        with self.assertRaises(ModelValidationError):
            TestModel(tags=["test"], scores=[1, 2, 3, 4])  # scores max 3 items

        # Note: unique_items constraint testing would require core validator support

    def test_enum_constraints(self):
        """Test enum field constraints"""
        class TestModel(Model):
            status: str = Field(enum=["active", "inactive", "pending"], description="Status")
            priority: str = Field(enum=["low", "medium", "high"], description="Priority")

        # Valid enum values
        valid = TestModel(status="active", priority="high")
        self.assertEqual(valid.status, "active")
        self.assertEqual(valid.priority, "high")

        # All valid combinations
        for status in ["active", "inactive", "pending"]:
            for priority in ["low", "medium", "high"]:
                with self.subTest(status=status, priority=priority):
                    model = TestModel(status=status, priority=priority)
                    self.assertEqual(model.status, status)
                    self.assertEqual(model.priority, priority)

        # Invalid enum values
        with self.assertRaises(ModelValidationError):
            TestModel(status="invalid", priority="high")

        with self.assertRaises(ModelValidationError):
            TestModel(status="active", priority="invalid")

    def test_combined_constraints(self):
        """Test multiple constraints on the same field"""
        class TestModel(Model):
            username: str = Field(
                min_length=3, 
                max_length=20, 
                pattern=r"^[a-zA-Z0-9_]+$",
                description="Username with multiple constraints"
            )

        # Valid - meets all constraints
        valid = TestModel(username="john_doe123")
        self.assertEqual(valid.username, "john_doe123")

        # Fails length constraint
        with self.assertRaises(ModelValidationError):
            TestModel(username="jo")  # too short

        with self.assertRaises(ModelValidationError):
            TestModel(username="a" * 25)  # too long

        # Fails pattern constraint
        with self.assertRaises(ModelValidationError):
            TestModel(username="john-doe")  # hyphen not allowed in pattern

    def test_optional_field_constraints(self):
        """Test constraints on optional fields"""
        class TestModel(Model):
            name: str = Field(description="Required name")
            nickname: Optional[str] = Field(
                required=False,
                min_length=2,
                max_length=10,
                description="Optional nickname"
            )

        # Valid with optional field
        with_nickname = TestModel(name="John", nickname="Johnny")
        self.assertEqual(with_nickname.nickname, "Johnny")

        # Valid without optional field
        without_nickname = TestModel(name="John")
        self.assertIsNone(getattr(without_nickname, 'nickname', None))

        # Invalid optional field value
        with self.assertRaises(ModelValidationError):
            TestModel(name="John", nickname="J")  # nickname too short


class TestComplexConstraintScenarios(unittest.TestCase):
    """Test complex constraint validation scenarios"""

    def test_nested_model_constraints(self):
        """Test constraints in nested models"""
        class Address(Model):
            street: str = Field(min_length=5, description="Street address")
            zipcode: str = Field(pattern=r"^\d{5}$", description="5-digit ZIP code")

        class Person(Model):
            name: str = Field(min_length=2, description="Person name")
            address: Address = Field(description="Home address")

        # Valid nested model
        valid = Person(
            name="John",
            address={
                "street": "123 Main Street",
                "zipcode": "12345"
            }
        )
        self.assertEqual(valid.name, "John")
        self.assertEqual(valid.address.street, "123 Main Street")

        # Invalid nested field
        with self.assertRaises(ModelValidationError):
            Person(
                name="John",
                address={
                    "street": "St",  # too short
                    "zipcode": "12345"
                }
            )

        with self.assertRaises(ModelValidationError):
            Person(
                name="John",
                address={
                    "street": "123 Main Street",
                    "zipcode": "1234"  # invalid pattern
                }
            )

    def test_list_of_models_with_constraints(self):
        """Test constraints on lists containing models"""
        class Tag(Model):
            name: str = Field(min_length=1, max_length=20, description="Tag name")
            color: str = Field(enum=["red", "blue", "green"], description="Tag color")

        class Post(Model):
            title: str = Field(min_length=5, description="Post title")
            tags: List[Tag] = Field(min_items=1, max_items=3, description="Post tags")

        # Valid post with tags
        valid = Post(
            title="My First Post",
            tags=[
                {"name": "python", "color": "blue"},
                {"name": "tutorial", "color": "green"}
            ]
        )
        self.assertEqual(len(valid.tags), 2)
        self.assertEqual(valid.tags[0].name, "python")

        # Invalid - no tags (violates min_items)
        with self.assertRaises(ModelValidationError):
            Post(title="My Post", tags=[])

        # Invalid - too many tags
        with self.assertRaises(ModelValidationError):
            Post(
                title="My Post",
                tags=[
                    {"name": "tag1", "color": "red"},
                    {"name": "tag2", "color": "blue"}, 
                    {"name": "tag3", "color": "green"},
                    {"name": "tag4", "color": "red"}  # exceeds max_items=3
                ]
            )

        # Invalid tag content
        with self.assertRaises(ModelValidationError):
            Post(
                title="My Post",
                tags=[{"name": "", "color": "blue"}]  # empty name violates min_length
            )

    def test_constraint_error_messages(self):
        """Test that constraint violations produce appropriate error messages"""
        class TestModel(Model):
            email: str = Field(email=True, description="Email address")
            age: int = Field(ge=18, le=65, description="Age")

        # Test email constraint error
        try:
            TestModel(email="invalid", age=25)
            self.fail("Expected ModelValidationError")
        except ModelValidationError as e:
            # Should contain information about the validation failure
            self.assertTrue(len(e.errors) > 0)

        # Test age constraint error
        try:
            TestModel(email="test@example.com", age=16)
            self.fail("Expected ModelValidationError")
        except ModelValidationError as e:
            self.assertTrue(len(e.errors) > 0)


if __name__ == '__main__':
    unittest.main()
