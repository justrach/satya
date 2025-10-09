"""
Serialization Decorators - Pydantic Compatible
==============================================

Implements Pydantic-compatible serialization decorators:
- @field_serializer - Custom serialization for specific fields
- @model_serializer - Custom serialization for entire model
"""

from typing import Any, Callable, Optional, Dict
from functools import wraps


def field_serializer(*fields: str, mode: str = 'plain', when_used: str = 'always'):
    """
    Decorator for custom field serialization (Pydantic compatible)
    
    Args:
        *fields: Field names to apply serializer to
        mode: 'plain' or 'wrap' (default: 'plain')
        when_used: 'always', 'unless-none', or 'json' (default: 'always')
    
    Example:
        @field_serializer('password')
        def serialize_password(self, value):
            return '***'
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function
        func.__field_serializer__ = True
        func.__serializer_fields__ = fields
        func.__serializer_mode__ = mode
        func.__serializer_when__ = when_used
        return func
    return decorator


def model_serializer(mode: str = 'plain'):
    """
    Decorator for custom model serialization (Pydantic compatible)
    
    Args:
        mode: 'plain' or 'wrap' (default: 'plain')
    
    Example:
        @model_serializer
        def serialize_model(self):
            return {'custom': 'serialization'}
    """
    def decorator(func: Callable) -> Callable:
        func.__model_serializer__ = True
        func.__serializer_mode__ = mode
        return func
    return decorator


def computed_field(func: Optional[Callable] = None, *, alias: Optional[str] = None, 
                   return_type: Optional[type] = None):
    """
    Decorator for computed fields (Pydantic compatible)
    
    Example:
        @computed_field
        @property
        def full_name(self) -> str:
            return f"{self.first_name} {self.last_name}"
    """
    def decorator(f: Callable) -> Callable:
        f.__computed_field__ = True
        f.__field_alias__ = alias
        f.__return_type__ = return_type
        return property(f)
    
    if func is None:
        return decorator
    return decorator(func)


__all__ = ['field_serializer', 'model_serializer', 'computed_field']
