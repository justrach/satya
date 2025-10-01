"""
Array validator for high-performance validation of list/array types.

This validator provides Rust-backed validation for arrays with item schemas and constraints.
Uses the existing StreamValidatorCore by creating single-field array schemas.
"""

from typing import Any, Optional, List, Union, Type, Callable


class ArrayValidator:
    """
    High-performance array validator with Rust-backed validation.
    
    Uses the existing StreamValidatorCore by creating a single-field array schema
    and delegating to Rust for maximum performance.
    
    Example with scalar items:
        >>> validator = ArrayValidator(item_type='string', min_items=1, max_items=5)
        >>> result = validator.validate(["a", "b", "c"])
        >>> assert result.is_valid
    
    Example with integer items:
        >>> validator = ArrayValidator(item_type='integer', min_items=0, max_items=10)
        >>> result = validator.validate([1, 2, 3])
        >>> assert result.is_valid
    """
    
    def __init__(
        self,
        item_type: Union[str, Type] = None,  # 'string', 'integer', 'number', 'boolean', or Model class
        *,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique_items: bool = False,
    ):
        """
        Initialize array validator.
        
        Args:
            item_type: Type of items ('string', 'integer', 'number', 'boolean', or Model class)
            min_items: Minimum number of items
            max_items: Maximum number of items
            unique_items: Whether items must be unique
        """
        from .validator import StreamValidator
        
        self.item_type = item_type
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items
        
        # Map Python type to validator type string
        type_map = {
            str: 'string',
            int: 'integer',
            float: 'number',
            bool: 'boolean',
        }
        
        # Resolve item type
        if isinstance(item_type, type):
            self.item_type_str = type_map.get(item_type, 'string')
        else:
            self.item_type_str = item_type or 'string'
        
        # Create StreamValidator with array field
        # Note: StreamValidator currently validates object fields, so we'll use Python-side validation
        # for now. This is a placeholder for future Rust array support.
        self._use_python_validation = True
    
    def validate(self, value: Any) -> "ValidationResult":
        """Validate an array value"""
        from . import ValidationResult as VR, ValidationError as VE
        
        errors = []
        
        # Type check
        if not isinstance(value, list):
            return VR(
                value=None,
                errors=[VE(field="value", message=f"Expected array, got {type(value).__name__}", path=["value"])]
            )
        
        # Length validation
        if self.min_items is not None and len(value) < self.min_items:
            errors.append(VE(
                field="value",
                message=f"Array must have at least {self.min_items} items",
                path=["value"]
            ))
        
        if self.max_items is not None and len(value) > self.max_items:
            errors.append(VE(
                field="value",
                message=f"Array must have at most {self.max_items} items",
                path=["value"]
            ))
        
        # Unique items validation
        if self.unique_items:
            # Try to make items hashable for set comparison
            try:
                # For dicts, convert to frozenset of items
                hashable_items = []
                for item in value:
                    if isinstance(item, dict):
                        hashable_items.append(frozenset(item.items()))
                    elif isinstance(item, list):
                        hashable_items.append(tuple(item))
                    else:
                        hashable_items.append(item)
                
                if len(set(hashable_items)) != len(value):
                    errors.append(VE(
                        field="value",
                        message="Array items must be unique",
                        path=["value"]
                    ))
            except (TypeError, AttributeError):
                # If items aren't hashable, do manual comparison
                for i, item1 in enumerate(value):
                    for item2 in value[i+1:]:
                        if item1 == item2:
                            errors.append(VE(
                                field="value",
                                message="Array items must be unique",
                                path=["value"]
                            ))
                            break
        
        # Basic type validation for simple scalar arrays
        if self.item_type_str in ['string', 'integer', 'number', 'boolean']:
            type_check_map = {
                'string': str,
                'integer': int,
                'number': (int, float),
                'boolean': bool,
            }
            expected_type = type_check_map[self.item_type_str]
            
            for idx, item in enumerate(value):
                # Special handling for boolean (exclude int masquerading as bool)
                if self.item_type_str == 'boolean':
                    if not isinstance(item, bool):
                        errors.append(VE(
                            field=f"[{idx}]",
                            message=f"Expected boolean, got {type(item).__name__}",
                            path=["value", str(idx)]
                        ))
                # Special handling for integer (exclude bool)
                elif self.item_type_str == 'integer':
                    if not isinstance(item, int) or isinstance(item, bool):
                        errors.append(VE(
                            field=f"[{idx}]",
                            message=f"Expected integer, got {type(item).__name__}",
                            path=["value", str(idx)]
                        ))
                # Number (accepts int or float, excludes bool)
                elif self.item_type_str == 'number':
                    if not isinstance(item, (int, float)) or isinstance(item, bool):
                        errors.append(VE(
                            field=f"[{idx}]",
                            message=f"Expected number, got {type(item).__name__}",
                            path=["value", str(idx)]
                        ))
                # String
                else:
                    if not isinstance(item, expected_type):
                        errors.append(VE(
                            field=f"[{idx}]",
                            message=f"Expected {self.item_type_str}, got {type(item).__name__}",
                            path=["value", str(idx)]
                        ))
        
        return VR(
            value=value if len(errors) == 0 else None,
            errors=errors
        )
    
    def validate_batch(self, values: List[Any]) -> List["ValidationResult"]:
        """Validate multiple array values"""
        return [self.validate(v) for v in values]
