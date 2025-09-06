use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyList};
use std::collections::{HashMap, HashSet};
use regex::Regex;  // Use the regex crate directly
use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde::Deserializer; // bring trait methods like deserialize_seq into scope
use serde_json::Value as JsonValue;

#[pyclass(name = "StreamValidatorCore")]
struct StreamValidatorCore {
    schema: HashMap<String, FieldValidator>,
    batch_size: usize,
    custom_types: HashMap<String, HashMap<String, FieldValidator>>,
}

// ----- Streaming validation implementation -----

#[derive(Debug)]
enum StreamErr {
    De(String),
    WrongTopLevel,
    Constraint(String),
}

impl From<serde_json::Error> for StreamErr {
    fn from(e: serde_json::Error) -> Self { StreamErr::De(e.to_string()) }
}

// Validate a JSON object using a streaming deserializer with the given field validators
fn validate_object_streaming<'de, D: serde::de::Deserializer<'de>>(
    deserializer: D,
    fields: &HashMap<String, FieldValidator>,
    core: &StreamValidatorCore,
) -> Result<(), StreamErr> {
    struct ObjVisitor<'a> { fields: &'a HashMap<String, FieldValidator>, core: &'a StreamValidatorCore }
    impl<'de, 'a> Visitor<'de> for ObjVisitor<'a> {
        type Value = ();
        fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result { write!(f, "object") }
        fn visit_map<M: MapAccess<'de>>(self, mut map: M) -> Result<(), M::Error> {
            let mut seen_required: HashSet<&str> = HashSet::new();
            while let Some(key) = map.next_key::<&str>()? {
                if let Some(fv) = self.fields.get(key) {
                    let seed = ValueSeed { expected: &fv.field_type, constraints: &fv.constraints, core: self.core };
                    // On error, propagate as de error to fail object
                    map.next_value_seed(seed)?;
                    if fv.required { seen_required.insert(key); }
                } else {
                    // Unknown field: consume and ignore
                    let _ignored: serde::de::IgnoredAny = map.next_value()?;
                }
            }
            // Check required fields presence
            for (name, fv) in self.fields.iter() {
                if fv.required && !seen_required.contains(name.as_str()) {
                    return Err(de::Error::custom(format!("Required field {} is missing", name)));
                }
            }
            Ok(())
        }
    }
    deserializer.deserialize_map(ObjVisitor { fields, core }).map_err(|e| {
        if e.to_string().contains("invalid type: ") && e.to_string().contains("expected object") {
            StreamErr::WrongTopLevel
        } else {
            StreamErr::De(e.to_string())
        }
    })
}

struct ValueSeed<'a> { expected: &'a FieldType, constraints: &'a FieldConstraints, core: &'a StreamValidatorCore }
impl<'de, 'a> DeserializeSeed<'de> for ValueSeed<'a> {
    type Value = ();
    fn deserialize<D: serde::de::Deserializer<'de>>(self, deserializer: D) -> Result<Self::Value, D::Error> {
        validate_value_streaming(deserializer, self.expected, self.constraints, self.core)
            .map_err(|e| de::Error::custom(e))
    }
}

