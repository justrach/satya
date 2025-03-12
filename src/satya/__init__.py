# Configuration flag for string representation
from typing import Any, Dict, Literal, Optional, Type, Union, Iterator, List, TypeVar, Generic, get_args, get_origin, ClassVar, Pattern
from dataclasses import dataclass
from . import _satya
from itertools import islice
from ._satya import StreamValidatorCore
from .validator import StreamValidator
import re
from uuid import UUID
from enum import Enum
from datetime import datetime
T = TypeVar('T')

@dataclass
class ValidationError:
    """Represents a validation error"""
    field: str
    message: str
    path: List[str]

    def __str__(self) -> str:
        if self.__class__.PRETTY_REPR:
            fields = []
            for name, value in self._data.items():
                fields.append(f"{name}={repr(value)}")
            return f"{self.__class__.__name__} {' '.join(fields)}"
        return super().__str__()

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

class StreamValidator:
    """Validator for streaming data validation"""
    def __init__(self):
        self._validator = StreamValidatorCore()
        self._type_registry = {}
        self._batch_size = 1000  # Default batch size
    
    def set_batch_size(self, size: int) -> None:
        """Set the batch size for stream processing"""
        if size < 1:
            raise ValueError("Batch size must be positive")
        self._batch_size = size
        self._validator.set_batch_size(size)
    
    def get_batch_size(self) -> int:
        """Get current batch size"""
        return self._batch_size
    
    def define_type(self, type_name: str, fields: Dict[str, Union[Type, str]], 
                   doc: Optional[str] = None) -> None:
        """
        Define a new custom type with fields
        
        Args:
            type_name: Name of the custom type
            fields: Dictionary mapping field names to their types
            doc: Optional documentation string
        """
        self._validator.define_custom_type(type_name)
        self._type_registry[type_name] = {
            'fields': fields,
            'doc': doc
        }
        
        for field_name, field_type in fields.items():
            self._validator.add_field_to_custom_type(
                type_name, 
                field_name,
                self._get_type_string(field_type),
                True  # Required by default
            )
    
    def add_field(self, name: str, field_type: Union[Type, str], 
                 required: bool = True, description: Optional[str] = None) -> None:
        """
        Add a field to the root schema
        
        Args:
            name: Field name
            field_type: Type of the field (can be primitive, List, Dict, or custom type)
            required: Whether the field is required (default: True)
            description: Optional field description
        """
        type_str = self._get_type_string(field_type)
        self._validator.add_field(name, type_str, required)
    
    def validate(self, data: Dict) -> ValidationResult[Dict]:
        """
        Validate a single dictionary against the schema
        
        Returns:
            ValidationResult containing either the valid data or validation errors
        """
        try:
            results = list(self.validate_stream([data]))
            if results:
                return ValidationResult(value=results[0])
            return ValidationResult(errors=[
                ValidationError(field="root", message="Validation failed", path=[])
            ])
        except Exception as e:
            return ValidationResult(errors=[
                ValidationError(field="root", message=str(e), path=[])
            ])
    
    def validate_stream(self, items: Iterator[Dict], 
                       collect_errors: bool = False) -> Iterator[Union[Dict, ValidationResult[Dict]]]:
        """Validate a stream of items"""
        batch = []
        for item in items:
            batch.append(item)
            if len(batch) >= self._batch_size:
                yield from self._process_batch(batch, collect_errors)
                batch = []
        
        if batch:  # Process remaining items
            yield from self._process_batch(batch, collect_errors)
    
    def _process_batch(self, batch: List[Dict], 
                      collect_errors: bool) -> Iterator[Union[Dict, ValidationResult[Dict]]]:
        """Process a batch of items"""
        try:
            results = self._validator.validate_batch(batch)
            for item, is_valid in zip(batch, results):
                if is_valid:
                    if collect_errors:
                        yield ValidationResult(value=item)
                    else:
                        yield item
                elif collect_errors:
                    yield ValidationResult(errors=[
                        ValidationError(field="root", message="Validation failed", path=[])
                    ])
        except Exception as e:
            if collect_errors:
                yield ValidationResult(errors=[
                    ValidationError(field="root", message=str(e), path=[])
                ])
    
    def _get_type_string(self, field_type: Union[Type, str]) -> str:
        """Convert Python type to type string"""
        if isinstance(field_type, str):
            return field_type
        
        # Handle Literal types
        if get_origin(field_type) == Literal:
            return "str"  # Literals are treated as strings with enum validation
        
        # Get type name dynamically
        type_name = getattr(field_type, '__name__', str(field_type))
        
        # Handle basic types
        type_map = {
            str: 'str',  # Use type objects as keys
            int: 'int',
            float: 'float',
            bool: 'bool',
            dict: 'dict',
            list: 'list',
            datetime: 'date-time',  # Now datetime will match
            UUID: 'uuid',
            Any: 'any',
        }
        
        # Get the base type for Optional/Union types
        if get_origin(field_type) == Union:
            args = get_args(field_type)
            # Remove None type for Optional fields
            types = [t for t in args if t != type(None)]
            if len(types) == 1:
                return self._get_type_string(types[0])
        
        # Handle List and Dict
        if get_origin(field_type) == list:
            inner_type = get_args(field_type)[0]
            return f"List[{self._get_type_string(inner_type)}]"
        elif get_origin(field_type) == dict:
            key_type, value_type = get_args(field_type)
            return f"Dict[{self._get_type_string(value_type)}]"
        
        # Handle Enum types
        if isinstance(field_type, type) and issubclass(field_type, Enum):
            return "str"  # Enums are treated as strings with enum validation
        
        # Handle Model types
        if isinstance(field_type, type) and hasattr(field_type, '__fields__'):
            return field_type.__name__
        
        # Try to get type from mapping
        if field_type in type_map:
            return type_map[field_type]
        
        # Fallback to type name mapping
        name_map = {
            'str': 'str',
            'int': 'int',
            'float': 'float',
            'bool': 'bool',
            'dict': 'dict',
            'list': 'list',
            'datetime': 'date-time',
            'date': 'date-time',
            'UUID': 'uuid',
            'Any': 'any',
        }
        if type_name in name_map:
            return name_map[type_name]
        
        raise ValueError(f"Unsupported type: {field_type}")
    
    def get_type_info(self, type_name: str) -> Optional[Dict]:
        """Get information about a registered custom type"""
        return self._type_registry.get(type_name)

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
        return super().__new__(mcs, name, bases, namespace)

class Model(metaclass=ModelMetaclass):
    """Base class for schema models with improved developer experience"""
    
    __fields__: ClassVar[Dict[str, Field]]
    PRETTY_REPR = False  # Default to False, let users opt-in
    
    def __init__(self, **data):
        self._data = data
        self._errors = []
        # Set attributes from data
        for name, field in self.__fields__.items():
            value = data.get(name, field.default)
            setattr(self, name, value)
        
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
                    'examples': field.examples
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
        validator = StreamValidator()
        _register_model(validator, cls)
        return validator
    
    def dict(self) -> Dict:
        """Convert to dictionary"""
        return self._data.copy()

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
    
    # Register this model
    validator.define_type(
        model.__name__,
        {name: field.type for name, field in model.__fields__.items()},
        doc=model.__doc__
    )

__all__ = ['StreamValidator'] 