from satya import StreamValidator, Model, Field
import json
from typing import List, Dict
from dataclasses import dataclass

# Define our models for API request/response validation
class User(Model):
    id: int = Field(description="User ID")
    name: str = Field(description="User's full name")
    email: str = Field(description="User's email address")
    active: bool = Field(default=True, description="Whether user is active")
    tags: List[str] = Field(default=[], description="User tags")
    metadata: Dict[str, str] = Field(default={}, description="Additional metadata")

class APIResponse(Model):
    success: bool = Field(description="Whether the request was successful")
    data: List[User] = Field(description="List of users")
    total_count: int = Field(description="Total number of users")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")

def main():
    """
    This example demonstrates how to validate nested models with Satya.
    
    You can use either approach:
    1. validator.validate(data) - Returns ValidationResult with errors
    2. Model(**data) - Raises exception on validation failure
    
    Both approaches now properly validate nested models!
    """
    # Sample JSON data (imagine this coming from an API request)
    json_data = {
        "success": True,
        "data": [
            {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "active": True,
                "tags": ["admin", "user"],
                "metadata": {"department": "Engineering"}
            },
            {
                "id": 2,
                "name": "Jane Smith",
                "email": "jane@example.com",
                "active": True,
                "tags": ["user"],
                "metadata": {"department": "Sales"}
            }
        ],
        "total_count": 2,
        "page": 1,
        "page_size": 10
    }

    # Create validator from our model
    validator = APIResponse.validator()

    # Validate the JSON data
    result = validator.validate(json_data)

    if result.is_valid:
        print("✅ Validation successful!")
        print("\nAPI Response Details:")
        print(f"Total Users: {result.value['total_count']}")
        print(f"Page: {result.value['page']}")
        print(f"Page Size: {result.value['page_size']}")
        print("\nUsers:")
        for user in result.value['data']:
            print(f"\n- User ID: {user.id}")
            print(f"  Name: {user.name}")
            print(f"  Email: {user.email}")
            print(f"  Tags: {', '.join(user.tags)}")
            print(f"  Department: {user.metadata.get('department', 'N/A')}")
    else:
        print("❌ Validation failed!")
        for error in result.errors:
            print(f"Error in field '{error.field}': {error.message}")

    # Let's try with invalid data
    invalid_json = {
        "success": True,
        "data": [
            {
                "id": "not_an_integer",  # This should be an integer
                "name": "John Doe",
                "email": "john@example.com",
                "tags": "not_a_list"  # This should be a list
            }
        ],
        "total_count": 1,
        "page": 1,
        "page_size": 10
    }

    print("\nTesting invalid data:")
    result = validator.validate(invalid_json)
    
    if not result.is_valid:
        print("❌ Validation failed (as expected)!")
        for error in result.errors:
            print(f"Error in field '{error.field}': {error.message}")
    else:
        print("⚠️  WARNING: Validation passed when it should have failed!")
    
    # Test with completely malformed data
    print("\nTesting completely malformed data:")
    malformed_json = {
        "success": "not_a_bool",  # Should be bool
        "data": "not_a_list",  # Should be list
        "total_count": "not_an_int",  # Should be int
        "page": -1,  # Should be positive
        "page_size": 0  # Should be positive
    }
    
    result = validator.validate(malformed_json)
    if not result.is_valid:
        print("❌ Validation failed (as expected)!")
        for error in result.errors:
            print(f"Error in field '{error.field}': {error.message}")
    else:
        print("⚠️  WARNING: Validation passed when it should have failed!")

if __name__ == "__main__":
    main() 