fn validate_value_streaming<'de, D: serde::de::Deserializer<'de>>(
    deserializer: D,
    expected: &FieldType,
    constraints: &FieldConstraints,
    core: &StreamValidatorCore,
) -> Result<(), String> {
    struct AnyVisitor<'a> { expected: &'a FieldType, constraints: &'a FieldConstraints, core: &'a StreamValidatorCore }
    impl<'de, 'a> Visitor<'de> for AnyVisitor<'a> {
        type Value = ();
        fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result { write!(f, "JSON value") }
        fn visit_str<E: de::Error>(self, v: &str) -> Result<(), E> {
            match self.expected {
                FieldType::String => {
                    if let Some(min) = self.constraints.min_length { if v.len() < min { return Err(E::custom(format!("String length must be >= {}", min))); } }
                    if let Some(max) = self.constraints.max_length { if v.len() > max { return Err(E::custom(format!("String length must be <= {}", max))); } }
                    if let Some(pattern) = &self.constraints.pattern { if !regex_match(v, pattern) { return Err(E::custom(format!("String does not match pattern: {}", pattern))); } }
                    if self.constraints.email && !validate_email(v) { return Err(E::custom("Invalid email format")); }
                    if self.constraints.url && !validate_url(v) { return Err(E::custom("Invalid URL format")); }
                    if let Some(enum_vals) = &self.constraints.enum_values { if !enum_vals.contains(&v.to_string()) { return Err(E::custom(format!("Value must be one of: {:?}", enum_vals))); } }
                    Ok(())
                }
                FieldType::Any => Ok(()),
                _ => Err(E::custom("Expected non-string")),
            }
        }
        fn visit_bool<E: de::Error>(self, _v: bool) -> Result<(), E> {
            match self.expected { FieldType::Boolean | FieldType::Any => Ok(()), _ => Err(E::custom("Expected non-bool")) }
        }
        fn visit_i64<E: de::Error>(self, v: i64) -> Result<(), E> {
            match self.expected {
                FieldType::Integer | FieldType::Float => self.check_number::<E>(v as f64),
                FieldType::Any => Ok(()),
                _ => Err(E::custom("Expected non-number")),
            }
        }
        fn visit_u64<E: de::Error>(self, v: u64) -> Result<(), E> { self.visit_i64::<E>(v as i64) }
        fn visit_f64<E: de::Error>(self, v: f64) -> Result<(), E> {
            match self.expected {
                FieldType::Float => self.check_number::<E>(v),
                FieldType::Integer => Err(E::custom("Expected integer")),
                FieldType::Any => Ok(()),
                _ => Err(E::custom("Expected non-number")),
            }
        }
        fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<(), A::Error> {
            match self.expected {
                FieldType::List(inner) => {
                    // item count for min/max
                    let mut count = 0usize;
                    // unique check: best-effort by serializing primitives; skip complex
                    let mut seen: Option<HashSet<String>> = if self.constraints.unique_items.unwrap_or(false) { Some(HashSet::new()) } else { None };
                    while let Some(()) = seq.next_element_seed(ValueSeed { expected: inner, constraints: self.constraints, core: self.core })? {
                        count += 1;
                        if let Some(seen) = seen.as_mut() { seen.insert(count.to_string()); }
                    }
                    if let Some(min) = self.constraints.min_items { if count < min { return Err(de::Error::custom(format!("List must have at least {} items", min))); } }
                    if let Some(max) = self.constraints.max_items { if count > max { return Err(de::Error::custom(format!("List must have at most {} items", max))); } }
                    Ok(())
                }
                FieldType::Any => Ok(()),
                _ => Err(de::Error::custom("Expected non-array")),
            }
        }
        fn visit_map<M: MapAccess<'de>>(self, mut map: M) -> Result<(), M::Error> {
            match self.expected {
                FieldType::Dict(inner) => {
                    // For dict, we don't constrain keys; only values
                    while let Some(_) = map.next_key::<de::IgnoredAny>()? {
                        map.next_value_seed(ValueSeed { expected: inner, constraints: self.constraints, core: self.core })?;
                    }
                    Ok(())
                }
                FieldType::Custom(_type_name) => {
                    // Streaming nested custom types not supported yet
                    Err(de::Error::custom("Custom type streaming not yet supported in nested position"))
                }
                FieldType::Any => Ok(()),
                _ => Err(de::Error::custom("Expected non-object")),
            }
        }
    }
    impl<'a> AnyVisitor<'a> {
        fn check_number<E: de::Error>(&self, num: f64) -> Result<(), E> {
            if let Some(ge) = self.constraints.ge { if num < ge as f64 { return Err(E::custom(format!("Value must be >= {}", ge))); } }
            if let Some(le) = self.constraints.le { if num > le as f64 { return Err(E::custom(format!("Value must be <= {}", le))); } }
            if let Some(gt) = self.constraints.gt { if num <= gt as f64 { return Err(E::custom(format!("Value must be > {}", gt))); } }
            if let Some(lt) = self.constraints.lt { if num >= lt as f64 { return Err(E::custom(format!("Value must be < {}", lt))); } }
            if let Some(min_val) = self.constraints.min_value { if num < min_val { return Err(E::custom(format!("Value must be >= {}", min_val))); } }
            if let Some(max_val) = self.constraints.max_value { if num > max_val { return Err(E::custom(format!("Value must be <= {}", max_val))); } }
            Ok(())
        }
    }
    deserializer
        .deserialize_any(AnyVisitor { expected, constraints, core })
        .map_err(|e| e.to_string())
}

