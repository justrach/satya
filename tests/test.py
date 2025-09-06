import os
import sys

# Add src to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from satya import StreamValidator

# Create a validator
validator = StreamValidator()

# Add some fields to validate
validator.add_field("name", str, required=True)
validator.add_field("age", int, required=True)
validator.add_field("email", str, required=False)

# Test data
valid_data = {
    "name": "John Doe",
    "age": 30,
    "email": "john@example.com"
}

invalid_data = {
    "name": "Jane Doe",
    "email": "jane@example.com"
    # missing required age field
}

# Validate
result1 = validator.validate(valid_data)
result2 = validator.validate(invalid_data)

print("Valid data result:", result1)
print("Invalid data result:", result2)

# Test stream validation
data_stream = [valid_data, invalid_data, valid_data]
print("\nStream validation results:")
for result in validator.validate_stream(data_stream, collect_errors=True):
    print(result) 