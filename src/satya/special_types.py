"""
Special Types - Pydantic-compatible special types
=================================================

Implements Pydantic-compatible special types:
- SecretStr, SecretBytes - For sensitive data
- FilePath, DirectoryPath, NewPath - For file system paths
- EmailStr, HttpUrl - Enhanced network types
- PositiveInt, NegativeInt, etc. - Constrained numeric types
- StrictStr, StrictInt, etc. - Strict (no coercion) types
- conint, confloat, constr, etc. - Constrained type constructors
- UUID1, UUID3, UUID4, UUID5 - UUID version types
- FutureDate, PastDate, etc. - Date/time constraint types
- AnyUrl, IPvAnyAddress, etc. - Network types
- ByteSize, Json - Utility types
"""

from typing import Any, Optional, Union
from pathlib import Path
import os
import math
import re as _re


# ============================================================================
# Secret Types
# ============================================================================

class SecretStr:
    """String type that masks its value in repr/str (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

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
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

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


# ============================================================================
# Path Types
# ============================================================================

class FilePath:
    """Path type that validates the file exists (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

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
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

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
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

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


# ============================================================================
# Network/String Types
# ============================================================================

class EmailStr(str):
    """String type with email validation (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {'email': True}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"EmailStr requires a string, got {type(value).__name__}")
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not _re.match(email_pattern, value):
            raise ValueError(f"Invalid email format: {value}")
        return str.__new__(cls, value)


class HttpUrl(str):
    """String type with HTTP/HTTPS URL validation (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {'url': True}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"HttpUrl requires a string, got {type(value).__name__}")
        url_pattern = r'^https?://[A-Za-z0-9.-]+(?::\d+)?(?:/[^\s]*)?$'
        if not _re.match(url_pattern, value):
            raise ValueError(f"Invalid HTTP URL format: {value}")
        return str.__new__(cls, value)


class AnyUrl(str):
    """URL with any scheme (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"AnyUrl requires a string, got {type(value).__name__}")
        if '://' not in value:
            raise ValueError(f"Invalid URL: missing scheme in {value}")
        return str.__new__(cls, value)


class AnyHttpUrl(str):
    """HTTP or HTTPS URL (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {'url': True}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"AnyHttpUrl requires a string, got {type(value).__name__}")
        if not (value.startswith('http://') or value.startswith('https://')):
            raise ValueError(f"URL must start with http:// or https://, got: {value}")
        return str.__new__(cls, value)


class FileUrl(str):
    """file:// URL (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"FileUrl requires a string, got {type(value).__name__}")
        if not value.startswith('file://'):
            raise ValueError(f"URL must start with file://, got: {value}")
        return str.__new__(cls, value)


class FtpUrl(str):
    """ftp:// URL (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"FtpUrl requires a string, got {type(value).__name__}")
        if not value.startswith('ftp://'):
            raise ValueError(f"URL must start with ftp://, got: {value}")
        return str.__new__(cls, value)


class WebsocketUrl(str):
    """ws:// or wss:// URL (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"WebsocketUrl requires a string, got {type(value).__name__}")
        if not (value.startswith('ws://') or value.startswith('wss://')):
            raise ValueError(f"URL must start with ws:// or wss://, got: {value}")
        return str.__new__(cls, value)


class IPvAnyAddress(str):
    """IPv4 or IPv6 address (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        import ipaddress
        if not isinstance(value, str):
            raise TypeError(f"IPvAnyAddress requires a string, got {type(value).__name__}")
        try:
            ipaddress.ip_address(value)
        except ValueError:
            raise ValueError(f"Invalid IP address: {value}")
        return str.__new__(cls, value)


class IPvAnyInterface(str):
    """IPv4 or IPv6 interface (address/prefix) (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        import ipaddress
        if not isinstance(value, str):
            raise TypeError(f"IPvAnyInterface requires a string, got {type(value).__name__}")
        try:
            ipaddress.ip_interface(value)
        except ValueError:
            raise ValueError(f"Invalid IP interface: {value}")
        return str.__new__(cls, value)


class IPvAnyNetwork(str):
    """IPv4 or IPv6 network (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        import ipaddress
        if not isinstance(value, str):
            raise TypeError(f"IPvAnyNetwork requires a string, got {type(value).__name__}")
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError:
            raise ValueError(f"Invalid IP network: {value}")
        return str.__new__(cls, value)


class NameEmail(str):
    """'Name <email>' or plain email format (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"NameEmail requires a string, got {type(value).__name__}")
        # Try "Name <email>" format
        match = _re.match(r'^(.+)\s+<([^>]+@[^>]+\.[^>]+)>$', value)
        if match:
            return str.__new__(cls, value)
        # Try plain email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if _re.match(email_pattern, value):
            return str.__new__(cls, value)
        raise ValueError(f"Invalid NameEmail format: {value}")


# DSN Types
class PostgresDsn(str):
    """PostgreSQL DSN URL (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"PostgresDsn requires a string, got {type(value).__name__}")
        if not (value.startswith('postgresql://') or value.startswith('postgres://')):
            raise ValueError(f"Invalid PostgreSQL DSN: must start with postgresql:// or postgres://")
        return str.__new__(cls, value)


class MySQLDsn(str):
    """MySQL DSN URL (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"MySQLDsn requires a string, got {type(value).__name__}")
        if not (value.startswith('mysql://') or value.startswith('mysql+pymysql://')):
            raise ValueError(f"Invalid MySQL DSN: must start with mysql://")
        return str.__new__(cls, value)


class RedisDsn(str):
    """Redis DSN URL (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"RedisDsn requires a string, got {type(value).__name__}")
        if not (value.startswith('redis://') or value.startswith('rediss://')):
            raise ValueError(f"Invalid Redis DSN: must start with redis:// or rediss://")
        return str.__new__(cls, value)


class MongoDsn(str):
    """MongoDB DSN URL (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"MongoDsn requires a string, got {type(value).__name__}")
        if not (value.startswith('mongodb://') or value.startswith('mongodb+srv://')):
            raise ValueError(f"Invalid MongoDB DSN: must start with mongodb://")
        return str.__new__(cls, value)


class KafkaDsn(str):
    """Kafka DSN URL (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value: str):
        if not isinstance(value, str):
            raise TypeError(f"KafkaDsn requires a string, got {type(value).__name__}")
        if not value.startswith('kafka://'):
            raise ValueError(f"Invalid Kafka DSN: must start with kafka://")
        return str.__new__(cls, value)


# ============================================================================
# Constrained Numeric Types
# ============================================================================

class PositiveInt(int):
    """Integer that must be positive (> 0)"""
    __satya_type_info__ = {'base_type': 'int', 'constraints': {'gt': 0}}

    def __new__(cls, value: int):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"PositiveInt requires an int, got {type(value).__name__}")
        if value <= 0:
            raise ValueError(f"PositiveInt must be > 0, got {value}")
        return int.__new__(cls, value)


class NegativeInt(int):
    """Integer that must be negative (< 0)"""
    __satya_type_info__ = {'base_type': 'int', 'constraints': {'lt': 0}}

    def __new__(cls, value: int):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"NegativeInt requires an int, got {type(value).__name__}")
        if value >= 0:
            raise ValueError(f"NegativeInt must be < 0, got {value}")
        return int.__new__(cls, value)


class NonNegativeInt(int):
    """Integer that must be non-negative (>= 0)"""
    __satya_type_info__ = {'base_type': 'int', 'constraints': {'ge': 0}}

    def __new__(cls, value: int):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"NonNegativeInt requires an int, got {type(value).__name__}")
        if value < 0:
            raise ValueError(f"NonNegativeInt must be >= 0, got {value}")
        return int.__new__(cls, value)


