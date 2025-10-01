"""
ABSENT sentinel for optional field behavior.

This module provides the ABSENT sentinel to distinguish between:
- None (field is explicitly set to None)
- ABSENT (field is not present in the data)

This is critical for JSON Schema compatibility where missing fields should stay absent
rather than being auto-injected with default values.
"""

from typing import TypeVar, Type


class _AbsentType:
    """
    Sentinel type for absent fields.
    
    Use this to indicate that a field can be absent from the data structure,
    rather than being present with a default value.
    
    Example:
        >>> from satya import Model, Field, ABSENT
        >>> 
        >>> class Config(Model):
        ...     name: str
        ...     version: str
        ...     python: str | type[ABSENT] = ABSENT  # Optional, stays absent
        ...     markers: str = ""  # Optional with default
        >>> 
        >>> data = {"name": "pkg", "version": "1.0"}
        >>> config = Config(**data)
        >>> config.dict()  # {"name": "pkg", "version": "1.0"}  # python field is absent
    
    Behavior:
        - Fields with ABSENT default will not appear in the output dictionary if not provided
        - Fields with other defaults (like "" or 0) will be included even if not provided
        - This matches fastjsonschema behavior where missing keys stay absent
    """
    
    def __repr__(self) -> str:
        return "ABSENT"
    
    def __bool__(self) -> bool:
        return False
    
    def __eq__(self, other) -> bool:
        return isinstance(other, _AbsentType)
    
    def __hash__(self) -> int:
        return hash("ABSENT")


# Create the singleton instance
ABSENT = _AbsentType()

T = TypeVar('T')


def is_absent(value: any) -> bool:
    """
    Check if a value is the ABSENT sentinel.
    
    Args:
        value: Value to check
    
    Returns:
        True if value is ABSENT, False otherwise
    
    Example:
        >>> from satya import ABSENT, is_absent
        >>> is_absent(ABSENT)  # True
        >>> is_absent(None)    # False
        >>> is_absent("")      # False
    """
    return value is ABSENT or isinstance(value, _AbsentType)


def filter_absent(data: dict) -> dict:
    """
    Remove all ABSENT values from a dictionary.
    
    Args:
        data: Dictionary potentially containing ABSENT values
    
    Returns:
        Dictionary with ABSENT values removed
    
    Example:
        >>> from satya import ABSENT, filter_absent
        >>> data = {"name": "test", "value": ABSENT, "count": 0}
        >>> filter_absent(data)  # {"name": "test", "count": 0}
    """
    return {k: v for k, v in data.items() if not is_absent(v)}


__all__ = ['ABSENT', 'is_absent', 'filter_absent']
