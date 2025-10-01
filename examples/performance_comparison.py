```python
# Before: fastjsonschema (820K/sec)
import fastjsonschema
validate = fastjsonschema.compile(schema)
result = validate(data)

# After: Satya (1.2M/sec) - 5x faster!
from satya import compile_json_schema
validate = compile_json_schema(schema)
result = validate.validate(data)  # 1.2M+ validations/sec!

# Batch validation for maximum performance
results = validate.validate_batch(large_dataset)  # 4M+ items/sec!
```
