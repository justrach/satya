from satya import Model, Field, List, Dict
from typing import Optional
import json
from datetime import datetime

def print_json(data):
    """Helper to print JSON data nicely"""
    print(json.dumps(data, indent=2))

def process_person(person: 'Person'):
    """Example function to process a validated person"""
    print(f"Processing person: {person.name}, age {person.age}")

def log_errors(errors):
    """Example function to log validation errors"""
    for error in errors:
        print(f"Validation error: {error}")

def generate_data():
    """Generator that simulates streaming data with delays"""
    print("Starting stream...")
    for i in range(5):
        data = {
            "name": f"Person_{i}",
            "age": 20 + i,
            "active": i % 2 == 0,
            "address": {
                "street": f"{i} Main St",
                "city": "Test City",
                "country": "Test Country",
                "location": {
                    "latitude": 40.0 + i,
                    "longitude": -70.0 + i
                }
            },
            "contacts": [f"contact_{i}@example.com"],
            "metadata": {"id": str(i)},
            "favorite_locations": []
        }
        print(f"Generating item {i}: {data}")
        yield data

class Location(Model):
    """Represents a geographical location"""
    latitude: float = Field(description="Latitude in degrees")
    longitude: float = Field(description="Longitude in degrees")
    name: Optional[str] = Field(
        required=False,
        description="Optional location name",
        examples=["Downtown SF", "Central Park"]
    )

class Address(Model):
    """Physical address with location"""
    street: str
    city: str
    country: str
    location: Location

class Contact(Model):
    """Contact information"""
    type: str = Field(examples=["email", "phone"])
    value: str

class Person(Model):
    """Person with address and contact information"""
    name: str
    age: int = Field(examples=[25, 30, 35])
    address: Address
    contacts: List[str]
    metadata: Dict[str, str] = Field(
        description="Additional metadata",
        examples=[{"joined": "2023-01-01", "status": "active"}]
    )
    favorite_locations: List[Location]

class User(Model):
    id: int
    name: str = Field(default='John Doe')
    signup_ts: Optional[datetime] = Field(required=False)
    friends: list[int] = Field(default_factory=list)

# Test validation
if __name__ == "__main__":
    # Create validator from model
    validator = Person.validator()

    # Example valid data
    valid_data = {
        "user": {
            "name": "John Doe",
            "age": 30,
            "address": {
                "street": "123 Main St",
                "city": "San Francisco",
                "country": "USA",
                "location": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "name": "Downtown SF"  # Optional field
                }
            },
            "contacts": [
                "+1-555-555-5555",
                "john@example.com"
            ],
            "metadata": {
                "joined": "2023-01-01",
                "status": "active"
            },
            "favorite_locations": [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "name": "New York"
                },
                {
                    "latitude": 51.5074,
                    "longitude": -0.1278
                    # name is optional, so we can skip it
                }
            ]
        },
        "contacts": [
            {
                "type": "email",
                "value": "john@example.com"
            },
            {
                "type": "phone",
                "value": "+1-555-555-5555"
            }
        ],
        "tags": {
            "department": "engineering",
            "role": "senior"
        }
    }

    # Example invalid data (with type errors)
    invalid_data = {
        "user": {
            "name": "Jane Doe",
            "age": "thirty",  # Should be int
            "address": {
                "street": "456 Oak St",
                "city": "London",
                "country": "UK",
                "location": {
                    "latitude": "invalid",  # Should be float
                    "longitude": -0.1278
                }
            },
            "contacts": "single_contact",  # Should be a list
            "metadata": {
                "joined": "2023-01-01"
            },
            "favorite_locations": [
                {
                    "latitude": 48.8566,
                    "longitude": "invalid"  # Should be float
                }
            ]
        },
        "contacts": [
            {
                "type": "email",
                # Missing required 'value' field
            }
        ],
        "tags": "invalid"  # Should be a dict
    }

    # Validate single item
    result = validator.validate(valid_data)
    if result.is_valid:
        person = Person(**result.value)
        print(f"Valid person: {person.name}, age {person.age}")
    else:
        print("Validation errors:", result.errors)

    # Stream validation
    print("\nProcessing stream:")
    for result in validator.validate_stream(generate_data(), collect_errors=True):
        if result.is_valid:
            person = Person(**result.value)
            process_person(person)
        else:
            log_errors(result.errors)

    # Get JSON Schema
    schema = Person.schema()
    print("\nJSON Schema:")
    print_json(schema)

    # Get type information
    location_info = validator.get_type_info("Location")
    if location_info:
        print("\nLocation type info:")
        print(f"Documentation: {location_info['doc']}")
        print("Fields:", location_info['fields'])

    # Test streaming with multiple items
    print("\nTesting stream of multiple items:")
    stream_data = [valid_data, invalid_data, valid_data]
    valid_count = 0
    for _ in validator.validate_stream(stream_data):
        valid_count += 1
    print(f"Valid items in stream: {valid_count} out of {len(stream_data)}")

    external_data = {'id': '123', 'signup_ts': '2017-06-01 12:22', 'friends': [1, '2', b'3']}
    user = User.parse(external_data)
    print(user)
    print(user.id) 