class NonPositiveInt(int):
    """Integer that must be non-positive (<= 0)"""
    __satya_type_info__ = {'base_type': 'int', 'constraints': {'le': 0}}

    def __new__(cls, value: int):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"NonPositiveInt requires an int, got {type(value).__name__}")
        if value > 0:
            raise ValueError(f"NonPositiveInt must be <= 0, got {value}")
        return int.__new__(cls, value)


class PositiveFloat(float):
    """Float that must be positive (> 0)"""
    __satya_type_info__ = {'base_type': 'float', 'constraints': {'gt': 0.0}}

    def __new__(cls, value: float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"PositiveFloat requires a number, got {type(value).__name__}")
        value = float(value)
        if value <= 0:
            raise ValueError(f"PositiveFloat must be > 0, got {value}")
        return float.__new__(cls, value)


class NegativeFloat(float):
    """Float that must be negative (< 0)"""
    __satya_type_info__ = {'base_type': 'float', 'constraints': {'lt': 0.0}}

    def __new__(cls, value: float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"NegativeFloat requires a number, got {type(value).__name__}")
        value = float(value)
        if value >= 0:
            raise ValueError(f"NegativeFloat must be < 0, got {value}")
        return float.__new__(cls, value)


class NonNegativeFloat(float):
    """Float that must be non-negative (>= 0)"""
    __satya_type_info__ = {'base_type': 'float', 'constraints': {'ge': 0.0}}

    def __new__(cls, value: float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"NonNegativeFloat requires a number, got {type(value).__name__}")
        value = float(value)
        if value < 0:
            raise ValueError(f"NonNegativeFloat must be >= 0, got {value}")
        return float.__new__(cls, value)


