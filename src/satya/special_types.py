"""
Special Types - Pydantic-compatible special types
=================================================

Implements Pydantic-compatible special types:
- SecretStr, SecretBytes - For sensitive data
- FilePath, DirectoryPath, NewPath - For file system paths
- EmailStr, HttpUrl - Enhanced network types
- PositiveInt, NegativeInt, etc. - Constrained numeric types
"""

from typing import Any, Union
from pathlib import Path
import os


class SecretStr:
    """String type that masks its value in repr/str (Pydantic compatible)"""
    
    def __init__(self, value: str):
        if not isinstance(value, str):
            raise TypeError(f"SecretStr requires a string, got {type(value).__name__}")
        self._value = value
    
    def get_secret_value(self) -> str:
        """Get the actual secret value"""
        return self._value
    
    def __repr__(self) -> str:
        return "SecretStr('**********')"
    
    def __str__(self) -> str:
        return "**********"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, SecretStr):
            return self._value == other._value
        return False
    
    def __hash__(self) -> int:
        return hash(self._value)


class SecretBytes:
    """Bytes type that masks its value in repr/str (Pydantic compatible)"""
    
    def __init__(self, value: bytes):
        if not isinstance(value, bytes):
            raise TypeError(f"SecretBytes requires bytes, got {type(value).__name__}")
        self._value = value
    
    def get_secret_value(self) -> bytes:
        """Get the actual secret value"""
        return self._value
    
    def __repr__(self) -> str:
        return "SecretBytes(b'**********')"
    
    def __str__(self) -> str:
        return "**********"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, SecretBytes):
            return self._value == other._value
        return False
    
    def __hash__(self) -> int:
        return hash(self._value)


class FilePath:
    """Path type that validates the file exists (Pydantic compatible)"""
    
    def __init__(self, value: Union[str, Path]):
        self._path = Path(value)
        if not self._path.exists():
            raise ValueError(f"Path does not exist: {self._path}")
        if not self._path.is_file():
            raise ValueError(f"Path is not a file: {self._path}")
    
    def __str__(self) -> str:
        return str(self._path)
    
    def __repr__(self) -> str:
        return f"FilePath('{self._path}')"
    
    def __fspath__(self) -> str:
        return str(self._path)
    
    @property
    def path(self) -> Path:
        return self._path


class DirectoryPath:
    """Path type that validates the directory exists (Pydantic compatible)"""
    
    def __init__(self, value: Union[str, Path]):
        self._path = Path(value)
        if not self._path.exists():
            raise ValueError(f"Path does not exist: {self._path}")
        if not self._path.is_dir():
            raise ValueError(f"Path is not a directory: {self._path}")
    
    def __str__(self) -> str:
        return str(self._path)
    
    def __repr__(self) -> str:
        return f"DirectoryPath('{self._path}')"
    
    def __fspath__(self) -> str:
        return str(self._path)
    
    @property
    def path(self) -> Path:
        return self._path


class NewPath:
    """Path type that may or may not exist (Pydantic compatible)"""
    
    def __init__(self, value: Union[str, Path]):
        self._path = Path(value)
    
    def __str__(self) -> str:
        return str(self._path)
    
    def __repr__(self) -> str:
        return f"NewPath('{self._path}')"
    
    def __fspath__(self) -> str:
        return str(self._path)
    
    @property
    def path(self) -> Path:
        return self._path


class EmailStr(str):
    """String type with email validation (Pydantic compatible)"""
    
    def __new__(cls, value: str):
        import re
        if not isinstance(value, str):
            raise TypeError(f"EmailStr requires a string, got {type(value).__name__}")
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValueError(f"Invalid email format: {value}")
        
        return str.__new__(cls, value)


class HttpUrl(str):
    """String type with HTTP/HTTPS URL validation (Pydantic compatible)"""
    
    def __new__(cls, value: str):
        import re
        if not isinstance(value, str):
            raise TypeError(f"HttpUrl requires a string, got {type(value).__name__}")
        
        # HTTP/HTTPS URL validation
        url_pattern = r'^https?://[A-Za-z0-9.-]+(?::\d+)?(?:/[^\s]*)?$'
        if not re.match(url_pattern, value):
            raise ValueError(f"Invalid HTTP URL format: {value}")
        
        return str.__new__(cls, value)


# Constrained numeric types (Pydantic compatible)
class PositiveInt(int):
    """Integer that must be positive (> 0)"""
    
    def __new__(cls, value: int):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"PositiveInt requires an int, got {type(value).__name__}")
        if value <= 0:
            raise ValueError(f"PositiveInt must be > 0, got {value}")
        return int.__new__(cls, value)


class NegativeInt(int):
    """Integer that must be negative (< 0)"""
    
    def __new__(cls, value: int):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"NegativeInt requires an int, got {type(value).__name__}")
        if value >= 0:
            raise ValueError(f"NegativeInt must be < 0, got {value}")
        return int.__new__(cls, value)


class NonNegativeInt(int):
    """Integer that must be non-negative (>= 0)"""
    
    def __new__(cls, value: int):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"NonNegativeInt requires an int, got {type(value).__name__}")
        if value < 0:
            raise ValueError(f"NonNegativeInt must be >= 0, got {value}")
        return int.__new__(cls, value)


class PositiveFloat(float):
    """Float that must be positive (> 0)"""
    
    def __new__(cls, value: float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"PositiveFloat requires a number, got {type(value).__name__}")
        value = float(value)
        if value <= 0:
            raise ValueError(f"PositiveFloat must be > 0, got {value}")
        return float.__new__(cls, value)


class NegativeFloat(float):
    """Float that must be negative (< 0)"""
    
    def __new__(cls, value: float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"NegativeFloat requires a number, got {type(value).__name__}")
        value = float(value)
        if value >= 0:
            raise ValueError(f"NegativeFloat must be < 0, got {value}")
        return float.__new__(cls, value)


class NonNegativeFloat(float):
    """Float that must be non-negative (>= 0)"""
    
    def __new__(cls, value: float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"NonNegativeFloat requires a number, got {type(value).__name__}")
        value = float(value)
        if value < 0:
            raise ValueError(f"NonNegativeFloat must be >= 0, got {value}")
        return float.__new__(cls, value)


__all__ = [
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
]
