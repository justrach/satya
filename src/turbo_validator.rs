// TurboValidator: Bulk Extraction Architecture for 2-3x Speedup
//
// Key insight: Minimize FFI boundary crossings.
// Before: Python → Rust → Python → Rust (per field, 3-6 crossings each)
// After:  Python → Rust (bulk extract + validate all) → Python (return result)
//
// Phase 1: Single-pass dict iteration via PyDict::iter()
// Phase 2: Pure Rust constraint validation (zero FFI)
// Result:  Rust-owned Vec<TurboValue>, lazy Python conversion

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString, PyInt, PyFloat, PyBool, PyList, PyAny, PyBytes};
use pyo3::exceptions::{PyValueError, PyAttributeError};
use std::collections::HashMap;
use std::sync::Arc;
use serde_json;

use crate::fast_parse;
use crate::blaze_validator::FieldType;

// ═══════════════════════════════════════════════════════════════════
// TurboValue: Extended FieldValue with Decimal support
// ═══════════════════════════════════════════════════════════════════

#[derive(Clone, Debug)]
pub enum TurboValue {
    Int(i64),
    Float(f64),
    Str(String),
    Bool(bool),
    List(Vec<TurboValue>),
    Dict(Vec<(String, TurboValue)>),  // Ordered pairs for stable JSON
    Decimal(String),                   // Stored as string repr
    None,
}

impl TurboValue {
    /// Convert to Python object (lazy — only called on attribute access)
    pub fn to_python(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            TurboValue::Int(i) => Ok(i.into_pyobject(py).unwrap().into_any().unbind()),
            TurboValue::Float(f) => Ok(PyFloat::new(py, *f).into_any().unbind()),
            TurboValue::Str(s) => Ok(PyString::new(py, s).into_any().unbind()),
            TurboValue::Bool(b) => Ok(PyBool::new(py, *b).as_any().clone().unbind()),
            TurboValue::None => Ok(py.None()),
            TurboValue::List(items) => {
                let py_list = PyList::empty(py);
                for item in items {
                    py_list.append(item.to_python(py)?)?;
                }
                Ok(py_list.into_any().unbind())
            }
            TurboValue::Dict(pairs) => {
                let py_dict = PyDict::new(py);
                for (k, v) in pairs {
                    py_dict.set_item(k, v.to_python(py)?)?;
                }
                Ok(py_dict.into_any().unbind())
            }
            TurboValue::Decimal(s) => {
                // Call decimal.Decimal(s) in Python
                let decimal_mod = py.import("decimal")?;
                let decimal_cls = decimal_mod.getattr("Decimal")?;
                let result = decimal_cls.call1((s.as_str(),))?;
                Ok(result.unbind())
            }
        }
    }

    /// Extract TurboValue from any Python object (for FieldType::Any)
    pub fn from_py_any(value: &Bound<'_, PyAny>) -> PyResult<Self> {
        if value.is_none() {
            return Ok(TurboValue::None);
        }
        // Order matters: check Bool before Int (bool is subclass of int)
        if value.is_instance_of::<PyBool>() {
            return Ok(TurboValue::Bool(value.extract()?));
        }
        if let Ok(i) = value.extract::<i64>() {
            return Ok(TurboValue::Int(i));
        }
        if let Ok(f) = value.extract::<f64>() {
            return Ok(TurboValue::Float(f));
        }
        if let Ok(s) = value.downcast::<PyString>() {
            return Ok(TurboValue::Str(s.to_str()?.to_owned()));
        }
        if let Ok(list) = value.downcast::<PyList>() {
            let mut items = Vec::with_capacity(list.len());
            for item in list.iter() {
                items.push(TurboValue::from_py_any(&item)?);
            }
            return Ok(TurboValue::List(items));
        }
        if let Ok(dict) = value.downcast::<PyDict>() {
            let mut pairs = Vec::with_capacity(dict.len());
            for (k, v) in dict.iter() {
                let key = k.extract::<String>()?;
                let val = TurboValue::from_py_any(&v)?;
                pairs.push((key, val));
            }
            return Ok(TurboValue::Dict(pairs));
        }
        // Fallback: convert to string
        Ok(TurboValue::Str(value.str()?.to_string()))
    }

    /// Serialize directly to JSON (bypasses Python entirely)
    pub fn to_json(&self) -> String {
        match self {
            TurboValue::Int(i) => i.to_string(),
            TurboValue::Float(f) => {
                if f.is_nan() {
                    "null".to_string()
                } else if f.is_infinite() {
                    "null".to_string()
                } else {
                    f.to_string()
                }
            }
            TurboValue::Str(s) => {
                // Proper JSON string escaping
                let mut out = String::with_capacity(s.len() + 2);
                out.push('"');
                for c in s.chars() {
                    match c {
                        '"' => out.push_str("\\\""),
                        '\\' => out.push_str("\\\\"),
                        '\n' => out.push_str("\\n"),
                        '\r' => out.push_str("\\r"),
                        '\t' => out.push_str("\\t"),
                        c if c < '\x20' => {
                            out.push_str(&format!("\\u{:04x}", c as u32));
                        }
                        c => out.push(c),
                    }
                }
                out.push('"');
                out
            }
            TurboValue::Bool(b) => if *b { "true" } else { "false" }.to_string(),
            TurboValue::None => "null".to_string(),
            TurboValue::List(items) => {
                let mut out = String::from("[");
                for (i, item) in items.iter().enumerate() {
                    if i > 0 { out.push(','); }
                    out.push_str(&item.to_json());
                }
                out.push(']');
                out
            }
            TurboValue::Dict(pairs) => {
                let mut out = String::from("{");
                for (i, (k, v)) in pairs.iter().enumerate() {
                    if i > 0 { out.push(','); }
                    // Key is always a string
                    out.push('"');
                    for c in k.chars() {
                        match c {
                            '"' => out.push_str("\\\""),
                            '\\' => out.push_str("\\\\"),
                            c => out.push(c),
                        }
                    }
                    out.push_str("\":");
                    out.push_str(&v.to_json());
                }
                out.push('}');
                out
            }
            TurboValue::Decimal(s) => s.clone(),
        }
    }
}

