from satya import Model, Field, ModelValidationError

class User(Model):
    id: int = Field(description="User ID")
    name: str = Field(description="User name")
    email: str = Field(description="Email address")
    active: bool = Field(default=True)

# Enable batching for optimal performance
validator = User.validator()
validator.set_batch_size(1000)  # Recommended for most workloads

# Process data efficiently
for valid_item in validator.validate_stream(data):
    process(valid_item)