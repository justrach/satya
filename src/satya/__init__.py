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
    __slots__ = ('_raw', '_errors_cache')

    def __init__(self, errors):
        self._raw = errors
        self._errors_cache = None
        Exception.__init__(self)

    @property
    def errors(self):
        if self._errors_cache is None:
            raw = self._raw
            if raw and isinstance(raw[0], tuple):
                self._errors_cache = [
                    ValidationError(field=t[0], message=t[1], path=[t[0]]) for t in raw
                ]
            else:
                self._errors_cache = raw
        return self._errors_cache

    def __str__(self):
        raw = self._raw
        if raw and isinstance(raw[0], tuple):
            return "; ".join(f"{t[0]}: {t[1]}" for t in raw)
        return "; ".join(f"{e.field}: {e.message}" for e in raw)


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

def _fast_construct_nested(ftype, val):
    """Fast inline constructor for nested models (avoids classmethod dispatch)."""
    ni = object.__new__(ftype)
    nested = ftype.__nested_fields__
    if nested:
        for name, sftype in nested.items():
            sv = val.get(name)
            if isinstance(sv, dict):
                val[name] = _fast_construct_nested(sftype, sv)
        list_models = ftype.__list_model_fields__
        if list_models:
            for name, item_type in list_models.items():
                sv = val.get(name)
                if isinstance(sv, list):
                    val[name] = [
                        _fast_construct_nested(item_type, item) if isinstance(item, dict) else item
                        for item in sv
                    ]
    ni.__dict__.update(val)
    return ni

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

        # Detect if Turbo fast-path is usable
        # Now supports: nested Models (Rust handles them), default_factory (Rust applies defaults)
        # Still disabled for: Decimal fields, custom validators, List[Model], Dict[str, Model]
        from decimal import Decimal as _Decimal
        _has_decimal = False
        _has_list_model = False
        for _f in fields.values():
            ft = _f.type
            # Unwrap Optional[T]
            _ft_origin = get_origin(ft)
            if _ft_origin is Union:
                _ft_args = get_args(ft)
                _non_none = [a for a in _ft_args if a is not type(None)]
                if _non_none:
                    ft = _non_none[0]
                    _ft_origin = get_origin(ft)
            # Check for Decimal
            if ft is _Decimal:
                _has_decimal = True
            # Check for List[Model] or Dict[str, Model] (not yet handled in Rust)
            if _ft_origin is list:
                _inner_args = get_args(ft) if _ft_origin else ()
                if _inner_args and isinstance(_inner_args[0], type) and issubclass(_inner_args[0], Model):
                    _has_list_model = True
            elif _ft_origin is dict:
                _inner_args = get_args(ft) if _ft_origin else ()
                if len(_inner_args) >= 2 and isinstance(_inner_args[1], type) and issubclass(_inner_args[1], Model):
                    _has_list_model = True
        namespace['__turbo_fast_path__'] = not _has_decimal and not _has_list_model and not has_validators
        namespace['__turbo__'] = None  # Cached turbo validator reference
        namespace['__nested_fields__'] = None  # Nested Model field map {name: ModelType}
        namespace['__list_model_fields__'] = None  # List[Model] field map {name: ItemModelType}
        namespace['__field_names_list__'] = list(fields.keys())  # Cached for Rust calls

        # Detect if any field has a default value (for skipping defaults loop)
        _has_any_default = any(
            f.default is not None or f.default_factory is not None
            for f in fields.values()
        )
        namespace['__has_defaults__'] = _has_any_default
        
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
                return hash(tuple(self._ensure_data().items()))
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

        cls = super().__new__(mcs, name, bases, namespace)

        # Python 3.14+ (PEP 649): annotations are deferred until after type.__new__()
        # If no annotations were found in namespace, access cls.__annotations__
        # which triggers lazy evaluation of deferred annotations
        if not annotations and name != 'Model':
            try:
                deferred_annotations = cls.__annotations__
            except Exception:
                deferred_annotations = {}
            if deferred_annotations:
                # Process fields from deferred annotations
                for field_name, field_type in deferred_annotations.items():
                    if field_name.startswith('_'):
                        continue
                    # Check for Field definition as class attribute
                    field_def = cls.__dict__.get(field_name)
                    if field_def is None:
                        field_def = Field()
                    elif not isinstance(field_def, Field):
                        field_def = Field(default=field_def)
                    if field_def.type is ...:
                        field_def.type = None
                        field_def.required = True
                    if field_def.type is None:
                        field_def.type = field_type
                    origin = get_origin(field_def.type)
                    args = get_args(field_def.type) if origin is not None else ()
                    if origin is Union and type(None) in args:
                        field_def.required = False
                    if (getattr(field_def, 'default', None) is not None or
                            getattr(field_def, 'default_factory', None) is not None):
                        field_def.required = False
                    fields[field_name] = field_def
                    # Remove Field objects from class to prevent shadowing
                    if field_name in cls.__dict__ and isinstance(cls.__dict__[field_name], Field):
                        try:
                            delattr(cls, field_name)
                        except (AttributeError, TypeError):
                            pass

                # Update class attributes with processed fields
                cls.__fields__ = fields
                cls.__field_names_list__ = list(fields.keys())
                cls.__is_simple_model__ = not has_validators and all(
                    not (f.min_length or f.max_length or f.pattern or f.email or f.url or
                         f.ge is not None or f.le is not None or f.gt is not None or f.lt is not None or
                         f.min_value is not None or f.max_value is not None or f.multiple_of is not None or
                         f.max_digits is not None or f.decimal_places is not None or
                         f.min_items is not None or f.max_items is not None or f.unique_items or
                         f.enum or f.strip_whitespace or f.to_lower or f.to_upper)
                    for f in fields.values()
                )
                # Recompute turbo fast path
                from decimal import Decimal as _Decimal
                _has_decimal = any(
                    _f.type is _Decimal for _f in fields.values()
                )
                _has_list_model = False
                for _f in fields.values():
                    ft = _f.type
                    _ft_origin = get_origin(ft)
                    if _ft_origin is Union:
                        _ft_args = get_args(ft)
                        _non_none = [a for a in _ft_args if a is not type(None)]
                        if _non_none:
                            ft = _non_none[0]
                            _ft_origin = get_origin(ft)
                    if _ft_origin is list:
                        _inner_args = get_args(ft) if _ft_origin else ()
                        if _inner_args and isinstance(_inner_args[0], type) and issubclass(_inner_args[0], Model):
                            _has_list_model = True
                    elif _ft_origin is dict:
                        _inner_args = get_args(ft) if _ft_origin else ()
                        if len(_inner_args) >= 2 and isinstance(_inner_args[1], type) and issubclass(_inner_args[1], Model):
                            _has_list_model = True
                cls.__turbo_fast_path__ = not _has_decimal and not _has_list_model and not has_validators
                cls.__has_defaults__ = any(
                    f.default is not None or f.default_factory is not None
                    for f in fields.values()
                )

        return cls

    def __call__(cls, **kwargs):
        """Override instance creation to bypass __init__ for turbo models."""
        turbo = cls.__turbo__
        if turbo is not None:
            instance = cls.__new__(cls)
            nested = cls.__nested_fields__
            if nested and cls.__nested_all_flat__:
                # Fast path: pre-create flat nested instances, Rust writes to their __dict__s
                nested_targets = {}
                for name, ftype in nested.items():
                    ni = object.__new__(ftype)
                    nested_targets[name] = ni.__dict__
                    instance.__dict__[name] = ni
                errs = turbo.validate_into_nested_dicts(kwargs, instance.__dict__, nested_targets)
            else:
                errs = turbo.validate_into_dict_result(kwargs, instance.__dict__)
                if errs is None and nested:
                    for name, ftype in nested.items():
                        val = instance.__dict__.get(name)
                        if isinstance(val, dict):
                            instance.__dict__[name] = _fast_construct_nested(ftype, val)
            if errs is not None:
                raise ModelValidationError(errs)
            return instance
        # First call or non-turbo: initialize validator and retry/fallback
        if hasattr(cls, 'validator'):
            if cls.__satya_validator_core__ is None:
                cls.__satya_validator_core__ = cls.validator()
                turbo = cls.__turbo__
                if turbo is not None:
                    return cls(**kwargs)
        return super().__call__(**kwargs)

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
        __tracebackhide__ = True

        # Get cached validator
        validator = self.__class__.__satya_validator_core__
        if validator is None:
            validator = self.__class__.validator()
            self.__class__.__satya_validator_core__ = validator

        # ═══ TURBO FAST PATH: validate directly into __dict__ (zero intermediate dict!) ═══
        turbo = self.__class__.__turbo__
        if turbo is not None:
            try:
                # Single FFI call: validate + write directly into __dict__!
                turbo.validate_into_dict(data, self.__dict__)
                # Wrap nested dicts as Model instances (no re-validation)
                nested_fields = self.__class__.__nested_fields__
                if nested_fields:
                    for name, ftype in nested_fields.items():
                        val = self.__dict__.get(name)
                        if isinstance(val, dict):
                            self.__dict__[name] = _fast_construct_nested(ftype, val)
                return
            except Exception as e:
                # Rust accumulates errors as newline-separated strings
                err_msg = str(e)
                err_lines = [line.strip() for line in err_msg.split('\n') if line.strip()]
                errors = []
                for line in err_lines:
                    # Extract field name from "Field 'name' ..." or "Required field 'name' ..."
                    field_name = "root"
                    # Strip "ValueError: " prefix if present (from PyO3 exception formatting)
                    msg = line
                    if msg.startswith("ValueError: "):
                        msg = msg[len("ValueError: "):]
                    if "Field '" in msg:
                        try:
                            field_name = msg.split("Field '")[1].split("'")[0]
                        except (IndexError, ValueError):
                            pass
                    errors.append(ValidationError(field=field_name, message=msg, path=[field_name]))
                raise ModelValidationError(errors)

        # ═══ STANDARD PATH: Full validation with nested model support ═══
        # Pre-process: Convert Model instances to dicts for validation
        processed_data = {}
        for key, value in data.items():
            if isinstance(value, Model):
                processed_data[key] = value._ensure_data()
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
                if field.default_factory is not None:
                    validated_dict[name] = field.default_factory()
                elif field.default is not None:
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

        object.__setattr__(self, '_data', validated_dict)
        object.__setattr__(self, '_errors', [])

        # Post-process: Convert nested dicts to Model instances
        for name, field in self.__fields__.items():
            value = validated_dict.get(name)
            if value is None:
                continue

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
                elif origin is list and args:
                    inner_type = args[0]
                    if isinstance(inner_type, type) and issubclass(inner_type, Model) and isinstance(value, list):
                        value = [inner_type(**v) if isinstance(v, dict) else v for v in value]
                        validated_dict[name] = value
                elif origin is dict and len(args) >= 2:
                    value_type = args[1]
                    if isinstance(value_type, type) and issubclass(value_type, Model) and isinstance(value, dict):
                        value = {k: value_type(**v) if isinstance(v, dict) else v for k, v in value.items()}
                        validated_dict[name] = value
            except ModelValidationError:
                raise
            except Exception:
                pass
    
    def __str__(self):
        """String representation of the model"""
        if self.__class__.PRETTY_REPR:
            fields = []
            for name, value in self._ensure_data().items():
                fields.append(f"{name}={repr(value)}")
            return f"{self.__class__.__name__} {' '.join(fields)}"
        return super().__str__()

    def __getattr__(self, name):
        """Handle attribute access — only called for attributes NOT in __dict__."""
        if name in self.__fields__:
            # Field exists but wasn't in __dict__ — check _data (standard path)
            try:
                data = object.__getattribute__(self, '_data')
            except AttributeError:
                data = None
            if data is not None:
                return data.get(name)
            return None  # Optional field with no default, not set
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        """Handle attribute setting with frozen and validate_assignment support"""
        # Allow setting internal attributes
        if name.startswith('_'):
            super().__setattr__(name, value)
            return

        # Check if model is frozen
        config = getattr(self.__class__, 'model_config', {})
        if config.get('frozen', False):
            raise ValueError(f"'{self.__class__.__name__}' is frozen and does not support item assignment")

        # Validate on assignment if enabled
        if config.get('validate_assignment', False) and name in self.__fields__:
            field = self.__fields__[name]
            field_type = field.type
            origin = get_origin(field_type)
            if origin is Union:
                args = get_args(field_type)
                non_none_types = [a for a in args if a is not type(None)]
                if value is not None and non_none_types:
                    expected_type = non_none_types[0]
                    if not isinstance(value, expected_type):
                        raise ValueError(f"Field '{name}' must be of type {expected_type.__name__}")
            elif field_type and not isinstance(value, field_type):
                raise ValueError(f"Field '{name}' must be of type {field_type.__name__}")

        # Update _data if it exists (standard path), otherwise __dict__ handles it
        try:
            data = object.__getattribute__(self, '_data')
            if data is not None:
                data[name] = value
        except AttributeError:
            pass
        # Always update __dict__ for native access
        self.__dict__[name] = value
    
    @classmethod
    def schema(cls) -> Dict:
        """Get JSON Schema representation"""
        return cls.json_schema()
        
    @classmethod
    def validator(cls) -> 'StreamValidator':
        """Create a validator for this model - TURBO OPTIMIZED!

        Uses TurboValidator for 2-3x speedup via bulk extraction architecture:
        - Phase 1: Single-pass dict iteration (minimal FFI crossings)
        - Phase 2: Pure Rust constraint validation (zero FFI)
        - Result stored in Rust-owned Vec (lazy Python conversion)
        """
        if cls._validator_instance is None:
            try:
                from ._satya import TurboValidatorPy
                from .validator import StreamValidator
                from decimal import Decimal

                # Create the TURBO validator (bulk extraction, 2-3x speedup!)
                turbo = TurboValidatorPy()

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

                    # Get the type string - check __satya_type_info__ protocol first
                    type_info = getattr(field_type, '__satya_type_info__', None)
                    if type_info:
                        type_str = type_info.get('base_type', 'any')
                    elif field_type == str:
                        type_str = 'str'
                    elif field_type == int:
                        type_str = 'int'
                    elif field_type == float:
                        type_str = 'float'
                    elif field_type == bool:
                        type_str = 'bool'
                    elif field_type is list or get_origin(field_type) is list:
                        type_str = 'list'
                    elif field_type is dict or get_origin(field_type) is dict:
                        type_str = 'dict'
                    elif field_type is Decimal:
                        type_str = 'decimal'
                    elif isinstance(field_type, type) and issubclass(field_type, int) and not issubclass(field_type, bool):
                        type_str = 'int'
                    elif isinstance(field_type, type) and issubclass(field_type, float):
                        type_str = 'float'
                    elif isinstance(field_type, type) and issubclass(field_type, str):
                        type_str = 'str'
                    else:
                        type_str = 'any'

                    turbo.add_field(field_name, type_str, field.required)

                # Set all constraints (ALL IN RUST NOW!)
                for field_name, field in cls.__fields__.items():
                    # Merge auto-constraints from __satya_type_info__ with Field-level constraints
                    field_type = field.type
                    origin = get_origin(field_type)
                    if origin is Union:
                        args = get_args(field_type)
                        non_none = [a for a in args if a is not type(None)]
                        if non_none:
                            field_type = non_none[0]
                    type_info = getattr(field_type, '__satya_type_info__', None)
                    auto_constraints = type_info.get('constraints', {}) if type_info else {}

                    # Use ge/le if available, otherwise fall back to min_value/max_value, then auto-constraints
                    ge_val = field.ge if field.ge is not None else field.min_value
                    if ge_val is None and 'ge' in auto_constraints:
                        ge_val = auto_constraints['ge']
                    le_val = field.le if field.le is not None else field.max_value
                    if le_val is None and 'le' in auto_constraints:
                        le_val = auto_constraints['le']
                    gt_val = field.gt if field.gt is not None else auto_constraints.get('gt')
                    lt_val = field.lt if field.lt is not None else auto_constraints.get('lt')

                    # String constraints with auto-constraint fallback
                    min_length = field.min_length if field.min_length is not None else auto_constraints.get('min_length')
                    max_length = field.max_length if field.max_length is not None else auto_constraints.get('max_length')
                    pattern = field.pattern if field.pattern is not None else auto_constraints.get('pattern')
                    email = (field.email if hasattr(field, 'email') else False) or auto_constraints.get('email', False)
                    url = (field.url if hasattr(field, 'url') else False) or auto_constraints.get('url', False)

                    turbo.set_constraints(
                        field_name,
                        float(gt_val) if gt_val is not None else None,
                        float(ge_val) if ge_val is not None else None,
                        float(lt_val) if lt_val is not None else None,
                        float(le_val) if le_val is not None else None,
                        min_length,
                        max_length,
                        pattern,
                        email,
                        url,
                        field.enum_values if hasattr(field, 'enum_values') else None,
                        field.min_items,
                        field.max_items,
                        field.unique_items if hasattr(field, 'unique_items') else False,
                    )

                # ═══ Link nested schemas BEFORE compile (so they're in the frozen Arc) ═══
                def _unwrap_optional(ft):
                    origin = get_origin(ft)
                    if origin is Union:
                        args = get_args(ft)
                        non_none = [a for a in args if a is not type(None)]
                        if non_none:
                            return non_none[0]
                    return ft

                nested_fields = {}
                list_model_fields = {}
                for field_name, field in cls.__fields__.items():
                    ft = _unwrap_optional(field.type)
                    if isinstance(ft, type) and issubclass(ft, Model) and ft is not Model:
                        nested_v = ft.validator()
                        nested_turbo = getattr(nested_v, '_turbo_validator', None)
                        if nested_turbo:
                            turbo.set_nested_schema(field_name, nested_turbo)
                            nested_fields[field_name] = ft
                    else:
                        ft_origin = get_origin(ft)
                        if ft_origin is list:
                            ft_args = get_args(ft)
                            if ft_args and isinstance(ft_args[0], type) and issubclass(ft_args[0], Model):
                                ft_args[0].validator()  # Ensure nested model is set up
                                list_model_fields[field_name] = ft_args[0]
                cls.__nested_fields__ = nested_fields
                cls.__list_model_fields__ = list_model_fields
                # Pre-compute: are ALL nested fields flat (no sub-nesting)?
                cls.__nested_all_flat__ = bool(nested_fields) and not list_model_fields and all(
                    not getattr(ft, '__nested_fields__', None) for ft in nested_fields.values()
                )

                # Compile with BLAZE cost-ordering optimizations!
                turbo.compile()

                # ═══ Pass defaults to Rust (eliminates Python defaults loop!) ═══
                for field_name, field in cls.__fields__.items():
                    if field.default is not None:
                        turbo.set_default(field_name, field.default, isinstance(field.default, (list, dict, set)))
                    elif field.default_factory is not None:
                        turbo.set_default(field_name, field.default_factory(), True)

                # Wrap in StreamValidator for compatibility
                validator = StreamValidator()
                _register_model(validator, cls)
                validator._turbo_validator = turbo  # Use the new TURBO validator

                # Cache turbo reference directly on class for fastest access
                if cls.__turbo_fast_path__:
                    cls.__turbo__ = turbo

                cls._validator_instance = validator
            except Exception as e:
                # Fallback to StreamValidator only
                from .validator import StreamValidator
                validator = StreamValidator()
                _register_model(validator, cls)
                cls._validator_instance = validator

        return cls._validator_instance
    
    def _ensure_data(self) -> Dict:
        """Get field data — from __dict__ (turbo fast path) or _data (standard path)."""
        try:
            data = object.__getattribute__(self, '_data')
            if data is not None:
                return data
        except AttributeError:
            pass
        # Turbo fast path: fields are in __dict__ directly
        return {name: self.__dict__.get(name) for name in self.__fields__ if name in self.__dict__}

    def dict(self) -> Dict:
        """Convert to dictionary"""
        return self._ensure_data().copy()

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
    def model_validate_json(cls, json_str: Union[str, bytes]) -> 'Model':
        """Validate JSON string/bytes and return a model instance (raises on error).

        TURBO FAST PATH: Python creates instance, Rust parses JSON + validates + populates __dict__.
        """
        # Ensure validator is initialized (sets up cls.__turbo__)
        if cls.__satya_validator_core__ is None:
            cls.__satya_validator_core__ = cls.validator()
        turbo = cls.__turbo__
        if turbo is not None:
            try:
                json_bytes = json_str.encode() if isinstance(json_str, str) else json_str
                instance = cls.__new__(cls)
                # Single FFI call: JSON parse + validate + write to __dict__
                turbo.validate_json_into_dict(json_bytes, instance.__dict__)
                # Wrap nested dicts as Model instances
                nested_fields = cls.__nested_fields__
                if nested_fields:
                    for name, ftype in nested_fields.items():
                        val = instance.__dict__.get(name)
                        if isinstance(val, dict):
                            instance.__dict__[name] = _fast_construct_nested(ftype, val)
                return instance
            except Exception as e:
                raise ModelValidationError([
                    ValidationError(field="root", message=str(e), path=[])
                ])
        # Standard path
        data = load_json(json_str)
        if not isinstance(data, dict):
            raise ModelValidationError([
                ValidationError(field='root', message='JSON must represent an object', path=['root'])
            ])
        return cls(**data)

    @classmethod
    def _construct_validated(cls, data: dict) -> 'Model':
        """Create a Model instance from a pre-validated dict (no re-validation).

        Used for nested models that have already been validated by Rust.
        """
        instance = cls.__new__(cls)
        nested = cls.__nested_fields__
        list_models = cls.__list_model_fields__
        # FAST PATH: No nested models and no list models → just update __dict__
        if nested is not None and not nested and not list_models:
            instance.__dict__.update(data)
            return instance
        # CACHED PATH: Use pre-computed field info
        if nested is not None:
            for name, ftype in nested.items():
                val = data.get(name)
                if val is not None and isinstance(val, dict):
                    data[name] = ftype._construct_validated(val)
            if list_models:
                for name, item_type in list_models.items():
                    val = data.get(name)
                    if val is not None and isinstance(val, list):
                        data[name] = [
                            item_type._construct_validated(item) if isinstance(item, dict) else item
                            for item in val
                        ]
            instance.__dict__.update(data)
            return instance
        # FULL PATH: __nested_fields__ is None → inspect all fields
        for field_name, field in cls.__fields__.items():
            val = data.get(field_name)
            if val is None:
                continue
            ft = field.type
            origin = get_origin(ft)
            if origin is Union:
                args = get_args(ft)
                non_none = [a for a in args if a is not type(None)]
                if non_none:
                    ft = non_none[0]
                    origin = get_origin(ft)
            if isinstance(ft, type) and issubclass(ft, Model) and ft is not Model:
                if isinstance(val, dict):
                    data[field_name] = ft._construct_validated(val)
            elif origin is list:
                inner_args = get_args(ft) if origin else ()
                if inner_args and isinstance(inner_args[0], type) and issubclass(inner_args[0], Model):
                    if isinstance(val, list):
                        data[field_name] = [
                            inner_args[0]._construct_validated(item) if isinstance(item, dict) else item
                            for item in val
                        ]
            elif origin is dict:
                inner_args = get_args(ft) if origin else ()
                if len(inner_args) >= 2 and isinstance(inner_args[1], type) and issubclass(inner_args[1], Model):
                    if isinstance(val, dict):
                        data[field_name] = {
                            k: inner_args[1]._construct_validated(v) if isinstance(v, dict) else v
                            for k, v in val.items()
                        }
        instance.__dict__.update(data)
        return instance
    
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
        # FAST PATH: No filters → direct dict construction
        cls = self.__class__
        no_filters = (include is None and exclude is None and not by_alias
                      and not exclude_unset and not exclude_defaults and not exclude_none)
        if no_filters:
            # Turbo models use __dict__, standard models use _data
            src = self.__dict__ if cls.__turbo__ else getattr(self, '_data', self.__dict__)
            # ULTRA-FAST: No nested models → skip isinstance checks
            if not cls.__nested_fields__:
                return {name: src[name] for name in cls.__field_names_list__ if name in src}
            # With nested models → need isinstance checks
            d = {}
            for name in cls.__field_names_list__:
                if name in src:
                    v = src[name]
                    if isinstance(v, Model):
                        d[name] = v.model_dump()
                    elif isinstance(v, list):
                        d[name] = [x.model_dump() if isinstance(x, Model) else x for x in v]
                    else:
                        d[name] = v
            return d

        # SLOW PATH: With filters
        def _dump_val(v):
            if isinstance(v, Model):
                return v.model_dump(mode=mode, include=include, exclude=exclude,
                                   by_alias=by_alias, exclude_unset=exclude_unset,
                                   exclude_defaults=exclude_defaults, exclude_none=exclude_none)
            if isinstance(v, list):
                return [_dump_val(x) for x in v]
            return v

        d = {}
        for k, v in self._ensure_data().items():
            if include and k not in include:
                continue
            if exclude and k in exclude:
                continue
            if exclude_unset and k not in self._ensure_data():
                continue
            if exclude_defaults:
                field = self.__fields__.get(k)
                if field and field.default is not None and v == field.default:
                    continue
            if exclude_none and v is None:
                continue
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
        # ULTRA-FAST PATH: No filters, no indent, no nested models → __dict__ → JSON in one Rust call
        cls = self.__class__
        no_filters = (include is None and exclude is None and not by_alias
                      and not exclude_unset and not exclude_defaults and not exclude_none)
        if no_filters and indent is None and not cls.__nested_fields__:
            try:
                from ._satya import TurboValidatorPy
                if cls.__turbo__:
                    # Turbo: __dict__ IS the field data → iterate directly (fastest)
                    return TurboValidatorPy.dict_to_json_direct(self.__dict__)
                else:
                    src = getattr(self, '_data', self.__dict__)
                    return TurboValidatorPy.dict_to_json_fields(src, cls.__field_names_list__)
            except Exception:
                pass
        data = self.model_dump(mode=mode, include=include, exclude=exclude,
                              by_alias=by_alias, exclude_unset=exclude_unset,
                              exclude_defaults=exclude_defaults, exclude_none=exclude_none)
        if indent is None:
            try:
                from ._satya import TurboValidatorPy
                return TurboValidatorPy.dict_to_json(data)
            except Exception:
                pass
        return json.dumps(data, indent=indent)
    
    def model_copy(self, *, update: Optional[Dict[str, Any]] = None, deep: bool = False) -> 'Model':
        """Create a copy of the model, optionally updating fields."""
        src = self._ensure_data()
        if deep:
            data = copy.deepcopy(src)
        else:
            data = src.copy()
        
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
    EmailStr, HttpUrl, AnyUrl, AnyHttpUrl, FileUrl, FtpUrl, WebsocketUrl,
    IPvAnyAddress, IPvAnyInterface, IPvAnyNetwork, NameEmail,
    PostgresDsn, MySQLDsn, RedisDsn, MongoDsn, KafkaDsn,
    PositiveInt, NegativeInt, NonNegativeInt, NonPositiveInt,
    PositiveFloat, NegativeFloat, NonNegativeFloat, NonPositiveFloat, FiniteFloat,
    StrictStr, StrictInt, StrictFloat, StrictBool, StrictBytes,
    conint, confloat, constr, conbytes, conlist, conset, confrozenset, condecimal,
    UUID1, UUID3, UUID4, UUID5,
    FutureDate, PastDate, FutureDatetime, PastDatetime, AwareDatetime, NaiveDatetime,
    ByteSize, Json,
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
    # Special types
    'SecretStr',
    'SecretBytes',
    'FilePath',
    'DirectoryPath',
    'NewPath',
    'EmailStr',
    'HttpUrl',
    'AnyUrl',
    'AnyHttpUrl',
    'FileUrl',
    'FtpUrl',
    'WebsocketUrl',
    'IPvAnyAddress',
    'IPvAnyInterface',
    'IPvAnyNetwork',
    'NameEmail',
    'PostgresDsn',
    'MySQLDsn',
    'RedisDsn',
    'MongoDsn',
    'KafkaDsn',
    'PositiveInt',
    'NegativeInt',
    'NonNegativeInt',
    'NonPositiveInt',
    'PositiveFloat',
    'NegativeFloat',
    'NonNegativeFloat',
    'NonPositiveFloat',
    'FiniteFloat',
    'StrictStr',
    'StrictInt',
    'StrictFloat',
    'StrictBool',
    'StrictBytes',
    'conint',
    'confloat',
    'constr',
    'conbytes',
    'conlist',
    'conset',
    'confrozenset',
    'condecimal',
    'UUID1',
    'UUID3',
    'UUID4',
    'UUID5',
    'FutureDate',
    'PastDate',
    'FutureDatetime',
    'PastDatetime',
    'AwareDatetime',
    'NaiveDatetime',
    'ByteSize',
    'Json',
    # Web framework support (TurboAPI enhancement)
    'web',
    # Performance profiling
    'profiling',
    # Version
    '__version__',
]