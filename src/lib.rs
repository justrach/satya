use pyo3::prelude::*;
use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use regex::Regex;  // Use the regex crate directly

#[pyclass(name = "StreamValidatorCore")]
struct StreamValidatorCore {
    schema: HashMap<String, FieldValidator>,
    batch_size: usize,
    custom_types: HashMap<String, HashMap<String, FieldValidator>>,
}

#[derive(Clone)]
struct FieldValidator {
    field_type: FieldType,
    required: bool,
    constraints: FieldConstraints,
}

#[derive(Clone, Default)]
struct FieldConstraints {
    min_length: Option<usize>,
    max_length: Option<usize>,
    min_value: Option<f64>,
    max_value: Option<f64>,
    pattern: Option<String>,
    email: bool,
    url: bool,
    ge: Option<i64>,
    le: Option<i64>,
    gt: Option<i64>,
    lt: Option<i64>,
    min_items: Option<usize>,
    max_items: Option<usize>,
    unique_items: bool,
    enum_values: Option<Vec<String>>,
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
    Any,
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
            required,
            constraints: FieldConstraints::default(),
        });
        Ok(())
    }

    fn add_field(&mut self, name: String, field_type: &str, required: bool) -> PyResult<()> {
        let field_type = self.parse_field_type(field_type)?;
        self.schema.insert(name, FieldValidator { field_type, required, constraints: FieldConstraints::default() });
        Ok(())
    }

    fn set_batch_size(&mut self, size: usize) {
        self.batch_size = size;
    }

    fn get_batch_size(&self) -> usize {
        self.batch_size
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
                self.validate_value(value, &validator.field_type, &validator.constraints)?;
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
            "str" | "string" | "email" | "url" | "uuid" | "date-time" => return Ok(FieldType::String),
            "int" | "integer" => return Ok(FieldType::Integer),
            "float" | "number" => return Ok(FieldType::Float),
            "bool" | "boolean" => return Ok(FieldType::Boolean),
            "any" => return Ok(FieldType::Any),
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
        
        // Finally treat everything else as a custom type
        Ok(FieldType::Custom(field_type.to_string()))
    }

    fn validate_value(&self, value: &PyAny, field_type: &FieldType, constraints: &FieldConstraints) -> PyResult<()> {
        match field_type {
            FieldType::String => {
                if !value.is_instance_of::<pyo3::types::PyString>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string"));
                }
                let s = value.downcast::<pyo3::types::PyString>()?.to_str()?;
                
                // Length validation
                if let Some(min_len) = constraints.min_length {
                    if s.len() < min_len {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("String length must be >= {}", min_len)
                        ));
                    }
                }
                if let Some(max_len) = constraints.max_length {
                    if s.len() > max_len {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("String length must be <= {}", max_len)
                        ));
                    }
                }

                // Email validation
                if constraints.email {
                    if !validate_email(s) {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid email format"));
                    }
                }

                // URL validation
                if constraints.url {
                    if !validate_url(s) {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid URL format"));
                    }
                }

                // Regex pattern validation
                if let Some(pattern) = &constraints.pattern {
                    if !regex_match(s, pattern) {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("String does not match pattern: {}", pattern)
                        ));
                    }
                }

                // Add enum validation
                if let Some(ref enum_values) = constraints.enum_values {
                    if !enum_values.contains(&s.to_string()) {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be one of: {:?}", enum_values)
                        ));
                    }
                }
            }
            FieldType::Integer | FieldType::Float => {
                let num = if value.is_instance_of::<pyo3::types::PyInt>()? {
                    value.downcast::<pyo3::types::PyInt>()?.extract::<f64>()?
                } else if value.is_instance_of::<pyo3::types::PyFloat>()? {
                    value.downcast::<pyo3::types::PyFloat>()?.extract::<f64>()?
                } else {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected number"));
                };

                // Add ge/le/gt/lt validation
                if let Some(ge) = constraints.ge {
                    if num < ge as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be >= {}", ge)
                        ));
                    }
                }
                if let Some(le) = constraints.le {
                    if num > le as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be <= {}", le)
                        ));
                    }
                }
                if let Some(gt) = constraints.gt {
                    if num <= gt as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be > {}", gt)
                        ));
                    }
                }
                if let Some(lt) = constraints.lt {
                    if num >= lt as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be < {}", lt)
                        ));
                    }
                }

                if let Some(min_val) = constraints.min_value {
                    if num < min_val {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be >= {}", min_val)
                        ));
                    }
                }
                if let Some(max_val) = constraints.max_value {
                    if num > max_val {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be <= {}", max_val)
                        ));
                    }
                }
            }
            FieldType::Boolean => {
                if !value.is_instance_of::<pyo3::types::PyBool>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected boolean"));
                }
            }
            FieldType::List(inner_type) => {
                let list = value.downcast::<pyo3::types::PyList>()?;
                
                // Add min/max items validation
                if let Some(min_items) = constraints.min_items {
                    if list.len() < min_items {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("List must have at least {} items", min_items)
                        ));
                    }
                }
                // ... similar for max_items
                
                // Add unique items validation
                if constraints.unique_items {
                    // This is a simple implementation - might need optimization for large lists
                    let mut seen = std::collections::HashSet::new();
                    for item in list.iter() {
                        let s = item.str()?.to_str()?;
                        if !seen.insert(s.to_string()) {
                            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                                "List items must be unique"
                            ));
                        }
                    }
                }
                
                // Validate each item
                for item in list.iter() {
                    self.validate_value(item, inner_type, constraints)?;
                }
            }
            FieldType::Dict(inner_type) => {
                if !value.is_instance_of::<pyo3::types::PyDict>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected dict"));
                }
                for item in value.downcast::<pyo3::types::PyDict>()?.values() {
                    self.validate_value(item, inner_type, constraints)?;
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
                        self.validate_value(field_value, &validator.field_type, &validator.constraints)?;
                    } else if validator.required {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Required field {} is missing in custom type {}", field_name, type_name)
                        ));
                    }
                }
            }
            FieldType::Any => {
                // Any type accepts all values without validation
            }
        }
        Ok(())
    }
}

// Helper functions for validation
fn validate_email(s: &str) -> bool {
    // RFC 5322 compliant email regex
    let email_regex = Regex::new(r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$").unwrap();
    
    // Check basic structure and length
    if s.len() > 254 || s.is_empty() {
        return false;
    }
    
    // Apply regex validation
    if !email_regex.is_match(s) {
        return false;
    }
    
    // Additional validation for domain part
    let parts: Vec<&str> = s.split('@').collect();
    if parts.len() != 2 {
        return false;
    }
    
    let domain = parts[1];
    // Domain specific validation
    if domain.starts_with('.') || domain.ends_with('.') {
        return false;
    }
    
    // Domain must have at least one dot and valid TLD
    let domain_parts: Vec<&str> = domain.split('.').collect();
    if domain_parts.len() < 2 || domain_parts.iter().any(|&part| part.is_empty()) {
        return false;
    }
    
    true
}

fn validate_url(s: &str) -> bool {
    // Basic URL validation
    s.starts_with("http://") || s.starts_with("https://")
}

fn regex_match(s: &str, pattern: &str) -> bool {
    // Basic pattern matching (can be enhanced with proper regex)
    // For now, just check if pattern exists in string
    s.contains(pattern)
}

#[pymodule]
fn _satya(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<StreamValidatorCore>()?;
    Ok(())
}