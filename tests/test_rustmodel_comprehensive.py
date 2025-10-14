"""
Comprehensive tests for RustModel
Test edge cases, stress scenarios, and correctness
"""

import pytest
from satya import Field
from satya.rust_model import RustModel


class TestBasicFunctionality:
    """Test basic RustModel functionality"""
    
    def test_simple_model_creation(self):
        """Test creating a simple model"""
        class User(RustModel):
            name: str
            age: int
        
        user = User(name="Alice", age=30)
        assert user.name == "Alice"
        assert user.age == 30
    
    def test_field_with_constraints(self):
        """Test fields with validation constraints"""
        class User(RustModel):
            name: str = Field(min_length=2, max_length=50)
            age: int = Field(ge=0, le=150)
        
        user = User(name="Alice", age=30)
        assert user.name == "Alice"
        assert user.age == 30
    
    def test_dict_conversion(self):
        """Test converting to dict"""
        class User(RustModel):
            name: str
            age: int
        
        user = User(name="Alice", age=30)
        data = user.dict()
        assert data == {"name": "Alice", "age": 30}
        assert isinstance(data, dict)
    
    def test_json_serialization(self):
        """Test JSON serialization"""
        class User(RustModel):
            name: str
            age: int
        
        user = User(name="Alice", age=30)
        json_str = user.json()
        assert '"name":"Alice"' in json_str or '"name": "Alice"' in json_str
        assert '"age":30' in json_str or '"age": 30' in json_str
    
    def test_from_dict(self):
        """Test creating from dict"""
        class User(RustModel):
            name: str
            age: int
        
        user = User.from_dict({"name": "Bob", "age": 25})
        assert user.name == "Bob"
        assert user.age == 25


class TestValidation:
    """Test validation logic"""
    
    def test_string_min_length(self):
        """Test string min_length constraint"""
        class User(RustModel):
            name: str = Field(min_length=2)
        
        # Valid
        user = User(name="Alice")
        assert user.name == "Alice"
        
        # Invalid
        with pytest.raises(ValueError, match="String length must be >= 2"):
            User(name="A")
    
    def test_string_max_length(self):
        """Test string max_length constraint"""
        class User(RustModel):
            name: str = Field(max_length=10)
        
        # Valid
        user = User(name="Alice")
        assert user.name == "Alice"
        
        # Invalid
        with pytest.raises(ValueError, match="String length must be <= 10"):
            User(name="A" * 11)
    
    def test_email_validation(self):
        """Test email validation"""
        class User(RustModel):
            email: str = Field(email=True)
        
        # Valid
        user = User(email="alice@example.com")
        assert user.email == "alice@example.com"
        
        # Invalid
        with pytest.raises(ValueError, match="Invalid email"):
            User(email="not-an-email")
    
    def test_url_validation(self):
        """Test URL validation"""
        class User(RustModel):
            website: str = Field(url=True)
        
        # Valid
        user = User(website="https://example.com")
        assert user.website == "https://example.com"
        
        # Invalid
        with pytest.raises(ValueError, match="Invalid URL"):
            User(website="not-a-url")
    
    def test_integer_ge(self):
        """Test integer ge (>=) constraint"""
        class User(RustModel):
            age: int = Field(ge=0)
        
        # Valid
        user = User(age=30)
        assert user.age == 30
        
        # Invalid
        with pytest.raises(ValueError, match="Value must be >= 0"):
            User(age=-1)
    
    def test_integer_le(self):
        """Test integer le (<=) constraint"""
        class User(RustModel):
            age: int = Field(le=150)
        
        # Valid
        user = User(age=30)
        assert user.age == 30
        
        # Invalid
        with pytest.raises(ValueError, match="Value must be <= 150"):
            User(age=200)
    
    def test_float_validation(self):
        """Test float validation"""
        class Product(RustModel):
            price: float = Field(gt=0, le=1000)
        
        # Valid
        product = Product(price=9.99)
        assert product.price == 9.99
        
        # Invalid - too low
        with pytest.raises(ValueError, match="Value must be > 0"):
            Product(price=0)
        
        # Invalid - too high
        with pytest.raises(ValueError, match="Value must be <= 1000"):
            Product(price=1001)


