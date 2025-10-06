"""
Web Framework Parameter Types for Satya

Provides FastAPI/TurboAPI-style parameter validation with Rust-backed performance.
Supports QueryParam, PathParam, HeaderParam, and FormField for high-performance web validation.
"""

from typing import Any, Optional, Pattern, List, Union, Callable
from dataclasses import dataclass
import re


@dataclass
class ParamConfig:
    """Configuration for web parameter validation"""
    default: Any = None
    alias: Optional[str] = None
    description: Optional[str] = None
    example: Optional[Any] = None
    deprecated: bool = False
    include_in_schema: bool = True
    
    # Validation constraints
    ge: Optional[Union[int, float]] = None
    le: Optional[Union[int, float]] = None
    gt: Optional[Union[int, float]] = None
    lt: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[Union[str, Pattern]] = None
    regex: Optional[Union[str, Pattern]] = None
    
    # String formats
    email: bool = False
    url: bool = False
    uuid: bool = False
    
    # Array constraints
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    unique_items: bool = False
    
    # Enum
    enum: Optional[List[Any]] = None
    
    # Custom validators
    validators: Optional[List[Callable]] = None


class WebParam:
    """Base class for web framework parameters"""
    
    def __init__(
        self,
        default: Any = ...,  # Use ... to indicate required
        *,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        example: Optional[Any] = None,
        deprecated: bool = False,
        include_in_schema: bool = True,
        ge: Optional[Union[int, float]] = None,
        le: Optional[Union[int, float]] = None,
        gt: Optional[Union[int, float]] = None,
        lt: Optional[Union[int, float]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[Union[str, Pattern]] = None,
        regex: Optional[Union[str, Pattern]] = None,
        email: bool = False,
        url: bool = False,
        uuid: bool = False,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique_items: bool = False,
        enum: Optional[List[Any]] = None,
        validators: Optional[List[Callable]] = None,
    ):
        self.default = default
        self.required = default is ...
        self.alias = alias
        self.description = description
        self.example = example
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        
        # Validation constraints
        self.ge = ge
        self.le = le
        self.gt = gt
        self.lt = lt
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern or regex
        self.email = email
        self.url = url
        self.uuid = uuid
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items
        self.enum = enum
        self.validators = validators or []
        
        # Location identifier
        self.param_type = "query"  # Override in subclasses
    
    def validate(self, value: Any) -> Any:
        """Validate and coerce the parameter value"""
        # If value is None and we have a default, use it
        if value is None:
            if self.required:
                raise ValueError(f"{self.param_type.title()} parameter is required")
            return self.default
        
        # String validation
        if isinstance(value, str):
            if self.min_length is not None and len(value) < self.min_length:
                raise ValueError(f"String must be at least {self.min_length} characters")
            if self.max_length is not None and len(value) > self.max_length:
                raise ValueError(f"String must be at most {self.max_length} characters")
            if self.pattern:
                pattern_str = self.pattern if isinstance(self.pattern, str) else self.pattern.pattern
                if not re.match(pattern_str, value):
                    raise ValueError(f"String does not match pattern: {pattern_str}")
            if self.email:
                email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                if not re.match(email_pattern, value):
                    raise ValueError("Invalid email format")
            if self.url:
                if not (value.startswith("http://") or value.startswith("https://")):
                    raise ValueError("Invalid URL format")
        
        # Numeric validation
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if self.ge is not None and value < self.ge:
                raise ValueError(f"Value must be >= {self.ge}")
            if self.le is not None and value > self.le:
                raise ValueError(f"Value must be <= {self.le}")
            if self.gt is not None and value <= self.gt:
                raise ValueError(f"Value must be > {self.gt}")
            if self.lt is not None and value >= self.lt:
                raise ValueError(f"Value must be < {self.lt}")
        
        # List validation
        if isinstance(value, list):
            if self.min_items is not None and len(value) < self.min_items:
                raise ValueError(f"Array must have at least {self.min_items} items")
            if self.max_items is not None and len(value) > self.max_items:
                raise ValueError(f"Array must have at most {self.max_items} items")
            if self.unique_items and len(set(value)) != len(value):
                raise ValueError("Array items must be unique")
        
        # Enum validation
        if self.enum is not None and value not in self.enum:
            raise ValueError(f"Value must be one of: {self.enum}")
        
        # Custom validators
        for validator in self.validators:
            value = validator(value)
        
        return value
    
    def to_json_schema(self) -> dict:
        """Convert parameter to JSON Schema"""
        schema = {}
        
        if self.description:
            schema["description"] = self.description
        if self.example is not None:
            schema["example"] = self.example
        if self.deprecated:
            schema["deprecated"] = True
        
        # Add constraints
        if self.ge is not None:
            schema["minimum"] = self.ge
        if self.le is not None:
            schema["maximum"] = self.le
        if self.gt is not None:
            schema["exclusiveMinimum"] = self.gt
        if self.lt is not None:
            schema["exclusiveMaximum"] = self.lt
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.pattern:
            pattern_str = self.pattern if isinstance(self.pattern, str) else self.pattern.pattern
            schema["pattern"] = pattern_str
        if self.email:
            schema["format"] = "email"
        if self.url:
            schema["format"] = "uri"
        if self.uuid:
            schema["format"] = "uuid"
        if self.min_items is not None:
            schema["minItems"] = self.min_items
        if self.max_items is not None:
            schema["maxItems"] = self.max_items
        if self.unique_items:
            schema["uniqueItems"] = True
        if self.enum is not None:
            schema["enum"] = self.enum
        
        return schema


class QueryParam(WebParam):
    """Query parameter (e.g., ?limit=10&offset=0)"""
    
    def __init__(self, default: Any = ..., **kwargs):
        super().__init__(default, **kwargs)
        self.param_type = "query"


class PathParam(WebParam):
    """Path parameter (e.g., /users/{user_id})"""
    
    def __init__(self, default: Any = ..., **kwargs):
        # Path parameters are always required
        if default is not ...:
            raise ValueError("Path parameters cannot have default values")
        super().__init__(default, **kwargs)
        self.param_type = "path"
        self.required = True


class HeaderParam(WebParam):
    """Header parameter (e.g., Authorization, User-Agent)"""
    
    def __init__(self, default: Any = ..., **kwargs):
        super().__init__(default, **kwargs)
        self.param_type = "header"
        
        # Convert header names to proper case if not aliased
        # e.g., "authorization" -> "Authorization"
        if self.alias is None and isinstance(default, str):
            self.alias = default.replace("_", "-").title()


class CookieParam(WebParam):
    """Cookie parameter"""
    
    def __init__(self, default: Any = ..., **kwargs):
        super().__init__(default, **kwargs)
        self.param_type = "cookie"


class FormField(WebParam):
    """Form field parameter (application/x-www-form-urlencoded or multipart/form-data)"""
    
    def __init__(self, default: Any = ..., **kwargs):
        super().__init__(default, **kwargs)
        self.param_type = "form"


class Body(WebParam):
    """Request body parameter"""
    
    def __init__(self, default: Any = ..., **kwargs):
        super().__init__(default, **kwargs)
        self.param_type = "body"


# Convenience aliases
Query = QueryParam
Path = PathParam
Header = HeaderParam
Cookie = CookieParam
Form = FormField


def validate_int(
    value: Any,
    *,
    ge: Optional[int] = None,
    le: Optional[int] = None,
    gt: Optional[int] = None,
    lt: Optional[int] = None,
) -> int:
    """Fast integer validation helper"""
    if not isinstance(value, int) or isinstance(value, bool):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Expected integer, got {type(value).__name__}")
    
    if ge is not None and value < ge:
        raise ValueError(f"Value must be >= {ge}")
    if le is not None and value > le:
        raise ValueError(f"Value must be <= {le}")
    if gt is not None and value <= gt:
        raise ValueError(f"Value must be > {gt}")
    if lt is not None and value >= lt:
        raise ValueError(f"Value must be < {lt}")
    
    return value


def validate_str(
    value: Any,
    *,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[Union[str, Pattern]] = None,
    email: bool = False,
    url: bool = False,
) -> str:
    """Fast string validation helper"""
    if not isinstance(value, str):
        value = str(value)
    
    if min_length is not None and len(value) < min_length:
        raise ValueError(f"String must be at least {min_length} characters")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"String must be at most {max_length} characters")
    if pattern:
        pattern_str = pattern if isinstance(pattern, str) else pattern.pattern
        if not re.match(pattern_str, value):
            raise ValueError(f"String does not match pattern: {pattern_str}")
    if email:
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            raise ValueError("Invalid email format")
    if url:
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("Invalid URL format")
    
    return value


def validate_float(
    value: Any,
    *,
    ge: Optional[float] = None,
    le: Optional[float] = None,
    gt: Optional[float] = None,
    lt: Optional[float] = None,
) -> float:
    """Fast float validation helper"""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Expected float, got {type(value).__name__}")
    
    value = float(value)  # Coerce int to float
    
    if ge is not None and value < ge:
        raise ValueError(f"Value must be >= {ge}")
    if le is not None and value > le:
        raise ValueError(f"Value must be <= {le}")
    if gt is not None and value <= gt:
        raise ValueError(f"Value must be > {gt}")
    if lt is not None and value >= lt:
        raise ValueError(f"Value must be < {lt}")
    
    return value


def validate_param(value: Any, param: WebParam) -> Any:
    """Validate a value against a WebParam configuration"""
    return param.validate(value)


__all__ = [
    "ParamConfig",
    "WebParam",
    "QueryParam",
    "PathParam",
    "HeaderParam",
    "CookieParam",
    "FormField",
    "Body",
    "Query",
    "Path",
    "Header",
    "Cookie",
    "Form",
    "validate_int",
    "validate_str",
    "validate_float",
    "validate_param",
]