// ═══════════════════════════════════════════════════════════════════
// TurboField: Field spec with pre-compiled constraints
// ═══════════════════════════════════════════════════════════════════

#[derive(Clone)]
pub struct TurboField {
    pub name: String,
    pub index: usize,
    pub field_type: FieldType,
    pub required: bool,
    pub strict: bool,
    // Numeric constraints
    pub gt: Option<f64>,
    pub ge: Option<f64>,
    pub lt: Option<f64>,
    pub le: Option<f64>,
    pub multiple_of: Option<f64>,
    pub finite: bool,
    // String constraints
    pub min_length: Option<usize>,
    pub max_length: Option<usize>,
    pub compiled_pattern: Option<regex::Regex>,  // Pre-compiled!
    pub email: bool,
    pub url: bool,
    pub enum_values: Option<Vec<String>>,
    // List constraints
    pub min_items: Option<usize>,
    pub max_items: Option<usize>,
    pub unique_items: bool,
    // Pre-computed: does this field have any constraints?
    pub has_constraints: bool,
    // Nested schema for recursive validation
    pub nested_schema: Option<Arc<TurboSchema>>,
}

// ═══════════════════════════════════════════════════════════════════
// TurboSchema: Shared schema (Arc'd across instances)
// ═══════════════════════════════════════════════════════════════════

pub struct TurboSchema {
    pub fields: Vec<TurboField>,
    pub field_map: HashMap<String, usize>,
    pub validation_order: Vec<usize>,  // BLAZE cost-ordered
    pub py_names: Vec<Py<PyString>>,   // Pre-interned field name keys for fast dict lookup
}

// ═══════════════════════════════════════════════════════════════════
// TurboValidatorPy: Python-exposed validator
// ═══════════════════════════════════════════════════════════════════

#[pyclass(name = "TurboValidatorPy")]
pub struct TurboValidatorPy {
    // Before compile(): mutable builder state
    fields: Vec<TurboField>,
    field_map: HashMap<String, usize>,
    // After compile(): shared immutable schema
    schema: Option<Arc<TurboSchema>>,
    // Default values stored separately (Py<PyAny> can't be cloned in free-threaded builds)
    defaults: HashMap<String, (Py<PyAny>, bool)>,  // (value, is_mutable)
}
