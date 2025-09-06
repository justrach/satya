# Configuration flag for string representation
from typing import Any, Dict, Literal, Optional, Type, Union, Iterator, List, TypeVar, Generic, get_args, get_origin, ClassVar, Pattern
from dataclasses import dataclass
from itertools import islice
from .json_loader import load_json  # Import the new JSON loader
import json
try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("satya")
except Exception:
    __version__ = "0.0.0"
import re
from uuid import UUID
from enum import Enum
from datetime import datetime
from decimal import Decimal
T = TypeVar('T')

@dataclass
class ValidationError:
    """Represents a validation error"""
    field: str
    message: str
    path: List[str]

    def __str__(self) -> str:
        loc = ".".join(self.path) if self.path else self.field
        return f"{loc}: {self.message}"

class ValidationResult(Generic[T]):
    """Represents the result of validation"""
    def __init__(self, value: Optional[T] = None, errors: Optional[List[ValidationError]] = None):
        self._value = value
        self._errors = errors or []
        
    @property
    def is_valid(self) -> bool:
        return len(self._errors) == 0
        
    @property
    def value(self) -> T:
        if not self.is_valid:
            raise ValueError("Cannot access value of invalid result")
        return self._value
        
    @property
    def errors(self) -> List[ValidationError]:
        return self._errors.copy()
    
    def __str__(self) -> str:
        if self.is_valid:
            return f"Valid: {self._value}"
        return f"Invalid: {'; '.join(str(err) for err in self._errors)}"

class ModelValidationError(Exception):
    """Exception raised when model validation fails (Pydantic-like)."""
    def __init__(self, errors: List[ValidationError]):
        self.errors = errors
        super().__init__("; ".join(f"{e.field}: {e.message}" for e in errors))


@dataclass
class FieldConfig:
    """Configuration for field validation"""
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[Pattern] = None
    email: bool = False
    url: bool = False
    description: Optional[str] = None

