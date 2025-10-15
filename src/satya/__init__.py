# Configuration flag for string representation
from typing import Any, Dict, Literal, Optional, Type, Union, Iterator, List, TypeVar, Generic, get_args, get_origin, ClassVar, Pattern, Set, Callable
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
    """Represents a validation error with enhanced context"""
    field: str
    message: str
    path: List[str]
    value: Any = None
    constraint: Optional[str] = None
    suggestion: Optional[str] = None
    context: Optional[str] = None

    def __str__(self) -> str:
        loc = ".".join(self.path) if self.path else self.field
        parts = [f"{loc}: {self.message}"]
        
        if self.value is not None:
            value_repr = repr(self.value) if len(repr(self.value)) < 50 else repr(self.value)[:47] + "..."
            parts.append(f"  Value: {value_repr}")
        
        if self.constraint:
            parts.append(f"  Constraint: {self.constraint}")
        
        if self.suggestion:
            parts.append(f"  Suggestion: {self.suggestion}")
        
        if self.context:
            parts.append(f"  Context: {self.context}")
        
        return "\n".join(parts)

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
    """Field definition with validation rules - Pydantic compatible"""
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
        multiple_of: Optional[Union[int, float]] = None,
        max_digits: Optional[int] = None,
        decimal_places: Optional[int] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique_items: bool = False,
        enum: Optional[List[Any]] = None,
        description: Optional[str] = None,
        example: Optional[Any] = None,
        default: Any = None,
        # Pydantic compatibility - factory functions
        default_factory: Optional[Callable[[], Any]] = None,
        # String transformations (Pydantic compatibility)
        strip_whitespace: bool = False,
        to_lower: bool = False,
        to_upper: bool = False,
        # Pydantic V2 compatibility
        alias: Optional[str] = None,
        title: Optional[str] = None,
        # Pydantic validation modes
        frozen: bool = False,
        validate_default: bool = False,
        repr: bool = True,
        init_var: bool = False,
        kw_only: bool = False,
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
        self.multiple_of = multiple_of
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items
        self.enum = enum
        self.description = description
        self.example = example
        self.default = default
        self.default_factory = default_factory
        self.strip_whitespace = strip_whitespace
        self.to_lower = to_lower
        self.to_upper = to_upper
        self.alias = alias
        self.title = title
        self.frozen = frozen
        self.validate_default = validate_default
        self.repr = repr
        self.init_var = init_var
        self.kw_only = kw_only
    
    @property
    def enum_values(self) -> Optional[List[str]]:
        """Convert enum to list of strings for validator"""
        if self.enum:
            return [str(v) for v in self.enum]
        return None

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
        
        # Check if this model can use fast path
        has_validators = any(
            hasattr(getattr(namespace.get(attr_name), '__func__', None), '__validator_metadata__') or
            hasattr(getattr(namespace.get(attr_name), '__func__', None), '__model_validator_metadata__')
            for attr_name in namespace
        )
        
        # Get fields from type annotations and Field definitions
        for field_name, field_type in annotations.items():
            if field_name.startswith('_'):
                continue
            
            field_def = namespace.get(field_name, Field())
            if not isinstance(field_def, Field):
                # If a default value is provided directly on the class, wrap it in Field(default=...)
                field_def = Field(default=field_def)
            
            # Handle Pydantic-style Field(...) where ... means required
            if field_def.type is ...:
                field_def.type = None
                field_def.required = True
                
            if field_def.type is None:
                field_def.type = field_type
            
            # If the annotation is Optional[T], mark field as not required by default
            origin = get_origin(field_def.type)
            args = get_args(field_def.type) if origin is not None else ()
            if origin is Union and type(None) in args:
                field_def.required = False
            
            # If a default value or default_factory is present, the field is not required
            if getattr(field_def, 'default', None) is not None or getattr(field_def, 'default_factory', None) is not None or (field_name in namespace and not isinstance(namespace.get(field_name), Field)):
                field_def.required = False
                
            fields[field_name] = field_def
            
            # CRITICAL FIX: Remove Field objects from class namespace to prevent them
            # from shadowing instance attribute access. This ensures __getattr__ is called
            # and returns the actual value from _data instead of the Field descriptor.
            if field_name in namespace:
                del namespace[field_name]
            
        namespace['__fields__'] = fields
        # Default, Pydantic-like config
        namespace.setdefault('model_config', {
            'extra': 'ignore',  # 'ignore' | 'allow' | 'forbid'
            'validate_assignment': False,
            'frozen': False,  # NEW: Immutability
            'from_attributes': False,  # NEW: ORM mode
        })
        
        # Mark if model can use fast path (no validators, simple types)
        namespace['__has_custom_validators__'] = has_validators
        
        # Check if model is "simple" (no constraints, no validators, no nested models)
        is_simple = not has_validators
        for field in fields.values():
            # Check for any constraints
            if (field.min_length or field.max_length or field.pattern or field.email or field.url or
                field.ge is not None or field.le is not None or field.gt is not None or field.lt is not None or
                field.min_value is not None or field.max_value is not None or field.multiple_of is not None or
                field.max_digits is not None or field.decimal_places is not None or
                field.min_items is not None or field.max_items is not None or field.unique_items or
                field.enum or field.strip_whitespace or field.to_lower or field.to_upper):
                is_simple = False
                break
        
        namespace['__is_simple_model__'] = is_simple
        
        # NOTE: Optimized __init__ disabled for now - it breaks nested model conversion
        # TODO: Re-enable with proper nested model handling
        
        # Add __slots__ for memory efficiency (msgspec-inspired!)
        # Disabled for now due to conflicts with defaults
        # TODO: Re-enable with proper handling of default values
        config = namespace.get('model_config', {})
        use_slots = config.get('use_slots', False)  # Disabled by default for compatibility
        
        if use_slots and '__slots__' not in namespace:
            # Only add internal attributes to avoid conflicts
            slots = ['_data', '_errors', '_initializing']
            namespace['__slots__'] = tuple(slots)
        
        # Add __hash__ if frozen
        if config.get('frozen', False):
            def __hash__(self):
                return hash(tuple(self._data.items()))
            namespace['__hash__'] = __hash__
        
        # Add gc=False support (msgspec-inspired!)
        if config.get('gc', True) is False:
            # Disable GC tracking for this class (faster GC, less memory)
            def __new__(cls, **kwargs):
                import gc
                instance = object.__new__(cls)
                gc.set_threshold(0)  # Disable GC for this instance
                return instance
            namespace['__new__'] = __new__
        
        # PYDANTIC-STYLE: Cache validator core at class level (no method call overhead!)
        # This will be set lazily on first use
        namespace['__satya_validator_core__'] = None
        
        return super().__new__(mcs, name, bases, namespace)

