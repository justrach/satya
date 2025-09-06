from typing import Any, Dict, Iterable, Iterator, Optional, List, get_args, get_origin
from ._satya import StreamValidatorCore
from . import ValidationError, ValidationResult

class StreamValidator:
    def __init__(self):
        self._core = StreamValidatorCore()
        # Compatibility alias expected by some benchmarks (validator._validator)
        self._validator = self._core
        # Keep a simple registry for introspection helpers, if needed later
        self._type_registry: Dict[str, Dict[str, Any]] = {}

    # --- Helpers ---
    def _type_to_str(self, tp: Any) -> str:
        """Convert Python/typing types to the string representation expected by the core."""
        # Handle typing Any
        try:
            from typing import Any as TypingAny
        except Exception:  # pragma: no cover
            TypingAny = object

        if tp is None:
            return "any"
        if tp is TypingAny:
            return "any"
        # Builtins
        if tp is str:
            return "str"
        if tp is int:
            return "int"
        if tp is float:
            return "float"
        if tp is bool:
            return "bool"

        # typing constructs
        origin = get_origin(tp)
        if origin is list or origin is List:  # type: ignore[name-defined]
            inner = get_args(tp)[0] if get_args(tp) else Any
            return f"List[{self._type_to_str(inner)}]"
        if origin is dict or origin is Dict:  # type: ignore[name-defined]
            # Only value type is represented in the core parser
            args = get_args(tp)
            value_tp = args[1] if len(args) >= 2 else Any
            return f"Dict[{self._type_to_str(value_tp)}]"

        # Model subclasses -> custom type by class name
        try:
            # Local import to avoid circular dependency at module import time
            from . import Model  # type: ignore
            if isinstance(tp, type) and issubclass(tp, Model):
                return tp.__name__
        except Exception:
            pass

        # Fallback to string name
        return getattr(tp, "__name__", str(tp))

    # --- Schema definition API ---
    def add_field(self, name: str, field_type: Any, required: bool = True):
        """Add a field to the root schema. Accepts Python/typing types or core type strings."""
        field_str = field_type if isinstance(field_type, str) else self._type_to_str(field_type)
        return self._core.add_field(name, field_str, required)

    def set_constraints(
        self,
        field_name: str,
        *,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        pattern: str | None = None,
        email: bool | None = None,
        url: bool | None = None,
        ge: int | None = None,
        le: int | None = None,
        gt: int | None = None,
        lt: int | None = None,
        min_items: int | None = None,
        max_items: int | None = None,
        unique_items: bool | None = None,
        enum_values: list[str] | None = None,
    ):
        """Set constraints for a root field on the core validator."""
        return self._core.set_field_constraints(
            field_name,
            min_length,
            max_length,
            min_value,
            max_value,
            pattern,
            email,
            url,
            ge,
            le,
            gt,
            lt,
            min_items,
            max_items,
            unique_items,
            enum_values,
        )

    def define_custom_type(self, type_name: str):
        """Define a new custom type."""
        self._type_registry.setdefault(type_name, {})
        return self._core.define_custom_type(type_name)

    def add_field_to_custom_type(self, type_name: str, field_name: str, field_type: Any, required: bool = True):
        """Add a field to a custom type. Accepts Python/typing types or core type strings."""
        field_str = field_type if isinstance(field_type, str) else self._type_to_str(field_type)
        self._type_registry.setdefault(type_name, {})[field_name] = field_str
        return self._core.add_field_to_custom_type(type_name, field_name, field_str, required)

    # Compatibility with older registration helper
    def define_type(self, type_name: str, fields: Dict[str, Any], doc: Optional[str] = None):
        """Compatibility shim: define a custom type and add its fields.
        'fields' may contain Python/typing types or core type strings.
        """
        self.define_custom_type(type_name)
        for fname, ftype in fields.items():
            self.add_field_to_custom_type(type_name, fname, ftype, required=True)
        return None

    # --- Validation API ---
    def validate_batch(self, items: Iterable[dict]):
        """Validate a batch of items and return a list of booleans."""
        return self._core.validate_batch(list(items))

    def validate(self, item: dict) -> ValidationResult:
        """Validate a single item and return a ValidationResult with optional error details."""
        try:
            ok = self._core.validate_item_internal(item)
            if ok:
                return ValidationResult(value=item)
            # Fallback (should not happen since core returns True or raises)
            return ValidationResult(errors=[ValidationError(field="root", message="validation failed", path=[])])
        except Exception as e:  # Capture PyErr from core
            return ValidationResult(errors=[ValidationError(field="root", message=str(e), path=[])])

    def validate_stream(self, items: Iterable[dict], collect_errors: bool = False) -> Iterator[ValidationResult]:
        """Validate a stream of items, yielding ValidationResult for each."""
        for it in items:
            res = self.validate(it)
            if res.is_valid or collect_errors:
                yield res

    # --- JSON bytes/str Validation API ---
    def validate_json(self, data: Any, mode: str = "object", streaming: bool = False):
        """Validate JSON provided as bytes or str using Rust core.
        mode:
          - 'object': top-level object -> returns bool
          - 'array' : top-level array of objects -> returns List[bool]
          - 'ndjson': newline-delimited JSON objects -> returns List[bool]
        If streaming=True, uses serde_json streaming validation to avoid building intermediate values.
        """
        mode = mode.lower()
        if mode == "object":
            return (
                self._core.validate_json_bytes_streaming(data)
                if streaming else self._core.validate_json_bytes(data)
            )
        if mode == "array":
            return (
                self._core.validate_json_array_bytes_streaming(data)
                if streaming else self._core.validate_json_array_bytes(data)
            )
        if mode == "ndjson":
            return (
                self._core.validate_ndjson_bytes_streaming(data)
                if streaming else self._core.validate_ndjson_bytes(data)
            )
        raise ValueError(f"Unknown mode: {mode}")

    @property
    def batch_size(self) -> int:
        """Get the current batch size from the core."""
        return self._core.get_batch_size()

    def set_batch_size(self, size: int):
        """Set the batch size in the core."""
        self._core.set_batch_size(size)
 