from typing import Type, Dict, Any
from . import Model  # Import directly from the package

class OpenAISchema:
    """Adapter to convert Satya models to OpenAI-compatible JSON schemas"""
    
    @staticmethod
    def from_model(model: Type[Model], name: str) -> Dict[str, Any]:
        """Convert a Satya model to OpenAI's JSON schema format"""
        base_schema = model.json_schema()
        
        return {
            "name": name,
            "schema": {
                "type": "object",
                "properties": base_schema["properties"],
                "required": base_schema["required"]
            }
        }

    @staticmethod
    def response_format(model: Type[Model], name: str) -> Dict[str, Any]:
        """Generate complete response_format for OpenAI API"""
        return {
            "type": "json_schema",
            "json_schema": OpenAISchema.from_model(model, name)
        } 