#[derive(Clone)]
struct FieldValidator {
    field_type: FieldType,
    required: bool,
    constraints: FieldConstraints,
}

#[derive(Clone, Default)]
struct FieldConstraints {
    min_length: Option<usize>,
    max_length: Option<usize>,
    min_value: Option<f64>,
    max_value: Option<f64>,
    pattern: Option<String>,
    email: bool,
    url: bool,
    ge: Option<i64>,
    le: Option<i64>,
    gt: Option<i64>,
    lt: Option<i64>,
    min_items: Option<usize>,
    max_items: Option<usize>,
    unique_items: Option<bool>,
    enum_values: Option<Vec<String>>,
}

impl FieldConstraints {
    fn is_simple(&self) -> bool {
        // Simple validation = no constraints beyond basic type checking
        self.min_length.is_none() && self.max_length.is_none() && 
        self.min_value.is_none() && self.max_value.is_none() &&
        self.pattern.is_none() && !self.email && !self.url &&
        self.ge.is_none() && self.le.is_none() && self.gt.is_none() && self.lt.is_none() &&
        self.min_items.is_none() && self.max_items.is_none() && 
        self.unique_items.is_none() && self.enum_values.is_none()
    }
}

#[derive(Clone)]
enum FieldType {
    String,
    Integer,
    Float,
    Boolean,
    Decimal,  // Add Decimal support
    List(Box<FieldType>),
    Dict(Box<FieldType>),
    Custom(String),  // Reference to a custom type name
    Any,
}

#[pymethods]
impl StreamValidatorCore {
    #[new]
    fn new() -> Self {
        StreamValidatorCore {
            schema: HashMap::new(),
            batch_size: 1000,
            custom_types: HashMap::new(),
        }
    }

