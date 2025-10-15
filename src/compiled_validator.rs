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
    // Numeric constraints
    pub gt: Option<f64>,
    pub ge: Option<f64>,
    pub lt: Option<f64>,
    pub le: Option<f64>,
    // String constraints
    pub min_length: Option<usize>,
    pub max_length: Option<usize>,
    pub pattern: Option<String>,
    // List constraints
    pub min_items: Option<usize>,
    pub max_items: Option<usize>,
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
                gt: None,
                ge: None,
                lt: None,
                le: None,
                min_length: None,
                max_length: None,
                pattern: None,
                min_items: None,
                max_items: None,
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
        
        // CRITICAL: Rebuild field_indices after sorting!
        field_indices.clear();
        for (idx, field) in fields.iter().enumerate() {
            field_indices.insert(field.name.clone(), idx);
        }
        
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
                
                // Validate constraints based on type
                match field.field_type {
                    CompiledFieldType::Int | CompiledFieldType::Float => {
                        if let Ok(num_val) = value.extract::<f64>() {
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
                        }
                    }
                    CompiledFieldType::String => {
                        // Extract string value for constraint validation
                        let str_val = value.extract::<String>().map_err(|_| {
                            PyErr::new::<pyo3::exceptions::PyValueError, _>(
                                format!("Field '{}' must be a string", field.name)
                            )
                        })?;
                        
                        // For min_length, check trimmed string (matches Python behavior)
                        if let Some(min_len) = field.min_length {
                            let trimmed_len = str_val.trim().len();
                            if trimmed_len < min_len {
                                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                                    format!("Field '{}' must have at least {} characters", field.name, min_len)
                                ));
                            }
                        }
                        // For max_length, check original string (matches Python behavior)
                        if let Some(max_len) = field.max_length {
                            if str_val.len() > max_len {
                                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                                    format!("Field '{}' must have at most {} characters", field.name, max_len)
                                ));
                            }
                        }
                        // Pattern validation would go here (requires regex crate)
                    }
                    CompiledFieldType::List => {
                        if let Ok(list) = value.downcast::<PyList>() {
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
                        }
                    }
                    _ => {}
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
    
    /// Set constraints for a specific field
    fn set_field_constraints(
        &mut self,
        field_name: String,
        gt: Option<f64>,
        ge: Option<f64>,
        lt: Option<f64>,
        le: Option<f64>,
        min_length: Option<usize>,
        max_length: Option<usize>,
        pattern: Option<String>,
        min_items: Option<usize>,
        max_items: Option<usize>,
    ) -> PyResult<()> {
        if let Some(idx) = self.0.field_indices.get(&field_name) {
            if let Some(field) = self.0.fields.get_mut(*idx) {
                field.gt = gt;
                field.ge = ge;
                field.lt = lt;
                field.le = le;
                field.min_length = min_length;
                field.max_length = max_length;
                field.pattern = pattern;
                field.min_items = min_items;
                field.max_items = max_items;
                return Ok(());
            }
        }
        Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(
            format!("Field '{}' not found", field_name)
        ))
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
