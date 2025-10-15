// Native Rust-backed Model - Eliminates FFI overhead
// Direct field storage in Rust, no Python dict overhead

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString, PyList};
use std::collections::HashMap;
use regex::Regex;
use once_cell::sync::Lazy;
use rayon::prelude::*;

static EMAIL_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$").unwrap()
});

static URL_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^https?://[A-Za-z0-9.-]+(?::\d+)?(?:/[^\s]*)?$").unwrap()
});

/// Field value stored in Rust (no Python overhead!)
#[derive(Clone, Debug)]
pub enum FieldValue {
    Int(i64),
    Float(f64),
    String(String),
    Bool(bool),
    None,
}

impl FieldValue {
    fn to_python(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            FieldValue::Int(i) => {
                let val = py.import("builtins")?.getattr("int")?.call1((*i,))?;
                Ok(val.unbind())
            }
            FieldValue::Float(f) => {
                let val = py.import("builtins")?.getattr("float")?.call1((*f,))?;
                Ok(val.unbind())
            }
            FieldValue::String(s) => {
                let val = py.import("builtins")?.getattr("str")?.call1((s.as_str(),))?;
                Ok(val.unbind())
            }
            FieldValue::Bool(b) => {
                let val = py.import("builtins")?.getattr("bool")?.call1((*b,))?;
                Ok(val.unbind())
            }
            FieldValue::None => Ok(py.None()),
        }
    }
}

/// Field specification
#[derive(Clone)]
pub struct NativeFieldSpec {
    pub name: String,
    pub required: bool,
    pub gt: Option<f64>,
    pub ge: Option<f64>,
    pub lt: Option<f64>,
    pub le: Option<f64>,
    pub min_length: Option<usize>,
    pub max_length: Option<usize>,
    pub pattern: Option<Regex>,
    pub email: bool,
    pub url: bool,
    pub enum_values: Option<Vec<String>>,
}

/// Native Model Validator - stores data in Rust!
pub struct NativeModelValidator {
    fields: Vec<NativeFieldSpec>,
    field_map: HashMap<String, usize>,
}

impl NativeModelValidator {
    pub fn new() -> Self {
        Self {
            fields: Vec::new(),
            field_map: HashMap::new(),
        }
    }
    