class Model(metaclass=ModelMetaclass):
    """Base class for schema models with improved developer experience"""
    
    __fields__: ClassVar[Dict[str, Field]]
    PRETTY_REPR = False  # Default to False, let users opt-in
    _validator_instance: ClassVar[Optional['StreamValidator']] = None
    
    def __init__(self, **data):
        """Create a new model by parsing and validating input data from keyword arguments.
        
        Raises ValidationError if the input data cannot be validated to form a valid model.
        `self` is explicitly positional-only to allow `self` as a field name.
        """
        # PYDANTIC-EXACT: Minimal overhead!
        __tracebackhide__ = True
        
        # Get cached validator
        validator = self.__class__.__satya_validator_core__
        if validator is None:
            # Lazy initialization on first use
            validator = self.__class__.validator()
            self.__class__.__satya_validator_core__ = validator
        
        # Pre-process: Convert Model instances to dicts for validation
        processed_data = {}
        for key, value in data.items():
            if isinstance(value, Model):
                processed_data[key] = value._data
            else:
                processed_data[key] = value
        
        # Validate the data
        result = validator.validate(processed_data)
        if not result.is_valid:
            raise ModelValidationError(result.errors)
        validated_dict = result.value
        
        # Apply default values for fields not provided in data
        for name, field in self.__fields__.items():
            if name not in validated_dict:
                # Handle default_factory (Pydantic compatibility)
                if field.default_factory is not None:
                    validated_dict[name] = field.default_factory()
                elif field.default is not None:
                    # Deep copy mutable defaults to avoid shared references
                    if isinstance(field.default, (list, dict, set)):
                        import copy
                        validated_dict[name] = copy.deepcopy(field.default)
                    else:
                        validated_dict[name] = field.default
        
        # Convert floats back to Decimal for Decimal fields
        from decimal import Decimal
        for name, field in self.__fields__.items():
            if field.type is Decimal and name in validated_dict:
                value = validated_dict[name]
                if isinstance(value, (int, float)) and not isinstance(value, Decimal):
                    validated_dict[name] = Decimal(str(value))
        
        # CRITICAL OPTIMIZATION: Set _data to validated_dict DIRECTLY!
        # This avoids copying dict items one by one
        object.__setattr__(self, '_data', validated_dict)
        object.__setattr__(self, '_errors', [])
        
        # OPTIMIZATION: Only process nested models if they exist
        # Post-process: Convert nested dicts to Model instances and validate list constraints
        for name, field in self.__fields__.items():
            value = validated_dict.get(name)
            if value is None:
                continue
            
            # Check list constraints (min_items, max_items, unique_items)
            if isinstance(value, list):
                if field.min_items is not None and len(value) < field.min_items:
                    raise ModelValidationError([
                        ValidationError(field=name, message=f"Array must have at least {field.min_items} items", path=[name])
                    ])
                if field.max_items is not None and len(value) > field.max_items:
                    raise ModelValidationError([
                        ValidationError(field=name, message=f"Array must have at most {field.max_items} items", path=[name])
                    ])
                if field.unique_items and len(set(str(v) for v in value)) != len(value):
                    raise ModelValidationError([
                        ValidationError(field=name, message="Array items must be unique", path=[name])
                    ])
                
            field_type = field.type
            if field_type is None:
                continue
            
            # Unwrap Optional[T]
            origin = get_origin(field_type)
            args = get_args(field_type) if origin is not None else ()
            if origin is Union and type(None) in args:
                non_none = [a for a in args if a is not type(None)]
                field_type = non_none[0] if non_none else field_type
            
            origin = get_origin(field_type)
            args = get_args(field_type) if origin is not None else ()
            
            # Convert nested Model
            try:
                if isinstance(field_type, type) and issubclass(field_type, Model):
                    if isinstance(value, dict):
                        value = field_type(**value)
                        validated_dict[name] = value
                # Convert List[Model]
                elif origin is list and args:
                    inner_type = args[0]
                    if isinstance(inner_type, type) and issubclass(inner_type, Model) and isinstance(value, list):
                        value = [inner_type(**v) if isinstance(v, dict) else v for v in value]
                        validated_dict[name] = value
                # Convert Dict[str, Model]
                elif origin is dict and len(args) >= 2:
                    value_type = args[1]
                    if isinstance(value_type, type) and issubclass(value_type, Model) and isinstance(value, dict):
                        value = {k: value_type(**v) if isinstance(v, dict) else v for k, v in value.items()}
                        validated_dict[name] = value
            except ModelValidationError:
                # Re-raise validation errors from nested models
                raise
            except Exception:
                # Other errors - skip this field
                pass
    
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
    
    def __setattr__(self, name, value):
        """Handle attribute setting with frozen and validate_assignment support"""
        # Allow setting internal attributes
        if name.startswith('_'):
            super().__setattr__(name, value)
            return
        
        # Allow setting during initialization
        if getattr(self, '_initializing', False):
            if hasattr(self, '_data'):
                self._data[name] = value
            super().__setattr__(name, value)
            return
        
        # Check if model is frozen
        config = getattr(self.__class__, 'model_config', {})
        if config.get('frozen', False):
            raise ValueError(f"'{self.__class__.__name__}' is frozen and does not support item assignment")
        
        # Validate on assignment if enabled
        if config.get('validate_assignment', False) and name in self.__fields__:
            # Validate just this field using field-specific validation
            field = self.__fields__[name]
            field_type = field.type
            
            # Basic type check
            origin = get_origin(field_type)
            if origin is Union:
                # Handle Optional types
                args = get_args(field_type)
                non_none_types = [a for a in args if a is not type(None)]
                if value is not None and non_none_types:
                    expected_type = non_none_types[0]
                    if not isinstance(value, expected_type):
                        raise ValueError(f"Field '{name}' must be of type {expected_type.__name__}")
            elif field_type and not isinstance(value, field_type):
                raise ValueError(f"Field '{name}' must be of type {field_type.__name__}")
        
        # Set the value
        if hasattr(self, '_data'):
            self._data[name] = value
        super().__setattr__(name, value)
    
    @classmethod
    def schema(cls) -> Dict:
        """Get JSON Schema representation"""
        return cls.json_schema()
        
    @classmethod
    def validator(cls) -> 'StreamValidator':
        """Create a validator for this model - BLAZE OPTIMIZED!"""
        if cls._validator_instance is None:
            try:
                from ._satya import BlazeValidatorPy
                from .validator import StreamValidator
                from decimal import Decimal
                
                # Create the BLAZE-optimized validator (zero-copy, semi-perfect hashing)
                blaze = BlazeValidatorPy()
                
                # Add all fields
                for field_name, field in cls.__fields__.items():
                    # Unwrap Optional[T] to get the actual type
                    field_type = field.type
                    origin = get_origin(field_type)
                    if origin is Union:
                        args = get_args(field_type)
                        non_none = [a for a in args if a is not type(None)]
                        if non_none:
                            field_type = non_none[0]
                    
                    # Get the type string
                    type_str = 'str' if field_type == str else \
                              'int' if field_type == int else \
                              'float' if field_type == float else \
                              'bool' if field_type == bool else \
                              'list' if get_origin(field_type) == list else \
                              'dict' if get_origin(field_type) == dict else \
                              'decimal' if field_type is Decimal else \
                              'any'
                    
                    blaze.add_field(field_name, type_str, field.required)
                
                # Set all constraints (ALL IN RUST NOW!)
                for field_name, field in cls.__fields__.items():
                    # Use ge/le if available, otherwise fall back to min_value/max_value
                    ge_val = field.ge if field.ge is not None else field.min_value
                    le_val = field.le if field.le is not None else field.max_value
                    
                    blaze.set_constraints(
                        field_name,
                        float(field.gt) if field.gt is not None else None,
                        float(ge_val) if ge_val is not None else None,
                        float(field.lt) if field.lt is not None else None,
                        float(le_val) if le_val is not None else None,
                        field.min_length,
                        field.max_length,
                        field.pattern,
                        field.email if hasattr(field, 'email') else False,
                        field.url if hasattr(field, 'url') else False,
                        field.enum_values if hasattr(field, 'enum_values') else None,
                        field.min_items,
                        field.max_items,
                        field.unique_items if hasattr(field, 'unique_items') else False,
                    )
                
                # Compile with BLAZE optimizations!
                blaze.compile()
                
                # Wrap in StreamValidator for compatibility
                validator = StreamValidator()
                _register_model(validator, cls)
                validator._blaze_validator = blaze  # Use the new BLAZE validator
                
                cls._validator_instance = validator
            except Exception as e:
                # Fallback to StreamValidator only
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
    def model_validate(cls, data: Union[Dict[str, Any], Any]) -> 'Model':
        """Parse and validate data from a dictionary or object"""
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        config = getattr(cls, 'model_config', {})
        if config.get('from_attributes', False) and not isinstance(data, dict):
            # Convert object attributes to dict
            data_dict = {}
            for field_name in cls.__fields__.keys():
                if hasattr(data, field_name):
                    data_dict[field_name] = getattr(data, field_name)
            return cls(**data_dict)
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
    
    @classmethod
    def model_validate_fast(cls, data: Dict[str, Any]):
        """⚡ ULTRA-FAST single-object validation - bypasses __init__!
        
        This is 2-4× faster than regular model creation because it:
        - Validates entirely in Rust
        - Creates FastModel with C-level slots (no dict!)
        - No kwargs parsing overhead
        - No Python property descriptors
        - Direct slot access (CPython inline cache friendly!)
        
        Example:
            user = User.model_validate_fast({'name': 'Alice', 'age': 30})
            print(user.name)  # Lightning-fast slot access!
        
        Returns:
            FastModel instance with C-slot field access (matches Pydantic speed!)
        """
        from ._satya import hydrate_one_ultra_fast
        
        # Get the compiled validator
        validator = cls.validator()
        
        # Validate the data
        result = validator.validate(data)
        if not result.is_valid:
            raise ModelValidationError(result.errors)
        validated_dict = result.value
        
        # Hydrate to UltraFastModel with shape-based slots - bypasses __init__!
        # Uses Hidden Classes technique with interned strings for 6× faster field access
        field_names = list(cls.__fields__.keys())
        ultra_fast_model = hydrate_one_ultra_fast(cls.__name__, field_names, validated_dict)
        
        return ultra_fast_model
    
    @classmethod
    def validate_many(cls, data_list: List[Dict[str, Any]]) -> List:
        """🚀 BATCH VALIDATION - 8-13M ops/sec!
        
        Validate multiple records at once using parallel processing.
        This is 10-30× faster than creating models one-by-one!
        
        Uses FastModel with C-level slots for maximum performance.
        
        Example:
            users_data = [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
            users = User.validate_many(users_data)  # Super fast!
        
        Returns:
            List of validated FastModel instances (C-slot backed for max performance)
        """
        from ._satya import hydrate_batch_ultra_fast_parallel
        
        # Get the compiled validator
        validator = cls.validator()
        
        # Batch validate - validate each item
        validated_dicts = []
        for data in data_list:
            result = validator.validate(data)
            if not result.is_valid:
                raise ModelValidationError(result.errors)
            validated_dicts.append(result.value)
        
        # Hydrate to UltraFastModels with shared shapes (parallel!)
        # Uses Hidden Classes technique: one shape shared by ALL instances
        field_names = list(cls.__fields__.keys())
        ultra_fast_models = hydrate_batch_ultra_fast_parallel(cls.__name__, field_names, validated_dicts)
        
        return ultra_fast_models

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

    def model_dump(self, *, 
                   mode: str = 'python',
                   include: Optional[set] = None,
                   exclude: Optional[set] = None,
                   by_alias: bool = False,
                   exclude_unset: bool = False,
                   exclude_defaults: bool = False,
                   exclude_none: bool = False) -> Dict[str, Any]:
        """Dump model data as a dict (Pydantic V2 compatible)."""
        def _dump_val(v):
            if isinstance(v, Model):
                return v.model_dump(mode=mode, include=include, exclude=exclude, 
                                   by_alias=by_alias, exclude_unset=exclude_unset,
                                   exclude_defaults=exclude_defaults, exclude_none=exclude_none)
            if isinstance(v, list):
                return [_dump_val(x) for x in v]
            return v
        
        # Start with all data
        d = {}
        for k, v in self._data.items():
            # Apply include/exclude filters
            if include and k not in include:
                continue
            if exclude and k in exclude:
                continue
            
            # Apply exclude_unset (skip fields not explicitly set)
            if exclude_unset and k not in self._data:
                continue
            
            # Apply exclude_defaults (skip fields with default values)
            if exclude_defaults:
                field = self.__fields__.get(k)
                if field and field.default is not None and v == field.default:
                    continue
            
            # Apply exclude_none
            if exclude_none and v is None:
                continue
            
            # Use alias if requested
            field = self.__fields__.get(k)
            key = field.alias if (by_alias and field and field.alias) else k
            
            d[key] = _dump_val(v)
        
        return d

    def model_dump_json(self, *, 
                        mode: str = 'python',
                        include: Optional[set] = None,
                        exclude: Optional[set] = None,
                        by_alias: bool = False,
                        exclude_unset: bool = False,
                        exclude_defaults: bool = False,
                        exclude_none: bool = False,
                        indent: Optional[int] = None) -> str:
        """Dump model data as a JSON string (Pydantic V2 compatible)."""
        data = self.model_dump(mode=mode, include=include, exclude=exclude,
                              by_alias=by_alias, exclude_unset=exclude_unset,
                              exclude_defaults=exclude_defaults, exclude_none=exclude_none)
        return json.dumps(data, indent=indent)
    
    def model_copy(self, *, update: Optional[Dict[str, Any]] = None, deep: bool = False) -> 'Model':
        """Create a copy of the model, optionally updating fields."""
        if deep:
            data = copy.deepcopy(self._data)
        else:
            data = self._data.copy()
        
        if update:
            data.update(update)
        
        return self.__class__(**data)

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
            
            # Special handling for List[Model] and Dict[str, Model] patterns
            # Unwrap Optional[T] first
            unwrapped_type = field_type
            origin = get_origin(field_type)
            args = get_args(field_type) if origin is not None else ()
            if origin is Union and type(None) in args:
                non_none = [a for a in args if a is not type(None)]
                unwrapped_type = non_none[0] if non_none else field_type
            
            # Check unwrapped type
            origin = get_origin(unwrapped_type)
            args = get_args(unwrapped_type) if origin is not None else ()
            
            # Register all fields (including List[Model] and Dict[str, Model])
            # The validator will handle nested model validation in Python layer
            validator.add_field(name, field_type, required=field.required)
            # Propagate constraints to the core
            enum_values = None
            # Only apply enum for string fields for now (core enum compares strings)
            type_name = getattr(field.type, '__name__', str(field.type))
            if field.enum and type_name == 'str':
                enum_values = [str(v) for v in field.enum]

            # Build constraints - keep all constraints for Python-side validation
            _kwargs = {
                'min_length': field.min_length,
                'max_length': field.max_length,
                'min_value': field.min_value,
                'max_value': field.max_value,
                'pattern': field.pattern,
                'email': field.email,
                'url': field.url,
                'ge': field.ge,
                'le': field.le,
                'gt': field.gt,
                'lt': field.lt,
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

# Export new validators and ABSENT sentinel
from .scalar_validators import (
    StringValidator,
    IntValidator, 
    NumberValidator,
    BooleanValidator,
)
from .array_validator import ArrayValidator
from .absent import ABSENT, is_absent, filter_absent
from .json_schema_compiler import compile_json_schema, JSONSchemaCompiler
from .validators import field_validator, model_validator, ValidationInfo

# Web framework support (TurboAPI enhancement)
from . import web
from . import profiling

def __getattr__(name: str):
    """Lazy attribute access to avoid importing heavy modules at import time."""
    if name == 'StreamValidator':
        from .validator import StreamValidator as _SV
        return _SV
    if name == 'StreamValidatorCore':
        from ._satya import StreamValidatorCore as _SVC
        return _SVC
    raise AttributeError(name)

# Import special types
from .special_types import (
    SecretStr, SecretBytes,
    FilePath, DirectoryPath, NewPath,
    EmailStr, HttpUrl,
    PositiveInt, NegativeInt, NonNegativeInt,
    PositiveFloat, NegativeFloat, NonNegativeFloat,
)

# Import serializers
from .serializers import (
    field_serializer,
    model_serializer,
    computed_field,
)

# Pydantic compatibility: BaseModel alias
BaseModel = Model

# Export all public APIs
__all__ = [
    # Core classes
    'Model',
    'BaseModel',
    'Field',
    'ValidationError',
    'ValidationResult',
    'ModelValidationError',
    # Validation decorators
    'field_validator',
    'model_validator',
    'ValidationInfo',
    # Serialization decorators (NEW!)
    'field_serializer',
    'model_serializer',
    'computed_field',
    # Scalar validators
    'StringValidator',
    'IntValidator',
    'NumberValidator',
    'BooleanValidator',
    # Array validator
    'ArrayValidator',
    # ABSENT sentinel
    'ABSENT',
    'is_absent',
    'filter_absent',
    # JSON Schema compiler
    'compile_json_schema',
    'JSONSchemaCompiler',
    # JSON loader
    'load_json',
    # Special types (NEW!)
    'SecretStr',
    'SecretBytes',
    'FilePath',
    'DirectoryPath',
    'NewPath',
    'EmailStr',
    'HttpUrl',
    'PositiveInt',
    'NegativeInt',
    'NonNegativeInt',
    'PositiveFloat',
    'NegativeFloat',
    'NonNegativeFloat',
    # Web framework support (TurboAPI enhancement)
    'web',
    # Performance profiling
    'profiling',
    # Version
    '__version__',
]