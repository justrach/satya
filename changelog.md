# Changelog

## [0.2.3] - 2024-01-15

### Added
- Enhanced field validation rules in Satya
  - Numeric constraints:
    - `ge` (greater than or equal)
    - `le` (less than or equal)
    - `gt` (greater than)
    - `lt` (less than)
  - Array constraints:
    - `min_items`
    - `max_items`
    - `unique_items`
  - String validation:
    - `email` format
    - `url` format
    - `pattern` (regex)
  - Enum validation
  - Documentation:
    - `description`
    - `example`

### Example Usage
<?python
from satya import Model, Field

class UserProfile(Model):
    user_id: str = Field(pattern=r"^usr_[a-zA-Z0-9]+$", description="Unique user ID")
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(email=True)
    age: int = Field(ge=13, le=120)
    tags: List[str] = Field(min_items=1, max_items=10, unique_items=True)
    subscription: str = Field(enum=["free", "basic", "premium"])
?>

### Changed
- Removed FieldConfig class in favor of direct Field attributes
- Updated JSON schema generation to support new validation rules
- Added regex dependency for pattern matching
- Improved error messages for validation failures

### Dependencies
- Added regex = "1.9.1" to Cargo.toml
- Updated pyo3 features to include "macros"

### Technical Details
- Field validation is now handled in Rust for better performance
- JSON schema generation properly includes all validation rules
- OpenAI schema adapter for LLM integrations 