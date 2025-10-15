// Full Model Validator - All validation logic in Rust
// Implements BLAZE paper optimizations + complete constraint validation

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString, PyInt, PyFloat, PyBool, PyList, PyAny};
use std::collections::HashMap;
use rayon::prelude::*;
use regex::Regex;
use once_cell::sync::Lazy;

/// Email regex (compiled once, reused forever)
static EMAIL_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$").unwrap()
});

/// URL regex (compiled once, reused forever)
static URL_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^https?://[A-Za-z0-9.-]+(?::\d+)?(?:/[^\s]*)?$").unwrap()
});

/// Field type enum
#[derive(Clone, Debug, PartialEq)]
pub enum FieldType {
    String,
    Int,
    Float,
    Bool,
    List,
    Dict,
    Decimal,  // Special handling for Python Decimal
    Any,
}

/// Complete field specification with all constraints
#[derive(Clone)]
pub struct FieldSpec {
    pub name: String,
    pub field_type: FieldType,
    pub required: bool,
    
    // Numeric constraints
    pub gt: Option<f64>,
    pub ge: Option<f64>,
    pub lt: Option<f64>,
    pub le: Option<f64>,
    
    // String constraints
    pub min_length: Option<usize>,
    pub max_length: Option<usize>,
    pub pattern: Option<Regex>,
    pub email: bool,
    pub url: bool,
    pub enum_values: Option<Vec<String>>,
    
    // List constraints
    pub min_items: Option<usize>,
    pub max_items: Option<usize>,
    pub unique_items: bool,
    
    // Optimization: field check order (BLAZE)
    pub check_order: usize,
}

impl FieldSpec {
    fn new(name: String, field_type: FieldType, required: bool) -> Self {
        Self {
            name,
            field_type,
            required,
            gt: None,
            ge: None,
            lt: None,
            le: None,
            min_length: None,
            max_length: None,
            pattern: None,
            email: false,
            url: false,
            enum_values: None,
            min_items: None,
            max_items: None,
            unique_items: false,
            check_order: 0,
        }
    }
}

/// BLAZE-optimized Model Validator
pub struct ModelValidator {
    fields: Vec<FieldSpec>,
    field_indices: HashMap<String, usize>,
    field_count: usize,
}

impl ModelValidator {
    pub fn new() -> Self {
        Self {
            fields: Vec::new(),
            field_indices: HashMap::new(),
            field_count: 0,
        }
    }
    
    /// Add a field to the schema
    pub fn add_field(&mut self, name: String, type_str: &str, required: bool) {
        let field_type = match type_str {
            "str" => FieldType::String,
            "int" => FieldType::Int,
            "float" => FieldType::Float,
            "bool" => FieldType::Bool,
            "list" => FieldType::List,
            "dict" => FieldType::Dict,
            "decimal" => FieldType::Decimal,
            _ => FieldType::Any,
        };
        
        let idx = self.fields.len();
        self.field_indices.insert(name.clone(), idx);
        self.fields.push(FieldSpec::new(name, field_type, required));
        self.field_count += 1;
    }
    
