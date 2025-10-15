"""
Rust-native Model implementation (v2.0)
Seamless integration of Rust backend with Python API
"""

from typing import Any, Dict, Type, get_type_hints
from satya._satya import compile_schema, SatyaModelInstance
from satya import Field, ModelMetaclass  # Import to use existing metaclass


class RustModelMeta(ModelMetaclass):
    """Metaclass that compiles schema and creates Rust-backed models"""
    
    def __new__(mcs, name, bases, namespace):
        # Use parent metaclass to populate __fields__
        cls = super().__new__(mcs, name, bases, namespace)
        
        # Skip for base Model class
        if name == 'RustModel':
            return cls
        
        # Compile schema from the class
        try:
            schema = compile_schema(cls)
            cls._rust_schema = schema
            cls._is_rust_native = True
        except Exception as e:
            # Fallback to regular Python if compilation fails
            print(f"Warning: Failed to compile Rust schema for {name}: {e}")
            cls._is_rust_native = False
        
        return cls


class RustModel(metaclass=RustModelMeta):
    """
    Base class for Rust-native models
    
    Usage:
        class User(RustModel):
            name: str = Field(min_length=2)
            age: int = Field(ge=0)
        
        user = User(name="Alice", age=30)  # Validated in Rust!
        print(user.name)  # Direct field access
        user.age = 31  # Validated in Rust!
    """
    
    __slots__ = ('_rust_instance',)  # Memory optimization
    
    _rust_schema = None
    _is_rust_native = False
    
    def __init__(self, **kwargs):
        """Initialize model with Rust validation (optimized)"""
        # Direct creation - schema is already compiled at class creation time
        # No need to check _is_rust_native every time (it's a class attribute)
        object.__setattr__(self, '_rust_instance', 
                          SatyaModelInstance.from_dict(self._rust_schema, kwargs))
    
    def __getattribute__(self, name: str) -> Any:
        """Get field value from Rust instance (highly optimized)"""
        # Ultra-fast path for internal attributes (single character check)
        if name[0] == '_':
            return object.__getattribute__(self, name)
        
        # Fast path for common methods
        if name == 'dict' or name == 'json':
            return object.__getattribute__(self, name)
        
        # Hot path: direct Rust field access
        # Inline the rust_instance lookup to avoid function call overhead
        try:
            return object.__getattribute__(self, '_rust_instance').get_field(name)
        except (AttributeError, KeyError):
            # Fall back to class attributes (rare)
            return object.__getattribute__(self, name)
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Set field value with Rust validation"""
        if name.startswith('_'):
            # Internal attributes
            object.__setattr__(self, name, value)
            return
        
        if hasattr(self, '_rust_instance'):
            try:
                self._rust_instance.set_field(name, value)
                return
            except AttributeError:
                pass
        
        # Fall back to normal attribute setting
        object.__setattr__(self, name, value)
    
    def dict(self) -> Dict[str, Any]:
        """Convert to Python dict"""
        return self._rust_instance.dict()
    
    def json(self) -> str:
        """Serialize to JSON string"""
        return self._rust_instance.json()
    
    def __repr__(self) -> str:
        """String representation"""
        return self._rust_instance.__repr__()
    
    def __str__(self) -> str:
        """String representation"""
        return self._rust_instance.__str__()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RustModel':
        """Create instance from dict"""
        return cls(**data)
    
    @classmethod
    def validate(cls, data: Dict[str, Any]) -> 'RustModel':
        """Validate and create instance"""
        return cls(**data)


# For backward compatibility, allow importing as Model
Model = RustModel
