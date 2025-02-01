# Configuration flag for string representation
from typing import Any, Dict, Optional, Type, Union, Iterator, List, TypeVar, Generic, get_args, get_origin, ClassVar
from dataclasses import dataclass
from . import _satya
from itertools import islice
from ._satya import StreamValidatorCore
from .validator import StreamValidator

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
    """A high-performance stream validator for JSON-like data"""
    
    def __init__(self, batch_size: int = 1000):
        """Initialize the validator with optional batch size for stream processing"""
        self._validator = _satya.StreamValidatorCore()
        self._validator.set_batch_size(batch_size)
        self._type_registry = {}
        
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
    
    def validate_stream(self, stream: Iterator[Dict], 
                       collect_errors: bool = False) -> Iterator[Union[Dict, ValidationResult[Dict]]]:
        """
        Validate a stream of dictionaries
        
        Args:
            stream: Iterator of dictionaries to validate
            collect_errors: If True, yield ValidationResult objects instead of just valid dicts
            
        Yields:
            Either validated dictionaries or ValidationResults depending on collect_errors
        """
        batch = []
        batch_size = self._validator.batch_size
        
        for item in stream:
            if not isinstance(item, dict):
                if collect_errors:
                    yield ValidationResult(errors=[
                        ValidationError(field="root", message="Item must be a dictionary", path=[])
                    ])
                continue
                
            batch.append(item)
            if len(batch) >= batch_size:
                yield from self._process_batch(batch, collect_errors)
                batch = []
        
        if batch:
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
        """Convert Python type hints to string representation"""
        # Handle string type names directly
        if isinstance(field_type, str):
            return field_type
        
        type_map = {
            str: "str",
            int: "int",
            float: "float",
            bool: "bool"
        }
        
        origin = get_origin(field_type)
        
        # Handle Optional types
        if origin is Union:
            args = get_args(field_type)
            if len(args) == 2 and args[1] is type(None):  # Optional[T] is Union[T, None]
                inner_type = self._get_type_string(args[0])
                return inner_type  # The Rust side will handle optionality via required=False
            
        # Handle List type hints
        if origin is list:
            inner_type = get_args(field_type)[0]
            if isinstance(inner_type, str) or hasattr(inner_type, "__forward_arg__"):
                inner_str = inner_type.__forward_arg__ if hasattr(inner_type, "__forward_arg__") else inner_type
                return f"List[{inner_str}]"
            return f"List[{self._get_type_string(inner_type)}]"
        
        # Handle Dict type hints
        if origin is dict:
            key_type, value_type = get_args(field_type)
            value_str = self._get_type_string(value_type)
            return f"Dict[{value_str}]"
        
        # Handle forward references
        if hasattr(field_type, "__forward_arg__"):
            return field_type.__forward_arg__
        
        # Handle Model classes
        if isinstance(field_type, type) and issubclass(field_type, Model):
            # Return the model class name as a custom type
            return field_type.__name__
        
        # Handle primitive types
        type_str = type_map.get(field_type)
        if type_str is None:
            raise ValueError(f"Unsupported type: {field_type}")
        return type_str
    
    def get_type_info(self, type_name: str) -> Optional[Dict]:
        """Get information about a registered custom type"""
        return self._type_registry.get(type_name)

class Field:
    """Field definition with enhanced features"""
    def __init__(
        self,
        type_: Optional[Type] = None,
        *,
        required: bool = True,
        description: Optional[str] = None,
        default: Any = None,
        examples: Optional[List[Any]] = None
    ):
        self.type = type_
        self.required = required
        self.description = description
        self.default = default
        self.examples = examples or []

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