    /// Set constraints for a field
    pub fn set_constraints(
        &mut self,
        field_name: &str,
        gt: Option<f64>,
        ge: Option<f64>,
        lt: Option<f64>,
        le: Option<f64>,
        min_length: Option<usize>,
        max_length: Option<usize>,
        pattern: Option<String>,
        email: bool,
        url: bool,
        enum_values: Option<Vec<String>>,
        min_items: Option<usize>,
        max_items: Option<usize>,
        unique_items: bool,
    ) -> PyResult<()> {
        if let Some(&idx) = self.field_indices.get(field_name) {
            if let Some(field) = self.fields.get_mut(idx) {
                field.gt = gt;
                field.ge = ge;
                field.lt = lt;
                field.le = le;
                field.min_length = min_length;
                field.max_length = max_length;
                field.pattern = pattern.and_then(|p| Regex::new(&p).ok());
                field.email = email;
                field.url = url;
                field.enum_values = enum_values;
                field.min_items = min_items;
                field.max_items = max_items;
                field.unique_items = unique_items;
                return Ok(());
            }
        }
        Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(
            format!("Field '{}' not found", field_name)
        ))
    }
    
    /// Compile and optimize the schema (BLAZE optimization)
    pub fn compile(&mut self) {
        // BLAZE OPTIMIZATION 1: Reorder fields by validation cost
        // Cheapest checks first to fail fast
        self.fields.sort_by_key(|f| {
            let type_cost = match f.field_type {
                FieldType::Bool => 0,
                FieldType::Int => 1,
                FieldType::Float => 2,
                FieldType::String => 3,
                FieldType::List => 4,
                FieldType::Dict => 5,
                FieldType::Decimal => 6,
                FieldType::Any => 7,
            };
            
            // Add constraint cost
            let constraint_cost = 
                (if f.gt.is_some() || f.ge.is_some() || f.lt.is_some() || f.le.is_some() { 1 } else { 0 }) +
                (if f.min_length.is_some() || f.max_length.is_some() { 1 } else { 0 }) +
                (if f.pattern.is_some() { 3 } else { 0 }) +  // Regex is expensive
                (if f.email || f.url { 2 } else { 0 });
            
            type_cost * 10 + constraint_cost
        });
        
        // BLAZE OPTIMIZATION 2: Rebuild field indices after reordering
        self.field_indices.clear();
        for (idx, field) in self.fields.iter_mut().enumerate() {
            self.field_indices.insert(field.name.clone(), idx);
            field.check_order = idx;
        }
    }
    
    /// Validate a single item (BLAZE-optimized)
    #[inline(always)]
    pub fn validate(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
        let validated = PyDict::new(py);
        
        // BLAZE OPTIMIZATION 3: Unroll loop for small schemas (≤5 fields)
        if self.field_count <= 5 {
            return self.validate_unrolled(py, data, validated);
        }
        
        // For larger schemas, use optimized loop
        for field in &self.fields {
            self.validate_field(py, data, &validated, field)?;
        }
        
        Ok(validated.unbind())
    }
    
    /// Unrolled validation for small schemas (BLAZE optimization)
    #[inline(always)]
    fn validate_unrolled(&self, py: Python<'_>, data: &Bound<'_, PyDict>, validated: Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
        if let Some(f) = self.fields.get(0) { self.validate_field(py, data, &validated, f)?; }
        if let Some(f) = self.fields.get(1) { self.validate_field(py, data, &validated, f)?; }
        if let Some(f) = self.fields.get(2) { self.validate_field(py, data, &validated, f)?; }
        if let Some(f) = self.fields.get(3) { self.validate_field(py, data, &validated, f)?; }
        if let Some(f) = self.fields.get(4) { self.validate_field(py, data, &validated, f)?; }
        Ok(validated.unbind())
    }
    
    /// Validate a single field with all constraints
    #[inline(always)]
    fn validate_field(&self, py: Python<'_>, data: &Bound<'_, PyDict>, validated: &Bound<'_, PyDict>, field: &FieldSpec) -> PyResult<()> {
        match data.get_item(&field.name)? {
            Some(value) => {
                // Handle None for optional fields
                if value.is_none() {
                    if !field.required {
                        // Optional field with None value - this is OK
                        validated.set_item(&field.name, &value)?;
                        return Ok(());
                    } else {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Required field '{}' cannot be None", field.name)
                        ));
                    }
                }
                
                // Type coercion + validation
                let coerced_value = self.coerce_and_validate_type(py, field, &value)?;
                
                // Constraint validation based on type
                match field.field_type {
                    FieldType::Int | FieldType::Float => {
                        self.validate_numeric_constraints(&field, &coerced_value)?;
                    }
                    FieldType::String => {
                        self.validate_string_constraints(&field, &coerced_value)?;
                    }
                    FieldType::List => {
                        self.validate_list_constraints(&field, &coerced_value)?;
                    }
                    _ => {}
                }
                
                validated.set_item(&field.name, &coerced_value)?;
            }
            None if field.required => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Required field '{}' is missing", field.name)
                ));
            }
            None => {}
        }
        
        Ok(())
    }
    
    /// Coerce value to the correct type and validate type
    #[inline(always)]
    fn coerce_and_validate_type<'py>(&self, py: Python<'py>, field: &FieldSpec, value: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
        match field.field_type {
            FieldType::String => {
                if value.is_exact_instance_of::<PyString>() {
                    Ok(value.clone())
                } else {
                    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Field '{}' must be a string", field.name)
                    ))
                }
            }
            FieldType::Int => {
                // Try to coerce string to int (Pydantic compatibility)
                if value.is_exact_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>() {
                    Ok(value.clone())
                } else if value.is_exact_instance_of::<PyString>() {
                    // Coerce string to int
                    let s: String = value.extract()?;
                    match s.trim().parse::<i64>() {
                        Ok(i) => {
                            let py_int = py.import("builtins")?.getattr("int")?.call1((i,))?;
                            Ok(py_int.into_any())
                        },
                        Err(_) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Field '{}' cannot be converted to int", field.name)
                        ))
                    }
                } else {
                    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Field '{}' must be an integer", field.name)
                    ))
                }
            }
            FieldType::Float => {
                // Accept int or float, coerce string to float
                if value.is_exact_instance_of::<PyFloat>() {
                    Ok(value.clone())
                } else if value.is_exact_instance_of::<PyInt>() {
                    // Coerce int to float
                    let i: i64 = value.extract()?;
                    let py_float = py.import("builtins")?.getattr("float")?.call1((i,))?;
                    Ok(py_float.into_any())
                } else if value.is_exact_instance_of::<PyString>() {
                    // Coerce string to float
                    let s: String = value.extract()?;
                    match s.trim().parse::<f64>() {
                        Ok(f) => {
                            let py_float = py.import("builtins")?.getattr("float")?.call1((f,))?;
                            Ok(py_float.into_any())
                        },
                        Err(_) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Field '{}' cannot be converted to float", field.name)
                        ))
                    }
                } else {
                    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Field '{}' must be a number", field.name)
                    ))
                }
            }
            FieldType::Bool => {
                if value.is_exact_instance_of::<PyBool>() {
                    Ok(value.clone())
                } else {
                    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Field '{}' must be a boolean", field.name)
                    ))
                }
            }
            FieldType::List => {
                if value.is_exact_instance_of::<PyList>() {
                    Ok(value.clone())
                } else {
                    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Field '{}' must be a list", field.name)
                    ))
                }
            }
            FieldType::Dict => {
                if value.is_exact_instance_of::<PyDict>() {
                    Ok(value.clone())
                } else {
                    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Field '{}' must be a dict", field.name)
                    ))
                }
            }
            FieldType::Decimal => {
                let decimal_type = py.import("decimal")?.getattr("Decimal")?;
                if value.is_instance(&decimal_type)? {
                    Ok(value.clone())
                } else if value.is_exact_instance_of::<PyString>() || value.is_exact_instance_of::<PyInt>() || value.is_exact_instance_of::<PyFloat>() {
                    // Coerce to Decimal
                    let decimal_class = py.import("decimal")?.getattr("Decimal")?;
                    Ok(decimal_class.call1((value,))?.into_any())
                } else {
                    Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Field '{}' must be a Decimal", field.name)
                    ))
                }
            }
            FieldType::Any => Ok(value.clone()),
        }
    }
    
    /// Validate numeric constraints (gt, ge, lt, le)
    #[inline(always)]
    fn validate_numeric_constraints(&self, field: &FieldSpec, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let num_val = value.extract::<f64>()?;
        
        if let Some(gt) = field.gt {
            if num_val <= gt {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must be > {}", field.name, gt)
                ));
            }
        }
        if let Some(ge) = field.ge {
            if num_val < ge {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must be >= {}", field.name, ge)
                ));
            }
        }
        if let Some(lt) = field.lt {
            if num_val >= lt {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must be < {}", field.name, lt)
                ));
            }
        }
        if let Some(le) = field.le {
            if num_val > le {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must be <= {}", field.name, le)
                ));
            }
        }
        
        Ok(())
    }
    
    /// Validate string constraints (min_length, max_length, pattern, email, url, enum)
    #[inline(always)]
    fn validate_string_constraints(&self, field: &FieldSpec, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let str_val = value.extract::<String>()?;
        
        // min_length (check trimmed)
        if let Some(min_len) = field.min_length {
            if str_val.trim().len() < min_len {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must have at least {} characters", field.name, min_len)
                ));
            }
        }
        
        // max_length (check original)
        if let Some(max_len) = field.max_length {
            if str_val.len() > max_len {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must have at most {} characters", field.name, max_len)
                ));
            }
        }
        
        // Pattern (regex)
        if let Some(ref pattern) = field.pattern {
            if !pattern.is_match(&str_val) {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' does not match pattern", field.name)
                ));
            }
        }
        
        // Email validation
        if field.email && !EMAIL_REGEX.is_match(&str_val) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Field '{}' must be a valid email", field.name)
            ));
        }
        
        // URL validation
        if field.url && !URL_REGEX.is_match(&str_val) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Field '{}' must be a valid URL", field.name)
            ));
        }
        
        // Enum validation
        if let Some(ref enum_vals) = field.enum_values {
            if !enum_vals.contains(&str_val) {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must be one of: {:?}", field.name, enum_vals)
                ));
            }
        }
        
        Ok(())
    }
    
    /// Validate list constraints (min_items, max_items, unique_items)
    #[inline(always)]
    fn validate_list_constraints(&self, field: &FieldSpec, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let list = value.downcast::<PyList>()?;
        let len = list.len();
        
        if let Some(min_items) = field.min_items {
            if len < min_items {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must have at least {} items", field.name, min_items)
                ));
            }
        }
        
        if let Some(max_items) = field.max_items {
            if len > max_items {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must have at most {} items", field.name, max_items)
                ));
            }
        }
        
        if field.unique_items {
            // Check uniqueness (convert to strings for comparison)
            let mut seen = std::collections::HashSet::new();
            for item in list.iter() {
                let item_str = item.str()?.to_string();
                if !seen.insert(item_str) {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Field '{}' must have unique items", field.name)
                    ));
                }
            }
        }
        
        Ok(())
    }
    
    /// Batch validation with parallel processing
    pub fn validate_batch(&self, py: Python<'_>, data_list: &Bound<'_, PyList>) -> PyResult<Py<PyList>> {
        let len = data_list.len();
        
        // For small batches, don't parallelize
        if len < 1000 {
            let result_list = PyList::empty(py);
            for item in data_list.iter() {
                let dict = item.downcast::<PyDict>()?;
                let validated = self.validate(py, dict)?;
                result_list.append(validated)?;
            }
            return Ok(result_list.unbind());
        }
        
        // Parallel validation for large batches
        let dicts: Vec<Py<PyDict>> = data_list
            .iter()
            .map(|item| item.downcast::<PyDict>().unwrap().clone().unbind())
            .collect();
        
        const CHUNK_SIZE: usize = 1000;
        
        let results: Vec<Vec<Py<PyDict>>> = py.detach(|| {
            dicts.par_chunks(CHUNK_SIZE)
                .map(|chunk| {
                    Python::with_gil(|py| {
                        chunk.iter()
                            .map(|dict_py| {
                                let dict = dict_py.bind(py);
                                self.validate(py, dict)
                            })
                            .collect::<PyResult<Vec<_>>>()
                    })
                })
                .collect::<PyResult<Vec<_>>>()
                .unwrap()
        });
        
        let result_list = PyList::empty(py);
        for chunk_results in results {
            for result in chunk_results {
                result_list.append(result)?;
            }
        }
        
        Ok(result_list.unbind())
    }
}

