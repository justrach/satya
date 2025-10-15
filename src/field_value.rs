// Field value types for Rust-native model storage
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};
use std::collections::HashMap;

/// Rust-native field value storage
/// This replaces Python dict with native Rust types for zero-overhead storage
#[derive(Clone, Debug)]
pub enum FieldValue {
    Int(i64),
    Float(f64),
    String(String),
    Bool(bool),
    List(Vec<FieldValue>),
    Dict(HashMap<String, FieldValue>),
    Model(Box<FieldValue>), // For nested models
    None,
}

impl FieldValue {
    /// Convert Rust FieldValue to Python object
    pub fn to_python(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match self {
            FieldValue::Int(i) => Ok(i.into_pyobject(py)?.into_any().unbind()),
            FieldValue::Float(f) => Ok(f.into_pyobject(py)?.into_any().unbind()),
            FieldValue::String(s) => Ok(s.into_pyobject(py)?.into_any().unbind()),
            FieldValue::Bool(b) => {
                // For bool, we need to use PyBool::new and unbind directly
                Ok(PyBool::new(py, *b).as_any().clone().unbind())
            }
            FieldValue::List(items) => {
                let py_list = PyList::empty(py);
                for item in items {
                    py_list.append(item.to_python(py)?)?;
                }
                Ok(py_list.into_any().unbind())
            }
            FieldValue::Dict(map) => {
                let py_dict = PyDict::new(py);
                for (k, v) in map {
                    py_dict.set_item(k, v.to_python(py)?)?;
                }
                Ok(py_dict.into_any().unbind())
            }
            FieldValue::Model(inner) => inner.to_python(py),
            FieldValue::None => Ok(py.None()),
        }
    }

