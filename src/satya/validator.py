from ._satya import StreamValidatorCore

class StreamValidator:
    def __init__(self):
        self._core = StreamValidatorCore()
        
    def add_field(self, name: str, field_type: str, required: bool = True):
        """Add a field to the schema"""
        return self._core.add_field(name, field_type, required)
        
    def define_custom_type(self, type_name: str):
        """Define a new custom type"""
        return self._core.define_custom_type(type_name)
        
    def add_field_to_custom_type(self, type_name: str, field_name: str, field_type: str, required: bool = True):
        """Add a field to a custom type"""
        return self._core.add_field_to_custom_type(type_name, field_name, field_type, required)
        
    def validate_batch(self, items):
        """Validate a batch of items"""
        return self._core.validate_batch(items)
        
    @property
    def batch_size(self):
        """Get the current batch size"""
        return self._core.batch_size
        
    def set_batch_size(self, size: int):
        """Set the batch size"""
        self._core.set_batch_size(size) 