class Field:
    """Field definition with validation rules"""
    def __init__(
        self,
        type_: Type = None,
        *,
        required: bool = True,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        email: bool = False,
        url: bool = False,
        ge: Optional[int] = None,
        le: Optional[int] = None,
        gt: Optional[int] = None,
        lt: Optional[int] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique_items: bool = False,
        enum: Optional[List[Any]] = None,
        description: Optional[str] = None,
        example: Optional[Any] = None,
        default: Any = None,
    ):
        self.type = type_
        self.required = required
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self.email = email
        self.url = url
        self.ge = ge
        self.le = le
        self.gt = gt
        self.lt = lt
        self.min_value = min_value
        self.max_value = max_value
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items
        self.enum = enum
        self.description = description
        self.example = example
        self.default = default

    def json_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for this field"""
        schema = {}
        
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.pattern is not None:
            schema["pattern"] = self.pattern
        if self.email:
            schema["pattern"] = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if self.ge is not None:
            schema["minimum"] = self.ge
        if self.le is not None:
            schema["maximum"] = self.le
        if self.gt is not None:
            schema["exclusiveMinimum"] = self.gt
        if self.lt is not None:
            schema["exclusiveMaximum"] = self.lt
        if self.description:
            schema["description"] = self.description
        if self.example:
            schema["example"] = self.example
        if self.min_items is not None:
            schema["minItems"] = self.min_items
        if self.max_items is not None:
            schema["maxItems"] = self.max_items
        if self.unique_items:
            schema["uniqueItems"] = True
        if self.enum:
            schema["enum"] = self.enum
            
        return schema

class ModelMetaclass(type):
    """Metaclass for handling model definitions"""
    def __new__(mcs, name, bases, namespace):
        fields = {}
        annotations = namespace.get('__annotations__', {})
        
        # Get fields from type annotations and Field definitions
        for field_name, field_type in annotations.items():
            if field_name.startswith('_'):
                continue
            
            field_def = namespace.get(field_name, Field())
            if not isinstance(field_def, Field):
                field_def = Field(default=field_def)
                
            if field_def.type is None:
                field_def.type = field_type
                
            fields[field_name] = field_def
            
        namespace['__fields__'] = fields
        # Default, Pydantic-like config
        namespace.setdefault('model_config', {
            'extra': 'ignore',  # 'ignore' | 'allow' | 'forbid'
            'validate_assignment': False,
        })
        return super().__new__(mcs, name, bases, namespace)

class Model(metaclass=ModelMetaclass):
    """Base class for schema models with improved developer experience"""
    
    __fields__: ClassVar[Dict[str, Field]]
    PRETTY_REPR = False  # Default to False, let users opt-in
    _validator_instance: ClassVar[Optional['StreamValidator']] = None
    
    def __init__(self, **data):
        """Validate on construction (Pydantic-like). Use model_construct to skip validation."""
        self._errors = []
        # Validate input using cached validator
        validator = self.__class__.validator()
        result = validator.validate(data)
        if not result.is_valid:
            raise ModelValidationError(result.errors)

        normalized = result.value or {}

        # Handle extras per model_config
        config = getattr(self.__class__, 'model_config', {}) or {}
        extra_mode = config.get('extra', 'ignore')
        field_names = set(self.__fields__.keys())
        input_keys = set(data.keys())
        extra_keys = [k for k in input_keys if k not in field_names]
        if extra_keys and extra_mode == 'forbid':
            raise ModelValidationError([
                ValidationError(field=k, message='extra fields not permitted', path=[k]) for k in extra_keys
            ])

        self._data = {}
        # Set known fields from normalized data (falls back to default)
        for name, field in self.__fields__.items():
            value = normalized.get(name, field.default)
            self._data[name] = value
            setattr(self, name, value)

        # Optionally keep extras
        if extra_mode == 'allow':
            for k in extra_keys:
                self._data[k] = data[k]
                setattr(self, k, data[k])
        
    def __str__(self):
        """String representation of the model"""
        if self.__class__.PRETTY_REPR:
            fields = []
            for name, value in self._data.items():
                fields.append(f"{name}={repr(value)}")
            return f"{self.__class__.__name__} {' '.join(fields)}"
        return super().__str__()
        
    @property
    def __dict__(self):
        """Make the model dict-like"""
        return self._data
        
    def __getattr__(self, name):
        """Handle attribute access for missing fields"""
        if name in self.__fields__:
            return self._data.get(name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    @classmethod
    def schema(cls) -> Dict:
        """Get JSON Schema representation"""
        return {
            'title': cls.__name__,
            'type': 'object',
            'properties': {
                name: {
                    'type': _type_to_json_schema(field.type),
                    'description': field.description,
                    'example': field.example
                }
                for name, field in cls.__fields__.items()
            },
            'required': [
                name for name, field in cls.__fields__.items()
                if field.required
            ]
        }
        
    @classmethod
    def validator(cls) -> 'StreamValidator':
        """Create a validator for this model"""
        if cls._validator_instance is None:
            # Import lazily to avoid initializing the Rust core on module import
            from .validator import StreamValidator
            validator = StreamValidator()
            _register_model(validator, cls)
            cls._validator_instance = validator
        return cls._validator_instance
    
    def dict(self) -> Dict:
        """Convert to dictionary"""
        return self._data.copy()

    # ---- Pydantic-like API ----
    @classmethod
    def model_validate(cls, data: Dict[str, Any]) -> 'Model':
        """Validate data and return a model instance (raises on error)."""
        return cls(**data)

    @classmethod
    def model_validate_json(cls, json_str: str) -> 'Model':
        """Validate JSON string and return a model instance (raises on error)."""
        data = load_json(json_str)
        if not isinstance(data, dict):
            raise ModelValidationError([
                ValidationError(field='root', message='JSON must represent an object', path=['root'])
            ])
        return cls(**data)

    # --- New: model-level JSON-bytes APIs (streaming or not) ---
    @classmethod
    def model_validate_json_bytes(cls, data: Union[str, bytes], *, streaming: bool = True) -> 'Model':
        """Validate a single JSON object provided as bytes/str. Returns model instance or raises."""
        validator = cls.validator()
        ok = validator.validate_json(data, mode="object", streaming=streaming)
        if not ok:
            raise ModelValidationError([
                ValidationError(field='root', message='JSON does not conform to schema', path=['root'])
            ])
        py = load_json(data)  # parse after validation to construct instance
        if not isinstance(py, dict):
            raise ModelValidationError([
                ValidationError(field='root', message='JSON must represent an object', path=['root'])
            ])
        return cls(**py)

    @classmethod
    def model_validate_json_array_bytes(cls, data: Union[str, bytes], *, streaming: bool = True) -> List[bool]:
        """Validate a top-level JSON array of objects from bytes/str. Returns per-item booleans."""
        validator = cls.validator()
        return validator.validate_json(data, mode="array", streaming=streaming)

    @classmethod
    def model_validate_ndjson_bytes(cls, data: Union[str, bytes], *, streaming: bool = True) -> List[bool]:
        """Validate NDJSON (one JSON object per line). Returns per-line booleans."""
        validator = cls.validator()
        return validator.validate_json(data, mode="ndjson", streaming=streaming)

    def model_dump(self, *, exclude_none: bool = False) -> Dict[str, Any]:
        """Dump model data as a dict."""
        d = self._data.copy()
        if exclude_none:
            d = {k: v for k, v in d.items() if v is not None}
        return d

    def model_dump_json(self, *, exclude_none: bool = False) -> str:
        """Dump model data as a JSON string."""
        return json.dumps(self.model_dump(exclude_none=exclude_none))

    @classmethod
    def model_json_schema(cls) -> dict:
        """Return JSON Schema for this model (alias)."""
        return cls.json_schema()

    @classmethod
    def parse_obj(cls, obj: Dict[str, Any]) -> 'Model':
        """Compatibility alias for Pydantic v1-style API."""
        return cls.model_validate(obj)

    @classmethod
    def parse_raw(cls, data: str) -> 'Model':
        """Compatibility alias for Pydantic v1-style API."""
        return cls.model_validate_json(data)

    @classmethod
    def model_construct(cls, **data: Any) -> 'Model':
        """Construct a model instance without validation (Pydantic-like)."""
        self = object.__new__(cls)
        self._errors = []
        config = getattr(cls, 'model_config', {}) or {}
        extra_mode = config.get('extra', 'ignore')
        self._data = {}
        # Set known fields
        for name, field in cls.__fields__.items():
            value = data.get(name, field.default)
            self._data[name] = value
            setattr(self, name, value)
        # Handle extras
        if extra_mode == 'allow':
            for k, v in data.items():
                if k not in cls.__fields__:
                    self._data[k] = v
                    setattr(self, k, v)
        elif extra_mode == 'forbid':
            extras = [k for k in data.keys() if k not in cls.__fields__]
            if extras:
                raise ModelValidationError([
                    ValidationError(field=k, message='extra fields not permitted', path=[k]) for k in extras
                ])
        return self

    @classmethod
    def json_schema(cls) -> dict:
        """Generate JSON Schema for this model"""
        properties = {}
        required = []

        for field_name, field in cls.__fields__.items():
            field_schema = _field_to_json_schema(field)
            properties[field_name] = field_schema
            if field.required:
                required.append(field_name)

        schema = {
            "type": "object",
            "title": cls.__name__,
            "properties": properties,
        }
        
        if required:
            schema["required"] = required

        return schema

def _python_type_to_json_type(py_type: type) -> str:
    """Convert Python type to JSON Schema type"""
    # Get the type name
    type_name = getattr(py_type, '__name__', str(py_type))
    
    # Basic type mapping
    basic_types = {
        'str': 'string',
        'int': 'integer',
        'float': 'number',
        'bool': 'boolean',
        'dict': 'object',
        'list': 'array',
        'datetime': 'string',
        'date': 'string',
        'UUID': 'string',
    }
    
    return basic_types.get(type_name, 'string')

def _field_to_json_schema(field: Field) -> dict:
    """Convert a Field to JSON Schema"""
    schema = {}
    
    # Get type name dynamically
    type_name = getattr(field.type, '__name__', str(field.type))
    
    # Handle basic types
    if type_name == 'str':
        schema["type"] = "string"
        if field.min_length is not None:
            schema["minLength"] = field.min_length
        if field.max_length is not None:
            schema["maxLength"] = field.max_length
        if field.pattern:
            schema["pattern"] = field.pattern
        if field.email:
            schema["format"] = "email"
        if field.url:
            schema["format"] = "uri"
    
    elif type_name in ('int', 'float'):
        schema["type"] = "number" if type_name == 'float' else "integer"
        if field.min_value is not None:
            schema["minimum"] = field.min_value
        if field.max_value is not None:
            schema["maximum"] = field.max_value
        if field.ge is not None:
            schema["minimum"] = field.ge
        if field.le is not None:
            schema["maximum"] = field.le
        if field.gt is not None:
            schema["exclusiveMinimum"] = field.gt
        if field.lt is not None:
            schema["exclusiveMaximum"] = field.lt
    
    elif type_name == 'bool':
        schema["type"] = "boolean"
    
    elif type_name in ('datetime', 'date'):
        schema["type"] = "string"
        schema["format"] = "date-time"
    
    elif type_name == 'UUID':
        schema["type"] = "string"
        schema["format"] = "uuid"
    
    # Handle complex types
    elif get_origin(field.type) == list:
        schema["type"] = "array"
        item_type = get_args(field.type)[0]
        if hasattr(item_type, "json_schema"):
            schema["items"] = item_type.json_schema()
        else:
            schema["items"] = {"type": _python_type_to_json_type(item_type)}
        if field.min_length is not None:
            schema["minItems"] = field.min_length
        if field.max_length is not None:
            schema["maxItems"] = field.max_length
    
    elif get_origin(field.type) == dict:
        schema["type"] = "object"
        value_type = get_args(field.type)[1]
        if value_type == Any:
            schema["additionalProperties"] = True
        else:
            schema["additionalProperties"] = {"type": _python_type_to_json_type(value_type)}
    
    # Handle enums
    elif isinstance(field.type, type) and issubclass(field.type, Enum):
        schema["type"] = "string"
        schema["enum"] = [e.value for e in field.type]
    
    # Handle Literal types
    elif get_origin(field.type) == Literal:
        schema["enum"] = list(get_args(field.type))
    
    # Handle nested models
    elif isinstance(field.type, type) and issubclass(field.type, Model):
        schema.update(field.type.json_schema())
    
    # Handle Optional types
    if get_origin(field.type) == Union and type(None) in get_args(field.type):
        schema["nullable"] = True
    
    if field.description:
        schema["description"] = field.description
    
    return schema

def _type_to_json_schema(type_: Type) -> Dict:
    """Convert Python type to JSON Schema"""
    if type_ == str:
        return {'type': 'string'}
    elif type_ == int:
        return {'type': 'integer'}
    elif type_ == float:
        return {'type': 'number'}
    elif type_ == bool:
        return {'type': 'boolean'}
    elif get_origin(type_) is list:
        return {
            'type': 'array',
            'items': _type_to_json_schema(get_args(type_)[0])
        }
    elif get_origin(type_) is dict:
        return {
            'type': 'object',
            'additionalProperties': _type_to_json_schema(get_args(type_)[1])
        }
    elif isinstance(type_, type) and issubclass(type_, Model):
        return {'$ref': f'#/definitions/{type_.__name__}'}
    return {'type': 'object'}

def _register_model(validator: 'StreamValidator', model: Type[Model], path: List[str] = None) -> None:
    """Register a model and its nested models with the validator"""
    path = path or []
    
    # Register nested models first
    for field in model.__fields__.values():
        field_type = field.type
        # Handle List[Model] case
        if get_origin(field_type) is list:
            inner_type = get_args(field_type)[0]
            if isinstance(inner_type, type) and issubclass(inner_type, Model):
                _register_model(validator, inner_type, path + [model.__name__])
        # Handle direct Model case
        elif isinstance(field_type, type) and issubclass(field_type, Model):
            _register_model(validator, field_type, path + [model.__name__])
    
    # Register this model as a custom type (for nested usage)
    validator.define_type(
        model.__name__,
        {name: field.type for name, field in model.__fields__.items()},
        doc=model.__doc__
    )

    # If this is the top-level model (no parent path), also populate the root schema
    if not path:
        for name, field in model.__fields__.items():
            validator.add_field(name, field.type, required=field.required)
            # Propagate constraints to the core
            enum_values = None
            # Only apply enum for string fields for now (core enum compares strings)
            type_name = getattr(field.type, '__name__', str(field.type))
            if field.enum and type_name == 'str':
                enum_values = [str(v) for v in field.enum]
            # pattern is already a str or None
            validator.set_constraints(
                name,
                min_length=field.min_length,
                max_length=field.max_length,
                min_value=field.min_value,
                max_value=field.max_value,
                pattern=field.pattern,
                email=field.email,
                url=field.url,
                ge=field.ge,
                le=field.le,
                gt=field.gt,
                lt=field.lt,
                min_items=field.min_items,
                max_items=field.max_items,
                unique_items=field.unique_items,
                enum_values=enum_values,
            )

BaseModel = Model

def __getattr__(name: str):
    """Lazy attribute access to avoid importing heavy modules at import time."""
    if name == 'StreamValidator':
        from .validator import StreamValidator as _SV
        return _SV
    if name == 'StreamValidatorCore':
        from ._satya import StreamValidatorCore as _SVC
        return _SVC
    raise AttributeError(name)

__all__ = ['StreamValidator', 'load_json', 'Model', 'BaseModel', 'Field', 'ValidationResult', 'ValidationError', 'ModelValidationError', '__version__']