    /// Extract FieldValue from Python object with type coercion
    pub fn from_python(py: Python<'_>, value: &Bound<'_, PyAny>, expected_type: &FieldType) -> PyResult<Self> {
        // Handle None first
        if value.is_none() {
            return Ok(FieldValue::None);
        }

        match expected_type {
            FieldType::Int => {
                // Try int first
                if let Ok(i) = value.extract::<i64>() {
                    return Ok(FieldValue::Int(i));
                }
                // Try float -> int coercion
                if let Ok(f) = value.extract::<f64>() {
                    return Ok(FieldValue::Int(f as i64));
                }
                // Try string -> int coercion
                if let Ok(s) = value.extract::<String>() {
                    if let Ok(i) = s.parse::<i64>() {
                        return Ok(FieldValue::Int(i));
                    }
                }
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Cannot convert to integer"
                ))
            }
            FieldType::Float => {
                // Try float first
                if let Ok(f) = value.extract::<f64>() {
                    return Ok(FieldValue::Float(f));
                }
                // Try int -> float coercion
                if let Ok(i) = value.extract::<i64>() {
                    return Ok(FieldValue::Float(i as f64));
                }
                // Try string -> float coercion
                if let Ok(s) = value.extract::<String>() {
                    if let Ok(f) = s.parse::<f64>() {
                        return Ok(FieldValue::Float(f));
                    }
                }
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Cannot convert to float"
                ))
            }
            FieldType::String => {
                // Try string first
                if let Ok(s) = value.extract::<String>() {
                    return Ok(FieldValue::String(s));
                }
                // Coerce other types to string
                let s = value.str()?.to_string();
                Ok(FieldValue::String(s))
            }
            FieldType::Bool => {
                // Strict boolean check (no coercion from int)
                if value.is_instance_of::<PyBool>() {
                    let b = value.extract::<bool>()?;
                    return Ok(FieldValue::Bool(b));
                }
                Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Expected boolean"
                ))
            }
            FieldType::List(inner_type) => {
                let py_list = value.downcast::<PyList>()?;
                let mut items = Vec::with_capacity(py_list.len());
                for item in py_list.iter() {
                    items.push(Self::from_python(py, &item, inner_type)?);
                }
                Ok(FieldValue::List(items))
            }
            FieldType::Dict(inner_type) => {
                let py_dict = value.downcast::<PyDict>()?;
                let mut map = HashMap::new();
                for (k, v) in py_dict.iter() {
                    let key = k.extract::<String>()?;
                    let val = Self::from_python(py, &v, inner_type)?;
                    map.insert(key, val);
                }
                Ok(FieldValue::Dict(map))
            }
            FieldType::Any => {
                // Best-effort type detection
                if value.is_instance_of::<PyBool>() {
                    Ok(FieldValue::Bool(value.extract()?))
                } else if value.is_instance_of::<PyInt>() {
                    Ok(FieldValue::Int(value.extract()?))
                } else if value.is_instance_of::<PyFloat>() {
                    Ok(FieldValue::Float(value.extract()?))
                } else if value.is_instance_of::<PyString>() {
                    Ok(FieldValue::String(value.extract()?))
                } else if value.is_instance_of::<PyList>() {
                    let py_list = value.downcast::<PyList>()?;
                    let mut items = Vec::with_capacity(py_list.len());
                    for item in py_list.iter() {
                        items.push(Self::from_python(py, &item, &FieldType::Any)?);
                    }
                    Ok(FieldValue::List(items))
                } else if value.is_instance_of::<PyDict>() {
                    let py_dict = value.downcast::<PyDict>()?;
                    let mut map = HashMap::new();
                    for (k, v) in py_dict.iter() {
                        let key = k.extract::<String>()?;
                        let val = Self::from_python(py, &v, &FieldType::Any)?;
                        map.insert(key, val);
                    }
                    Ok(FieldValue::Dict(map))
                } else {
                    Ok(FieldValue::None)
                }
            }
        }
    }

    /// Serialize to JSON string
    pub fn to_json(&self) -> String {
        match self {
            FieldValue::Int(i) => i.to_string(),
            FieldValue::Float(f) => f.to_string(),
            FieldValue::String(s) => format!("\"{}\"", s.replace('"', "\\\"")),
            FieldValue::Bool(b) => b.to_string(),
            FieldValue::List(items) => {
                let items_json: Vec<String> = items.iter().map(|v| v.to_json()).collect();
                format!("[{}]", items_json.join(","))
            }
            FieldValue::Dict(map) => {
                let items_json: Vec<String> = map
                    .iter()
                    .map(|(k, v)| format!("\"{}\":{}", k, v.to_json()))
                    .collect();
                format!("{{{}}}", items_json.join(","))
            }
            FieldValue::Model(inner) => inner.to_json(),
            FieldValue::None => "null".to_string(),
        }
    }
}

/// Field type definition
#[derive(Clone, Debug)]
pub enum FieldType {
    Int,
    Float,
    String,
    Bool,
    List(Box<FieldType>),
    Dict(Box<FieldType>),
    Any,
}

impl FieldType {
    /// Parse field type from Python type annotation
    pub fn from_python_type(py: Python<'_>, type_obj: &Bound<'_, PyAny>) -> PyResult<Self> {
        let type_str = type_obj.str()?.to_string();
        
        // Handle basic types
        if type_str.contains("int") {
            return Ok(FieldType::Int);
        }
        if type_str.contains("float") {
            return Ok(FieldType::Float);
        }
        if type_str.contains("str") {
            return Ok(FieldType::String);
        }
        if type_str.contains("bool") {
            return Ok(FieldType::Bool);
        }
        if type_str.contains("list") || type_str.contains("List") {
            // TODO: Extract inner type
            return Ok(FieldType::List(Box::new(FieldType::Any)));
        }
        if type_str.contains("dict") || type_str.contains("Dict") {
            // TODO: Extract inner type
            return Ok(FieldType::Dict(Box::new(FieldType::Any)));
        }
        
        // Default to Any
        Ok(FieldType::Any)
    }
}
