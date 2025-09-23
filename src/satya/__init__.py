# Configuration flag for string representation
from typing import Any, Dict, Literal, Optional, Type, Union, Iterator, List, TypeVar, Generic, get_args, get_origin, ClassVar, Pattern, Set
from dataclasses import dataclass
from itertools import islice
from .json_loader import load_json  # Import the new JSON loader
import json
import copy
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
        # Start by inheriting fields from base classes (shallow copy)
        fields = {}
        for base in bases:
            base_fields = getattr(base, '__fields__', None)
            if isinstance(base_fields, dict):
                fields.update(base_fields)
        annotations = namespace.get('__annotations__', {})
        
        # Get fields from type annotations and Field definitions
        for field_name, field_type in annotations.items():
            if field_name.startswith('_'):
                continue
            
            field_def = namespace.get(field_name, Field())
            if not isinstance(field_def, Field):
                # If a default value is provided directly on the class, wrap it in Field(default=...)
                field_def = Field(default=field_def)
                
            if field_def.type is None:
                field_def.type = field_type
            
            # If the annotation is Optional[T], mark field as not required by default
            origin = get_origin(field_def.type)
            args = get_args(field_def.type) if origin is not None else ()
            if origin is Union and type(None) in args:
                field_def.required = False
            
            # If a default value is present (including default=None), the field is not required
            if getattr(field_def, 'default', None) is not None or (field_name in namespace and not isinstance(namespace.get(field_name), Field)):
                field_def.required = False
                
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
        
        # Preprocess data to handle Dict[str, Model] fields
        validation_data = {}
        for name, field in self.__fields__.items():
            if name in data:
                field_type = field.type
                # For Dict[str, Model] fields, skip from validator data
                # Validation happens during model construction
                if get_origin(field_type) == dict:
                    key_type, value_type = get_args(field_type)
                    if isinstance(value_type, type) and issubclass(value_type, Model):
                        continue  # Skip this field from validator
                validation_data[name] = data[name]
        
        # Validate input using cached validator (only non-Dict[str, Model] fields)
        if validation_data:
            validator = self.__class__.validator()
            result = validator.validate(validation_data)
            if not result.is_valid:
                raise ModelValidationError(result.errors)

        normalized = data.copy()  # Use original data for construction

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
        # Set known fields from normalized data (falls back to default),
        # instantiate nested models, and avoid sharing mutable defaults
        for name, field in self.__fields__.items():
            # choose value: provided or default
            if name in normalized:
                value = normalized[name]
            else:
                default_val = getattr(field, 'default', None)
                # deep-copy mutable defaults to avoid shared state
                if isinstance(default_val, (list, dict)):
                    value = copy.deepcopy(default_val)
                else:
                    value = default_val

            # Convert nested dicts/lists into Model instances when annotated
            tp = field.type
            # Unwrap Optional[T]
            origin = get_origin(tp)
            args = get_args(tp) if origin is not None else ()
            if origin is Union and type(None) in args:
                non_none = [a for a in args if a is not type(None)]
                tp_unwrapped = non_none[0] if non_none else tp
            else:
                tp_unwrapped = tp

            origin2 = get_origin(tp_unwrapped)
            args2 = get_args(tp_unwrapped) if origin2 is not None else ()
            # Direct nested Model
            if isinstance(tp_unwrapped, type) and issubclass(tp_unwrapped, Model):
                if isinstance(value, dict):
                    value = tp_unwrapped(**value)  # Let nested validation raise if invalid
            # List[Model]
            elif origin2 is list and args2:
                inner = args2[0]
                if isinstance(inner, type) and issubclass(inner, Model) and isinstance(value, list):
                    value = [inner(**v) if isinstance(v, dict) else v for v in value]
            # Dict[str, Model] - NEW: Support for dictionary of models
            elif origin2 is dict and len(args2) >= 2:
                key_type, value_type = args2[0], args2[1]
                if (isinstance(value_type, type) and issubclass(value_type, Model) 
                    and isinstance(value, dict)):
                    # Validate each value in the dictionary is a valid model instance
                    validated_dict = {}
                    for k, v in value.items():
                        if isinstance(v, dict):
                            validated_dict[k] = value_type(**v)
                        else:
                            validated_dict[k] = v
                    value = validated_dict

            self._data[name] = value
            setattr(self, name, value)

        # Optionally keep extras
        if extra_mode == 'allow':
            for k in extra_keys:
                self._data[k] = data[k]
                setattr(self, k, data[k])

        # Additional Python-side constraint enforcement to complement the core:
        # - floats with gt/lt (core int slots only)
        # - whitespace-only strings against min_length
        # - simple URL (http/https) and email checks
        errors: List[ValidationError] = []
        for fname, field in self.__fields__.items():
            val = getattr(self, fname, None)
            # Skip absent optionals
            if val is None:
                continue

            tp = field.type
            try:
                # String constraints
                if isinstance(val, str):
                    s_trim = val.strip()
                    if field.min_length is not None and len(s_trim) < field.min_length:
                        errors.append(ValidationError(field=fname, message=f"String shorter than min_length={field.min_length}", path=[fname]))
                    if field.max_length is not None and len(val) > field.max_length:
                        errors.append(ValidationError(field=fname, message=f"String longer than max_length={field.max_length}", path=[fname]))
                    if field.pattern and not re.match(field.pattern, val):
                        errors.append(ValidationError(field=fname, message=f"String does not match pattern: {field.pattern}", path=[fname]))
                    if field.email:
                        email_pat = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                        if not re.match(email_pat, val):
                            errors.append(ValidationError(field=fname, message="Invalid email format", path=[fname]))
                    if field.url:
                        # Require protocol and a hostname (simple but stricter)
                        if not re.match(r"^https?://[A-Za-z0-9.-]+(?::\d+)?(?:/[^\s]*)?$", val):
                            errors.append(ValidationError(field=fname, message="Invalid URL format", path=[fname]))

                # Integer constraints
                if isinstance(val, int) and not isinstance(val, bool):
                    if field.ge is not None and val < field.ge:
                        errors.append(ValidationError(field=fname, message=f"Value must be >= {field.ge}", path=[fname]))
                    if field.le is not None and val > field.le:
                        errors.append(ValidationError(field=fname, message=f"Value must be <= {field.le}", path=[fname]))
                    if field.gt is not None and val <= field.gt:
                        errors.append(ValidationError(field=fname, message=f"Value must be > {field.gt}", path=[fname]))
                    if field.lt is not None and val >= field.lt:
                        errors.append(ValidationError(field=fname, message=f"Value must be < {field.lt}", path=[fname]))

                # Float constraints
                if isinstance(val, float):
                    if field.min_value is not None and val < field.min_value:
                        errors.append(ValidationError(field=fname, message=f"Value must be >= {field.min_value}", path=[fname]))
                    if field.max_value is not None and val > field.max_value:
                        errors.append(ValidationError(field=fname, message=f"Value must be <= {field.max_value}", path=[fname]))
                    for op_name, thr, cmp in (
                        ("ge", field.ge, lambda a, b: a < float(b) if b is not None else False),
                        ("le", field.le, lambda a, b: a > float(b) if b is not None else False),
                        ("gt", field.gt, lambda a, b: a <= float(b) if b is not None else False),
                        ("lt", field.lt, lambda a, b: a >= float(b) if b is not None else False),
                    ):
                        if thr is not None and cmp(val, thr):
                            op_txt = ">=" if op_name == "ge" else "<=" if op_name == "le" else ">" if op_name == "gt" else "<"
                            errors.append(ValidationError(field=fname, message=f"Value must be {op_txt} {thr}", path=[fname]))

                # List constraints
                if isinstance(val, list):
                    if field.min_items is not None and len(val) < field.min_items:
                        errors.append(ValidationError(field=fname, message=f"Array must have at least {field.min_items} items", path=[fname]))
                    if field.max_items is not None and len(val) > field.max_items:
                        errors.append(ValidationError(field=fname, message=f"Array must have at most {field.max_items} items", path=[fname]))
                    if field.unique_items:
                        if len(set(val)) != len(val):
                            errors.append(ValidationError(field=fname, message="Array items must be unique", path=[fname]))

                # Enum constraints propagated via Field(enum=...)
                if getattr(field, 'enum', None) and isinstance(val, str):
                    if val not in field.enum:
                        errors.append(ValidationError(field=fname, message=f"Value not in enum: {field.enum}", path=[fname]))
            except Exception:
                # Best-effort enforcement only
                pass

        if errors:
            raise ModelValidationError(errors)
        
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
        return cls.json_schema()
        
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
        def _dump_val(v):
            if isinstance(v, Model):
                return v.model_dump(exclude_none=exclude_none)
            if isinstance(v, list):
                return [_dump_val(x) for x in v]
            return v
        d = {k: _dump_val(v) for k, v in self._data.items()}
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
    def parse_raw(cls, data: str) -> 'Model':
        """Compatibility alias for Pydantic v1-style API."""
        return cls.model_validate_json(data)

    @classmethod
    def parse_obj(cls, obj: Dict[str, Any]) -> 'Model':
        """Compatibility alias for Pydantic v1-style API."""
        return cls.model_validate(obj)

    @classmethod
    def model_validate_nested(cls, data: Dict[str, Any]) -> 'Model':
        """Validate model with enhanced support for nested Dict[str, CustomModel] patterns.
        
        This method provides better validation for complex nested structures like MAP-Elites
        archives where you have Dict[str, ArchiveEntry] patterns.
        """
        registry = ModelRegistry()
        result = registry.validate_with_dependencies(cls, data)
        if not result.is_valid:
            raise ModelValidationError(result.errors)
        return result.value

    @classmethod
    def model_construct(cls, **data: Any) -> 'Model':
        """Construct a model instance without validation (Pydantic-like)."""
        self = object.__new__(cls)
        self._errors = []
        config = getattr(cls, 'model_config', {}) or {}
        extra_mode = config.get('extra', 'ignore')
        self._data = {}
        # Set known fields from normalized data (falls back to default)
        for name, field in self.__fields__.items():
            value = data.get(name, field.default)
            # Construct nested Model instances where applicable
            ftype = field.type
            try:
                # Handle Optional[T]
                if get_origin(ftype) is Union and type(None) in get_args(ftype):
                    inner = [a for a in get_args(ftype) if a is not type(None)][0]
                else:
                    inner = ftype
                # Nested Model
                if isinstance(inner, type) and issubclass(inner, Model) and isinstance(value, dict):
                    value = inner(**value)
                # List[Model]
                if get_origin(inner) is list:
                    inner_arg = get_args(inner)[0] if get_args(inner) else Any
                    if isinstance(inner_arg, type) and issubclass(inner_arg, Model) and isinstance(value, list):
                        value = [inner_arg(**v) if isinstance(v, dict) else v for v in value]
            except Exception:
                # Best-effort construction; leave value as-is on failure
                pass
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
            # Only mark as required if field has no default and is not Optional
            origin = get_origin(field.type)
            args = get_args(field.type) if origin is not None else ()
            is_optional = origin is Union and type(None) in args
            has_default = field.default is not None
            if field.required and not has_default and not is_optional:
                required.append(field_name)

        schema = {
            "type": "object",
            "title": cls.__name__,
            "properties": properties,
        }
        
        if required:
            schema["required"] = required

        # Map model_config.extra to JSON Schema additionalProperties
        config = getattr(cls, 'model_config', {}) or {}
        extra_mode = config.get('extra', 'ignore')
        if extra_mode == 'forbid':
            schema["additionalProperties"] = False
        elif extra_mode == 'allow':
            schema["additionalProperties"] = True
        else:
            schema["additionalProperties"] = False  # Default for OpenAI compatibility

        return schema

    @classmethod
    def model_json_schema(cls) -> Dict[str, Any]:
        """
        Generate JSON schema compatible with OpenAI API.

        This method fixes issues in the raw schema() output to ensure
        compatibility with OpenAI's structured output requirements.

        Returns:
            Dict containing the fixed JSON schema
        """
        raw_schema = cls.json_schema()
        return cls._fix_schema_for_openai(raw_schema)

    @staticmethod
    def _fix_schema_for_openai(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Fix schema issues for OpenAI compatibility"""
        if not isinstance(schema, dict):
            return schema

        fixed_schema = {}
        for key, value in schema.items():
            if key == "properties" and isinstance(value, dict):
                # Fix the properties section
                fixed_properties = {}
                for prop_name, prop_def in value.items():
                    if isinstance(prop_def, dict) and "type" in prop_def:
                        fixed_prop = prop_def.copy()
                        # Fix nested type objects: {"type": {"type": "string"}} -> {"type": "string"}
                        if isinstance(prop_def["type"], dict) and "type" in prop_def["type"]:
                            fixed_prop["type"] = prop_def["type"]["type"]
                        fixed_properties[prop_name] = fixed_prop
                    else:
                        fixed_properties[prop_name] = prop_def
                fixed_schema[key] = fixed_properties
            elif key == "required" and isinstance(value, list):
                # Fix required: remove fields that are nullable (Optional)
                fixed_required = []
                properties = fixed_schema.get("properties", schema.get("properties", {}))
                for req_field in value:
                    prop_def = properties.get(req_field, {})
                    if not (isinstance(prop_def, dict) and prop_def.get("nullable")):
                        fixed_required.append(req_field)
                fixed_schema[key] = fixed_required
            elif key in ["type", "title", "additionalProperties"]:
                # Keep essential schema fields
                fixed_schema[key] = value
            # Skip other fields that might cause issues

        # Ensure additionalProperties is False for strict schemas
        fixed_schema["additionalProperties"] = False

        return fixed_schema

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
    # Propagate explicit enum constraints from Field(enum=...)
    if getattr(field, 'enum', None):
        schema["enum"] = field.enum
    
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

class ModelRegistry:
    """Enhanced registry for tracking model dependencies and relationships"""
    
    def __init__(self):
        self._models: Dict[str, Type[Model]] = {}
        self._dependencies: Dict[str, Set[str]] = {}
        self._resolution_order: Dict[str, int] = {}
        
    def register_model(self, model_class: Type[Model]) -> None:
        """Register a model and analyze its dependencies"""
        model_name = model_class.__name__
        if model_name in self._models:
            return  # Already registered
            
        self._models[model_name] = model_class
        self._dependencies[model_name] = self._analyze_dependencies(model_class)
        
    def _analyze_dependencies(self, model_class: Type[Model]) -> Set[str]:
        """Analyze all nested model dependencies for a given model class"""
        dependencies = set()
        
        for field in model_class.__fields__.values():
            field_type = field.type
            
            # Handle Dict[str, CustomModel] patterns
            if get_origin(field_type) == dict:
                key_type, value_type = get_args(field_type)
                if self._is_model_class(value_type):
                    dependencies.add(value_type.__name__)
                    # Recursively analyze nested dependencies
                    dependencies.update(self._analyze_dependencies(value_type))
                    
            # Handle List[CustomModel] patterns
            elif get_origin(field_type) == list:
                item_type = get_args(field_type)[0]
                if self._is_model_class(item_type):
                    dependencies.add(item_type.__name__)
                    dependencies.update(self._analyze_dependencies(item_type))
                    
            # Handle direct Model references
            elif self._is_model_class(field_type):
                dependencies.add(field_type.__name__)
                dependencies.update(self._analyze_dependencies(field_type))
                
        return dependencies
        
    def _is_model_class(self, type_: Any) -> bool:
        """Check if a type is a Model subclass"""
        try:
            return isinstance(type_, type) and issubclass(type_, Model)
        except TypeError:
            return False
            
    def get_resolution_order(self, model_class: Type[Model]) -> List[Type[Model]]:
        """Get the order in which models should be validated (topological sort)"""
        model_name = model_class.__name__
        
        # Ensure all dependencies are registered
        for dep_name in self._dependencies.get(model_name, set()):
            if dep_name in self._models:
                self.get_resolution_order(self._models[dep_name])
                
        # Perform topological sort
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(name: str):
            if name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {name}")
            if name in visited:
                return
                
            temp_visited.add(name)
            
            # Visit dependencies first
            for dep in self._dependencies.get(name, set()):
                if dep in self._models:
                    visit(dep)
                    
            temp_visited.remove(name)
            visited.add(name)
            order.append(self._models[name])
            
        visit(model_name)
        return order
        
    def validate_with_dependencies(self, model_class: Type[Model], data: Dict[str, Any]) -> ValidationResult:
        """Validate a model and all its dependencies in the correct order"""
        try:
            # Register the model and get validation order
            self.register_model(model_class)
            validation_order = self.get_resolution_order(model_class)
            
            # Validate dependencies first, then the main model
            validated_instances = {}
            
            for model_cls in reversed(validation_order):  # Dependencies first
                model_name = model_cls.__name__
                
                if model_cls == model_class:
                    # This is the main model we're validating
                    instance = model_cls(**data)
                    validated_instances[model_name] = instance
                else:
                    # This is a dependency that should already be validated
                    # through nested validation in the main model
                    pass
                    
            # Return the main model instance
            return ValidationResult(value=validated_instances[model_class.__name__])
            
        except ModelValidationError as e:
            return ValidationResult(errors=e.errors)
        except Exception as e:
            return ValidationResult(errors=[
                ValidationError(field="root", message=f"Validation failed: {str(e)}", path=[])
            ])

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
        # Handle Dict[str, Model] case - NEW
        elif get_origin(field_type) is dict:
            value_type = get_args(field_type)[1]
            if isinstance(value_type, type) and issubclass(value_type, Model):
                _register_model(validator, value_type, path + [model.__name__])
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
            field_type = field.type
            
            # Special handling for Dict[str, Model] patterns
            if get_origin(field_type) == dict:
                key_type, value_type = get_args(field_type)
                if isinstance(value_type, type) and issubclass(value_type, Model):
                    # For Dict[str, Model] fields, skip validator registration
                    # Validation happens entirely in Python during model construction
                    continue
                    
            validator.add_field(name, field_type, required=field.required)
            # Propagate constraints to the core
            enum_values = None
            # Only apply enum for string fields for now (core enum compares strings)
            type_name = getattr(field.type, '__name__', str(field.type))
            if field.enum and type_name == 'str':
                enum_values = [str(v) for v in field.enum]

            # Prepare constraints safely for the core (avoid passing float to int-only slots)
            ge_val = field.ge
            le_val = field.le
            gt_val = field.gt
            lt_val = field.lt
            min_val = field.min_value
            max_val = field.max_value

            if type_name == 'float':
                # Route inclusive bounds through min_value/max_value, skip int-only exclusive slots
                if ge_val is not None:
                    min_val = float(ge_val) if min_val is None else max(float(ge_val), float(min_val))
                    ge_val = None
                if le_val is not None:
                    max_val = float(le_val) if max_val is None else min(float(le_val), float(max_val))
                    le_val = None
                # Skip gt/lt for core; enforce in Python layer
                gt_val = None
                lt_val = None

            # Build constraints and filter to parameters supported by validator.set_constraints
            _kwargs = {
                'min_length': field.min_length,
                'max_length': field.max_length,
                'min_value': min_val,
                'max_value': max_val,
                'pattern': field.pattern,
                'email': field.email,
                'url': field.url,
                'ge': ge_val,
                'le': le_val,
                'gt': gt_val,
                'lt': lt_val,
                'min_items': field.min_items,
                'max_items': field.max_items,
                'unique_items': field.unique_items,
                'enum_values': enum_values,
            }
            try:
                import inspect
                sig = inspect.signature(validator.set_constraints)
                allowed = set(sig.parameters.keys())
            except Exception:
                allowed = set(_kwargs.keys())
            filtered = {k: v for k, v in _kwargs.items() if k in allowed}
            validator.set_constraints(name, **filtered)

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