class NonPositiveFloat(float):
    """Float that must be non-positive (<= 0)"""
    __satya_type_info__ = {'base_type': 'float', 'constraints': {'le': 0.0}}

    def __new__(cls, value: float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"NonPositiveFloat requires a number, got {type(value).__name__}")
        value = float(value)
        if value > 0:
            raise ValueError(f"NonPositiveFloat must be <= 0, got {value}")
        return float.__new__(cls, value)


class FiniteFloat(float):
    """Float that must be finite (no NaN, no inf)"""
    __satya_type_info__ = {'base_type': 'float', 'constraints': {'finite': True}}

    def __new__(cls, value: float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"FiniteFloat requires a number, got {type(value).__name__}")
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"FiniteFloat must be finite, got {value}")
        return float.__new__(cls, value)


# ============================================================================
# Strict Types (no coercion)
# ============================================================================

class StrictStr(str):
    """String type that does not allow coercion from non-string types."""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}, 'strict': True}

    def __new__(cls, value):
        if not isinstance(value, str):
            raise TypeError(f"StrictStr requires a string, got {type(value).__name__}")
        return str.__new__(cls, value)


class StrictInt(int):
    """Integer type that does not allow coercion from non-int types."""
    __satya_type_info__ = {'base_type': 'int', 'constraints': {}, 'strict': True}

    def __new__(cls, value):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"StrictInt requires an int, got {type(value).__name__}")
        return int.__new__(cls, value)


class StrictFloat(float):
    """Float type that does not allow coercion from non-float types."""
    __satya_type_info__ = {'base_type': 'float', 'constraints': {}, 'strict': True}

    def __new__(cls, value):
        if not isinstance(value, (float, int)) or isinstance(value, bool):
            raise TypeError(f"StrictFloat requires a float, got {type(value).__name__}")
        return float.__new__(cls, float(value))


class StrictBool:
    """Boolean type that does not allow coercion."""
    __satya_type_info__ = {'base_type': 'bool', 'constraints': {}, 'strict': True}

    def __new__(cls, value):
        if not isinstance(value, bool):
            raise TypeError(f"StrictBool requires a bool, got {type(value).__name__}")
        return value


class StrictBytes(bytes):
    """Bytes type that does not allow coercion from non-bytes types."""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}, 'strict': True}

    def __new__(cls, value):
        if not isinstance(value, bytes):
            raise TypeError(f"StrictBytes requires bytes, got {type(value).__name__}")
        return bytes.__new__(cls, value)