/// Python wrapper
#[pyclass]
pub struct BlazeModelValidator(pub ModelValidator);

#[pymethods]
impl BlazeModelValidator {
    #[new]
    fn new() -> Self {
        Self(ModelValidator::new())
    }
    
    fn add_field(&mut self, name: String, type_str: String, required: bool) {
        self.0.add_field(name, &type_str, required);
    }
    
    fn set_constraints(
        &mut self,
        field_name: String,
        gt: Option<f64>,
        ge: Option<f64>,
        lt: Option<f64>,
        le: Option<f64>,
        min_length: Option<usize>,
        max_length: Option<usize>,
        pattern: Option<String>,
        email: bool,
        url: bool,
        enum_values: Option<Vec<String>>,
        min_items: Option<usize>,
        max_items: Option<usize>,
        unique_items: bool,
    ) -> PyResult<()> {
        self.0.set_constraints(
            &field_name, gt, ge, lt, le, min_length, max_length,
            pattern, email, url, enum_values, min_items, max_items, unique_items
        )
    }
    
    fn compile(&mut self) {
        self.0.compile();
    }
    
    fn validate(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
        self.0.validate(py, data)
    }
    
    fn validate_batch(&self, py: Python<'_>, data_list: &Bound<'_, PyList>) -> PyResult<Py<PyList>> {
        self.0.validate_batch(py, data_list)
    }
}
