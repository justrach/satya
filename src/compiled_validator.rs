// BLAZE-STYLE Compiled Validator
// Precompiles schemas into optimized validation instructions
// Based on: Blaze: Compiling JSON Schema for 10× Faster Validation (arXiv:2503.02770v2)

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString, PyInt, PyFloat, PyBool, PyList, PyAny};
use std::collections::HashMap;
use rayon::prelude::*;

/// Compiled field validator - specialized for each field
#[derive(Clone)]
pub struct CompiledField {
    pub name: String,
    pub field_type: CompiledFieldType,
    pub required: bool,
    pub check_order: usize, // For instruction reordering
}

#[derive(Clone, Debug)]
pub enum CompiledFieldType {
    String,
    Int,
    Float,
    Bool,
    List,
    Dict,
    Any,
}

/// BLAZE-STYLE: Compiled validator with optimized instruction ordering
pub struct CompiledValidator {
    fields: Vec<CompiledField>,
    field_count: usize,
    // Semi-perfect hash map for O(1) field lookup
    field_indices: HashMap<String, usize>,
}

impl CompiledValidator {
    /// Compile a schema into optimized validation instructions
    pub fn compile(schema: Vec<(String, String, bool)>) -> Self {
        let mut fields = Vec::new();
        let mut field_indices = HashMap::new();
        
        for (idx, (name, type_str, required)) in schema.iter().enumerate() {
            let field_type = match type_str.as_str() {
                "str" => CompiledFieldType::String,
                "int" => CompiledFieldType::Int,
                "float" => CompiledFieldType::Float,
                "bool" => CompiledFieldType::Bool,
                "list" => CompiledFieldType::List,
                "dict" => CompiledFieldType::Dict,
                _ => CompiledFieldType::Any,
            };
            
            fields.push(CompiledField {
                name: name.clone(),
                field_type,
                required: *required,
                check_order: idx,
            });
            
            field_indices.insert(name.clone(), idx);
        }
        
        // BLAZE OPTIMIZATION: Reorder instructions - simple checks first!
        fields.sort_by_key(|f| {
            match f.field_type {
                CompiledFieldType::Int => 0,    // Fastest
                CompiledFieldType::Bool => 1,
                CompiledFieldType::Float => 2,
                CompiledFieldType::String => 3,
                CompiledFieldType::List => 4,
                CompiledFieldType::Dict => 5,
                CompiledFieldType::Any => 6,    // Slowest
            }
        });
        
        let field_count = fields.len();
        
        Self {
            fields,
            field_count,
            field_indices,
        }
    }
    
    /// BLAZE-STYLE: Validate with specialized, inlined checks
    #[inline(always)]
    pub fn validate_fast(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
        // BLAZE OPTIMIZATION: Pre-allocate result dict
        let validated = PyDict::new(py);
        
        // BLAZE OPTIMIZATION: Unroll loop for small models (≤5 fields)
        if self.field_count <= 5 {
            return self.validate_unrolled(py, data, validated.clone());
        }
        
        // For larger models, use optimized loop
        for field in &self.fields {
            self.validate_field_inline(py, data, &validated, field)?;
        }
        
        Ok(validated.unbind())
    }
    
    /// BLAZE OPTIMIZATION: Unrolled validation for small models
    #[inline(always)]
    fn validate_unrolled(&self, py: Python<'_>, data: &Bound<'_, PyDict>, validated: Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
        // Manually unroll up to 5 fields to avoid loop overhead
        if let Some(f0) = self.fields.get(0) {
            self.validate_field_inline(py, data, &validated, f0)?;
        }
        if let Some(f1) = self.fields.get(1) {
            self.validate_field_inline(py, data, &validated, f1)?;
        }
        if let Some(f2) = self.fields.get(2) {
            self.validate_field_inline(py, data, &validated, f2)?;
        }
        if let Some(f3) = self.fields.get(3) {
            self.validate_field_inline(py, data, &validated, f3)?;
        }
        if let Some(f4) = self.fields.get(4) {
            self.validate_field_inline(py, data, &validated, f4)?;
        }
        
        Ok(validated.unbind())
    }
    