# ============================================================================
# Constrained Type Constructors
# ============================================================================

def conint(
    *,
    gt: Optional[int] = None,
    ge: Optional[int] = None,
    lt: Optional[int] = None,
    le: Optional[int] = None,
    multiple_of: Optional[int] = None,
    strict: bool = False,
) -> type:
    """Create a constrained integer type (Pydantic compatible)."""
    constraints = {}
    if gt is not None: constraints['gt'] = gt
    if ge is not None: constraints['ge'] = ge
    if lt is not None: constraints['lt'] = lt
    if le is not None: constraints['le'] = le
    if multiple_of is not None: constraints['multiple_of'] = multiple_of

    class ConstrainedInt(int):
        __satya_type_info__ = {
            'base_type': 'int',
            'constraints': constraints,
            'strict': strict,
        }

        def __new__(cls, value):
            if strict and not isinstance(value, int):
                raise TypeError(f"Expected int, got {type(value).__name__}")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"Expected int, got {type(value).__name__}")
            v = int(value)
            if gt is not None and v <= gt:
                raise ValueError(f"Value must be > {gt}, got {v}")
            if ge is not None and v < ge:
                raise ValueError(f"Value must be >= {ge}, got {v}")
            if lt is not None and v >= lt:
                raise ValueError(f"Value must be < {lt}, got {v}")
            if le is not None and v > le:
                raise ValueError(f"Value must be <= {le}, got {v}")
            if multiple_of is not None and v % multiple_of != 0:
                raise ValueError(f"Value must be multiple of {multiple_of}, got {v}")
            return int.__new__(cls, v)

    ConstrainedInt.__name__ = 'ConstrainedInt'
    ConstrainedInt.__qualname__ = 'ConstrainedInt'
    return ConstrainedInt


def confloat(
    *,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    allow_inf_nan: bool = True,
    strict: bool = False,
) -> type:
    """Create a constrained float type (Pydantic compatible)."""
    constraints = {}
    if gt is not None: constraints['gt'] = gt
    if ge is not None: constraints['ge'] = ge
    if lt is not None: constraints['lt'] = lt
    if le is not None: constraints['le'] = le
    if multiple_of is not None: constraints['multiple_of'] = multiple_of
    if not allow_inf_nan: constraints['finite'] = True

    class ConstrainedFloat(float):
        __satya_type_info__ = {
            'base_type': 'float',
            'constraints': constraints,
            'strict': strict,
        }

        def __new__(cls, value):
            if strict and not isinstance(value, (float, int)):
                raise TypeError(f"Expected float, got {type(value).__name__}")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"Expected float, got {type(value).__name__}")
            v = float(value)
            if not allow_inf_nan and (math.isnan(v) or math.isinf(v)):
                raise ValueError(f"Value must be finite, got {v}")
            if gt is not None and v <= gt:
                raise ValueError(f"Value must be > {gt}, got {v}")
            if ge is not None and v < ge:
                raise ValueError(f"Value must be >= {ge}, got {v}")
            if lt is not None and v >= lt:
                raise ValueError(f"Value must be < {lt}, got {v}")
            if le is not None and v > le:
                raise ValueError(f"Value must be <= {le}, got {v}")
            if multiple_of is not None and v % multiple_of != 0:
                raise ValueError(f"Value must be multiple of {multiple_of}, got {v}")
            return float.__new__(cls, v)

    ConstrainedFloat.__name__ = 'ConstrainedFloat'
    ConstrainedFloat.__qualname__ = 'ConstrainedFloat'
    return ConstrainedFloat