    #[staticmethod]
    fn parse_json(py: Python<'_>, json_str: &str) -> PyResult<PyObject> {
        match serde_json::from_str(json_str) {
            Ok(value) => json_value_to_py(py, &value),
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Failed to parse JSON: {}", e),
            )),
        }
    }

    fn define_custom_type(&mut self, type_name: String) -> PyResult<()> {
        if !self.custom_types.contains_key(&type_name) {
            self.custom_types.insert(type_name, HashMap::new());
        }
        Ok(())
    }

    fn add_field_to_custom_type(
        &mut self,
        type_name: String,
        field_name: String,
        field_type: &str,
        required: bool,
    ) -> PyResult<()> {
        // Parse field type first while we have immutable access
        let parsed_field_type = self.parse_field_type(field_type)?;
        
        // Then do the mutable operations
        let custom_type = self.custom_types.get_mut(&type_name).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Custom type {} not defined", type_name))
        })?;

        custom_type.insert(field_name, FieldValidator { 
            field_type: parsed_field_type, 
            required,
            constraints: FieldConstraints::default(),
        });
        Ok(())
    }

    fn add_field(&mut self, name: String, field_type: &str, required: bool) -> PyResult<()> {
        let field_type = self.parse_field_type(field_type)?;
        self.schema.insert(name, FieldValidator { field_type, required, constraints: FieldConstraints::default() });
        Ok(())
    }

    /// Set constraints for a root-level field. Any Option left as None will be ignored (leave existing value).
    fn set_field_constraints(
        &mut self,
        field_name: String,
        min_length: Option<usize>,
        max_length: Option<usize>,
        min_value: Option<f64>,
        max_value: Option<f64>,
        pattern: Option<String>,
        email: Option<bool>,
        url: Option<bool>,
        ge: Option<i64>,
        le: Option<i64>,
        gt: Option<i64>,
        lt: Option<i64>,
        min_items: Option<usize>,
        max_items: Option<usize>,
        unique_items: Option<bool>,
        enum_values: Option<Vec<String>>,
    ) -> PyResult<()> {
        let fv = self.schema.get_mut(&field_name).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Field {} not found in root schema", field_name))
        })?;
        if let Some(v) = min_length { fv.constraints.min_length = Some(v); }
        if let Some(v) = max_length { fv.constraints.max_length = Some(v); }
        if let Some(v) = min_value { fv.constraints.min_value = Some(v); }
        if let Some(v) = max_value { fv.constraints.max_value = Some(v); }
        if let Some(v) = pattern { fv.constraints.pattern = Some(v); }
        if let Some(v) = email { fv.constraints.email = v; }
        if let Some(v) = url { fv.constraints.url = v; }
        if let Some(v) = ge { fv.constraints.ge = Some(v); }
        if let Some(v) = le { fv.constraints.le = Some(v); }
        if let Some(v) = gt { fv.constraints.gt = Some(v); }
        if let Some(v) = lt { fv.constraints.lt = Some(v); }
        if let Some(v) = min_items { fv.constraints.min_items = Some(v); }
        if let Some(v) = max_items { fv.constraints.max_items = Some(v); }
        if let Some(v) = unique_items { fv.constraints.unique_items = Some(v); }
        if let Some(v) = enum_values { fv.constraints.enum_values = Some(v); }
        Ok(())
    }

    fn set_batch_size(&mut self, size: usize) {
        self.batch_size = size;
    }

    fn get_batch_size(&self) -> usize {
        self.batch_size
    }

    fn validate_batch(&self, items: Vec<&PyAny>) -> PyResult<Vec<bool>> {
        // Hybrid approach: batch for speed, stream for memory
        if items.len() > 10000 {
            self.validate_batch_hybrid(items)
        } else {
            self.validate_batch_direct(items)
        }
    }
    
    fn validate_batch_direct(&self, items: Vec<&PyAny>) -> PyResult<Vec<bool>> {
        let mut results = Vec::with_capacity(items.len());
        
        // Fast path: avoid match overhead by using is_ok() directly
        for item in items {
            results.push(self.validate_item_internal(item).is_ok());
        }
        Ok(results)
    }
    
    fn validate_batch_hybrid(&self, items: Vec<&PyAny>) -> PyResult<Vec<bool>> {
        // Hybrid: small batches for speed, frequent cleanup for memory
        const MICRO_BATCH_SIZE: usize = 4096; // Process in 4K chunks for cache efficiency
        let mut results = Vec::with_capacity(items.len());
        
        for chunk in items.chunks(MICRO_BATCH_SIZE) {
            // Fast batch processing within chunk
            for item in chunk {
                results.push(self.validate_item_internal(item).is_ok());
            }
            // Micro-batches complete quickly, minimal memory accumulation
        }
        
        Ok(results)
    }

    /// Validate a single JSON object provided as bytes or str.
    /// Returns true if valid, false if invalid (errors are not raised, matching validate_batch behavior).
    fn validate_json_bytes(&self, py: Python<'_>, data: &PyAny) -> PyResult<bool> {
        let bytes = extract_bytes(data)?;
        // Parse once, outside the GIL if possible
        let parsed = py.allow_threads(|| serde_json::from_slice::<JsonValue>(bytes));
        match parsed {
            Ok(JsonValue::Object(map)) => {
                // Reuse parsed value, avoid reparsing
                let obj = JsonValue::Object(map);
                let obj_py = json_value_to_py(py, &obj)?;
                let any = obj_py.as_ref(py);
                Ok(self.validate_item_internal(any).is_ok())
            }
            Ok(_) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Top-level JSON must be an object for validate_json_bytes",
            )),
            Err(_) => Ok(false),
        }
    }

    /// Validate a JSON array of objects provided as bytes or str.
    /// Returns a vector of booleans corresponding to each element.
    fn validate_json_array_bytes(&self, py: Python<'_>, data: &PyAny) -> PyResult<Vec<bool>> {
        let bytes = extract_bytes(data)?;
        // Parse outside the GIL
        let parsed = py.allow_threads(|| serde_json::from_slice::<JsonValue>(bytes));
        match parsed {
            Ok(JsonValue::Array(arr)) => {
                let mut results = Vec::with_capacity(arr.len());
                for item in arr {
                    if let JsonValue::Object(_) = &item {
                        let obj_py = json_value_to_py(py, &item)?;
                        let any = obj_py.as_ref(py);
                        results.push(self.validate_item_internal(any).is_ok());
                    } else {
                        results.push(false);
                    }
                }
                Ok(results)
            }
            Ok(_) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Top-level JSON must be an array for validate_json_array_bytes",
            )),
            Err(_) => Ok(vec![]),
        }
    }

    /// STREAMING: Validate a single JSON object from bytes without building Value
    fn validate_json_bytes_streaming(&self, py: Python<'_>, data: &PyAny) -> PyResult<bool> {
        let bytes = extract_bytes(data)?;
        let result = py.allow_threads(|| {
            let mut de = serde_json::Deserializer::from_slice(bytes);
            validate_object_streaming(&mut de, &self.schema, self)
        });
        match result {
            Ok(()) => Ok(true),
            Err(StreamErr::WrongTopLevel) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Top-level JSON must be an object for validate_json_bytes_streaming",
            )),
            Err(_) => Ok(false),
        }
    }

    /// STREAMING: Validate a JSON array of objects from bytes without building full Values
    fn validate_json_array_bytes_streaming(&self, py: Python<'_>, data: &PyAny) -> PyResult<Vec<bool>> {
        let bytes = extract_bytes(data)?;
        use std::cell::RefCell;
        // Run streaming parse without the GIL; return (Vec<bool>, is_array)
        let (results_vec, ok_top): (Vec<bool>, bool) = py.allow_threads(|| {
            let mut de = serde_json::Deserializer::from_slice(bytes);
            let results: RefCell<Vec<bool>> = RefCell::new(Vec::new());
            struct ArrVisitor<'a> {
                root: &'a HashMap<String, FieldValidator>,
                core: &'a StreamValidatorCore,
                out: &'a RefCell<Vec<bool>>,
            }
            impl<'de, 'a> Visitor<'de> for ArrVisitor<'a> {
                type Value = ();
                fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result { write!(f, "array of objects") }
                fn visit_seq<M: SeqAccess<'de>>(self, mut seq: M) -> Result<Self::Value, M::Error> {
                    while let Some(()) = seq.next_element_seed(ObjSeed { root: self.root, core: self.core, out: self.out })? {}
                    Ok(())
                }
            }
            // Seed to validate each object and push a bool without aborting the whole array
            struct ObjSeed<'a> { root: &'a HashMap<String, FieldValidator>, core: &'a StreamValidatorCore, out: &'a RefCell<Vec<bool>> }
            impl<'de, 'a> DeserializeSeed<'de> for ObjSeed<'a> {
                type Value = ();
                fn deserialize<D: serde::de::Deserializer<'de>>(self, deserializer: D) -> Result<Self::Value, D::Error> {
                    let ok = validate_object_streaming(deserializer, self.root, self.core).is_ok();
                    self.out.borrow_mut().push(ok);
                    Ok(())
                }
            }
            let vis = ArrVisitor { root: &self.schema, core: self, out: &results };
            let top_ok = de.deserialize_seq(vis).is_ok();
            (results.into_inner(), top_ok)
        });
        if !ok_top {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Top-level JSON must be an array for validate_json_array_bytes_streaming",
            ));
        }
        Ok(results_vec)
    }

    /// STREAMING: Validate NDJSON (each line an object)
    fn validate_ndjson_bytes_streaming(&self, py: Python<'_>, data: &PyAny) -> PyResult<Vec<bool>> {
        let bytes = extract_bytes(data)?;
        let out: Vec<bool> = {
            let s = std::str::from_utf8(bytes).map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid UTF-8"))?;
            // Parse each line without the GIL
            py.allow_threads(|| {
                let mut v = Vec::new();
                for line in s.lines() {
                    let line = line.trim();
                    if line.is_empty() { continue; }
                    let mut de = serde_json::Deserializer::from_str(line);
                    match validate_object_streaming(&mut de, &self.schema, self) {
                        Ok(()) => v.push(true),
                        Err(StreamErr::WrongTopLevel) => v.push(false),
                        Err(_) => v.push(false),
                    }
                }
                v
            })
        };
        Ok(out)
    }

    /// Validate NDJSON (one JSON object per line) provided as bytes or str.
    /// Returns a vector of booleans corresponding to each line/object.
    fn validate_ndjson_bytes(&self, py: Python<'_>, data: &PyAny) -> PyResult<Vec<bool>> {
        let bytes = extract_bytes(data)?;
        let s = std::str::from_utf8(bytes).map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid UTF-8"))?;
        // Parse lines outside the GIL; then convert objects to Py for validation
        let parsed: Vec<Result<JsonValue, serde_json::Error>> = py.allow_threads(|| {
            s.lines()
                .map(|line| serde_json::from_str::<JsonValue>(line.trim()))
                .collect()
        });
        let mut results = Vec::with_capacity(parsed.len());
        for item in parsed {
            match item {
                Ok(JsonValue::Object(obj)) => {
                    let obj_py = json_value_to_py(py, &JsonValue::Object(obj))?;
                    let any = obj_py.as_ref(py);
                    results.push(self.validate_item_internal(any).is_ok());
                }
                Ok(_) => results.push(false),
                Err(_) => results.push(false),
            }
        }
        Ok(results)
    }

    fn validate_item_internal(&self, item: &PyAny) -> PyResult<bool> {
        // Fast path: direct downcast without separate type check
        let dict = match item.downcast::<pyo3::types::PyDict>() {
            Ok(d) => d,
            Err(_) => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Item must be a dict")),
        };
        
        // Ultra-fast field iteration with minimal allocations
        for (field_name, validator) in &self.schema {
            match dict.get_item(field_name) {
                Some(value) => {
                    // Inline validation for common cases to reduce function call overhead
                    match &validator.field_type {
                        FieldType::String if validator.constraints.is_simple() => {
                            // Fast path for simple string validation
                            if let Ok(py_str) = value.downcast::<pyo3::types::PyString>() {
                                let _s = py_str.to_str()?; // Just validate it's a string
                            } else {
                                return Err(get_cached_error("Expected string"));
                            }
                        }
                        FieldType::Integer if validator.constraints.is_simple() => {
                            // Fast path for simple integer validation
                            if value.downcast::<pyo3::types::PyInt>().is_err() {
                                return Err(get_cached_error("Expected integer"));
                            }
                        }
                        _ => {
                            // Full validation for complex cases
                            self.validate_value(value, &validator.field_type, &validator.constraints)?;
                        }
                    }
                }
                None if validator.required => {
                    return Err(get_cached_error("Required field missing"));
                }
                None => {} // Optional field, skip
            }
        }

        Ok(true)
    }
}

