from satya import StreamValidator, Model, Field
from typing import List, Dict, Optional, Union, Literal, Any
from datetime import datetime
from enum import Enum
from uuid import UUID
import json

class PublicationStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class GeoLocation(Model):
    latitude: float = Field(
        min_value=-90.0,
        max_value=90.0,
        description="Latitude coordinate"
    )
    longitude: float = Field(
        min_value=-180.0,
        max_value=180.0,
        description="Longitude coordinate"
    )

class Address(Model):
    street: str = Field(
        min_length=5, 
        max_length=100,
        description="Street address"
    )
    city: str = Field(
        pattern=r'^[A-Za-z\s]+$',
        description="City name (letters only)"
    )
    postal_code: str = Field(
        pattern=r'^\d{5}(-\d{4})?$',
        description="US postal code format"
    )
    country: str = Field(
        min_length=2,
        max_length=2,
        description="Two-letter country code"
    )
    location: Optional[GeoLocation] = Field(
        required=False,
        description="Geographic coordinates"
    )

class SocialMedia(Model):
    platform: Literal["twitter", "facebook", "linkedin", "github"] = Field(
        description="Social media platform"
    )
    username: str = Field(
        pattern=r'^@?[a-zA-Z0-9_]+$',
        description="Social media handle"
    )
    url: str = Field(
        url=True,
        description="Profile URL"
    )

class User(Model):
    id: UUID = Field(
        pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        description="User UUID v4"
    )
    username: str = Field(
        min_length=3,
        max_length=20,
        pattern=r'^[a-zA-Z0-9_]+$',
        description="Username (alphanumeric and underscore)"
    )
    email: str = Field(
        email=True,
        description="Valid email address"
    )
    status: PublicationStatus = Field(
        description="User account status"
    )
    age: int = Field(
        min_value=13,
        max_value=120,
        description="User age (13-120)"
    )
    score: float = Field(
        min_value=0.0,
        max_value=100.0,
        description="User score (0-100)"
    )
    address: Address = Field(
        description="User's address"
    )
    social_profiles: List[SocialMedia] = Field(
        min_length=0,
        max_length=5,
        description="Social media profiles"
    )
    interests: List[str] = Field(
        min_length=1,
        max_length=5,
        description="List of interests (1-5 items)"
    )
    metadata: Dict[str, Any] = Field(
        description="Additional user metadata"
    )
    last_login: Optional[datetime] = Field(
        required=False,
        description="Last login timestamp"
    )

def main():
    # Print the JSON Schema
    print("\nJSON Schema for User model:")
    schema = User.json_schema()
    print(json.dumps(schema, indent=2))

    # Valid user data
    valid_user = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "username": "john_doe",
        "email": "john@example.com",
        "status": "published",
        "age": 25,
        "score": 85.5,
        "address": {
            "street": "123 Main Street",
            "city": "New York",
            "postal_code": "10001",
            "country": "US",
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        },
        "social_profiles": [
            {
                "platform": "twitter",
                "username": "@johndoe",
                "url": "https://twitter.com/johndoe"
            },
            {
                "platform": "github",
                "username": "johndoe",
                "url": "https://github.com/johndoe"
            }
        ],
        "interests": ["coding", "music", "sports"],
        "metadata": {
            "language": "en",
            "theme": "dark"
        },
        "last_login": "2024-01-01T12:00:00Z"
    }

    # Create validator
    validator = User.validator()

    # Validate and print results
    result = validator.validate(valid_user)
    if result.is_valid:
        print("\n✅ Valid user data passed all validations!")
    else:
        print("\n❌ Validation failed!")
        for error in result.errors:
            print(f"Error in {error.field}: {error.message}")

if __name__ == "__main__":
    main() 