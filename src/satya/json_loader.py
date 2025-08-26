"""
JSON loading utilities for Satya.
"""
from typing import Any, Dict, List, Union

# First try to use orjson for best performance if available
try:
    import orjson
    _HAVE_ORJSON = True
except ImportError:
    _HAVE_ORJSON = False

# Fallback to standard json
import json

def load_json(json_str: str) -> Union[Dict, List, Any]:
    """
    Parse a JSON string efficiently.
    
    This function tries to use the fastest available JSON parser:
    1. orjson if available (very fast C-based implementation)
    2. standard json module as fallback
    
    Args:
        json_str: The JSON string to parse
        
    Returns:
        The parsed JSON data as Python objects
        
    Raises:
        ValueError: If the JSON is invalid
    """
    if _HAVE_ORJSON:
        try:
            return orjson.loads(json_str)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON: {e}")
    else:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}") 