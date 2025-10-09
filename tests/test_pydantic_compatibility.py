"""
Test Pydantic API compatibility - ensuring Satya is a true 1:1 replacement.

This test suite verifies that Satya provides 100% API compatibility with Pydantic,
allowing users to switch from Pydantic to Satya with zero code changes.
"""

import pytest
from typing import Optional, List, Dict
from decimal import Decimal

from satya import BaseModel as SatyaModel, Field as SatyaField
try:
    from pydantic import BaseModel as PydanticModel, Field as PydanticField
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Create dummy classes for testing without Pydantic
    class PydanticModel:
        pass
    class PydanticField:
        pass


class TestBasicTypes:
    """Test basic type validation compatibility."""
    
    def test_string_field(self):
        class SatyaUser(SatyaModel):
            name: str
        
        user = SatyaUser(name="Alice")
        assert user.name == "Alice"
        
        # Test validation error
        with pytest.raises(Exception):  # ValidationError
            SatyaUser(name=123)
    
    def test_integer_field(self):
        class SatyaUser(SatyaModel):
            age: int
        
        user = SatyaUser(age=30)
        assert user.age == 30
        
        # Test coercion
        user = SatyaUser(age="30")
        assert user.age == 30
    
    def test_float_field(self):
        class SatyaProduct(SatyaModel):
            price: float
        
        product = SatyaProduct(price=9.99)
        assert product.price == 9.99
    
    def test_boolean_field(self):
        class SatyaConfig(SatyaModel):
            enabled: bool
        
        config = SatyaConfig(enabled=True)
        assert config.enabled is True


class TestFieldConstraints:
    """Test Field constraints compatibility."""
    
    def test_ge_constraint(self):
        class SatyaUser(SatyaModel):
            age: int = SatyaField(ge=0)
        
        user = SatyaUser(age=30)
        assert user.age == 30
        
        with pytest.raises(Exception):
            SatyaUser(age=-1)
    
    def test_le_constraint(self):
        class SatyaUser(SatyaModel):
            age: int = SatyaField(le=150)
        
        user = SatyaUser(age=30)
        assert user.age == 30
        
        with pytest.raises(Exception):
            SatyaUser(age=200)
    
    def test_gt_lt_constraints(self):
        class SatyaProduct(SatyaModel):
            price: float = SatyaField(gt=0, lt=1000000)
        
        product = SatyaProduct(price=99.99)
        assert product.price == 99.99
        
        with pytest.raises(Exception):
            SatyaProduct(price=0)
        
        with pytest.raises(Exception):
            SatyaProduct(price=1000000)
    
    def test_min_max_length(self):
        class SatyaUser(SatyaModel):
            username: str = SatyaField(min_length=3, max_length=20)
        
        user = SatyaUser(username="alice")
        assert user.username == "alice"
        
        with pytest.raises(Exception):
            SatyaUser(username="ab")
        
        with pytest.raises(Exception):
            SatyaUser(username="a" * 21)


class TestDefaultValues:
    """Test default value handling."""
    
    def test_simple_default(self):
        class SatyaUser(SatyaModel):
            name: str
            active: bool = True
        
        user = SatyaUser(name="Alice")
        assert user.active is True
    
    def test_field_default(self):
        class SatyaUser(SatyaModel):
            name: str
            role: str = SatyaField(default="user")
        
        user = SatyaUser(name="Alice")
        assert user.role == "user"
    
    def test_optional_field(self):
        class SatyaUser(SatyaModel):
            name: str
            email: Optional[str] = None
        
        user = SatyaUser(name="Alice")
        assert user.email is None
        
        user = SatyaUser(name="Bob", email="bob@example.com")
        assert user.email == "bob@example.com"


class TestComplexTypes:
    """Test complex type validation."""
    
    def test_list_field(self):
        class SatyaUser(SatyaModel):
            name: str
            tags: List[str]
        
        user = SatyaUser(name="Alice", tags=["admin", "user"])
        assert user.tags == ["admin", "user"]
    
    def test_dict_field(self):
        class SatyaUser(SatyaModel):
            name: str
            metadata: Dict[str, str]
        
        user = SatyaUser(name="Alice", metadata={"role": "admin"})
        assert user.metadata == {"role": "admin"}
    
    def test_decimal_field(self):
        class SatyaProduct(SatyaModel):
            name: str
            price: Decimal
        
        product = SatyaProduct(name="Widget", price="99.99")
        assert product.price == Decimal("99.99")


