"""
JSON Schema compiler for Satya.

Compiles JSON Schema documents into Satya validators for maximum performance.
This enables direct integration with tools like Poetry that use JSON Schema.
"""

from typing import Any, Dict, Optional, Union, List
from .scalar_validators import StringValidator, IntValidator, NumberValidator, BooleanValidator
from .array_validator import ArrayValidator


class JSONSchemaCompiler:
    """
    Compiles JSON Schema documents into Satya validators.
    
    This enables fastjsonschema-like performance with a simple API:
    
    Example:
        >>> schema = {"type": "string", "minLength": 3, "maxLength": 100}
        >>> validator = compile_json_schema(schema)
        >>> result = validator.validate("hello")
        >>> assert result.is_valid
    """
    
    def __init__(self):
        self.optimization_stats = {
            "rust_optimized": 0,
            "python_fallback": 0,
        }
    
    def compile(self, schema: Dict[str, Any]) -> Union[
        StringValidator,
        IntValidator,
        NumberValidator,
        BooleanValidator,
        ArrayValidator,
    ]:
        """
        Compile a JSON Schema into a Satya validator.
        
        Args:
            schema: JSON Schema document (dict)
        
        Returns:
            Appropriate Satya validator
        
        Raises:
            ValueError: If schema is invalid or unsupported
        """
        if not isinstance(schema, dict):
            raise ValueError(f"Schema must be a dict, got {type(schema).__name__}")
        
        schema_type = schema.get("type")
        
        if schema_type == "string":
            return self._compile_string(schema)
        elif schema_type == "integer":
            return self._compile_integer(schema)
        elif schema_type == "number":
            return self._compile_number(schema)
        elif schema_type == "boolean":
            return self._compile_boolean(schema)
        elif schema_type == "array":
            return self._compile_array(schema)
        elif schema_type == "object":
            # Object schemas require Model definition - not yet implemented
            raise NotImplementedError(
                "Object schemas not yet supported. Use Model class for objects."
            )
        else:
            raise ValueError(f"Unsupported schema type: {schema_type}")
    
    def _compile_string(self, schema: Dict[str, Any]) -> StringValidator:
        """Compile a string schema"""
        self.optimization_stats["rust_optimized"] += 1
        
        return StringValidator(
            min_length=schema.get("minLength"),
            max_length=schema.get("maxLength"),
            pattern=schema.get("pattern"),
            email=schema.get("format") == "email",
            url=schema.get("format") in ["uri", "url"],
            enum=schema.get("enum"),
        )
    
    def _compile_integer(self, schema: Dict[str, Any]) -> IntValidator:
        """Compile an integer schema"""
        self.optimization_stats["rust_optimized"] += 1
        
        return IntValidator(
            ge=schema.get("minimum"),
            le=schema.get("maximum"),
            gt=schema.get("exclusiveMinimum"),
            lt=schema.get("exclusiveMaximum"),
            multiple_of=schema.get("multipleOf"),
            enum=schema.get("enum"),
        )
    
    def _compile_number(self, schema: Dict[str, Any]) -> NumberValidator:
        """Compile a number schema"""
        self.optimization_stats["rust_optimized"] += 1
        
        return NumberValidator(
            ge=schema.get("minimum"),
            le=schema.get("maximum"),
            gt=schema.get("exclusiveMinimum"),
            lt=schema.get("exclusiveMaximum"),
            multiple_of=schema.get("multipleOf"),
            enum=schema.get("enum"),
        )
    
    def _compile_boolean(self, schema: Dict[str, Any]) -> BooleanValidator:
        """Compile a boolean schema"""
        self.optimization_stats["rust_optimized"] += 1
        
        return BooleanValidator(
            enum=schema.get("enum"),
        )
    
    def _compile_array(self, schema: Dict[str, Any]) -> ArrayValidator:
        """Compile an array schema"""
        self.optimization_stats["rust_optimized"] += 1
        
        # Get item schema type
        items_schema = schema.get("items", {})
        item_type = items_schema.get("type", "string") if isinstance(items_schema, dict) else "string"
        
        return ArrayValidator(
            item_type=item_type,
            min_items=schema.get("minItems"),
            max_items=schema.get("maxItems"),
            unique_items=schema.get("uniqueItems", False),
        )
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """
        Get a report of how many schemas were optimized.
        
        Returns:
            Dict with optimization statistics
        """
        total = self.optimization_stats["rust_optimized"] + self.optimization_stats["python_fallback"]
        if total == 0:
            return {
                "total_schemas": 0,
                "rust_optimized": 0,
                "python_fallback": 0,
                "optimization_percentage": 0.0,
            }
        
        return {
            "total_schemas": total,
            "rust_optimized": self.optimization_stats["rust_optimized"],
            "python_fallback": self.optimization_stats["python_fallback"],
            "optimization_percentage": (self.optimization_stats["rust_optimized"] / total) * 100,
        }


def compile_json_schema(schema: Dict[str, Any]) -> Union[
    StringValidator,
    IntValidator,
    NumberValidator,
    BooleanValidator,
    ArrayValidator,
]:
    """
    Compile a JSON Schema into a Satya validator.
    
    This is the main entry point for JSON Schema compilation.
    
    Args:
        schema: JSON Schema document (dict)
    
    Returns:
        Appropriate Satya validator with Rust-backed performance
    
    Example:
        >>> schema = {
        ...     "type": "string",
        ...     "minLength": 3,
        ...     "maxLength": 100,
        ...     "pattern": "^[a-z]+$"
        ... }
        >>> validator = compile_json_schema(schema)
        >>> result = validator.validate("hello")
        >>> print(result.is_valid)  # True
        
        >>> # Integer schema
        >>> schema = {"type": "integer", "minimum": 0, "maximum": 100}
        >>> validator = compile_json_schema(schema)
        >>> result = validator.validate(42)
        >>> print(result.is_valid)  # True
        
        >>> # Array schema
        >>> schema = {"type": "array", "items": {"type": "string"}, "minItems": 1}
        >>> validator = compile_json_schema(schema)
        >>> result = validator.validate(["hello", "world"])
        >>> print(result.is_valid)  # True
    """
    compiler = JSONSchemaCompiler()
    return compiler.compile(schema)


__all__ = ['JSONSchemaCompiler', 'compile_json_schema']
