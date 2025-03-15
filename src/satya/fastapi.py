"""
FastAPI integration for satya.

This module provides a simple integration with FastAPI, allowing satya models 
to be used for responses. For request models, we still need to use Pydantic.

The core integration provides:
1. SatyaJSONResponse - A response class that can serialize satya Model instances
2. response_model_satya - A helper function to extract JSON schema from satya models
"""
from typing import Any, Dict, Type, Optional, List, Union, get_args, get_origin
import inspect
import json

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from satya import Model, ValidationError


class SatyaJSONResponse(JSONResponse):
    """
    Custom JSONResponse class that properly serializes satya Model instances.
    
    This response class automatically converts satya models to dictionaries
    before JSON encoding them.
    """
    def render(self, content: Any) -> bytes:
        if isinstance(content, Model):
            content = content.dict()
        elif isinstance(content, list) and all(isinstance(item, Model) for item in content):
            content = [item.dict() for item in content]
        elif isinstance(content, dict):
            # Recursively handle nested models in dictionaries
            for key, value in content.items():
                if isinstance(value, Model):
                    content[key] = value.dict()
                elif isinstance(value, list) and all(isinstance(item, Model) for item in value):
                    content[key] = [item.dict() for item in value]
        
        return super().render(content)


class SatyaValidationHTTPException(HTTPException):
    """
    Exception for validation errors that matches FastAPI's error format.
    """
    def __init__(self, errors: List[ValidationError], status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY):
        detail = {
            "detail": [
                {
                    "loc": error.path or ["body"],
                    "msg": error.message,
                    "type": "validation_error"
                }
                for error in errors
            ]
        }
        super().__init__(status_code=status_code, detail=detail)


def validate_request_model(model_class: Type[Model], data: Dict) -> Model:
    """
    Validate input data against a satya model.
    
    Args:
        model_class: The satya Model class to validate against
        data: The data to validate
        
    Returns:
        An instance of the model if validation succeeds
        
    Raises:
        SatyaValidationHTTPException: If validation fails
    """
    validator = model_class.validator()
    result = validator.validate(data)
    
    if not result.is_valid:
        raise SatyaValidationHTTPException(result.errors)
    
    # Create a model instance from the validated data
    return model_class(**result.value)
