#!/usr/bin/env python
import sys

try:
    from satya import StreamValidatorCore
    print(f"StreamValidatorCore class: {StreamValidatorCore}")
    
    # Check available methods on StreamValidatorCore
    print("\nAvailable methods on StreamValidatorCore:")
    methods = [name for name in dir(StreamValidatorCore) if not name.startswith("_")]
    print(methods)
    
    # Check if parse_json is in the list
    print(f"\nIs parse_json available? {'parse_json' in methods}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1) 