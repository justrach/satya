"""
Scalar validators for high-performance validation of primitive types.

These validators provide Rust-backed validation for strings, numbers, and booleans,
enabling fast validation for non-object schemas.

These are thin wrappers around the existing StreamValidatorCore, creating single-field
schemas and delegating to Rust for maximum performance.
"""

from typing import Any, Optional, List
from dataclasses import dataclass


class StringValidator:
    """
    High-performance string validator with Rust-backed validation.
    
    Uses the existing StreamValidatorCore by creating a single-field schema
    and delegating to Rust for maximum performance.
    
    Example:
        >>> validator = StringValidator(min_length=5, max_length=100, pattern=r'^[a-z]+$')
        >>> result = validator.validate("hello")
        >>> assert result.is_valid
    """
    
    def __init__(
        self,
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        email: bool = False,
        url: bool = False,
        enum: Optional[List[str]] = None,
    ):
        # Import here to avoid circular dependencies
        from .validator import StreamValidator
        
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self.email = email
        self.url = url
        self.enum = enum
        
        # Create a StreamValidator with a single "value" field
        self._validator = StreamValidator()
        self._validator.add_field("value", "string", required=True)
        self._validator.set_constraints(
            "value",
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            email=email,
            url=url,
            enum_values=enum,
        )
    
    def validate(self, value: Any) -> "ValidationResult":
        """Validate a string value using Rust core"""
        # Wrap value in dict for validator
        data = {"value": value}
        
        # Use Rust-backed validation
        result = self._validator.validate(data)
        
        # Return with simplified interface
        from . import ValidationResult as VR, ValidationError as VE
        if result.is_valid:
            return VR(value=value, errors=[])
        else:
            # Unwrap errors to remove "value" prefix
            errors = [VE(field="value", message=e.message, path=["value"]) for e in result.errors]
            return VR(value=None, errors=errors)
    
    def validate_batch(self, values: List[Any]) -> List["ValidationResult"]:
        """Validate multiple string values using Rust batch validation"""
        # Wrap each value in dict
        items = [{"value": v} for v in values]
        
        # Use Rust batch validation
        batch_results = self._validator.validate_batch(items)
        
        # Convert to ValidationResult list
        from . import ValidationResult as VR, ValidationError as VE
        results = []
        for i, is_valid in enumerate(batch_results):
            if is_valid:
                results.append(VR(value=values[i], errors=[]))
            else:
                # Get detailed errors via single validation
                detailed = self.validate(values[i])
                results.append(detailed)
        
        return results


class IntValidator:
    """
    High-performance integer validator with Rust-backed validation.
    
    Uses the existing StreamValidatorCore for maximum performance.
    
    Example:
        >>> validator = IntValidator(ge=0, le=100)
        >>> result = validator.validate(42)
        >>> assert result.is_valid
    """
    
    def __init__(
        self,
        *,
        ge: Optional[int] = None,  # greater than or equal
        le: Optional[int] = None,  # less than or equal
        gt: Optional[int] = None,  # greater than
        lt: Optional[int] = None,  # less than
        multiple_of: Optional[int] = None,
        enum: Optional[List[int]] = None,
    ):
        from .validator import StreamValidator
        
        self.ge = ge
        self.le = le
        self.gt = gt
        self.lt = lt
        self.multiple_of = multiple_of
        self.enum = enum
        
        # Create StreamValidator with single integer field
        self._validator = StreamValidator()
        self._validator.add_field("value", "integer", required=True)
        self._validator.set_constraints(
            "value",
            ge=ge,
            le=le,
            gt=gt,
            lt=lt,
            enum_values=[str(v) for v in enum] if enum else None,  # Convert to strings for enum
        )
        # Note: multiple_of not in StreamValidator constraints, handle in Python
    
    def validate(self, value: Any) -> "ValidationResult":
        """Validate an integer value using Rust core"""
        from . import ValidationResult as VR, ValidationError as VE
        
        # Type check first (exclude bool)
        if not isinstance(value, int) or isinstance(value, bool):
            return VR(
                value=None,
                errors=[VE(field="value", message=f"Expected integer, got {type(value).__name__}", path=["value"])]
            )
        
        # Rust validation
        data = {"value": value}
        result = self._validator.validate(data)
        
        # Additional Python validation for multiple_of (not in Rust core)
        errors = []
        if not result.is_valid:
            errors = [VE(field="value", message=e.message, path=["value"]) for e in result.errors]
        
        if self.multiple_of is not None and value % self.multiple_of != 0:
            errors.append(VE(
                field="value",
                message=f"Value must be a multiple of {self.multiple_of}",
                path=["value"]
            ))
        
        return VR(
            value=value if len(errors) == 0 else None,
            errors=errors
        )
    
    def validate_batch(self, values: List[Any]) -> List["ValidationResult"]:
        """Validate multiple integer values"""
        return [self.validate(v) for v in values]