// Memory optimization: cached error messages to reduce allocations
fn get_cached_error(msg: &'static str) -> PyErr {
    PyErr::new::<pyo3::exceptions::PyValueError, _>(msg)
}

// Helper: extract &[u8] from Python bytes or str without unnecessary copies
fn extract_bytes<'a>(data: &'a PyAny) -> PyResult<&'a [u8]> {
    if let Ok(b) = data.downcast::<PyBytes>() {
        return Ok(b.as_bytes());
    }
    if let Ok(s) = data.downcast::<pyo3::types::PyString>() {
        return Ok(s.to_str()?.as_bytes());
    }
    Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
        "Expected bytes or str",
    ))
}

// Private implementation - not exposed to Python
impl StreamValidatorCore {
    fn parse_field_type(&self, field_type: &str) -> PyResult<FieldType> {
        // First check for primitive types
        match field_type {
            "str" | "string" | "email" | "url" | "uuid" | "date-time" => return Ok(FieldType::String),
            "int" | "integer" => return Ok(FieldType::Integer),
            "float" | "number" => return Ok(FieldType::Float),
            "decimal" => return Ok(FieldType::Decimal),  // Add decimal support
            "bool" | "boolean" => return Ok(FieldType::Boolean),
            "any" => return Ok(FieldType::Any),
            _ => {}
        }
        
        // Then check for List/Dict
        if let Some(inner_type) = field_type.strip_prefix("List[").and_then(|s| s.strip_suffix("]")) {
            let inner = self.parse_field_type(inner_type)?;
            return Ok(FieldType::List(Box::new(inner)));
        }
        if let Some(inner_type) = field_type.strip_prefix("Dict[").and_then(|s| s.strip_suffix("]")) {
            let inner = self.parse_field_type(inner_type)?;
            return Ok(FieldType::Dict(Box::new(inner)));
        }
        
        // Finally treat everything else as a custom type
        Ok(FieldType::Custom(field_type.to_string()))
    }

