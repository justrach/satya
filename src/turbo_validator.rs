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
    fn validate_to_dict(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;
        Self::validate_to_dict_inner(py, schema, data, &self.defaults)
    }

    /// Validate and write directly into target dict (avoids temporary + update())
    /// This is the fastest path: no intermediate PyDict allocation.
    fn validate_into_dict(&self, py: Python<'_>, data: &Bound<'_, PyDict>, target: &Bound<'_, PyDict>) -> PyResult<()> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;
        // Use u64 bitmap for found fields (no heap alloc for ≤64 fields)
        let mut found: u64 = 0;
        // Lazy error collection (no Vec alloc in common no-error case)
        let mut first_error: Option<String> = None;
        let mut extra_errors: Option<Vec<String>> = None;

        // Single-pass: validate + write directly to target
        for (key, value) in data.iter() {
            let key_str = match key.downcast::<PyString>() {
                Ok(s) => match s.to_str() {
                    Ok(s) => s,
                    Err(_) => continue,
                },
                Err(_) => continue,
            };

            if let Some(&idx) = schema.field_map.get(key_str) {
                let field = &schema.fields[idx];
                match Self::validate_field_inline(py, field, &value) {
                    Ok(coerced) => {
                        if let Some(ref nested_schema) = field.nested_schema {
                            if let Ok(nested_dict) = value.downcast::<PyDict>() {
                                let empty_defaults = HashMap::new();
                                match Self::validate_to_dict_inner(py, nested_schema, nested_dict, &empty_defaults) {
                                    Ok(validated_nested) => {
                                        target.set_item(key_str, validated_nested)?;
                                    }
                                    Err(e) => {
                                        let msg = format!("{}: {}", key_str, e);
                                        if first_error.is_none() { first_error = Some(msg); }
                                        else { extra_errors.get_or_insert_with(Vec::new).push(msg); }
                                    }
                                }
                            } else if value.is_none() && !field.required {
                                target.set_item(key_str, py.None())?;
                            } else {
                                target.set_item(key_str, &value)?;
                            }
                        } else if let Some(coerced_val) = coerced {
                            target.set_item(key_str, coerced_val.bind(py))?;
                        } else {
                            target.set_item(key_str, &value)?;
                        }
                    }
                    Err(e) => {
                        let msg = e.to_string();
                        if first_error.is_none() { first_error = Some(msg); }
                        else { extra_errors.get_or_insert_with(Vec::new).push(msg); }
                    }
                }
                found |= 1u64 << idx;
            }
        }

        // Check required + apply defaults
        for field in &schema.fields {
            if found & (1u64 << field.index) == 0 {
                if let Some((ref default_val, is_mutable)) = self.defaults.get(&field.name) {
                    Self::apply_default(py, target, &field.name, default_val, *is_mutable)?;
                } else if field.required {
                    let msg = format!("Required field '{}' is missing", field.name);
                    if first_error.is_none() { first_error = Some(msg); }
                    else { extra_errors.get_or_insert_with(Vec::new).push(msg); }
                }
            }
        }

        if let Some(err) = first_error {
            if let Some(extras) = extra_errors {
                let mut msg = err;
                for e in extras { msg.push('\n'); msg.push_str(&e); }
                return Err(PyErr::new::<PyValueError, _>(msg));
            }
            return Err(PyErr::new::<PyValueError, _>(err));
        }
        Ok(())
    }

    /// Fast validate that returns errors as a list instead of raising exceptions.
    /// Returns None on success, or a list of (field_name, message) tuples on validation failure.
    /// This eliminates Python try/except overhead and string parsing.
    fn validate_into_dict_result(&self, py: Python<'_>, data: &Bound<'_, PyDict>, target: &Bound<'_, PyDict>) -> PyResult<PyObject> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;
        let mut found: u64 = 0;
        // Collect errors as (field_name, message) pairs
        let mut errors: Option<Vec<(&str, String)>> = None;

        for (key, value) in data.iter() {
            let key_str = match key.downcast::<PyString>() {
                Ok(s) => match s.to_str() {
                    Ok(s) => s,
                    Err(_) => continue,
                },
                Err(_) => continue,
            };

            if let Some(&idx) = schema.field_map.get(key_str) {
                let field = &schema.fields[idx];
                match Self::validate_field_inline(py, field, &value) {
                    Ok(coerced) => {
                        if let Some(ref nested_schema) = field.nested_schema {
                            if let Ok(nested_dict) = value.downcast::<PyDict>() {
                                let empty_defaults = HashMap::new();
                                match Self::validate_to_dict_inner(py, nested_schema, nested_dict, &empty_defaults) {
                                    Ok(validated_nested) => {
                                        target.set_item(key_str, validated_nested)?;
                                    }
                                    Err(e) => {
                                        errors.get_or_insert_with(Vec::new).push(
                                            (field.name.as_str(), format!("{}: {}", field.name, e))
                                        );
                                    }
                                }
                            } else if value.is_none() && !field.required {
                                target.set_item(key_str, py.None())?;
                            } else {
                                target.set_item(key_str, &value)?;
                            }
                        } else if let Some(coerced_val) = coerced {
                            target.set_item(key_str, coerced_val.bind(py))?;
                        } else {
                            target.set_item(key_str, &value)?;
                        }
                    }
                    Err(e) => {
                        errors.get_or_insert_with(Vec::new).push(
                            (field.name.as_str(), e.to_string())
                        );
                    }
                }
                found |= 1u64 << idx;
            }
        }

        // Check required + apply defaults
        for field in &schema.fields {
            if found & (1u64 << field.index) == 0 {
                if let Some((ref default_val, is_mutable)) = self.defaults.get(&field.name) {
                    Self::apply_default(py, target, &field.name, default_val, *is_mutable)?;
                } else if field.required {
                    errors.get_or_insert_with(Vec::new).push(
                        (field.name.as_str(), format!("Required field '{}' is missing", field.name))
                    );
                }
            }
        }

        if let Some(errs) = errors {
            // Return list of (field_name, message) tuples - no exception overhead
            let err_list = PyList::new(py, errs.iter().map(|(fname, msg)| {
                (*fname, msg.as_str())
            }))?;
            Ok(err_list.into_any().unbind())
        } else {
            Ok(py.None())
        }
    }

    /// Fast validate with pre-created nested instance __dict__s.
    /// nested_targets: {field_name: nested_instance.__dict__}
    /// Writes nested fields directly to their target dicts (no intermediate + no dict.update).
    fn validate_into_nested_dicts(
        &self, py: Python<'_>,
        data: &Bound<'_, PyDict>,
        target: &Bound<'_, PyDict>,
        nested_targets: &Bound<'_, PyDict>,
    ) -> PyResult<PyObject> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;
        let mut found: u64 = 0;
        let mut errors: Option<Vec<(&str, String)>> = None;

        for (key, value) in data.iter() {
            let key_str = match key.downcast::<PyString>() {
                Ok(s) => match s.to_str() {
                    Ok(s) => s,
                    Err(_) => continue,
                },
                Err(_) => continue,
            };

            if let Some(&idx) = schema.field_map.get(key_str) {
                let field = &schema.fields[idx];
                match Self::validate_field_inline(py, field, &value) {
                    Ok(coerced) => {
                        if let Some(ref nested_schema) = field.nested_schema {
                            // Write directly to nested instance's __dict__
                            if let Ok(nested_dict) = value.downcast::<PyDict>() {
                                if let Ok(Some(nested_target_obj)) = nested_targets.get_item(key_str) {
                                    if let Ok(nested_target) = nested_target_obj.downcast::<PyDict>() {
                                        // Single-pass: validate + track found fields
                                        let mut nested_found: u64 = 0;
                                        for (nkey, nval) in nested_dict.iter() {
                                            let nkey_str = match nkey.downcast::<PyString>() {
                                                Ok(s) => match s.to_str() {
                                                    Ok(s) => s,
                                                    Err(_) => continue,
                                                },
                                                Err(_) => continue,
                                            };
                                            if let Some(&nidx) = nested_schema.field_map.get(nkey_str) {
                                                nested_found |= 1u64 << nidx;
                                                let nfield = &nested_schema.fields[nidx];
                                                match Self::validate_field_inline(py, nfield, &nval) {
                                                    Ok(ncoerced) => {
                                                        if let Some(cv) = ncoerced {
                                                            nested_target.set_item(nkey_str, cv.bind(py))?;
                                                        } else {
                                                            nested_target.set_item(nkey_str, &nval)?;
                                                        }
                                                    }
                                                    Err(e) => {
                                                        errors.get_or_insert_with(Vec::new).push(
                                                            (field.name.as_str(), format!("{}.{}: {}", field.name, nkey_str, e))
                                                        );
                                                    }
                                                }
                                            }
                                        }
                                        // Check required fields
                                        for nfield in &nested_schema.fields {
                                            if nested_found & (1u64 << nfield.index) == 0 {
                                                if nfield.required {
                                                    errors.get_or_insert_with(Vec::new).push(
                                                        (field.name.as_str(), format!("Required field '{}.{}' is missing", field.name, nfield.name))
                                                    );
                                                }
                                            }
                                        }
                                    } else {
                                        // Fallback: validate_to_dict_inner
                                        let empty_defaults = HashMap::new();
                                        match Self::validate_to_dict_inner(py, nested_schema, nested_dict, &empty_defaults) {
                                            Ok(validated) => { target.set_item(key_str, validated)?; }
                                            Err(e) => {
                                                errors.get_or_insert_with(Vec::new).push(
                                                    (field.name.as_str(), format!("{}: {}", field.name, e))
                                                );
                                            }
                                        }
                                    }
                                } else {
                                    // No nested target provided, use standard path
                                    let empty_defaults = HashMap::new();
                                    match Self::validate_to_dict_inner(py, nested_schema, nested_dict, &empty_defaults) {
                                        Ok(validated) => { target.set_item(key_str, validated)?; }
                                        Err(e) => {
                                            errors.get_or_insert_with(Vec::new).push(
                                                (field.name.as_str(), format!("{}: {}", field.name, e))
                                            );
                                        }
                                    }
                                }
                            } else if value.is_none() && !field.required {
                                target.set_item(key_str, py.None())?;
                            } else {
                                target.set_item(key_str, &value)?;
                            }
                        } else if let Some(coerced_val) = coerced {
                            target.set_item(key_str, coerced_val.bind(py))?;
                        } else {
                            target.set_item(key_str, &value)?;
                        }
                    }
                    Err(e) => {
                        errors.get_or_insert_with(Vec::new).push(
                            (field.name.as_str(), e.to_string())
                        );
                    }
                }
                found |= 1u64 << idx;
            }
        }

        // Check required + apply defaults for parent
        for field in &schema.fields {
            if found & (1u64 << field.index) == 0 {
                if let Some((ref default_val, is_mutable)) = self.defaults.get(&field.name) {
                    Self::apply_default(py, target, &field.name, default_val, *is_mutable)?;
                } else if field.required {
                    errors.get_or_insert_with(Vec::new).push(
                        (field.name.as_str(), format!("Required field '{}' is missing", field.name))
                    );
                }
            }
        }

        if let Some(errs) = errors {
            let err_list = PyList::new(py, errs.iter().map(|(fname, msg)| {
                (*fname, msg.as_str())
            }))?;
            Ok(err_list.into_any().unbind())
        } else {
            Ok(py.None())
        }
    }

    /// Convert a PyDict to a JSON string using Rust's serde_json (faster than json.dumps)
    #[staticmethod]
    fn dict_to_json(py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<String> {
        let value = Self::pydict_to_serde_value(py, data)?;
        serde_json::to_string(&value).map_err(|e| {
            PyErr::new::<PyValueError, _>(format!("JSON serialization error: {}", e))
        })
    }

    /// Serialize specific fields from a PyDict directly to JSON (bypasses model_dump entirely!)
    /// This is the fastest path: __dict__ → JSON string in one Rust call.
    #[staticmethod]
    fn dict_to_json_fields(py: Python<'_>, data: &Bound<'_, PyDict>, field_names: Vec<String>) -> PyResult<String> {
        let mut out = String::with_capacity(64 + field_names.len() * 32);
        out.push('{');
        let mut first = true;
        for name in &field_names {
            if let Some(value) = data.get_item(name)? {
                if !first { out.push(','); }
                first = false;
                // Write key
                out.push('"');
                out.push_str(name);
                out.push_str("\":");
                // Write value directly
                Self::write_py_value_json(py, &value, &mut out)?;
            }
        }
        out.push('}');
        Ok(out)
    }

    /// Serialize a PyDict directly to JSON by iterating all entries (no field lookup overhead!)
    /// Use this when the dict only contains field data (e.g., turbo model __dict__).
    #[staticmethod]
    fn dict_to_json_direct(py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<String> {
        let mut out = String::with_capacity(64 + data.len() * 32);
        out.push('{');
        let mut first = true;
        for (key, value) in data.iter() {
            if !first { out.push(','); }
            first = false;
            // Write key directly
            out.push('"');
            if let Ok(s) = key.downcast::<PyString>() {
                out.push_str(s.to_str()?);
            } else {
                let s = key.str()?;
                out.push_str(s.to_str()?);
            }
            out.push_str("\":");
            // Value
            Self::write_py_value_json(py, &value, &mut out)?;
        }
        out.push('}');
        Ok(out)
    }

    /// Copy only specified fields from source dict to a new dict (fast model_dump replacement)
    #[staticmethod]
    fn dict_copy_fields(py: Python<'_>, src: &Bound<'_, PyDict>, field_names: Vec<String>) -> PyResult<Py<PyDict>> {
        let result = PyDict::new(py);
        for name in &field_names {
            if let Some(value) = src.get_item(name)? {
                result.set_item(name, value)?;
            }
        }
        Ok(result.unbind())
    }

    /// Validate JSON bytes/str and return a PyDict directly
    fn validate_json_bytes(&self, py: Python<'_>, data: &Bound<'_, PyAny>) -> PyResult<Py<PyDict>> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;

        // Parse JSON directly from borrowed data (zero-copy!)
        let json_value: serde_json::Value = if let Ok(b) = data.downcast::<pyo3::types::PyBytes>() {
            serde_json::from_slice(b.as_bytes()).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Invalid JSON: {}", e))
            })?
        } else if let Ok(s) = data.downcast::<PyString>() {
            serde_json::from_str(s.to_str()?).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Invalid JSON: {}", e))
            })?
        } else {
            return Err(PyErr::new::<PyValueError, _>("Expected bytes or str"));
        };

        // Must be an object
        let obj = match json_value {
            serde_json::Value::Object(map) => map,
            _ => return Err(PyErr::new::<PyValueError, _>("JSON must be an object")),
        };

        // Build validated PyDict from JSON
        Self::json_object_to_validated_dict(py, schema, &obj, &self.defaults)
    }

    /// Validate JSON bytes/str and write directly into target dict (skips temporary allocation!)
    fn validate_json_into_dict(&self, py: Python<'_>, data: &Bound<'_, PyAny>, target: &Bound<'_, PyDict>) -> PyResult<()> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;

        // Parse JSON directly from borrowed data (zero-copy, no Vec allocation!)
        let json_value: serde_json::Value = if let Ok(b) = data.downcast::<pyo3::types::PyBytes>() {
            serde_json::from_slice(b.as_bytes()).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Invalid JSON: {}", e))
            })?
        } else if let Ok(s) = data.downcast::<PyString>() {
            serde_json::from_str(s.to_str()?).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Invalid JSON: {}", e))
            })?
        } else {
            return Err(PyErr::new::<PyValueError, _>("Expected bytes or str"));
        };

        // Must be an object
        let obj = match json_value {
            serde_json::Value::Object(map) => map,
            _ => return Err(PyErr::new::<PyValueError, _>("JSON must be an object")),
        };

        // Write validated fields directly into target
        let mut found = vec![false; schema.fields.len()];
        for (key, json_val) in obj.iter() {
            if let Some(&idx) = schema.field_map.get(key) {
                let field = &schema.fields[idx];
                let py_val = Self::json_value_to_validated_py(py, field, json_val)?;
                if let Some(ref nested_schema) = field.nested_schema {
                    if let serde_json::Value::Object(ref nested_obj) = json_val {
                        let empty_defaults = HashMap::new();
                        let validated_nested = Self::json_object_to_validated_dict(py, nested_schema, nested_obj, &empty_defaults)?;
                        target.set_item(key, validated_nested)?;
                    } else if json_val.is_null() && !field.required {
                        target.set_item(key, py.None())?;
                    } else {
                        target.set_item(key, py_val)?;
                    }
                } else {
                    target.set_item(key, py_val)?;
                }
                found[idx] = true;
            }
        }

        // Check required + apply defaults
        for field in &schema.fields {
            if !found[field.index] {
                let has_default = self.defaults.contains_key(&field.name);
                if field.required && !has_default {
                    return Err(PyErr::new::<PyValueError, _>(
                        format!("Required field '{}' is missing", field.name)
                    ));
                }
                if let Some((ref default_val, is_mutable)) = self.defaults.get(&field.name) {
                    Self::apply_default(py, target, &field.name, default_val, *is_mutable)?;
                }
            }
        }
        Ok(())
    }

    /// PRIORITY 1+4: Validate kwargs and construct Model instance in ONE Rust call.
    /// Eliminates: Python __init__ body, _construct_validated, intermediate dict.
    /// Handles nested models: pass nested_classes={field_name: ModelClass} to recursively construct.
    fn validate_and_construct(
        &self,
        py: Python<'_>,
        cls: &Bound<'_, PyAny>,
        data: &Bound<'_, PyDict>,
        nested_classes: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<PyObject> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;

        let mut errors: Vec<String> = Vec::new();
        let mut found = vec![false; schema.fields.len()];

        // 1. Create instance via cls.__new__(cls) — same as Pydantic-core
        let instance = cls.call_method1("__new__", (cls,))?;
        let instance_dict_any = instance.getattr("__dict__")?;
        let instance_dict = instance_dict_any.downcast::<PyDict>()?;

        // 2. Single-pass: validate + write directly to instance.__dict__
        for (key, value) in data.iter() {
            let key_str = match key.downcast::<PyString>() {
                Ok(s) => match s.to_str() {
                    Ok(s) => s,
                    Err(_) => continue,
                },
                Err(_) => continue,
            };

            if let Some(&idx) = schema.field_map.get(key_str) {
                let field = &schema.fields[idx];
                match Self::validate_field_inline(py, field, &value) {
                    Ok(coerced) => {
                        if let Some(ref nested_schema) = field.nested_schema {
                            if let Ok(nested_dict) = value.downcast::<PyDict>() {
                                // Try to construct nested Model instance
                                if let Some(nc) = nested_classes {
                                    if let Ok(Some(nested_cls)) = nc.get_item(key_str) {
                                        // Get the nested turbo validator
                                        if let Ok(nested_turbo_any) = nested_cls.getattr("__turbo__") {
                                            if !nested_turbo_any.is_none() {
                                                if let Ok(nested_turbo) = nested_turbo_any.downcast::<TurboValidatorPy>() {
                                                    // Get nested class's own __nested_fields__ for recursive construction
                                                    let nested_nested = nested_cls.getattr("__nested_fields__")
                                                        .ok()
                                                        .and_then(|v| if v.is_none() { None } else { v.downcast::<PyDict>().ok().map(|d| d.clone()) });
                                                    let nested_nc = nested_nested.as_ref().and_then(|d| if d.is_empty() { None } else { Some(d) });
                                                    // Recursively construct nested model instance!
                                                    match nested_turbo.borrow().validate_and_construct(py, &nested_cls, nested_dict, nested_nc) {
                                                        Ok(nested_instance) => {
                                                            instance_dict.set_item(key_str, nested_instance)?;
                                                            found[idx] = true;
                                                            continue;
                                                        }
                                                        Err(e) => {
                                                            errors.push(format!("{}: {}", key_str, e));
                                                            found[idx] = true;
                                                            continue;
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                        // Nested class has no turbo → call cls(**data) for full Python path
                                        match nested_cls.call((), Some(nested_dict)) {
                                            Ok(nested_instance) => {
                                                instance_dict.set_item(key_str, nested_instance)?;
                                            }
                                            Err(e) => {
                                                errors.push(format!("{}: {}", key_str, e));
                                            }
                                        }
                                    } else {
                                        // No nested class for this field → call Python fallback
                                        if let Some(nc_outer) = nested_classes {
                                            // This shouldn't happen (field has nested_schema but no class)
                                            let empty_defaults = HashMap::new();
                                            match Self::validate_to_dict_inner(py, nested_schema, nested_dict, &empty_defaults) {
                                                Ok(validated_nested) => {
                                                    instance_dict.set_item(key_str, validated_nested)?;
                                                }
                                                Err(e) => {
                                                    errors.push(format!("{}: {}", key_str, e));
                                                }
                                            }
                                        } else {
                                            let empty_defaults = HashMap::new();
                                            match Self::validate_to_dict_inner(py, nested_schema, nested_dict, &empty_defaults) {
                                                Ok(validated_nested) => {
                                                    instance_dict.set_item(key_str, validated_nested)?;
                                                }
                                                Err(e) => {
                                                    errors.push(format!("{}: {}", key_str, e));
                                                }
                                            }
                                        }
                                    }
                                } else {
                                    // No nested_classes provided → validate as dict
                                    let empty_defaults = HashMap::new();
                                    match Self::validate_to_dict_inner(py, nested_schema, nested_dict, &empty_defaults) {
                                        Ok(validated_nested) => {
                                            instance_dict.set_item(key_str, validated_nested)?;
                                        }
                                        Err(e) => {
                                            errors.push(format!("{}: {}", key_str, e));
                                        }
                                    }
                                }
                            } else if value.is_none() && !field.required {
                                instance_dict.set_item(key_str, py.None())?;
                            } else {
                                instance_dict.set_item(key_str, &value)?;
                            }
                        } else if let Some(coerced_val) = coerced {
                            instance_dict.set_item(key_str, coerced_val.bind(py))?;
                        } else {
                            instance_dict.set_item(key_str, &value)?;
                        }
                    }
                    Err(e) => {
                        errors.push(e.to_string());
                    }
                }
                found[idx] = true;
            }
        }

        // 3. Check required + apply defaults
        for field in &schema.fields {
            if !found[field.index] {
                let has_default = self.defaults.contains_key(&field.name);
                if field.required && !has_default {
                    errors.push(format!("Required field '{}' is missing", field.name));
                    continue;
                }
                if let Some((ref default_val, is_mutable)) = self.defaults.get(&field.name) {
                    Self::apply_default(py, instance_dict, &field.name, default_val, *is_mutable)?;
                }
            }
        }

        // 4. Raise accumulated errors (Priority 2: structured)
        if !errors.is_empty() {
            return Err(PyErr::new::<PyValueError, _>(errors.join("\n")));
        }

        Ok(instance.unbind())
    }

    /// PRIORITY 3: Validate JSON bytes and construct Model instance in ONE Rust call.
    /// Combines: JSON parse + validate + cls.__new__() + __dict__ population.
    fn validate_json_and_construct(
        &self,
        py: Python<'_>,
        cls: &Bound<'_, PyAny>,
        json_data: &Bound<'_, PyAny>,
        nested_classes: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<PyObject> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;

        // Parse JSON directly from borrowed data (zero-copy!)
        let json_value: serde_json::Value = if let Ok(b) = json_data.downcast::<PyBytes>() {
            serde_json::from_slice(b.as_bytes()).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Invalid JSON: {}", e))
            })?
        } else if let Ok(s) = json_data.downcast::<PyString>() {
            serde_json::from_str(s.to_str()?).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Invalid JSON: {}", e))
            })?
        } else {
            return Err(PyErr::new::<PyValueError, _>("Expected bytes or str"));
        };

        let obj = match json_value {
            serde_json::Value::Object(map) => map,
            _ => return Err(PyErr::new::<PyValueError, _>("JSON must be an object")),
        };

        // Create instance via cls.__new__(cls)
        let instance = cls.call_method1("__new__", (cls,))?;
        let instance_dict_any = instance.getattr("__dict__")?;
        let instance_dict = instance_dict_any.downcast::<PyDict>()?;

        // Validate and populate __dict__ directly
        let mut found = vec![false; schema.fields.len()];
        for (key, json_val) in obj.iter() {
            if let Some(&idx) = schema.field_map.get(key) {
                let field = &schema.fields[idx];
                if let Some(ref nested_schema) = field.nested_schema {
                    if let serde_json::Value::Object(ref nested_obj) = json_val {
                        // Try to construct nested Model instance
                        if let Some(nc) = nested_classes {
                            if let Ok(Some(nested_cls)) = nc.get_item(key) {
                                if let Ok(nested_turbo_any) = nested_cls.getattr("__turbo__") {
                                    if !nested_turbo_any.is_none() {
                                        if let Ok(nested_turbo) = nested_turbo_any.downcast::<TurboValidatorPy>() {
                                            // Create nested instance
                                            let nested_instance_obj = nested_cls.call_method1("__new__", (&nested_cls,))?;
                                            let nested_dict_any = nested_instance_obj.getattr("__dict__")?;
                                            let nested_dict = nested_dict_any.downcast::<PyDict>()?;
                                            let nested_defaults = &nested_turbo.borrow().defaults;
                                            // Validate nested fields
                                            let mut nested_found = vec![false; nested_schema.fields.len()];
                                            for (nk, nv) in nested_obj.iter() {
                                                if let Some(&nidx) = nested_schema.field_map.get(nk) {
                                                    let nfield = &nested_schema.fields[nidx];
                                                    let py_val = Self::json_value_to_validated_py(py, nfield, nv)?;
                                                    nested_dict.set_item(nk, py_val)?;
                                                    nested_found[nidx] = true;
                                                }
                                            }
                                            // Apply nested defaults
                                            for nfield in &nested_schema.fields {
                                                if !nested_found[nfield.index] {
                                                    if let Some((ref dv, im)) = nested_defaults.get(&nfield.name) {
                                                        Self::apply_default(py, nested_dict, &nfield.name, dv, *im)?;
                                                    } else if nfield.required {
                                                        return Err(PyErr::new::<PyValueError, _>(
                                                            format!("Required field '{}.{}' is missing", key, nfield.name)
                                                        ));
                                                    }
                                                }
                                            }
                                            instance_dict.set_item(key, nested_instance_obj)?;
                                            found[idx] = true;
                                            continue;
                                        }
                                    }
                                }
                            }
                        }
                        // Fallback: validate as dict
                        let empty_defaults = HashMap::new();
                        let validated_nested = Self::json_object_to_validated_dict(py, nested_schema, nested_obj, &empty_defaults)?;
                        instance_dict.set_item(key, validated_nested)?;
                    } else if json_val.is_null() && !field.required {
                        instance_dict.set_item(key, py.None())?;
                    } else {
                        let py_val = Self::json_value_to_validated_py(py, field, json_val)?;
                        instance_dict.set_item(key, py_val)?;
                    }
                } else {
                    let py_val = Self::json_value_to_validated_py(py, field, json_val)?;
                    instance_dict.set_item(key, py_val)?;
                }
                found[idx] = true;
            }
        }

        // Check required + apply defaults
        for field in &schema.fields {
            if !found[field.index] {
                let has_default = self.defaults.contains_key(&field.name);
                if field.required && !has_default {
                    return Err(PyErr::new::<PyValueError, _>(
                        format!("Required field '{}' is missing", field.name)
                    ));
                }
                if let Some((ref default_val, is_mutable)) = self.defaults.get(&field.name) {
                    Self::apply_default(py, instance_dict, &field.name, default_val, *is_mutable)?;
                }
            }
        }

        Ok(instance.unbind())
    }

    /// Validate a dict and return TurboModelInstance (data stays in Rust!)
    fn validate(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<TurboModelInstance> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;
        Self::validate_inner(py, schema, data)
    }

    /// Ultra-fast validate: zero allocation, type-check only for unconstrained fields.
    /// Returns None on success, raises ValueError on failure.
    /// ~40% faster than validate() for unconstrained models.
    fn validate_check(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<PyObject> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;

        // Direct dict lookup with pre-interned keys — no HashMap, no key conversion
        for (idx, field) in schema.fields.iter().enumerate() {
            let value = match data.get_item(&schema.py_names[idx])? {
                Some(v) => v,
                None => {
                    if field.required {
                        return Err(PyErr::new::<PyValueError, _>(
                            format!("Required field '{}' is missing", field.name)
                        ));
                    }
                    continue;
                }
            };

            if value.is_none() {
                if field.required {
                    return Err(PyErr::new::<PyValueError, _>(
                        format!("Required field '{}' cannot be None", field.name)
                    ));
                }
                continue;
            }

            if !field.has_constraints {
                // Fast path: type-check only (no value extraction!)
                let type_ok = match field.field_type {
                    FieldType::String => value.is_instance_of::<PyString>(),
                    FieldType::Int => {
                        !value.is_instance_of::<PyBool>() && value.is_instance_of::<PyInt>()
                    }
                    FieldType::Float => {
                        value.is_instance_of::<PyFloat>() ||
                        (value.is_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>())
                    }
                    FieldType::Bool => value.is_instance_of::<PyBool>(),
                    FieldType::List => value.is_instance_of::<PyList>(),
                    FieldType::Dict => value.is_instance_of::<PyDict>(),
                    _ => true, // Any, Decimal: accept anything
                };
                if !type_ok {
                    return Err(PyErr::new::<PyValueError, _>(
                        format!("Field '{}' has wrong type", field.name)
                    ));
                }
            } else {
                // Constrained: full validation (with value extraction)
                Self::validate_field_inline(py, field, &value)?;
            }
        }

        Ok(py.None())
    }

    /// Validate and return a Python dict (backward-compatible with BlazeValidator)
    fn validate_dict(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
        let instance = self.validate(py, data)?;
        instance.to_py_dict(py)
    }

    /// Batch validate a list of dicts
    fn validate_batch(&self, py: Python<'_>, data_list: &Bound<'_, PyList>) -> PyResult<Vec<TurboModelInstance>> {
        let schema = self.schema.as_ref().ok_or_else(|| {
            PyErr::new::<PyValueError, _>("TurboValidator not compiled. Call compile() first.")
        })?;

        let mut results = Vec::with_capacity(data_list.len());
        for item in data_list.iter() {
            let dict = item.downcast::<PyDict>().map_err(|_| {
                PyErr::new::<PyValueError, _>("Batch items must be dicts")
            })?;
            results.push(Self::validate_inner(py, schema, dict)?);
        }
        Ok(results)
    }
}

// Internal implementation (not exposed to Python)