def constr(
    *,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    strip_whitespace: bool = False,
    to_lower: bool = False,
    to_upper: bool = False,
    strict: bool = False,
) -> type:
    """Create a constrained string type (Pydantic compatible)."""
    constraints = {}
    if min_length is not None: constraints['min_length'] = min_length
    if max_length is not None: constraints['max_length'] = max_length
    if pattern is not None: constraints['pattern'] = pattern

    class ConstrainedStr(str):
        __satya_type_info__ = {
            'base_type': 'str',
            'constraints': constraints,
            'strict': strict,
        }

        def __new__(cls, value):
            if strict and not isinstance(value, str):
                raise TypeError(f"Expected str, got {type(value).__name__}")
            if not isinstance(value, str):
                value = str(value)
            if strip_whitespace:
                value = value.strip()
            if to_lower:
                value = value.lower()
            if to_upper:
                value = value.upper()
            if min_length is not None and len(value) < min_length:
                raise ValueError(f"String must have at least {min_length} characters, got {len(value)}")
            if max_length is not None and len(value) > max_length:
                raise ValueError(f"String must have at most {max_length} characters, got {len(value)}")
            if pattern is not None and not _re.match(pattern, value):
                raise ValueError(f"String does not match pattern: {pattern}")
            return str.__new__(cls, value)

    ConstrainedStr.__name__ = 'ConstrainedStr'
    ConstrainedStr.__qualname__ = 'ConstrainedStr'
    return ConstrainedStr


def conbytes(
    *,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    strict: bool = False,
) -> type:
    """Create a constrained bytes type (Pydantic compatible)."""
    constraints = {}
    if min_length is not None: constraints['min_length'] = min_length
    if max_length is not None: constraints['max_length'] = max_length

    class ConstrainedBytes(bytes):
        __satya_type_info__ = {
            'base_type': 'str',
            'constraints': constraints,
            'strict': strict,
        }

        def __new__(cls, value):
            if strict and not isinstance(value, bytes):
                raise TypeError(f"Expected bytes, got {type(value).__name__}")
            if isinstance(value, str):
                value = value.encode('utf-8')
            if not isinstance(value, bytes):
                raise TypeError(f"Expected bytes, got {type(value).__name__}")
            if min_length is not None and len(value) < min_length:
                raise ValueError(f"Bytes must have at least {min_length} bytes, got {len(value)}")
            if max_length is not None and len(value) > max_length:
                raise ValueError(f"Bytes must have at most {max_length} bytes, got {len(value)}")
            return bytes.__new__(cls, value)

    ConstrainedBytes.__name__ = 'ConstrainedBytes'
    ConstrainedBytes.__qualname__ = 'ConstrainedBytes'
    return ConstrainedBytes


