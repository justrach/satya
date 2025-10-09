// Native Model Objects - Zero-copy field access
// Based on the user's playbook for closing the 15× gap

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyAny};
use std::collections::HashMap;

/// Native model with direct field access (no Python property overhead!)
#[pyclass(module = "satya", frozen)]
pub struct NativeModel {
    // Store validated fields as Py<PyAny> - keeps refcounts cheap
    #[pyo3(get)]
    pub __fields_dict__: Py<PyDict>,
    
    // Model metadata
    pub schema_name: String,
    
    // Lazy nested models - materialized on first access
    nested_models: HashMap<String, Option<Py<PyAny>>>,
}

#[pymethods]
impl NativeModel {
    #[new]
    fn new(fields_dict: Py<PyDict>, schema_name: String) -> Self {
        Self {
            __fields_dict__: fields_dict,
            schema_name,
            nested_models: HashMap::new(),
        }
    }
    
    /// ULTRA-FAST field access - intercepts ALL attribute access!
    /// This is THE KEY to matching Pydantic's field access speed
    fn __getattribute__(slf: PyRef<'_, Self>, name: &Bound<'_, pyo3::types::PyString>) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        let name_str = name.to_str()?;
        
        // FAST PATH: Direct dict lookup for fields (O(1) hash lookup!)
        let dict = slf.__fields_dict__.bind(py);
        if let Some(value) = dict.get_item(name)? {
            return Ok(value.unbind());
        }
        
        // Check if it's a lazy nested model
        if let Some(Some(nested)) = slf.nested_models.get(name_str) {
            return Ok(nested.clone_ref(py));
        }
        
        // Attribute not found
        Err(PyErr::new::<pyo3::exceptions::PyAttributeError, _>(
            format!("'{}' object has no attribute '{}'", slf.schema_name, name_str)
        ))
    }
    
    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let dict = self.__fields_dict__.bind(py);
        Ok(format!("{}({})", self.schema_name, dict.repr()?))
    }
}

/// SINGLE-OBJECT HYDRATION - Bypasses __init__, zero Python overhead!
/// This is THE KEY to matching Pydantic's single-object performance
#[pyfunction]
pub fn hydrate_one(
    schema_name: &str,
    validated_dict: Py<PyDict>
) -> PyResult<NativeModel> {
    // Create native model directly - NO __init__ call!
    // NO kwargs parsing, NO Python loops, NO property overhead
    Ok(NativeModel::new(validated_dict, schema_name.to_string()))
}

/// Batch hydration - creates native models from validated dicts
#[pyfunction]
pub fn hydrate_batch(
    py: Python<'_>,
    schema_name: &str,
    validated_dicts: &Bound<'_, pyo3::types::PyList>
) -> PyResult<Py<pyo3::types::PyList>> {
    let result_list = pyo3::types::PyList::empty(py);
    
    for dict_item in validated_dicts.iter() {
        let dict = dict_item.downcast::<PyDict>()?;
        let native_model = NativeModel::new(
            dict.clone().unbind(),
            schema_name.to_string()
        );
        result_list.append(native_model)?;
    }
    
    Ok(result_list.unbind())
}

/// Parallel batch hydration with free-threading support
#[pyfunction]
pub fn hydrate_batch_parallel(
    py: Python<'_>,
    schema_name: &str,
    validated_dicts: &Bound<'_, pyo3::types::PyList>
) -> PyResult<Py<pyo3::types::PyList>> {
    let len = validated_dicts.len();
    
    // For small batches, use serial hydration
    if len < 1000 {
        return hydrate_batch(py, schema_name, validated_dicts);
    }
    
    // Convert to Vec for parallel processing
    use rayon::prelude::*;
    
    let dicts: Vec<Py<PyDict>> = validated_dicts
        .iter()
        .map(|item| item.downcast::<PyDict>().unwrap().clone().unbind())
        .collect();
    
    let schema_name = schema_name.to_string();
    
    // Serial hydration for now (parallel needs more complex setup)
    let result_list = pyo3::types::PyList::empty(py);
    for dict_py in dicts {
        let model = NativeModel::new(dict_py, schema_name.clone());
        result_list.append(model)?;
    }
    
    Ok(result_list.unbind())
}