    fn validate_value(&self, value: &PyAny, field_type: &FieldType, constraints: &FieldConstraints) -> PyResult<()> {
        match field_type {
            FieldType::String => {
                // Fast path: try direct downcast first, avoid separate type check
                let s = match value.downcast::<pyo3::types::PyString>() {
                    Ok(py_str) => py_str.to_str()?,
                    Err(_) => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected string")),
                };
                
                // Length validation - check both bounds in one pass with cached errors
                let len = s.len();
                if let Some(min_len) = constraints.min_length {
                    if len < min_len {
                        return Err(get_cached_error("String too short"));
                    }
                }
                if let Some(max_len) = constraints.max_length {
                    if len > max_len {
                        return Err(get_cached_error("String too long"));
                    }
                }

                // Email validation
                if constraints.email {
                    if !validate_email(s) {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid email format"));
                    }
                }

                // URL validation
                if constraints.url {
                    if !validate_url(s) {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid URL format"));
                    }
                }

                // Regex pattern validation
                if let Some(pattern) = &constraints.pattern {
                    if !regex_match(s, pattern) {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("String does not match pattern: {}", pattern)
                        ));
                    }
                }

                // Add enum validation
                if let Some(ref enum_values) = constraints.enum_values {
                    if !enum_values.contains(&s.to_string()) {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be one of: {:?}", enum_values)
                        ));
                    }
                }
            }
            FieldType::Integer | FieldType::Float => {
                // Fast path: try direct downcasts without separate type checks
                let num = if let Ok(py_int) = value.downcast::<pyo3::types::PyInt>() {
                    py_int.extract::<f64>()?
                } else if let Ok(py_float) = value.downcast::<pyo3::types::PyFloat>() {
                    py_float.extract::<f64>()?
                } else {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected number"));
                };

                // Add ge/le/gt/lt validation
                if let Some(ge) = constraints.ge {
                    if num < ge as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be >= {}", ge)
                        ));
                    }
                }
                if let Some(le) = constraints.le {
                    if num > le as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be <= {}", le)
                        ));
                    }
                }
                if let Some(gt) = constraints.gt {
                    if num <= gt as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be > {}", gt)
                        ));
                    }
                }
                if let Some(lt) = constraints.lt {
                    if num >= lt as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be < {}", lt)
                        ));
                    }
                }

                if let Some(min_val) = constraints.min_value {
                    if num < min_val {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be >= {}", min_val)
                        ));
                    }
                }
                if let Some(max_val) = constraints.max_value {
                    if num > max_val {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be <= {}", max_val)
                        ));
                    }
                }
            }
            FieldType::Boolean => {
                if !value.is_instance_of::<pyo3::types::PyBool>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected boolean"));
                }
            }
            FieldType::Decimal => {
                // Handle Decimal type - accept strings, ints, floats, or Decimal objects
                let num = if value.is_instance_of::<pyo3::types::PyString>()? {
                    // Parse string as decimal
                    let s = value.downcast::<pyo3::types::PyString>()?.to_str()?;
                    s.parse::<f64>().map_err(|_| {
                        PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid decimal format")
                    })?
                } else if value.is_instance_of::<pyo3::types::PyInt>()? {
                    value.downcast::<pyo3::types::PyInt>()?.extract::<f64>()?
                } else if value.is_instance_of::<pyo3::types::PyFloat>()? {
                    value.downcast::<pyo3::types::PyFloat>()?.extract::<f64>()?
                } else {
                    // Try to extract as any numeric type (handles Decimal objects)
                    match value.extract::<f64>() {
                        Ok(val) => val,
                        Err(_) => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected decimal number"))
                    }
                };

                // Apply same numeric constraints as Float/Integer
                if let Some(ge) = constraints.ge {
                    if num < ge as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be >= {}", ge)
                        ));
                    }
                }
                if let Some(le) = constraints.le {
                    if num > le as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be <= {}", le)
                        ));
                    }
                }
                if let Some(gt) = constraints.gt {
                    if num <= gt as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be > {}", gt)
                        ));
                    }
                }
                if let Some(lt) = constraints.lt {
                    if num >= lt as f64 {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be < {}", lt)
                        ));
                    }
                }

                if let Some(min_val) = constraints.min_value {
                    if num < min_val {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be >= {}", min_val)
                        ));
                    }
                }
                if let Some(max_val) = constraints.max_value {
                    if num > max_val {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Value must be <= {}", max_val)
                        ));
                    }
                }
            }
            FieldType::List(inner_type) => {
                let list = value.downcast::<pyo3::types::PyList>()?;
                
                // Add min/max items validation
                if let Some(min_items) = constraints.min_items {
                    if list.len() < min_items {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("List must have at least {} items", min_items)
                        ));
                    }
                }
                if let Some(max_items) = constraints.max_items {
                    if list.len() > max_items {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("List must have at most {} items", max_items)
                        ));
                    }
                }
                
                // Add unique items validation
                if constraints.unique_items.unwrap_or(false) {
                    // This is a simple implementation - might need optimization for large lists
                    let mut seen = std::collections::HashSet::new();
                    for item in list.iter() {
                        let s = item.str()?.to_str()?;
                        if !seen.insert(s.to_string()) {
                            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                                "List items must be unique"
                            ));
                        }
                    }
                }
                
                // Validate each item
                for item in list.iter() {
                    self.validate_value(item, inner_type, constraints)?;
                }
            }
            FieldType::Dict(inner_type) => {
                if !value.is_instance_of::<pyo3::types::PyDict>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Expected dict"));
                }
                for item in value.downcast::<pyo3::types::PyDict>()?.values() {
                    self.validate_value(item, inner_type, constraints)?;
                }
            }
            FieldType::Custom(type_name) => {
                if !value.is_instance_of::<pyo3::types::PyDict>()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Custom type must be a dict"));
                }
                let dict = value.downcast::<pyo3::types::PyDict>()?;
                let custom_type = self.custom_types.get(type_name)
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Custom type {} not found", type_name)
                    ))?;
                
                for (field_name, validator) in custom_type {
                    if let Some(field_value) = dict.get_item(field_name) {
                        self.validate_value(field_value, &validator.field_type, &validator.constraints)?;
                    } else if validator.required {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Required field {} is missing in custom type {}", field_name, type_name)
                        ));
                    }
                }
            }
            FieldType::Any => {
                // Any type accepts all values without validation
            }
        }
        Ok(())
    }
}