    pub fn add_field(&mut self, name: String, required: bool) {
        let idx = self.fields.len();
        self.field_map.insert(name.clone(), idx);
        self.fields.push(NativeFieldSpec {
            name,
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
        });
    }
    
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
    ) -> PyResult<()> {
        if let Some(&idx) = self.field_map.get(field_name) {
            let field = &mut self.fields[idx];
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
            Ok(())
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                format!("Field '{}' not found", field_name)
            ))
        }
    }
    
    /// Validate and create native model instance
    pub fn validate_and_create(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<NativeModelInstance> {
        let mut values = Vec::with_capacity(self.fields.len());
        
        for field in &self.fields {
            let value = match data.get_item(&field.name)? {
                Some(v) if v.is_none() => {
                    if field.required {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Required field '{}' cannot be None", field.name)
                        ));
                    }
                    FieldValue::None
                }
                Some(v) => {
                    // Extract and validate
                    self.extract_and_validate(field, &v)?
                }
                None if field.required => {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Required field '{}' is missing", field.name)
                    ));
                }
                None => FieldValue::None,
            };
            
            values.push(value);
        }
        
        Ok(NativeModelInstance {
            validator: self.clone(),
            values,
        })
    }
    
    fn extract_and_validate(&self, field: &NativeFieldSpec, value: &Bound<'_, pyo3::PyAny>) -> PyResult<FieldValue> {
        use pyo3::types::{PyInt, PyFloat, PyBool, PyString};
        
        // Try int
        if let Ok(i) = value.downcast::<PyInt>() {
            if !value.is_instance_of::<PyBool>() {
                let val = i.extract::<i64>()?;
                self.validate_numeric(field, val as f64)?;
                return Ok(FieldValue::Int(val));
            }
        }
        
        // Try float
        if let Ok(f) = value.downcast::<PyFloat>() {
            let val = f.extract::<f64>()?;
            self.validate_numeric(field, val)?;
            return Ok(FieldValue::Float(val));
        }
        
        // Try string (with coercion)
        if let Ok(s) = value.downcast::<PyString>() {
            let val = s.to_string();
            self.validate_string(field, &val)?;
            return Ok(FieldValue::String(val));
        } else if let Ok(val) = value.extract::<String>() {
            // Try coercion from other types
            self.validate_string(field, &val)?;
            return Ok(FieldValue::String(val));
        }
        
        // Try bool
        if let Ok(b) = value.downcast::<PyBool>() {
            let val = b.extract::<bool>()?;
            return Ok(FieldValue::Bool(val));
        }
        
        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Field '{}' has unsupported type", field.name)
        ))
    }
    
    #[inline(always)]
    fn validate_numeric(&self, field: &NativeFieldSpec, val: f64) -> PyResult<()> {
        if let Some(gt) = field.gt {
            if val <= gt {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must be > {}", field.name, gt)
                ));
            }
        }
        if let Some(ge) = field.ge {
            if val < ge {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must be >= {}", field.name, ge)
                ));
            }
        }
        if let Some(lt) = field.lt {
            if val >= lt {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must be < {}", field.name, lt)
                ));
            }
        }
        if let Some(le) = field.le {
            if val > le {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must be <= {}", field.name, le)
                ));
            }
        }
        Ok(())
    }
    
    #[inline(always)]
    fn validate_string(&self, field: &NativeFieldSpec, val: &str) -> PyResult<()> {
        if let Some(min_len) = field.min_length {
            if val.trim().len() < min_len {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must have at least {} characters", field.name, min_len)
                ));
            }
        }
        
        if let Some(max_len) = field.max_length {
            if val.len() > max_len {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must have at most {} characters", field.name, max_len)
                ));
            }
        }
        
        if let Some(ref pattern) = field.pattern {
            if !pattern.is_match(val) {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' does not match pattern", field.name)
                ));
            }
        }
        
        if field.email && !EMAIL_REGEX.is_match(val) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Field '{}' must be a valid email", field.name)
            ));
        }
        
        if field.url && !URL_REGEX.is_match(val) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Field '{}' must be a valid URL", field.name)
            ));
        }
        
        if let Some(ref enum_vals) = field.enum_values {
            if !enum_vals.contains(&val.to_string()) {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Field '{}' must be one of: {:?}", field.name, enum_vals)
                ));
            }
        }
        
        Ok(())
    }
    
    /// Batch validation with parallel processing
    pub fn validate_batch(&self, py: Python<'_>, data_list: &Bound<'_, PyList>) -> PyResult<Vec<NativeModelInstance>> {
        let len = data_list.len();
        
        if len < 1000 {
            // Small batch - sequential
            let mut results = Vec::with_capacity(len);
            for item in data_list.iter() {
                let dict = item.downcast::<PyDict>()?;
                results.push(self.validate_and_create(py, dict)?);
            }
            return Ok(results);
        }
        
        // Large batch - parallel
        let dicts: Vec<Py<PyDict>> = data_list
            .iter()
            .map(|item| item.downcast::<PyDict>().unwrap().clone().unbind())
            .collect();
        
        let validator = self.clone();
        let results: Vec<NativeModelInstance> = py.detach(|| {
            dicts.par_iter()
                .map(|dict_py| {
                    Python::with_gil(|py| {
                        let dict = dict_py.bind(py);
                        validator.validate_and_create(py, dict)
                    })
                })
                .collect::<PyResult<Vec<_>>>()
                .unwrap()
        });
        
        Ok(results)
    }
}

impl Clone for NativeModelValidator {
    fn clone(&self) -> Self {
        Self {
            fields: self.fields.clone(),
            field_map: self.field_map.clone(),
        }
    }
}

/// Native Model Instance - data stored in Rust!
#[pyclass]
pub struct NativeModelInstance {
    validator: NativeModelValidator,
    values: Vec<FieldValue>,
}

#[pymethods]
impl NativeModelInstance {
    /// Get field value by name (fast!)
    fn __getattr__(&self, py: Python<'_>, name: String) -> PyResult<PyObject> {
        if let Some(&idx) = self.validator.field_map.get(&name) {
            self.values[idx].to_python(py)
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyAttributeError, _>(
                format!("'NativeModelInstance' object has no attribute '{}'", name)
            ))
        }
    }
    
    /// Convert to dict
    fn dict(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (field, value) in self.validator.fields.iter().zip(self.values.iter()) {
            dict.set_item(&field.name, value.to_python(py)?)?;
        }
        Ok(dict.unbind())
    }
    
    fn __repr__(&self) -> String {
        format!("NativeModelInstance({} fields)", self.values.len())
    }
}

/// Python wrapper
#[pyclass]
pub struct NativeValidatorPy(pub NativeModelValidator);

#[pymethods]
impl NativeValidatorPy {
    #[new]
    fn new() -> Self {
        Self(NativeModelValidator::new())
    }
    
    fn add_field(&mut self, name: String, required: bool) {
        self.0.add_field(name, required);
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
    ) -> PyResult<()> {
        self.0.set_constraints(
            &field_name, gt, ge, lt, le, min_length, max_length,
            pattern, email, url, enum_values
        )
    }
    
    /// Validate and return native instance (NO DICT OVERHEAD!)
    fn validate(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<NativeModelInstance> {
        self.0.validate_and_create(py, data)
    }
    
    /// Batch validation with parallel processing
    fn validate_batch(&self, py: Python<'_>, data_list: &Bound<'_, PyList>) -> PyResult<Vec<NativeModelInstance>> {
        self.0.validate_batch(py, data_list)
    }
}
