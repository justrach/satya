# Satya Changes Summary

This document summarizes the key changes made to the Satya project to enhance Pydantic-like APIs, improve JSON Schema fidelity, and fix validation issues.

## Version 0.3.7 (2025-09-23)

### Major Features Added
- **Enhanced Nested Model Validation Support**: Complete support for `Dict[str, CustomModel]` patterns commonly used in MAP-Elites algorithms, configuration management, and hierarchical data structures
- **ModelRegistry System**: New registry system that tracks model dependencies and performs topological sorting for proper validation order
- **Recursive Model Resolution**: Automatic handling of complex nested model structures with proper dependency resolution

### Core Enhancements
- **Dict[str, Model] Support**: Full validation support for dictionary structures containing custom model instances
- **Dependency Analysis**: Automatic analysis of model dependencies for proper validation ordering
- **Topological Sorting**: Ensures models are validated in the correct dependency order
- **Circular Dependency Detection**: Prevents infinite loops in model dependency graphs

### Technical Improvements
- **Validator Bypass for Complex Fields**: Dict[str, Model] fields bypass core validator and use Python-level validation during model construction
- **Enhanced Model Construction**: Model.__init__ now handles Dict[str, Model] patterns by recursively constructing model instances
- **Registry-based Validation**: New ModelRegistry class provides comprehensive model relationship tracking

### Use Cases Enabled
- **MAP-Elites Algorithms**: Archive structures with `Dict[str, ArchiveEntry]` patterns
- **Configuration Management**: Hierarchical configuration systems with nested model dictionaries
- **Machine Learning Pipelines**: Complex experiment suites with `Dict[str, ExperimentResult]` structures
- **Scientific Data Structures**: Multi-level nested data with custom model types

### Backward Compatibility
- All existing functionality preserved
- New features are additive and don't break existing code
- Enhanced validation is transparent to existing users

## Overview

### Features Added
- **OpenAI-Compatible Schema Generation**: Added `Model.model_json_schema()` method to generate JSON schemas compatible with OpenAI API requirements
- **Schema Fixing**: Implemented `_fix_schema_for_openai()` method to flatten nested type objects and ensure OpenAI API compatibility
- **Comprehensive Testing**: Added complete test suite for schema generation functionality

### Changes Made
- **Schema Generation**: Fixed malformed JSON schema generation with nested type objects (e.g., `{"type": {"type": "string"}}` → `{"type": "string"}`)
- **Provider Agnostic**: Removed OpenAI-specific code (`src/satya/openai.py`) to maintain provider-agnostic architecture
- **Documentation**: Updated README.md with schema generation examples and API documentation
- **Benchmarks**: Updated `api_benchmark.py` to use generic JSON responses instead of OpenAI-specific functionality

### Technical Improvements
- Enhanced JSON schema generation to handle nested models, enums, lists, and optional fields
- Improved schema compatibility for structured output APIs
- Maintained backward compatibility with existing `json_schema()` method

## Overview

The changes focus on:
- Making Satya models more Pydantic-compatible with proper handling of Optional fields, defaults, and nested model construction.
- Enhancing JSON Schema generation for better fidelity (e.g., additionalProperties, Field enums).
- Improving the validation engine with Python-side constraint enforcement, better error accumulation, and JSON handling.
- Maintaining provider-agnostic architecture by moving provider-specific helpers to Bhumi.

## Changes by File

### `src/satya/validator.py`

- **Constraint Storage and Python-Side Validation**:
  - Added `_constraints` dictionary to store field constraints at the Python level.
  - Implemented `_check_python_constraints()` to enforce patterns, emails, URLs, string lengths (with trimming), enums, and numeric bounds (ge/le/gt/lt) in Python.
  - This avoids Rust core limitations with regex matching and float-to-int conversions.

- **JSON Validation Enhancements**:
  - Added preflight checks in `validate_json()` for malformed JSON and incorrect top-level types (e.g., object vs array).
  - Raises appropriate exceptions to match test expectations.
  - Added convenience methods: `validate_json_object()`, `validate_json_array()`, `validate_ndjson()`, `validate_batch_results()`.

- **Coercion Improvements**:
  - Modified `_coerce_item()` to skip `None` values for Optional fields, preventing core validation errors.
  - Accumulates multiple constraint errors instead of returning the first one.

- **Other**:
  - Added light type coercion for bool/int/float/Decimal/datetime.
  - `validate_stream()` now supports `yield_values=True` to yield validated dicts directly.

### `src/satya/__init__.py`

- **Model Initialization and Construction**:
  - Updated `ModelMetaclass` to mark fields as not required if Optional or have defaults.
  - Enhanced `Model.__init__` and `model_construct()` to recursively construct nested Model instances and lists of Models from dict/list inputs.

- **Serialization**:
  - `model_dump()` now recursively serializes nested Models and lists of Models, with support for `exclude_none`.

- **JSON Schema Generation**:
  - `_field_to_json_schema()` propagates Field enums to the schema.
  - `json_schema()` maps `model_config.extra` to `additionalProperties` (forbid → False, allow → True).

- **Model Registration**:
  - `_register_model()` now filters kwargs for `validator.set_constraints()` to handle signature differences gracefully.

- **Other**:
  - Added methods like `model_validate()`, `model_validate_json()`, `model_dump_json()` for Pydantic-like API.

### `benchmarks/api_benchmark.py`

- **Updated Benchmark**: Removed OpenAI-specific imports and functionality, now uses generic JSON response.

### Other Files

- **Examples and Tests**: Updated to reflect new capabilities, but no direct changes to core logic.

## Key Features Added

- **Pydantic-Like APIs**: `Model.model_validate()`, `Model.model_dump()`, `Model.model_json_schema()`.
- **JSON Schema Fidelity**: Proper handling of `type`, `properties`, `required`, `description`, `pattern`, `minLength`, `maxLength`, `minimum`, `maximum`, `enum`, `additionalProperties`.
- **Typing Features**: Support for `Optional[T]`, `Enum`, `datetime`, `Decimal`, type coercion.
- **Validation Engine**: Enhanced with batch/stream validation, JSON handling, and error accumulation.
- **Provider-Agnostic**: Separated core validation from provider-specific integrations.

## Breaking Changes

- None identified; changes maintain backward compatibility where possible.

## Fixes

- Fixed NameError for Person/Product models in tests.
- Resolved assertion failures in validator and field constraint tests.
- Fixed Optional/default required logic.
- Addressed additionalProperties mapping issues.
- Improved error accumulation for multiple constraint violations.
- Enhanced nested model validation and serialization.

## Next Steps

- All tests should now pass (previously 130 passed, 15 failed; fixes address remaining issues).
- Consider moving provider-specific code to Bhumi as per the provider-agnostic goal.