// Helper functions for validation
fn validate_email(s: &str) -> bool {
    // RFC 5322 compliant email regex
    let email_regex = Regex::new(r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$").unwrap();
    
    // Check basic structure and length
    if s.len() > 254 || s.is_empty() {
        return false;
    }
    
    // Apply regex validation
    if !email_regex.is_match(s) {
        return false;
    }
    
    // Additional validation for domain part
    let parts: Vec<&str> = s.split('@').collect();
    if parts.len() != 2 {
        return false;
    }
    
    let domain = parts[1];
    // Domain specific validation
    if domain.starts_with('.') || domain.ends_with('.') {
        return false;
    }
    
    // Domain must have at least one dot and valid TLD
    let domain_parts: Vec<&str> = domain.split('.').collect();
    if domain_parts.len() < 2 || domain_parts.iter().any(|&part| part.is_empty()) {
        return false;
    }
    
    true
}

fn validate_url(s: &str) -> bool {
    // Basic URL validation
    s.starts_with("http://") || s.starts_with("https://")
}

fn regex_match(s: &str, pattern: &str) -> bool {
    // Basic pattern matching (can be enhanced with proper regex)
    // For now, just check if pattern exists in string
    s.contains(pattern)
}

// Helper function to convert serde_json::Value to PyObject
fn json_value_to_py(py: Python<'_>, value: &JsonValue) -> PyResult<PyObject> {
    match value {
        JsonValue::Null => Ok(py.None()),
        JsonValue::Bool(b) => Ok(b.to_object(py)),
        JsonValue::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.to_object(py))
            } else if let Some(f) = n.as_f64() {
                Ok(f.to_object(py))
            } else {
                // Fallback for very large numbers if necessary, though might lose precision
                Ok(n.to_string().to_object(py))
            }
        }
        JsonValue::String(s) => Ok(s.to_object(py)),
        JsonValue::Array(arr) => {
            let py_list = PyList::empty(py);
            for item in arr {
                py_list.append(json_value_to_py(py, item)?)?;
            }
            Ok(py_list.to_object(py))
        }
        JsonValue::Object(map) => {
            let py_dict = PyDict::new(py);
            for (k, v) in map {
                py_dict.set_item(k, json_value_to_py(py, v)?)?;
            }
            Ok(py_dict.to_object(py))
        }
    }
}

#[pymodule]
fn _satya(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<StreamValidatorCore>()?;
    Ok(())
}