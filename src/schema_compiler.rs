// Schema compilation for Rust-native models
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyType};
use std::collections::HashMap;
use std::sync::Arc;
use regex::Regex;
use once_cell::sync::Lazy;

use crate::field_value::{FieldType, FieldValue};

// Email regex pattern (RFC 5322 simplified)
static EMAIL_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$").unwrap()
});

// URL regex pattern
static URL_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^https?://[^\s/$.?#].[^\s]*$").unwrap()
});

/// Compiled field definition with constraints
#[derive(Clone, Debug)]
pub struct CompiledField {
    pub name: String,
    pub index: usize,
    pub field_type: FieldType,
    pub required: bool,
    pub constraints: FieldConstraints,
}

/// Field constraints for validation
#[derive(Clone, Debug, Default)]
pub struct FieldConstraints {
    // String constraints
    pub min_length: Option<usize>,
    pub max_length: Option<usize>,
    pub pattern: Option<String>,
    pub email: bool,
    pub url: bool,
    
    // Numeric constraints
    pub ge: Option<i64>,
    pub le: Option<i64>,
    pub gt: Option<i64>,
    pub lt: Option<i64>,
    pub min_value: Option<f64>,
    pub max_value: Option<f64>,
    pub multiple_of: Option<f64>,
    
    // List constraints
    pub min_items: Option<usize>,
    pub max_items: Option<usize>,
    pub unique_items: bool,
    
    // Enum constraint
    pub enum_values: Option<Vec<String>>,
}

impl FieldConstraints {
    /// Validate a field value against constraints
    pub fn validate(&self, value: &FieldValue) -> Result<(), String> {
        match value {
            FieldValue::String(s) => self.validate_string(s),
            FieldValue::Int(i) => self.validate_int(*i),
            FieldValue::Float(f) => self.validate_float(*f),
            FieldValue::List(items) => self.validate_list(items),
            _ => Ok(()),
        }
    }

    fn validate_string(&self, s: &str) -> Result<(), String> {
        let len = s.len();
        
        if let Some(min) = self.min_length {
            if len < min {
                return Err(format!("String length must be >= {}", min));
            }
        }
        
        if let Some(max) = self.max_length {
            if len > max {
                return Err(format!("String length must be <= {}", max));
            }
        }
        
        if self.email && !is_valid_email(s) {
            return Err("Invalid email format".to_string());
        }
        
        if self.url && !is_valid_url(s) {
            return Err("Invalid URL format".to_string());
        }
        
        if let Some(ref pattern) = self.pattern {
            if !regex_match(s, pattern) {
                return Err(format!("String does not match pattern: {}", pattern));
            }
        }
        
        if let Some(ref enum_vals) = self.enum_values {
            if !enum_vals.contains(&s.to_string()) {
                return Err(format!("Value must be one of: {:?}", enum_vals));
            }
        }
        
        Ok(())
    }

    fn validate_int(&self, i: i64) -> Result<(), String> {
        if let Some(ge) = self.ge {
            if i < ge {
                return Err(format!("Value must be >= {}", ge));
            }
        }
        
        if let Some(le) = self.le {
            if i > le {
                return Err(format!("Value must be <= {}", le));
            }
        }
        
        if let Some(gt) = self.gt {
            if i <= gt {
                return Err(format!("Value must be > {}", gt));
            }
        }
        
        if let Some(lt) = self.lt {
            if i >= lt {
                return Err(format!("Value must be < {}", lt));
            }
        }
        
        if let Some(multiple) = self.multiple_of {
            if (i as f64) % multiple != 0.0 {
                return Err(format!("Value must be multiple of {}", multiple));
            }
        }
        
        Ok(())
    }

    fn validate_float(&self, f: f64) -> Result<(), String> {
        if let Some(min) = self.min_value {
            if f < min {
                return Err(format!("Value must be >= {}", min));
            }
        }
        
        if let Some(max) = self.max_value {
            if f > max {
                return Err(format!("Value must be <= {}", max));
            }
        }
        
        if let Some(ge) = self.ge {
            if f < ge as f64 {
                return Err(format!("Value must be >= {}", ge));
            }
        }
        
        if let Some(le) = self.le {
            if f > le as f64 {
                return Err(format!("Value must be <= {}", le));
            }
        }
        
        if let Some(gt) = self.gt {
            if f <= gt as f64 {
                return Err(format!("Value must be > {}", gt));
            }
        }
        
        if let Some(lt) = self.lt {
            if f >= lt as f64 {
                return Err(format!("Value must be < {}", lt));
            }
        }
        
        if let Some(multiple) = self.multiple_of {
            if f % multiple != 0.0 {
                return Err(format!("Value must be multiple of {}", multiple));
            }
        }
        
        Ok(())
    }

    fn validate_list(&self, items: &[FieldValue]) -> Result<(), String> {
        let len = items.len();
        
        if let Some(min) = self.min_items {
            if len < min {
                return Err(format!("List must have at least {} items", min));
            }
        }
        
        if let Some(max) = self.max_items {
            if len > max {
                return Err(format!("List must have at most {} items", max));
            }
        }
        
        if self.unique_items {
            // Simple uniqueness check using JSON serialization
            let mut seen = std::collections::HashSet::new();
            for item in items {
                let json = item.to_json();
                if !seen.insert(json) {
                    return Err("List items must be unique".to_string());
                }
            }
        }
        
        Ok(())
    }
}

/// Compiled schema for a model class
#[derive(Clone)]
#[pyclass(name = "CompiledSchema")]
pub struct CompiledSchema {
    pub name: String,
    pub fields: Vec<CompiledField>,
    pub field_map: HashMap<String, usize>,
}

