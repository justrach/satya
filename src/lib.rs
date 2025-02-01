use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass(name = "StreamValidatorCore")]
struct StreamValidatorCore {
    schema: HashMap<String, FieldValidator>,
    batch_size: usize,
    custom_types: HashMap<String, HashMap<String, FieldValidator>>,
}

struct FieldValidator {
    field_type: FieldType,
    required: bool,
}

#[derive(Clone)]
enum FieldType {
    String,
    Integer,
    Float,
    Boolean,
    List(Box<FieldType>),
    Dict(Box<FieldType>),
    Custom(String),  // Reference to a custom type name
}

#[pymethods]
impl StreamValidatorCore {
    #[new]
    fn new() -> Self {
        StreamValidatorCore {
            schema: HashMap::new(),
            batch_size: 1000,
            custom_types: HashMap::new(),
        }
    }

    #[getter]
    fn batch_size(&self) -> usize {
        self.batch_size
    }

    fn define_custom_type(&mut self, type_name: String) -> PyResult<()> {
        if !self.custom_types.contains_key(&type_name) {
            self.custom_types.insert(type_name, HashMap::new());
        }
        Ok(())
    }

    fn add_field_to_custom_type(
        &mut self,
        type_name: String,
        field_name: String,
        field_type: &str,
        required: bool,
    ) -> PyResult<()> {
        // Parse field type first while we have immutable access
        let parsed_field_type = self.parse_field_type(field_type)?;
        
        // Then do the mutable operations
        let custom_type = self.custom_types.get_mut(&type_name).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Custom type {} not defined", type_name))
        })?;

        custom_type.insert(field_name, FieldValidator { 
            field_type: parsed_field_type, 
            required 
        });
        Ok(())
    }

    fn add_field(&mut self, name: String, field_type: &str, required: bool) -> PyResult<()> {
        let field_type = self.parse_field_type(field_type)?;
        self.schema.insert(name, FieldValidator { field_type, required });
        Ok(())
    }

    fn set_batch_size(&mut self, size: usize) {
        self.batch_size = size;
    }

    fn validate_batch(&self, items: Vec<&PyAny>) -> PyResult<Vec<bool>> {
        let mut results = Vec::with_capacity(items.len());
        
        for item in items {
            match self.validate_item_internal(item) {
                Ok(_) => results.push(true),
                Err(_) => results.push(false),
            }
        }
        Ok(results)
    }

    fn validate_item_internal(&self, item: &PyAny) -> PyResult<bool> {
        if !item.is_instance_of::<pyo3::types::PyDict>()? {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Item must be a dict"));
        }

        let dict = item.downcast::<pyo3::types::PyDict>()?;
        
        for (field_name, validator) in &self.schema {
            if let Some(value) = dict.get_item(field_name) {
                self.validate_value(value, &validator.field_type)?;
            } else if validator.required {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Required field {} is missing", field_name)
                ));
            }
        }

        Ok(true)
    }
}

// Private implementation - not exposed to Python
impl StreamValidatorCore {
    fn parse_field_type(&self, field_type: &str) -> PyResult<FieldType> {
        // First check for primitive types
        match field_type {
            "str" => return Ok(FieldType::String),
            "int" => return Ok(FieldType::Integer),
            "float" => return Ok(FieldType::Float),
            "bool" => return Ok(FieldType::Boolean),
            _ => {}
        }
        
        // Then check for List/Dict
        if let Some(inner_type) = field_type.strip_prefix("List[").and_then(|s| s.strip_suffix("]")) {
            let inner = self.parse_field_type(inner_type)?;
            return Ok(FieldType::List(Box::new(inner)));
        }
        if let Some(inner_type) = field_type.strip_prefix("Dict[").and_then(|s| s.strip_suffix("]")) {
            let inner = self.parse_field_type(inner_type)?;
            return Ok(FieldType::Dict(Box::new(inner)));
        }
        
        // Finally check for custom type
        if self.custom_types.contains_key(field_type) {
            return Ok(FieldType::Custom(field_type.to_string()));
        }
        
        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unsupported type: {}", field_type)
        ))
    }

    fn validate_value(&self, value: &PyAny, field_type: &FieldType) -> PyResult<()> {
        match field_type {
            FieldType::String => {
                if !value.is_instance_of::<pyo3::types::PyString>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string"));
                }
            }
            FieldType::Integer => {
                if !value.is_instance_of::<pyo3::types::PyInt>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected integer"));
                }
            }
            FieldType::Float => {
                if !value.is_instance_of::<pyo3::types::PyFloat>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected float"));
                }
            }
            FieldType::Boolean => {
                if !value.is_instance_of::<pyo3::types::PyBool>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected boolean"));
                }
            }
            FieldType::List(inner_type) => {
                if !value.is_instance_of::<pyo3::types::PyList>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected list"));
                }
                for item in value.downcast::<pyo3::types::PyList>()?.iter() {
                    self.validate_value(item, inner_type)?;
                }
            }
            FieldType::Dict(inner_type) => {
                if !value.is_instance_of::<pyo3::types::PyDict>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected dict"));
                }
                for item in value.downcast::<pyo3::types::PyDict>()?.values() {
                    self.validate_value(item, inner_type)?;
                }
            }
            FieldType::Custom(type_name) => {
                if !value.is_instance_of::<pyo3::types::PyDict>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Custom type must be a dict"));
                }
                let dict = value.downcast::<pyo3::types::PyDict>()?;
                let custom_type = self.custom_types.get(type_name)
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Custom type {} not found", type_name)
                    ))?;
                
                for (field_name, validator) in custom_type {
                    if let Some(field_value) = dict.get_item(field_name) {
                        self.validate_value(field_value, &validator.field_type)?;
                    } else if validator.required {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Required field {} is missing in custom type {}", field_name, type_name)
                        ));
                    }
                }
            }
        }
        Ok(())
    }
}

#[pymodule]
fn _satya(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<StreamValidatorCore>()?;
    Ok(())
}