class TestFieldAccess:
    """Test field access and updates"""
    
    def test_field_read(self):
        """Test reading field values"""
        class User(RustModel):
            name: str
            age: int
        
        user = User(name="Alice", age=30)
        assert user.name == "Alice"
        assert user.age == 30
    
    def test_field_update(self):
        """Test updating field values"""
        class User(RustModel):
            name: str
            age: int = Field(ge=0, le=150)
        
        user = User(name="Alice", age=30)
        user.age = 31
        assert user.age == 31
    
    def test_field_update_with_validation(self):
        """Test field update triggers validation"""
        class User(RustModel):
            age: int = Field(ge=0, le=150)
        
        user = User(age=30)
        
        # Valid update
        user.age = 31
        assert user.age == 31
        
        # Invalid update
        with pytest.raises(ValueError, match="Value must be <= 150"):
            user.age = 200


class TestEdgeCases:
    """Test edge cases and corner scenarios"""
    
    def test_empty_model(self):
        """Test model with no fields"""
        class Empty(RustModel):
            pass
        
        empty = Empty()
        assert empty.dict() == {}
    
    def test_many_fields(self):
        """Test model with many fields (20+)"""
        class LargeModel(RustModel):
            f1: str
            f2: str
            f3: str
            f4: str
            f5: str
            f6: int
            f7: int
            f8: int
            f9: int
            f10: int
            f11: float
            f12: float
            f13: float
            f14: float
            f15: float
            f16: bool
            f17: bool
            f18: bool
            f19: bool
            f20: bool
        
        data = {f"f{i}": "test" if i <= 5 else (i if i <= 10 else (float(i) if i <= 15 else True)) for i in range(1, 21)}
        model = LargeModel(**data)
        assert model.f1 == "test"
        assert model.f10 == 10
        assert model.f15 == 15.0
        assert model.f20 is True
    
    def test_unicode_strings(self):
        """Test Unicode string handling"""
        class User(RustModel):
            name: str
        
        user = User(name="Alice 你好 🚀")
        assert user.name == "Alice 你好 🚀"
    
    def test_special_characters(self):
        """Test special characters in strings"""
        class User(RustModel):
            name: str
        
        user = User(name='Test "quotes" and \'apostrophes\' and \n newlines')
        assert "quotes" in user.name
    
    def test_zero_values(self):
        """Test zero/empty values"""
        class Data(RustModel):
            count: int
            amount: float
            name: str
        
        data = Data(count=0, amount=0.0, name="")
        assert data.count == 0
        assert data.amount == 0.0
        assert data.name == ""
    
    def test_boolean_fields(self):
        """Test boolean field handling"""
        class User(RustModel):
            active: bool
            verified: bool
        
        user = User(active=True, verified=False)
        assert user.active is True
        assert user.verified is False


class TestMultipleModels:
    """Test multiple model classes"""
    
    def test_multiple_independent_models(self):
        """Test creating multiple independent model classes"""
        class User(RustModel):
            name: str
            age: int
        
        class Product(RustModel):
            name: str
            price: float
        
        user = User(name="Alice", age=30)
        product = Product(name="Widget", price=9.99)
        
        assert user.name == "Alice"
        assert product.name == "Widget"
        assert user.age == 30
        assert product.price == 9.99
    
    def test_model_instances_independent(self):
        """Test model instances are independent"""
        class User(RustModel):
            name: str
            age: int
        
        user1 = User(name="Alice", age=30)
        user2 = User(name="Bob", age=25)
        
        user1.age = 31
        assert user1.age == 31
        assert user2.age == 25  # user2 unchanged


class TestStress:
    """Stress tests"""
    
    def test_create_many_instances(self):
        """Test creating many instances"""
        class User(RustModel):
            name: str
            age: int
        
        users = [User(name=f"User{i}", age=20 + i) for i in range(1000)]
        assert len(users) == 1000
        assert users[0].name == "User0"
        assert users[999].name == "User999"
    
    def test_rapid_field_updates(self):
        """Test rapid field updates"""
        class Counter(RustModel):
            count: int = Field(ge=0)
        
        counter = Counter(count=0)
        for i in range(1000):
            counter.count = i
        
        assert counter.count == 999
    
    def test_large_string_values(self):
        """Test large string values"""
        class Data(RustModel):
            content: str
        
        large_string = "A" * 10000
        data = Data(content=large_string)
        assert len(data.content) == 10000


class TestRepr:
    """Test string representations"""
    
    def test_repr(self):
        """Test __repr__"""
        class User(RustModel):
            name: str
            age: int
        
        user = User(name="Alice", age=30)
        repr_str = repr(user)
        assert "User" in repr_str
    
    def test_str(self):
        """Test __str__"""
        class User(RustModel):
            name: str
            age: int
        
        user = User(name="Alice", age=30)
        str_str = str(user)
        assert "User" in str_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