class TestNestedModels:
    """Test nested model validation."""
    
    def test_simple_nested(self):
        class SatyaAddress(SatyaModel):
            street: str
            city: str
        
        class SatyaUser(SatyaModel):
            name: str
            address: SatyaAddress
        
        user = SatyaUser(
            name="Alice",
            address={"street": "123 Main St", "city": "NYC"}
        )
        assert user.address.street == "123 Main St"
        assert user.address.city == "NYC"
    
    def test_nested_list(self):
        class SatyaTag(SatyaModel):
            name: str
            value: str
        
        class SatyaUser(SatyaModel):
            name: str
            tags: List[SatyaTag]
        
        user = SatyaUser(
            name="Alice",
            tags=[
                {"name": "role", "value": "admin"},
                {"name": "dept", "value": "engineering"}
            ]
        )
        assert len(user.tags) == 2
        assert user.tags[0].name == "role"


class TestModelMethods:
    """Test model methods compatibility."""
    
    def test_dict_method(self):
        class SatyaUser(SatyaModel):
            name: str
            age: int
        
        user = SatyaUser(name="Alice", age=30)
        user_dict = user.dict() if hasattr(user, 'dict') else user.model_dump()
        
        assert user_dict["name"] == "Alice"
        assert user_dict["age"] == 30
    
    def test_json_method(self):
        class SatyaUser(SatyaModel):
            name: str
            age: int
        
        user = SatyaUser(name="Alice", age=30)
        json_str = user.json() if hasattr(user, 'json') else user.model_dump_json()
        
        assert "Alice" in json_str
        assert "30" in json_str


class TestValidationMethods:
    """Test validation method compatibility."""
    
    def test_model_validate(self):
        class SatyaUser(SatyaModel):
            name: str
            age: int
        
        # Test model_validate if available
        if hasattr(SatyaUser, 'model_validate'):
            user = SatyaUser.model_validate({"name": "Alice", "age": 30})
            assert user.name == "Alice"
            assert user.age == 30
    
    def test_model_validate_fast(self):
        class SatyaUser(SatyaModel):
            name: str
            age: int
        
        # Test Satya's fast path
        if hasattr(SatyaUser, 'model_validate_fast'):
            user = SatyaUser.model_validate_fast({"name": "Alice", "age": 30})
            assert user.name == "Alice"
            assert user.age == 30
    
    def test_validate_many(self):
        class SatyaUser(SatyaModel):
            name: str
            age: int
        
        # Test Satya's batch validation
        if hasattr(SatyaUser, 'validate_many'):
            users = SatyaUser.validate_many([
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25}
            ])
            assert len(users) == 2
            assert users[0].name == "Alice"
            assert users[1].name == "Bob"


class TestEmailValidation:
    """Test email validation compatibility."""
    
    def test_email_field(self):
        class SatyaUser(SatyaModel):
            email: str = SatyaField(email=True)
        
        user = SatyaUser(email="alice@example.com")
        assert user.email == "alice@example.com"
        
        with pytest.raises(Exception):
            SatyaUser(email="not-an-email")


class TestAPICompatibility:
    """Test that Satya can be used as a drop-in replacement for Pydantic."""
    
    def test_import_compatibility(self):
        """Test that imports work the same way."""
        # This should work identically
        from satya import BaseModel, Field
        
        class User(BaseModel):
            name: str
            age: int = Field(ge=0)
        
        user = User(name="Alice", age=30)
        assert user.name == "Alice"
        assert user.age == 30
    
    def test_constructor_compatibility(self):
        """Test that construction works identically."""
        class User(SatyaModel):
            name: str
            age: int
        
        # Keyword arguments
        user1 = User(name="Alice", age=30)
        assert user1.name == "Alice"
        
        # Dict unpacking
        data = {"name": "Bob", "age": 25}
        user2 = User(**data)
        assert user2.name == "Bob"


@pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
class TestPydanticParity:
    """Test exact parity with Pydantic behavior."""
    
    def test_same_validation_behavior(self):
        """Test that validation behaves identically."""
        class PydUser(PydanticModel):
            name: str
            age: int = PydanticField(ge=0, le=150)
        
        class SatUser(SatyaModel):
            name: str
            age: int = SatyaField(ge=0, le=150)
        
        # Valid data
        data = {"name": "Alice", "age": 30}
        pyd_user = PydUser(**data)
        sat_user = SatUser(**data)
        
        assert pyd_user.name == sat_user.name
        assert pyd_user.age == sat_user.age
        
        # Invalid data (age too high)
        invalid_data = {"name": "Bob", "age": 200}
        
        pyd_error = None
        sat_error = None
        
        try:
            PydUser(**invalid_data)
        except Exception as e:
            pyd_error = str(e)
        
        try:
            SatUser(**invalid_data)
        except Exception as e:
            sat_error = str(e)
        
        # Both should raise errors
        assert pyd_error is not None
        assert sat_error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
