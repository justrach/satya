# Satya LLM Integration Lessons and Best Practices

This document outlines best practices and lessons learned when integrating Satya with LLM APIs (e.g., OpenAI). The key themes include:

- Keep it simple
- Match external API structures exactly
- Handle errors gracefully
- Consider performance in async contexts
- Test thoroughly with real data
- Document clearly

---

## 1. Model Definition

- **Keep models simple** and match exactly with external API structures.
- **Remove unnecessary field descriptions and defaults** unless required.
- **Avoid custom methods** in models unless absolutely necessary.
- **Let Satya handle serialization/deserialization.**
- **Avoid nested validation** when possible.

### Example (Good):

```python
class Message(Model):
    role: str
    content: str
    refusal: Optional[str] = Field(required=False)
```

### Example (Not Recommended):

```python
class Message(Model):
    role: str = Field(
        description="Role of the message sender",
        examples=["system", "user", "assistant"]
    )
    content: str = Field(description="Content of the message")

    def dict(self):
        return {"role": self.role, "content": self.content}
```

---

## 2. Validation

- Use `validator()` for simple cases.
- For complex nested structures, **validate components separately**.
- **Handle validation errors gracefully** with fallbacks.
- **Avoid chaining multiple validations.**

### Example (Good):

```python
validator = OpenAIResponse.validator()
result = validator.validate(response_data)
if result.is_valid:
    response_obj = OpenAIResponse(result.value)
else:
    handle_error()
```

### Example (Not Recommended):

```python
validator = OpenAIResponse.validator()
result = validator.validate(response_data)
if result.is_valid:
    nested_validator = NestedModel.validator()
    nested_result = nested_validator.validate(result.value['nested'])
```

---

## 3. Error Handling

- **Always provide a fallback** for validation failures.
- Log validation errors in debug mode.
- **Return partial data** rather than failing completely.

### Example:

```python
try:
    result = validator.validate(data)
    if result.is_valid:
        return Model(result.value)
except Exception as e:
    if debug:
        print(f"Validation error: {e}")
    return fallback_response()
```

---

## 4. Performance

- **Avoid repeated validation** of the same data.
- **Cache validators** when possible.
- **Don't validate what you don't need.**
- For high throughput, **validate only critical fields.**

### Example:

```python
# Cache validator
_validator = None

def get_validator():
    global _validator
    if _validator is None:
        _validator = Model.validator()
    return _validator
```

---

## 5. Integration with External APIs

- **Match external API structures exactly.**
- Use **Optional fields** for varying responses.
- **Handle API versioning** in models.

### Example:

```python
class APIResponse(Model):
    id: str
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
    system_fingerprint: Optional[str] = Field(required=False)  # New in API v2
```

---

## 6. Common Pitfalls

- Over-validation slows performance.
- Complex nested validation often fails.
- Custom serialization methods are usually unnecessary.
- Validation inside async loops can block.

### Example (What **Not** to Do):

```python
class ComplexModel(Model):
    field1: SubModel1
    field2: SubModel2

    def validate_all(self):
        self.field1.validate()
        self.field2.validate()
        self.cross_validate()
```

---

## 7. Async Usage

- **Don't block on validation** in async code.
- Use **batch validation** for multiple items.
- **Keep validation simple** in high-concurrency scenarios.

### Example:

```python
async def process_batch(items):
    validator = Model.validator()
    results = []
    for item in items:
        result = validator.validate(item)
        if result.is_valid:
            results.append(Model(result.value))
    return results
```

---

## 8. Testing

- **Test with real API responses.**
- **Include error cases.**
- **Verify fallback behavior.**

### Example:

```python
def test_validation():
    validator = Model.validator()
    
    # Test valid case
    result = validator.validate(valid_data)
    assert result.is_valid
    
    # Test invalid case
    result = validator.validate(invalid_data)
    assert not result.is_valid
    assert "error_field" in result.errors
```

---

## 9. Documentation

- **Document required vs optional fields.**
- **Explain validation behavior.**
- **Include examples** of valid structures.

### Example:

```markdown
Model for API responses

Required fields:
- id: str
- created: int
- choices: List[Choice]

Optional fields:
- system_fingerprint: str (added in API v2)

Example valid structure:
{
    "id": "abc123",
    "created": 1234567890,
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello!"
            }
        }
    ]
}
```

---

## 10. Version Compatibility

- **Handle different API versions gracefully.**
- Use **Optional fields** for version differences.
- **Document version requirements.**

### Example:

```python
class ResponseV2(Model):
    # Fields from v1
    id: str
    created: int
    # New in v2
    system_fingerprint: Optional[str] = Field(required=False)

    @classmethod
    def from_v1(cls, v1_data):
        return cls(
            id=v1_data["id"],
            created=v1_data["created"],
            system_fingerprint=None
        )
```

---

Following these guidelines will help create robust, maintainable LLM integrations with Satya.

Happy coding!
