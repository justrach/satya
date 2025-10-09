"""
Validation Decorators - Pydantic-compatible validation system
=============================================================

This module implements @field_validator and @model_validator decorators
to provide custom validation logic, matching Pydantic's API.

Features:
- @field_validator with 'before', 'after', 'plain', 'wrap' modes
- @model_validator with 'before', 'after' modes
- ValidationInfo context object
- Full Pydantic compatibility
"""

from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, get_type_hints
from dataclasses import dataclass
from functools import wraps
import inspect

T = TypeVar('T')


@dataclass
class ValidationInfo:
    """
    Context information available to validators.
    
    Attributes:
        field_name: Name of the field being validated
        data: Dictionary of all field values
        config: Model configuration
        context: Optional validation context
    """
    field_name: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


class ValidatorMetadata:
    """Metadata for storing validator information (not a descriptor)"""
    
    def __init__(
        self,
        func: Callable,
        field_names: List[str],
        mode: str = 'after',
        check_fields: bool = True
    ):
        self.func = func
        self.field_names = field_names
        self.mode = mode
        self.check_fields = check_fields
        self.is_field_validator = True


class ModelValidatorMetadata:
    """Metadata for storing model validator information (not a descriptor)"""
    
    def __init__(self, func: Callable, mode: str = 'after'):
        self.func = func
        self.mode = mode
        self.is_model_validator = True


def field_validator(
    *fields: str,
    mode: str = 'after',
    check_fields: bool = True
) -> Callable:
    """
    Decorator for field-level validation.
    
    Args:
        *fields: Field names to validate
        mode: Validation mode - 'before', 'after', 'plain', or 'wrap'
        check_fields: Whether to check if fields exist
        
    Returns:
        Decorated validator function
        
    Example:
        >>> class User(Model):
        ...     name: str
        ...     age: int
        ...     
        ...     @field_validator('name')
        ...     def validate_name(cls, v, info):
        ...         if not v.strip():
        ...             raise ValueError('Name cannot be empty')
        ...         return v.title()
    """
    if mode not in ('before', 'after', 'plain', 'wrap'):
        raise ValueError(f"mode must be 'before', 'after', 'plain', or 'wrap', got {mode!r}")
    
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function itself
        metadata = ValidatorMetadata(
            func=func,
            field_names=list(fields),
            mode=mode,
            check_fields=check_fields
        )
        func.__validator_metadata__ = metadata
        return func
    
    return decorator


def model_validator(mode: str = 'after') -> Callable:
    """
    Decorator for model-level validation.
    
    Args:
        mode: Validation mode - 'before' or 'after'
        
    Returns:
        Decorated validator function
        
    Example:
        >>> class UserRegistration(Model):
        ...     password: str
        ...     password_confirm: str
        ...     
        ...     @model_validator(mode='after')
        ...     def check_passwords_match(self):
        ...         if self.password != self.password_confirm:
        ...             raise ValueError('Passwords do not match')
        ...         return self
    """
    if mode not in ('before', 'after'):
        raise ValueError(f"mode must be 'before' or 'after', got {mode!r}")
    
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function itself
        metadata = ModelValidatorMetadata(func=func, mode=mode)
        func.__model_validator_metadata__ = metadata
        return func
    
    return decorator


def run_field_validators(
    cls: type,
    field_name: str,
    value: Any,
    values: Dict[str, Any],
    mode: str
) -> Any:
    """
    Run field validators for a specific field.
    
    Args:
        cls: Model class
        field_name: Name of field being validated
        value: Current field value
        values: Dictionary of all field values
        mode: Validation mode ('before' or 'after')
        
    Returns:
        Validated value
    """
    # Get all validators for this class
    validators = []
    
    # Collect validators from class and all base classes
    for klass in inspect.getmro(cls):
        for attr_name in dir(klass):
            try:
                attr = getattr(klass, attr_name)
                if hasattr(attr, '__validator_metadata__'):
                    metadata = attr.__validator_metadata__
                    if field_name in metadata.field_names and metadata.mode == mode:
                        validators.append((attr, metadata))
            except AttributeError:
                continue
    
    # Run validators
    for func, metadata in validators:
        info = ValidationInfo(
            field_name=field_name,
            data=values,
            config=getattr(cls, 'model_config', {})
        )
        
        try:
            if metadata.mode == 'wrap':
                # Wrap mode: validator gets the value and a handler function
                def handler(v):
                    return v
                value = func(cls, value, handler, info)
            elif metadata.mode == 'plain':
                # Plain mode: validator completely replaces validation
                value = func(cls, value, info)
            else:
                # Before/After mode: standard validation
                value = func(cls, value, info)
        except Exception as e:
            # Re-raise with field context
            raise ValueError(f"Validation error for field '{field_name}': {str(e)}") from e
    
    return value


def run_model_validators(
    instance: Any,
    mode: str,
    values: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Run model validators.
    
    Args:
        instance: Model instance (for 'after' mode) or class (for 'before' mode)
        mode: Validation mode ('before' or 'after')
        values: Dictionary of values (for 'before' mode)
        
    Returns:
        Validated instance or values
    """
    cls = instance if mode == 'before' else instance.__class__
    
    # Fast path: Check cache first
    cache_key = f'__has_{mode}_model_validators__'
    if hasattr(cls, cache_key):
        if not getattr(cls, cache_key):
            # No validators for this mode - return immediately
            return values if mode == 'before' else instance
    
    # Get all model validators (and cache the result)
    validators = []
    
    for klass in inspect.getmro(cls):
        for attr_name in dir(klass):
            try:
                attr = getattr(klass, attr_name)
                if hasattr(attr, '__model_validator_metadata__'):
                    metadata = attr.__model_validator_metadata__
                    if metadata.mode == mode:
                        validators.append((attr, metadata))
            except AttributeError:
                continue
    
    # Cache whether this class has validators for this mode
    setattr(cls, cache_key, len(validators) > 0)
    
    # Fast path: No validators
    if not validators:
        return values if mode == 'before' else instance
    
    # Run validators
    result = values if mode == 'before' else instance
    
    for func, metadata in validators:
        try:
            if mode == 'before':
                # Before mode: validate dict of values
                result = func(cls, result)
            else:
                # After mode: validate model instance
                result = func(result)
        except Exception as e:
            raise ValueError(f"Model validation error: {str(e)}") from e
    
    return result


# Export public API
__all__ = [
    'field_validator',
    'model_validator',
    'ValidationInfo',
    'run_field_validators',
    'run_model_validators',
]
