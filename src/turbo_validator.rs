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

#[pymethods]
impl TurboValidatorPy {
    #[new]
    fn new() -> Self {
        Self {
            fields: Vec::new(),
            field_map: HashMap::new(),
            schema: None,
            defaults: HashMap::new(),
        }
    }

    /// Add a field to the schema
    fn add_field(&mut self, name: String, type_str: String, required: bool) {
        let field_type = match type_str.as_str() {
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
        self.field_map.insert(name.clone(), idx);

        self.fields.push(TurboField {
            name,
            index: idx,
            field_type,
            required,
            strict: false,
            gt: None,
            ge: None,
            lt: None,
            le: None,
            multiple_of: None,
            finite: false,
            min_length: None,
            max_length: None,
            compiled_pattern: None,
            email: false,
            url: false,
            enum_values: None,
            min_items: None,
            max_items: None,
            unique_items: false,
            has_constraints: false,
            nested_schema: None,
        });
    }

    /// Set constraints for a field (with pre-compiled regex!)
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
        if let Some(&idx) = self.field_map.get(&field_name) {
            if let Some(field) = self.fields.get_mut(idx) {
                field.gt = gt;
                field.ge = ge;
                field.lt = lt;
                field.le = le;
                field.min_length = min_length;
                field.max_length = max_length;
                // Pre-compile regex at schema build time (not per-validation!)
                field.compiled_pattern = pattern.and_then(|p| regex::Regex::new(&p).ok());
                field.email = email;
                field.url = url;
                field.enum_values = enum_values;
                field.min_items = min_items;
                field.max_items = max_items;
                field.unique_items = unique_items;
                // Pre-compute constraint flag
                field.has_constraints = field.gt.is_some() || field.ge.is_some()
                    || field.lt.is_some() || field.le.is_some()
                    || field.min_length.is_some() || field.max_length.is_some()
                    || field.compiled_pattern.is_some()
                    || field.email || field.url
                    || field.enum_values.is_some()
                    || field.min_items.is_some() || field.max_items.is_some()
                    || field.unique_items;
                return Ok(());
            }
        }
        Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(
            format!("Field '{}' not found", field_name)
        ))
    }

    /// Compile and optimize the schema (BLAZE cost-ordering)
    fn compile(&mut self, py: Python<'_>) {
        // BLAZE: Reorder fields by validation cost (cheapest first for fail-fast)
        let mut field_costs: Vec<(usize, u32)> = self.fields.iter().enumerate().map(|(idx, f)| {
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
            let constraint_cost =
                (if f.gt.is_some() || f.ge.is_some() || f.lt.is_some() || f.le.is_some() { 1 } else { 0 }) +
                (if f.min_length.is_some() || f.max_length.is_some() { 1 } else { 0 }) +
                (if f.compiled_pattern.is_some() { 3 } else { 0 }) +
                (if f.email || f.url { 2 } else { 0 });
            (idx, type_cost * 10 + constraint_cost)
        }).collect();

        field_costs.sort_by_key(|(_, cost)| *cost);
        let validation_order = field_costs.iter().map(|(idx, _)| *idx).collect();

        // Pre-intern field names as Python strings for fast dict lookup
        let py_names: Vec<Py<PyString>> = self.fields.iter()
            .map(|f| PyString::intern(py, &f.name).clone().unbind())
            .collect();

        self.schema = Some(Arc::new(TurboSchema {
            fields: self.fields.clone(),
            field_map: self.field_map.clone(),
            validation_order,
            py_names,
        }));
    }

    /// Store a Python default value for a field (called from Python's validator() setup)
    fn set_default(&mut self, field_name: String, value: Py<PyAny>, is_mutable: bool) -> PyResult<()> {
        if self.field_map.contains_key(&field_name) {
            self.defaults.insert(field_name, (value, is_mutable));
            return Ok(());
        }
        Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(
            format!("Field '{}' not found", field_name)
        ))
    }

    /// Link a nested TurboSchema for recursive validation
    fn set_nested_schema(&mut self, field_name: String, nested_validator: &TurboValidatorPy) -> PyResult<()> {
        if let Some(&idx) = self.field_map.get(&field_name) {
            if let Some(field) = self.fields.get_mut(idx) {
                field.nested_schema = nested_validator.schema.clone();
                return Ok(());
            }
        }
        Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(
            format!("Field '{}' not found", field_name)
        ))
    }

    /// Validate a dict and return a PyDict directly (no TurboValue intermediate!)
    /// This is the key performance optimization: validate + build PyDict in one pass.