class NumberValidator:
    """
    High-performance number (float/int) validator with Rust-backed validation.
    
    Uses the existing StreamValidatorCore for maximum performance.
    
    Example:
        >>> validator = NumberValidator(ge=0.0, le=100.0)
        >>> result = validator.validate(42.5)
        >>> assert result.is_valid
    """
    
    def __init__(
        self,
        *,
        ge: Optional[float] = None,  # greater than or equal
        le: Optional[float] = None,  # less than or equal
        gt: Optional[float] = None,  # greater than
        lt: Optional[float] = None,  # less than
        multiple_of: Optional[float] = None,
        enum: Optional[List[float]] = None,
    ):
        from .validator import StreamValidator
        
        self.ge = ge
        self.le = le
        self.gt = gt
        self.lt = lt
        self.multiple_of = multiple_of
        self.enum = enum
        
        # Create StreamValidator with single number field
        self._validator = StreamValidator()
        self._validator.add_field("value", "number", required=True)
        self._validator.set_constraints(
            "value",
            min_value=ge,
            max_value=le,
            # Note: gt/lt not directly supported, handle in Python
            enum_values=[str(v) for v in enum] if enum else None,
        )
    
    def validate(self, value: Any) -> "ValidationResult":
        """Validate a number value using Rust core"""
        from . import ValidationResult as VR, ValidationError as VE
        
        # Type check (accept int and float, exclude bool)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return VR(
                value=None,
                errors=[VE(field="value", message=f"Expected number, got {type(value).__name__}", path=["value"])]
            )
        
        # Rust validation (covers ge/le)
        data = {"value": value}
        result = self._validator.validate(data)
        
        # Additional Python validation for constraints not in Rust core
        errors = []
        if not result.is_valid:
            errors = [VE(field="value", message=e.message, path=["value"]) for e in result.errors]
        
        num_value = float(value)
        
        # gt/lt validation (not in Rust core for floats)
        if self.gt is not None and num_value <= self.gt:
            errors.append(VE(
                field="value",
                message=f"Value must be > {self.gt}",
                path=["value"]
            ))
        
        if self.lt is not None and num_value >= self.lt:
            errors.append(VE(
                field="value",
                message=f"Value must be < {self.lt}",
                path=["value"]
            ))
        
        # Multiple of validation
        if self.multiple_of is not None:
            remainder = abs(num_value % self.multiple_of)
            epsilon = 1e-10
            if remainder > epsilon and remainder < (self.multiple_of - epsilon):
                errors.append(VE(
                    field="value",
                    message=f"Value must be a multiple of {self.multiple_of}",
                    path=["value"]
                ))
        
        return VR(
            value=value if len(errors) == 0 else None,
            errors=errors
        )
    
    def validate_batch(self, values: List[Any]) -> List["ValidationResult"]:
        """Validate multiple number values"""
        return [self.validate(v) for v in values]


class BooleanValidator:
    """
    High-performance boolean validator with Rust-backed validation.
    
    Uses the existing StreamValidatorCore for maximum performance.
    
    Example:
        >>> validator = BooleanValidator()
        >>> result = validator.validate(True)
        >>> assert result.is_valid
    """
    
    def __init__(self, *, enum: Optional[List[bool]] = None):
        from .validator import StreamValidator
        
        self.enum = enum
        
        # Create StreamValidator with single boolean field
        self._validator = StreamValidator()
        self._validator.add_field("value", "boolean", required=True)
        if enum:
            self._validator.set_constraints(
                "value",
                enum_values=[str(v).lower() for v in enum],  # Convert to 'true'/'false'
            )
    
    def validate(self, value: Any) -> "ValidationResult":
        """Validate a boolean value using Rust core"""
        from . import ValidationResult as VR, ValidationError as VE
        
        # Type check
        if not isinstance(value, bool):
            return VR(
                value=None,
                errors=[VE(field="value", message=f"Expected boolean, got {type(value).__name__}", path=["value"])]
            )
        
        # Rust validation
        data = {"value": value}
        result = self._validator.validate(data)
        
        if result.is_valid:
            return VR(value=value, errors=[])
        else:
            errors = [VE(field="value", message=e.message, path=["value"]) for e in result.errors]
            return VR(value=None, errors=errors)
    
    def validate_batch(self, values: List[Any]) -> List["ValidationResult"]:
        """Validate multiple boolean values using Rust batch validation"""
        items = [{"value": v} for v in values]
        batch_results = self._validator.validate_batch(items)
        
        from . import ValidationResult as VR, ValidationError as VE
        results = []
        for i, is_valid in enumerate(batch_results):
            if isinstance(values[i], bool) and is_valid:
                results.append(VR(value=values[i], errors=[]))
            else:
                detailed = self.validate(values[i])
                results.append(detailed)
        
        return results