def conlist(
    item_type: type = Any,
    *,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> type:
    """Create a constrained list type (Pydantic compatible)."""
    constraints = {}
    if min_length is not None: constraints['min_items'] = min_length
    if max_length is not None: constraints['max_items'] = max_length

    class ConstrainedList(list):
        __satya_type_info__ = {
            'base_type': 'list',
            'constraints': constraints,
        }

        def __new__(cls, value):
            if not isinstance(value, (list, tuple)):
                raise TypeError(f"Expected list, got {type(value).__name__}")
            if min_length is not None and len(value) < min_length:
                raise ValueError(f"List must have at least {min_length} items, got {len(value)}")
            if max_length is not None and len(value) > max_length:
                raise ValueError(f"List must have at most {max_length} items, got {len(value)}")
            return list.__new__(cls)

        def __init__(self, value):
            super().__init__(value)

    ConstrainedList.__name__ = 'ConstrainedList'
    ConstrainedList.__qualname__ = 'ConstrainedList'
    return ConstrainedList


def conset(
    item_type: type = Any,
    *,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> type:
    """Create a constrained set type (Pydantic compatible)."""
    class ConstrainedSet(set):
        __satya_type_info__ = {
            'base_type': 'any',
            'constraints': {},
        }

        def __new__(cls, value):
            if not isinstance(value, (set, frozenset, list, tuple)):
                raise TypeError(f"Expected set, got {type(value).__name__}")
            s = set(value)
            if min_length is not None and len(s) < min_length:
                raise ValueError(f"Set must have at least {min_length} items, got {len(s)}")
            if max_length is not None and len(s) > max_length:
                raise ValueError(f"Set must have at most {max_length} items, got {len(s)}")
            return set.__new__(cls)

        def __init__(self, value):
            super().__init__(set(value) if not isinstance(value, set) else value)

    ConstrainedSet.__name__ = 'ConstrainedSet'
    ConstrainedSet.__qualname__ = 'ConstrainedSet'
    return ConstrainedSet


def confrozenset(
    item_type: type = Any,
    *,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> type:
    """Create a constrained frozenset type (Pydantic compatible)."""
    class ConstrainedFrozenSet(frozenset):
        __satya_type_info__ = {
            'base_type': 'any',
            'constraints': {},
        }

        def __new__(cls, value):
            if not isinstance(value, (set, frozenset, list, tuple)):
                raise TypeError(f"Expected frozenset, got {type(value).__name__}")
            s = frozenset(value)
            if min_length is not None and len(s) < min_length:
                raise ValueError(f"Frozenset must have at least {min_length} items, got {len(s)}")
            if max_length is not None and len(s) > max_length:
                raise ValueError(f"Frozenset must have at most {max_length} items, got {len(s)}")
            return frozenset.__new__(cls, s)

    ConstrainedFrozenSet.__name__ = 'ConstrainedFrozenSet'
    ConstrainedFrozenSet.__qualname__ = 'ConstrainedFrozenSet'
    return ConstrainedFrozenSet


def condecimal(
    *,
    gt: Optional[Any] = None,
    ge: Optional[Any] = None,
    lt: Optional[Any] = None,
    le: Optional[Any] = None,
    max_digits: Optional[int] = None,
    decimal_places: Optional[int] = None,
    multiple_of: Optional[Any] = None,
) -> type:
    """Create a constrained Decimal type (Pydantic compatible)."""
    from decimal import Decimal as _Decimal

    constraints = {}
    if gt is not None: constraints['gt'] = float(gt)
    if ge is not None: constraints['ge'] = float(ge)
    if lt is not None: constraints['lt'] = float(lt)
    if le is not None: constraints['le'] = float(le)

    class ConstrainedDecimal(_Decimal):
        __satya_type_info__ = {
            'base_type': 'decimal',
            'constraints': constraints,
        }

        def __new__(cls, value):
            if not isinstance(value, (_Decimal, int, float, str)):
                raise TypeError(f"Expected Decimal, got {type(value).__name__}")
            v = _Decimal(str(value)) if not isinstance(value, _Decimal) else value
            if gt is not None and v <= _Decimal(str(gt)):
                raise ValueError(f"Value must be > {gt}, got {v}")
            if ge is not None and v < _Decimal(str(ge)):
                raise ValueError(f"Value must be >= {ge}, got {v}")
            if lt is not None and v >= _Decimal(str(lt)):
                raise ValueError(f"Value must be < {lt}, got {v}")
            if le is not None and v > _Decimal(str(le)):
                raise ValueError(f"Value must be <= {le}, got {v}")
            if max_digits is not None:
                digits = len(v.as_tuple().digits)
                if digits > max_digits:
                    raise ValueError(f"Value must have at most {max_digits} digits, got {digits}")
            if decimal_places is not None:
                exp = v.as_tuple().exponent
                places = -exp if isinstance(exp, int) and exp < 0 else 0
                if places > decimal_places:
                    raise ValueError(f"Value must have at most {decimal_places} decimal places, got {places}")
            return _Decimal.__new__(cls, str(v))

    ConstrainedDecimal.__name__ = 'ConstrainedDecimal'
    ConstrainedDecimal.__qualname__ = 'ConstrainedDecimal'
    return ConstrainedDecimal


# ============================================================================
# UUID Types
# ============================================================================

class UUID1(str):
    """UUID version 1 (time-based)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value):
        import uuid as _uuid
        if isinstance(value, _uuid.UUID):
            if value.version != 1:
                raise ValueError(f"UUID must be version 1, got version {value.version}")
            return str.__new__(cls, str(value))
        s = str(value)
        try:
            parsed = _uuid.UUID(s)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {s}")
        if parsed.version != 1:
            raise ValueError(f"UUID must be version 1, got version {parsed.version}")
        return str.__new__(cls, str(parsed))


class UUID3(str):
    """UUID version 3 (MD5 namespace)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value):
        import uuid as _uuid
        if isinstance(value, _uuid.UUID):
            if value.version != 3:
                raise ValueError(f"UUID must be version 3, got version {value.version}")
            return str.__new__(cls, str(value))
        s = str(value)
        try:
            parsed = _uuid.UUID(s)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {s}")
        if parsed.version != 3:
            raise ValueError(f"UUID must be version 3, got version {parsed.version}")
        return str.__new__(cls, str(parsed))


class UUID4(str):
    """UUID version 4 (random)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value):
        import uuid as _uuid
        if isinstance(value, _uuid.UUID):
            if value.version != 4:
                raise ValueError(f"UUID must be version 4, got version {value.version}")
            return str.__new__(cls, str(value))
        s = str(value)
        try:
            parsed = _uuid.UUID(s)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {s}")
        if parsed.version != 4:
            raise ValueError(f"UUID must be version 4, got version {parsed.version}")
        return str.__new__(cls, str(parsed))


class UUID5(str):
    """UUID version 5 (SHA-1 namespace)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value):
        import uuid as _uuid
        if isinstance(value, _uuid.UUID):
            if value.version != 5:
                raise ValueError(f"UUID must be version 5, got version {value.version}")
            return str.__new__(cls, str(value))
        s = str(value)
        try:
            parsed = _uuid.UUID(s)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {s}")
        if parsed.version != 5:
            raise ValueError(f"UUID must be version 5, got version {parsed.version}")
        return str.__new__(cls, str(parsed))


# ============================================================================
# Date/Time Types
# ============================================================================

class FutureDate:
    """Date that must be in the future"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value):
        from datetime import date
        if isinstance(value, str):
            value = date.fromisoformat(value)
        if not isinstance(value, date):
            raise TypeError(f"Expected date, got {type(value).__name__}")
        if value <= date.today():
            raise ValueError(f"Date must be in the future, got {value}")
        return value


class PastDate:
    """Date that must be in the past"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value):
        from datetime import date
        if isinstance(value, str):
            value = date.fromisoformat(value)
        if not isinstance(value, date):
            raise TypeError(f"Expected date, got {type(value).__name__}")
        if value >= date.today():
            raise ValueError(f"Date must be in the past, got {value}")
        return value


class FutureDatetime:
    """Datetime that must be in the future"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value):
        from datetime import datetime, timezone
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise TypeError(f"Expected datetime, got {type(value).__name__}")
        now = datetime.now(timezone.utc) if value.tzinfo else datetime.now()
        if value <= now:
            raise ValueError(f"Datetime must be in the future, got {value}")
        return value


class PastDatetime:
    """Datetime that must be in the past"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value):
        from datetime import datetime, timezone
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise TypeError(f"Expected datetime, got {type(value).__name__}")
        now = datetime.now(timezone.utc) if value.tzinfo else datetime.now()
        if value >= now:
            raise ValueError(f"Datetime must be in the past, got {value}")
        return value


class AwareDatetime:
    """Datetime with timezone info (not naive)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value):
        from datetime import datetime
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise TypeError(f"Expected datetime, got {type(value).__name__}")
        if value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return value


class NaiveDatetime:
    """Datetime without timezone info"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __new__(cls, value):
        from datetime import datetime
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise TypeError(f"Expected datetime, got {type(value).__name__}")
        if value.tzinfo is not None:
            raise ValueError("Datetime must be naive (no timezone)")
        return value


# ============================================================================
# Utility Types
# ============================================================================

class ByteSize(int):
    """Parse human-readable byte sizes like '1GB', '500MB' (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'int', 'constraints': {'ge': 0}}

    _UNITS = {
        'b': 1, 'byte': 1, 'bytes': 1,
        'kb': 1000, 'kib': 1024,
        'mb': 1000**2, 'mib': 1024**2,
        'gb': 1000**3, 'gib': 1024**3,
        'tb': 1000**4, 'tib': 1024**4,
        'pb': 1000**5, 'pib': 1024**5,
    }

    def __new__(cls, value):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return int.__new__(cls, int(value))
        if isinstance(value, str):
            match = _re.match(r'^([\d.]+)\s*([a-zA-Z]*)$', value.strip())
            if match:
                num_str, unit = match.group(1), match.group(2).lower()
                num = float(num_str)
                if not unit or unit in ('b', 'byte', 'bytes'):
                    return int.__new__(cls, int(num))
                if unit in cls._UNITS:
                    return int.__new__(cls, int(num * cls._UNITS[unit]))
            # Try plain number
            try:
                return int.__new__(cls, int(float(value)))
            except ValueError:
                pass
            raise ValueError(f"Cannot parse ByteSize: {value}")
        raise TypeError(f"ByteSize requires int or str, got {type(value).__name__}")

    def human_readable(self, decimal: bool = True) -> str:
        """Return human-readable string."""
        value = int(self)
        if decimal:
            units = [('PB', 1000**5), ('TB', 1000**4), ('GB', 1000**3),
                     ('MB', 1000**2), ('KB', 1000), ('B', 1)]
        else:
            units = [('PiB', 1024**5), ('TiB', 1024**4), ('GiB', 1024**3),
                     ('MiB', 1024**2), ('KiB', 1024), ('B', 1)]
        for suffix, factor in units:
            if value >= factor:
                result = value / factor
                if result == int(result):
                    return f"{int(result)}{suffix}"
                return f"{result:.1f}{suffix}"
        return f"{value}B"


class Json:
    """Validate that a string contains valid JSON (Pydantic compatible)"""
    __satya_type_info__ = {'base_type': 'str', 'constraints': {}}

    def __init__(self, value: str):
        import json as _json
        if not isinstance(value, str):
            raise TypeError(f"Json requires a string, got {type(value).__name__}")
        try:
            self._parsed = _json.loads(value)
        except (_json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid JSON: {e}")
        self._raw = value

    @property
    def parsed(self):
        """Get the parsed JSON value."""
        return self._parsed

    def __str__(self) -> str:
        return self._raw

    def __repr__(self) -> str:
        return f"Json({self._raw!r})"


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Secret types
    'SecretStr',
    'SecretBytes',
    # Path types
    'FilePath',
    'DirectoryPath',
    'NewPath',
    # Network/URL types
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
    # DSN types
    'PostgresDsn',
    'MySQLDsn',
    'RedisDsn',
    'MongoDsn',
    'KafkaDsn',
    # Constrained numeric types
    'PositiveInt',
    'NegativeInt',
    'NonNegativeInt',
    'NonPositiveInt',
    'PositiveFloat',
    'NegativeFloat',
    'NonNegativeFloat',
    'NonPositiveFloat',
    'FiniteFloat',
    # Strict types
    'StrictStr',
    'StrictInt',
    'StrictFloat',
    'StrictBool',
    'StrictBytes',
    # Constrained type constructors
    'conint',
    'confloat',
    'constr',
    'conbytes',
    'conlist',
    'conset',
    'confrozenset',
    'condecimal',
    # UUID types
    'UUID1',
    'UUID3',
    'UUID4',
    'UUID5',
    # Date/Time types
    'FutureDate',
    'PastDate',
    'FutureDatetime',
    'PastDatetime',
    'AwareDatetime',
    'NaiveDatetime',
    # Utility types
    'ByteSize',
    'Json',
]
