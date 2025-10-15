"""
Test suite for field access developer experience.
Ensures that field values are returned directly, not Field objects.
"""
import unittest
from satya import Model, Field, ModelValidationError


class TestFieldAccessDX(unittest.TestCase):
    """Test that field access returns values, not Field objects"""
    
    def test_basic_field_access_returns_values(self):
        """Field access should return actual values, not Field objects"""
        class User(Model):
            name: str
            age: int = Field(ge=0)
            
        user = User(name="Alice", age=30)
        
        # Should return actual values
        self.assertIsInstance(user.name, str)
        self.assertEqual(user.name, "Alice")
        self.assertIsInstance(user.age, int)
        self.assertEqual(user.age, 30)
    
    def test_math_operations_work(self):
        """Math operations should work directly on field values"""
        class Account(Model):
            balance: float = Field(gt=0)
            fee: float = Field(ge=0)
            
        account = Account(balance=1000.0, fee=10.0)
        
        # Math operations should work
        result = account.balance - account.fee
        self.assertEqual(result, 990.0)
        
        result = account.balance + account.fee
        self.assertEqual(result, 1010.0)
        
        result = account.balance * 0.1
        self.assertEqual(result, 100.0)
        
        result = account.balance / 10
        self.assertEqual(result, 100.0)
    
    def test_comparison_operations_work(self):
        """Comparison operations should work directly on field values"""
        class Product(Model):
            price: float = Field(gt=0)
            quantity: int = Field(ge=0)
            
        product = Product(price=99.99, quantity=5)
        
        # Comparisons should work
        self.assertTrue(product.price < 100)
        self.assertTrue(product.price > 50)
        self.assertTrue(product.price <= 99.99)
        self.assertTrue(product.price >= 99.99)
        self.assertTrue(product.price == 99.99)
        self.assertTrue(product.quantity >= 0)
    
    def test_string_formatting_works(self):
        """String formatting should work with field values"""
        class User(Model):
            name: str
            age: int
            
        user = User(name="Bob", age=25)
        
        # f-strings should work
        result = f"Name: {user.name}, Age: {user.age}"
        self.assertEqual(result, "Name: Bob, Age: 25")
        
        # Format specifiers should work
        result = f"Age: {user.age:03d}"
        self.assertEqual(result, "Age: 025")
    
    def test_default_values_applied(self):
        """Default values should be applied for missing fields"""
        class Config(Model):
            host: str = Field(default="localhost")
            port: int = Field(default=8080)
            debug: bool = Field(default=False)
            
        config = Config(host="example.com")
        
        # Defaults should be applied
        self.assertEqual(config.host, "example.com")
        self.assertEqual(config.port, 8080)
        self.assertEqual(config.debug, False)
        
        # Should be actual types
        self.assertIsInstance(config.port, int)
        self.assertIsInstance(config.debug, bool)
    
    def test_nested_model_field_access(self):
        """Nested model field access should work"""
        class Address(Model):
            street: str
            city: str
            
        class Person(Model):
            name: str
            address: Address
            
        person = Person(
            name="Charlie",
            address=Address(street="123 Main St", city="NYC")
        )
        
        # Nested field access should work
        self.assertEqual(person.address.street, "123 Main St")
        self.assertEqual(person.address.city, "NYC")
        
        # Should be actual types
        self.assertIsInstance(person.address.street, str)
    
    def test_list_comprehension_with_fields(self):
        """List comprehensions should work with field values"""
        class Item(Model):
            price: float = Field(gt=0)
            discount: float = Field(ge=0, le=1)
            
        item = Item(price=100.0, discount=0.2)
        
        # List comprehension should work
        prices = [item.price * (1 - item.discount) for _ in range(3)]
        self.assertEqual(prices, [80.0, 80.0, 80.0])
    
    def test_function_parameters_with_fields(self):
        """Functions should accept field values directly"""
        class Rectangle(Model):
            width: float = Field(gt=0)
            height: float = Field(gt=0)
            
        def calculate_area(width: float, height: float) -> float:
            return width * height
        
        rect = Rectangle(width=10.0, height=5.0)
        
        # Should work without manual conversion
        area = calculate_area(rect.width, rect.height)
        self.assertEqual(area, 50.0)
    
    def test_constraints_still_validated(self):
        """Constraints should still be validated"""
        class User(Model):
            age: int = Field(ge=0, le=150)
            
        # Valid age should work
        user = User(age=30)
        self.assertEqual(user.age, 30)
        
        # Invalid age should raise error
        with self.assertRaises(ModelValidationError):
            User(age=-1)
        
        with self.assertRaises(ModelValidationError):
            User(age=200)
    
    def test_model_instance_as_nested_field(self):
        """Should accept Model instances as nested fields"""
        class Address(Model):
            city: str
            
        class Person(Model):
            name: str
            address: Address
            
        # Create address first
        address = Address(city="NYC")
        
        # Pass Model instance directly
        person = Person(name="Dave", address=address)
        
        # Should work
        self.assertEqual(person.address.city, "NYC")
        self.assertIsInstance(person.address, Address)


class TestPydanticCompatibility(unittest.TestCase):
    """Test that Satya provides Pydantic-like developer experience"""
    
    def test_pydantic_style_usage(self):
        """Should work like Pydantic"""
        class User(Model):
            name: str
            age: int = Field(ge=0, le=150)
            email: str
            
        user = User(name="Alice", age=30, email="alice@example.com")
        
        # All Pydantic-style operations should work
        self.assertEqual(user.name, "Alice")
        self.assertEqual(user.age, 30)
        self.assertTrue(user.age + 5 == 35)  # Math
        self.assertTrue(user.age > 18)  # Comparison
        
        # String formatting
        result = f"Name: {user.name}, Age: {user.age}"
        self.assertIn("Alice", result)
        self.assertIn("30", result)


if __name__ == "__main__":
    unittest.main()
