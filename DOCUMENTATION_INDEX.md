# 📚 Satya Documentation Index

## Quick Links

| Document | Purpose | Audience |
|----------|---------|----------|
| **[README.md](README.md)** | Main documentation, quick start, API reference | All users |
| **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** | Architecture, usage patterns, performance tips | Developers |
| **[SUMMARY_IMPROVEMENTS.md](SUMMARY_IMPROVEMENTS.md)** | Complete optimization journey, academic foundations | Technical audience |
| **[CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)** | v0.3.86 changes, migration guide | All users |
| **[changelog.md](changelog.md)** | Version history, release notes | All users |

---

## 🚀 Getting Started (5 minutes)

### 1. Installation
```bash
pip install satya
```

### 2. First Validation
```python
from satya import BaseModel

class User(BaseModel):
    name: str
    age: int

user = User(name="Alice", age=30)
print(user)  # User(name='Alice', age=30)
```

### 3. Performance Mode
```python
# Single (1.2M ops/sec)
user = User.model_validate_fast({"name": "Alice", "age": 30})

# Batch (4.4M ops/sec)
users = User.validate_many([{...}, {...}])
```

**Next**: Read [README.md](README.md#quick-start) for full quick start guide.

---

## 📖 Documentation by Use Case

### For New Users
1. **[README.md](README.md)** - Start here!
   - Installation
   - Quick start examples
   - Feature overview
   - Basic API reference

2. **[examples/](examples/)** - Working code
   - `ultra_fast_showcase.py` - Performance demo
   - `scalar_validation_example.py` - Primitive validators
   - `json_schema_example.py` - JSON Schema support

### For Developers
1. **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Architecture deep dive
   - Component overview
   - Key optimizations explained
   - Advanced usage patterns
   - Performance patterns

2. **[SUMMARY_IMPROVEMENTS.md](SUMMARY_IMPROVEMENTS.md)** - Technical journey
   - Complete optimization history
   - Academic foundations (BLAZE, Violet papers)
   - Implementation phases
   - Performance benchmarks

3. **Source Code**
   - `src/satya/` - Python API layer
   - `src/*.rs` - Rust core (BLAZE, shapes, parallel)

### For Upgrading Users
1. **[CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)** - What changed in v0.3.86
   - Performance improvements
   - Technical changes
   - Migration guide
   - Before/after comparison

2. **[changelog.md](changelog.md)** - Complete version history
   - All releases
   - Breaking changes
   - Feature additions

### For Performance Optimization
1. **[IMPLEMENTATION_GUIDE.md - Performance Features](IMPLEMENTATION_GUIDE.md#performance-features)**
   - Adaptive serial/parallel
   - BLAZE compilation
   - Shape caching

2. **[README.md - Performance Guide](README.md#performance-optimization-guide)**
   - Batch processing
   - Batch size guidelines
   - Hybrid validation

3. **[benchmarks/](benchmarks/)** - Performance benchmarks
   - Comparative benchmarks
   - Real-world scenarios

---

## 🎓 Learning Path

### Path 1: Quick User (30 minutes)
```
README.md (Quick Start) 
→ examples/ultra_fast_showcase.py 
→ Your application!
```

### Path 2: Power User (2 hours)
```
README.md (Full read)
→ IMPLEMENTATION_GUIDE.md (Architecture + Patterns)
→ examples/ (All examples)
→ Benchmark your application
```

### Path 3: Deep Dive (4+ hours)
```
README.md
→ IMPLEMENTATION_GUIDE.md
→ SUMMARY_IMPROVEMENTS.md (Academic foundations)
→ Source code (src/)
→ CHANGES_SUMMARY.md (Implementation details)
```

### Path 4: Contributor (ongoing)
```
All documentation
→ Source code deep dive
→ benchmarks/ analysis
→ docs/archive/ (historical context)
→ CONTRIBUTING.md
```

---

## 📊 Performance Reference

### Quick Comparison

| Library | Single | Batch | Field Access |
|---------|--------|-------|--------------|
| **Satya** | **1,188K/s** | **4,444K/s** | **62.9M/s** |
| Pydantic | 624K/s | 842K/s | 63.0M/s |
| **Result** | **1.90× faster** | **5.28× faster** | **1.00× (parity)** |

**Source**: [SUMMARY_IMPROVEMENTS.md](SUMMARY_IMPROVEMENTS.md#-final-performance-results)

### Optimization Journey

| Phase | Single | Batch | Field Access |
|-------|--------|-------|--------------|
| Start | 195K/s | N/A | 5.2M/s |
| BLAZE | 244K/s | 6.45M/s | 5.2M/s |
| Parallel | 432K/s | 13.06M/s | 5.2M/s |
| Native | 481K/s | 8.1M/s | 42.8M/s |
| **Hidden Classes** | **1,188K/s** | **4,444K/s** | **62.9M/s** |

**Source**: [SUMMARY_IMPROVEMENTS.md](SUMMARY_IMPROVEMENTS.md#overall-journey)

---

## 🔧 API Reference Quick Links

### Core Classes
- **BaseModel** - Main model class ([README.md](README.md#quick-start))
- **Field** - Field constraints ([README.md](README.md#example-2))
- **validators** - Custom validation ([README.md](README.md#validation-capabilities))

### Scalar Validators
- **StringValidator** - String validation ([README.md](README.md#-scalar-validators-new-in-v0382))
- **IntValidator** - Integer validation
- **NumberValidator** - Float validation
- **BooleanValidator** - Boolean validation

### JSON Schema
- **compile_json_schema()** - JSON Schema compiler ([README.md](README.md#-json-schema-compiler-new-in-v0383))
- **JSONSchemaCompiler** - Advanced compiler

### Fast APIs
- **model_validate_fast()** - Ultra-fast single validation
- **validate_many()** - Ultra-fast batch validation

---

## 🗂️ Repository Structure

```
satya/
├── README.md                      # Main documentation
├── IMPLEMENTATION_GUIDE.md        # Architecture guide
├── SUMMARY_IMPROVEMENTS.md        # Technical journey
├── CHANGES_SUMMARY.md            # v0.3.86 changes
├── DOCUMENTATION_INDEX.md        # This file
├── changelog.md                  # Version history
│
├── src/
│   ├── satya/                    # Python API
│   │   ├── __init__.py          # Main exports
│   │   ├── model.py             # BaseModel
│   │   ├── validator.py         # StreamValidator
│   │   ├── scalar_validators.py # Primitive validators
│   │   └── json_schema_compiler.py
│   │
│   ├── lib.rs                   # Rust FFI entry
│   ├── fast_model.rs            # Hidden Classes impl
│   ├── compiled_validator.rs   # BLAZE compiler
│   └── native_model.rs          # Alternative impl
│
├── examples/                     # Working examples
│   ├── ultra_fast_showcase.py   # Performance demo
│   ├── scalar_validation_example.py
│   └── json_schema_example.py
│
├── tests/                        # Test suite
├── benchmarks/                   # Performance benchmarks
│
├── docs/                         # Additional docs
│   ├── migration.md             # Migration guide
│   └── archive/                 # Historical docs
│
└── CONTRIBUTING.md              # Contribution guide
```

---

## 📝 Common Tasks

### Task: Validate a single object
**Doc**: [README.md - Quick Start](README.md#quick-start)
```python
user = User.model_validate_fast(data)
```

### Task: Validate a batch
**Doc**: [README.md - Performance](README.md#-performance)
```python
users = User.validate_many(batch_data)
```

### Task: Add field constraints
**Doc**: [README.md - Example 2](README.md#example-2)
```python
age: int = Field(ge=0, le=150)
email: str = Field(email=True)
```

### Task: Optimize performance
**Doc**: [IMPLEMENTATION_GUIDE.md - Performance Features](IMPLEMENTATION_GUIDE.md#performance-features)
- Use `validate_many()` for batches
- Set batch size 1K-10K
- Use `model_validate_fast()` for single

### Task: Understand architecture
**Doc**: [IMPLEMENTATION_GUIDE.md - Architecture Overview](IMPLEMENTATION_GUIDE.md#architecture-overview)
- Read Python → PyO3 → Rust flow
- Understand Hidden Classes
- Learn about BLAZE compilation

### Task: Migrate from Pydantic
**Doc**: [README.md](README.md) + [docs/migration.md](docs/migration.md)
- Replace `from pydantic import BaseModel` with `from satya import BaseModel`
- Use `validate_many()` for batches
- Test performance improvements

### Task: Contribute
**Doc**: [CONTRIBUTING.md](CONTRIBUTING.md)
- Read contribution guidelines
- Check issue tracker
- Submit PR

---

## 🔍 Search Tips

### Finding Information

**"How do I..."**
- Start with [README.md](README.md)
- Check [IMPLEMENTATION_GUIDE.md - Common Patterns](IMPLEMENTATION_GUIDE.md#common-patterns)
- Browse [examples/](examples/)

**"Why is Satya fast?"**
- Read [SUMMARY_IMPROVEMENTS.md](SUMMARY_IMPROVEMENTS.md)
- See [IMPLEMENTATION_GUIDE.md - Architecture](IMPLEMENTATION_GUIDE.md#architecture-overview)

**"What changed in v0.3.86?"**
- Read [CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)
- Check [changelog.md](changelog.md)

**"How do I optimize my code?"**
- See [IMPLEMENTATION_GUIDE.md - Performance Checklist](IMPLEMENTATION_GUIDE.md#performance-checklist)
- Read [README.md - Performance Guide](README.md#performance-optimization-guide)

---

## 📞 Getting Help

1. **Check Documentation** (you're here!)
2. **Browse Examples** - `examples/` folder
3. **Search Issues** - [GitHub Issues](https://github.com/justrach/satya/issues)
4. **Open New Issue** - If not found

---

## 🎯 Version Information

- **Current Version**: v0.3.86
- **Release Date**: 2025-10-09
- **Status**: Production Ready
- **Python**: 3.8+ (3.13 supported)
- **Platform**: Linux, macOS, Windows

---

## ⭐ Key Highlights

### What Makes Satya Special?

1. **🏆 Fastest**: 1.90× faster than Pydantic for validation
2. **🔥 At Parity**: Field access as fast as Pydantic (1.00×)
3. **🚀 Comprehensive**: Full validation (email, URL, regex, constraints)
4. **📚 Research-Backed**: Built on 30+ years of VM optimization
5. **🎯 Production-Ready**: 178 tests, real-world usage

### Core Innovations

1. **Hidden Classes** (V8/PyPy) - Zero-allocation field mapping
2. **BLAZE Compilation** - Schema → optimized instructions
3. **Adaptive Parallelism** - Smart serial/parallel switching
4. **Interned Strings** - O(1) field name comparison
5. **Shape Registry** - Global metadata caching

**Learn More**: [SUMMARY_IMPROVEMENTS.md](SUMMARY_IMPROVEMENTS.md)

---

**Happy Validating!** 🎉

For questions, see [GitHub Issues](https://github.com/justrach/satya/issues).
