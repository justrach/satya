// Rust-native model instance - the core of the new architecture
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyType, PyList};
use std::sync::Arc;
use rayon::prelude::*;

use crate::field_value::FieldValue;
use crate::schema_compiler::CompiledSchema;

/// Rust-native model instance
/// This replaces Python dict with native Rust storage for maximum performance
#[pyclass(name = "SatyaModelInstance")]
pub struct SatyaModelInstance {
    fields: Vec<FieldValue>,
    schema: Arc<CompiledSchema>,
}

#[pymethods]
impl SatyaModelInstance {
    /// Create a new model instance from kwargs
    #[new]
    #[pyo3(signature = (**kwargs))]
    fn new(py: Python<'_>, kwargs: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        // Get the schema from the class (will be set by metaclass)
        // For now, we'll create a dummy schema
        // TODO: Get schema from class attribute
        
        let schema = Arc::new(CompiledSchema {
            name: "DummyModel".to_string(),
            fields: vec![],
            field_map: std::collections::HashMap::new(),
        });
        
        let fields = Vec::new();
        
        Ok(Self { fields, schema })
    }

    /// Create instance from dict with validation
    #[staticmethod]
    fn from_dict(
        py: Python<'_>,
        schema: &CompiledSchema,
        data: &Bound<'_, PyDict>,
    ) -> PyResult<Self> {
        let mut fields = Vec::with_capacity(schema.fields.len());
        
        // Extract and validate each field
        for field in &schema.fields {
            let value = match data.get_item(&field.name)? {
                Some(v) if v.is_none() => {
                    if field.required {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Field '{}' is required", field.name)
                        ));
                    }
                    FieldValue::None
                }
                Some(v) => {
                    // Extract and convert to Rust type
                    FieldValue::from_python(py, &v, &field.field_type)?
                }
                None if field.required => {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Field '{}' is missing", field.name)
                    ));
                }
                None => FieldValue::None,
            };
            
            fields.push(value);
        }
        
        // Validate all constraints in Rust
        if let Err(errors) = schema.validate(&fields) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                errors.join("; ")
            ));
        }
        
        Ok(Self {
            fields,
            schema: Arc::new(schema.clone()),
        })
    }

    /// Get field value by name
    fn get_field(&self, py: Python<'_>, name: &str) -> PyResult<Py<PyAny>> {
        if let Some(&idx) = self.schema.field_map.get(name) {
            return self.fields[idx].to_python(py);
        }
        Err(PyErr::new::<pyo3::exceptions::PyAttributeError, _>(
            format!("'{}' object has no field '{}'", self.schema.name, name)
        ))
    }

    /// Set field value by name with validation
    fn set_field(&mut self, py: Python<'_>, name: &str, value: Py<PyAny>) -> PyResult<()> {
        if let Some(&idx) = self.schema.field_map.get(name) {
            let field = &self.schema.fields[idx];
            
            // Validate in Rust
            let validated = FieldValue::from_python(py, value.bind(py), &field.field_type)?;
            
            // Validate constraints
            if let Err(e) = field.constraints.validate(&validated) {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(e));
            }
            
            // Update Rust field
            self.fields[idx] = validated;
            return Ok(());
        }
        
        Err(PyErr::new::<pyo3::exceptions::PyAttributeError, _>(
            format!("'{}' object has no field '{}'", self.schema.name, name)
        ))
    }

    /// Convert to Python dict
    fn dict(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        
        for (field, value) in self.schema.fields.iter().zip(self.fields.iter()) {
            dict.set_item(&field.name, value.to_python(py)?)?;
        }
        
        Ok(dict.unbind())
    }

    /// Convert to JSON string
    fn json(&self, py: Python<'_>) -> PyResult<String> {
        let mut json = String::from("{");
        
        for (i, (field, value)) in self.schema.fields.iter().zip(self.fields.iter()).enumerate() {
            if i > 0 {
                json.push(',');
            }
            json.push_str(&format!("\"{}\":", field.name));
            json.push_str(&value.to_json());
        }
        
        json.push('}');
        Ok(json)
    }

    /// String representation
    fn __repr__(&self) -> PyResult<String> {
        Ok(format!("{}(...)", self.schema.name))
    }

    /// String representation
    fn __str__(&self) -> PyResult<String> {
        self.__repr__()
    }
}

/// Batch validation for multiple instances
#[pyfunction]
pub fn validate_batch_native(
    py: Python<'_>,
    schema: &CompiledSchema,
    data_list: &Bound<'_, PyList>,
) -> PyResult<Vec<SatyaModelInstance>> {
    let len = data_list.len();
    let mut results = Vec::with_capacity(len);
    
    // Sequential validation (parallel requires Send+Sync which PyO3 types don't have)
    for item in data_list.iter() {
        let dict = item.downcast::<PyDict>()?;
        results.push(SatyaModelInstance::from_dict(py, schema, dict)?);
    }
    
    Ok(results)
}

/// Parallel batch validation (for large batches without GIL)
/// This extracts data to Rust first, then validates in parallel
#[pyfunction]
pub fn validate_batch_parallel(
    py: Python<'_>,
    schema: &CompiledSchema,
    data_list: &Bound<'_, PyList>,
) -> PyResult<Vec<SatyaModelInstance>> {
    let len = data_list.len();
    
    // Extract all data to Rust structures first (with GIL)
    let mut raw_data: Vec<Vec<(String, FieldValue)>> = Vec::with_capacity(len);
    for item in data_list.iter() {
        let dict = item.downcast::<PyDict>()?;
        let mut row = Vec::new();
        
        for field in &schema.fields {
            let value = match dict.get_item(&field.name)? {
                Some(v) if v.is_none() => FieldValue::None,
                Some(v) => FieldValue::from_python(py, &v, &field.field_type)?,
                None => FieldValue::None,
            };
            row.push((field.name.clone(), value));
        }
        raw_data.push(row);
    }
    
    // Release GIL and validate in parallel
    let schema_arc = Arc::new(schema.clone());
    let results: Result<Vec<_>, String> = py.allow_threads(|| {
        raw_data.par_iter().map(|row| {
            let mut fields = Vec::with_capacity(schema_arc.fields.len());
            
            for (field_name, value) in row {
                fields.push(value.clone());
            }
            
            // Validate in parallel
            schema_arc.validate(&fields).map_err(|e| e.join("; "))?;
            
            Ok(SatyaModelInstance {
                fields,
                schema: schema_arc.clone(),
            })
        }).collect()
    });
    
    results.map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e))
}

/// Compile a schema from a Python class
#[pyfunction]
pub fn compile_schema(py: Python<'_>, py_class: &Bound<'_, PyType>) -> PyResult<CompiledSchema> {
    CompiledSchema::from_python_class(py, py_class)
}