    /// BLAZE OPTIMIZATION: Inline field validation (no function call overhead)
    #[inline(always)]
    fn validate_field_inline(&self, _py: Python<'_>, data: &Bound<'_, PyDict>, validated: &Bound<'_, PyDict>, field: &CompiledField) -> PyResult<()> {
        match data.get_item(&field.name)? {
            Some(value) => {
                // BLAZE OPTIMIZATION: is_exact_instance_of for fastest type check
                let type_ok = match field.field_type {
                    CompiledFieldType::String => value.is_exact_instance_of::<PyString>(),
                    CompiledFieldType::Int => value.is_exact_instance_of::<PyInt>() && !value.is_instance_of::<PyBool>(),
                    CompiledFieldType::Float => value.is_exact_instance_of::<PyFloat>() || value.is_exact_instance_of::<PyInt>(),
                    CompiledFieldType::Bool => value.is_exact_instance_of::<PyBool>(),
                    CompiledFieldType::List => value.is_exact_instance_of::<PyList>(),
                    CompiledFieldType::Dict => value.is_exact_instance_of::<PyDict>(),
                    CompiledFieldType::Any => true,
                };
                
                if !type_ok {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Field '{}' has incorrect type", field.name)
                    ));
                }
                
                validated.set_item(&field.name, &value)?;
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
}

#[pyclass]
pub struct BlazeCompiledValidator(pub CompiledValidator);

#[pymethods]
impl BlazeCompiledValidator {
    #[new]
    fn new() -> Self {
        Self(CompiledValidator {
            fields: Vec::new(),
            field_count: 0,
            field_indices: HashMap::new(),
        })
    }
    
    fn compile_schema(&mut self, schema: Vec<(String, String, bool)>) {
        self.0 = CompiledValidator::compile(schema);
    }
    
    fn validate_fast(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
        self.0.validate_fast(py, data)
    }
    
    /// SINGLE-OBJECT FAST PATH - Validate and return dict (optimized for latency!)
    /// This is the N=1 case of batch processing, reusing the same optimized code
    fn validate_one(&self, py: Python<'_>, data: &Bound<'_, PyDict>) -> PyResult<Py<PyDict>> {
        // Reuse the batch-optimized validator for single object
        // Same fast path, zero Python overhead!
        self.0.validate_fast(py, data)
    }
    
    /// PARALLEL BATCH VALIDATION - Process multiple records at once!
    /// Uses PyO3 0.26+ free-threading for Python 3.13+ (backwards compatible)
    fn validate_batch(&self, py: Python<'_>, data_list: &Bound<'_, PyList>) -> PyResult<Py<PyList>> {
        let len = data_list.len();
        
        // For small batches, don't use parallelization (overhead not worth it)
        if len < 1000 {
            let result_list = PyList::empty(py);
            for item in data_list.iter() {
                let dict = item.downcast::<PyDict>()?;
                let validated = self.0.validate_fast(py, dict)?;
                result_list.append(validated)?;
            }
            return Ok(result_list.unbind());
        }
        
        // Convert Python list to Vec of Py<PyDict> for parallel processing
        let dicts: Vec<Py<PyDict>> = data_list
            .iter()
            .map(|item| item.downcast::<PyDict>().unwrap().clone().unbind())
            .collect();
        
        // PARALLEL VALIDATION with rayon!
        // PyO3 0.26+: Use py.detach() for free-threading support
        // Process in chunks to amortize GIL acquisition cost
        const CHUNK_SIZE: usize = 1000;
        
        // Detach from Python for parallel processing
        let results: Vec<Vec<Py<PyDict>>> = py.detach(|| {
            dicts.par_chunks(CHUNK_SIZE)
                .map(|chunk| {
                    // Attach to Python once per chunk (PyO3 0.26+ API)
                    #[cfg(Py_GIL_DISABLED)]
                    {
                        // Free-threaded Python 3.13+: No GIL needed!
                        Python::attach(|py| {
                            chunk.iter()
                                .map(|dict_py| {
                                    let dict = dict_py.bind(py);
                                    self.0.validate_fast(py, dict)
                                })
                                .collect::<PyResult<Vec<_>>>()
                        })
                    }
                    #[cfg(not(Py_GIL_DISABLED))]
                    {
                        // Python 3.12 and earlier: Acquire GIL
                        Python::with_gil(|py| {
                            chunk.iter()
                                .map(|dict_py| {
                                    let dict = dict_py.bind(py);
                                    self.0.validate_fast(py, dict)
                                })
                                .collect::<PyResult<Vec<_>>>()
                        })
                    }
                })
                .collect::<PyResult<Vec<_>>>()
                .unwrap()
        });
        
        // Flatten and collect results into a Python list
        let result_list = PyList::empty(py);
        for chunk_results in results {
            for result in chunk_results {
                result_list.append(result)?;
            }
        }
        
        Ok(result_list.unbind())
    }
}