#[pymethods]
impl CompiledSchema {
    fn __repr__(&self) -> String {
        format!("CompiledSchema(name='{}', fields={})", self.name, self.fields.len())
    }
}

impl CompiledSchema {
    /// Compile a schema from a Python model class
    pub fn from_python_class(py: Python<'_>, py_class: &Bound<'_, PyType>) -> PyResult<Self> {
        let name = py_class.name()?.to_string();
        let mut fields = Vec::new();
        let mut field_map = HashMap::new();
        
        // Get __annotations__ to extract field types
        if let Ok(annotations) = py_class.getattr("__annotations__") {
            let annotations_dict = annotations.downcast::<PyDict>()?;
            
            for (idx, (field_name, field_type)) in annotations_dict.iter().enumerate() {
                let name_str = field_name.extract::<String>()?;
                let parsed_type = FieldType::from_python_type(py, &field_type)?;
                
                // Check if field is required by looking at the Field object in __fields__
                let required = if let Ok(fields_dict) = py_class.getattr("__fields__") {
                    if let Ok(dict) = fields_dict.downcast::<PyDict>() {
                        if let Ok(Some(field_obj)) = dict.get_item(&name_str) {
                            // Check if it's a Field object with a required attribute
                            if let Ok(req) = field_obj.getattr("required") {
                                req.extract().unwrap_or(true)
                            } else {
                                true
                            }
                        } else {
                            true
                        }
                    } else {
                        true
                    }
                } else {
                    true
                };
                
                // Extract constraints from Field() if present
                let constraints = Self::extract_constraints(py, py_class, &name_str)?;
                
                let field = CompiledField {
                    name: name_str.clone(),
                    index: idx,
                    field_type: parsed_type,
                    required,
                    constraints,
                };
                
                field_map.insert(name_str, idx);
                fields.push(field);
            }
        }
        
        Ok(Self {
            name,
            fields,
            field_map,
        })
    }

    /// Extract field constraints from Field() definition
    fn extract_constraints(
        _py: Python<'_>,
        py_class: &Bound<'_, PyType>,
        field_name: &str,
    ) -> PyResult<FieldConstraints> {
        let mut constraints = FieldConstraints::default();
        
        // Try to get the Field object from __fields__ dict
        let field_obj = if let Ok(fields_dict) = py_class.getattr("__fields__") {
            if let Ok(dict) = fields_dict.downcast::<PyDict>() {
                dict.get_item(field_name)?.map(|item| item.to_owned())
            } else {
                None
            }
        } else {
            None
        };
        
        if let Some(field_obj) = field_obj {
            // Helper macro to extract optional attributes
            macro_rules! extract_opt {
                ($attr:expr, $field:ident) => {
                    if let Ok(val) = field_obj.getattr($attr) {
                        if !val.is_none() {
                            if let Ok(extracted) = val.extract() {
                                constraints.$field = Some(extracted);
                            }
                        }
                    }
                };
            }
            
            macro_rules! extract_bool {
                ($attr:expr, $field:ident) => {
                    if let Ok(val) = field_obj.getattr($attr) {
                        if !val.is_none() {
                            if let Ok(extracted) = val.extract() {
                                constraints.$field = extracted;
                            }
                        }
                    }
                };
            }
            
            // Extract all constraints
            extract_opt!("min_length", min_length);
            extract_opt!("max_length", max_length);
            extract_opt!("pattern", pattern);
            extract_bool!("email", email);
            extract_bool!("url", url);
            extract_opt!("ge", ge);
            extract_opt!("le", le);
            extract_opt!("gt", gt);
            extract_opt!("lt", lt);
            extract_opt!("min_value", min_value);
            extract_opt!("max_value", max_value);
            extract_opt!("multiple_of", multiple_of);
            extract_opt!("min_items", min_items);
            extract_opt!("max_items", max_items);
            extract_bool!("unique_items", unique_items);
            
            // Extract enum values
            if let Ok(enum_val) = field_obj.getattr("enum") {
                if !enum_val.is_none() {
                    if let Ok(enum_list) = enum_val.extract::<Vec<String>>() {
                        constraints.enum_values = Some(enum_list);
                    }
                }
            }
        }
        
        Ok(constraints)
    }

    /// Validate all fields in a model instance
    pub fn validate(&self, fields: &[FieldValue]) -> Result<(), Vec<String>> {
        let mut errors = Vec::new();
        
        for (field, value) in self.fields.iter().zip(fields.iter()) {
            // Skip None values for optional fields
            if matches!(value, FieldValue::None) && !field.required {
                continue;
            }
            
            // Validate required fields
            if matches!(value, FieldValue::None) && field.required {
                errors.push(format!("Field '{}' is required", field.name));
                continue;
            }
            
            // Validate constraints
            if let Err(e) = field.constraints.validate(value) {
                errors.push(format!("Field '{}': {}", field.name, e));
            }
        }
        
        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }
}

// Helper functions for validation

fn is_valid_email(s: &str) -> bool {
    // Use compiled regex for email validation
    EMAIL_REGEX.is_match(s)
}

fn is_valid_url(s: &str) -> bool {
    // Use compiled regex for URL validation
    URL_REGEX.is_match(s)
}

fn regex_match(s: &str, pattern: &str) -> bool {
    // Compile and cache regex patterns for better performance
    // Note: In production, we'd want to cache compiled patterns
    if let Ok(re) = Regex::new(pattern) {
        re.is_match(s)
    } else {
        false
    }
}
