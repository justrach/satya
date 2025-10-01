# Poetry Integration - Quick Action Plan

**Goal**: Replace fastjsonschema with Satya in Poetry for 5.2x performance boost

---

## 🎯 Quick Steps for Agent Execution

### Phase 1: Setup (5 minutes)

```bash
cd /Users/rachpradhan/oss-libs-to-mod/poetry
git checkout -b feat/satya-integration
git pull origin main
```

### Phase 2: Analysis (10 minutes)

```bash
# Find all fastjsonschema usage
grep -r "fastjsonschema" --include="*.py" src/ tests/
grep -r "from fastjsonschema" --include="*.py" src/
grep -r "import fastjsonschema" --include="*.py" src/

# Count occurrences
grep -r "fastjsonschema" --include="*.py" src/ | wc -l

# Save to file for reference
grep -r "fastjsonschema" --include="*.py" src/ > /tmp/poetry_fastjsonschema_usage.txt
```

### Phase 3: Create Adapter (15 minutes)

1. Create file: `src/poetry/core/json/satya_adapter.py`
2. Copy content from `POETRY_INTEGRATION_GUIDE.md` section "Step 2"
3. Ensure imports are correct

### Phase 4: Update Dependencies (2 minutes)

```bash
# Edit pyproject.toml
poetry remove fastjsonschema
poetry add satya@^0.3.81
```

### Phase 5: Replace Imports (20 minutes)

**Strategy**: Use compatibility import for zero code changes

In `src/poetry/core/json/__init__.py`:
```python
# Add this at the top
from poetry.core.json import satya_adapter as fastjsonschema

# Or explicit exports
from poetry.core.json.satya_adapter import compile, validate, ValidationError
```

### Phase 6: Testing (15 minutes)

```bash
# Run existing test suite
poetry run pytest tests/ -v --tb=short

# Run specific JSON validation tests
poetry run pytest tests/json/ -v
poetry run pytest tests/core/ -v -k "schema"

# Quick smoke test
poetry check
poetry install --dry-run
```

### Phase 7: Benchmark (10 minutes)

```bash
# Create benchmark file (copy from guide)
# Run benchmark
poetry run python benchmarks/satya_vs_fastjsonschema.py
```

---

## 📋 Detailed Checklist

### Pre-Integration
- [ ] Poetry repo cloned to `/Users/rachpradhan/oss-libs-to-mod/poetry`
- [ ] Feature branch created
- [ ] Current tests passing baseline established

### Core Implementation
- [ ] `satya_adapter.py` created in correct location
- [ ] Satya added to `pyproject.toml`
- [ ] fastjsonschema removed from `pyproject.toml`
- [ ] Compatibility layer imports added
- [ ] No direct code changes to Poetry internals (use adapter)

### Testing & Validation
- [ ] Adapter unit tests created
- [ ] Adapter tests pass
- [ ] Existing Poetry test suite passes
- [ ] Manual validation: `poetry check` works
- [ ] Manual validation: `poetry install` works
- [ ] Manual validation: `poetry lock` works
- [ ] Benchmark shows >=5x improvement

### Performance Verification
- [ ] Benchmark results documented
- [ ] Lock file validation tested with 100+ packages
- [ ] pyproject.toml validation tested
- [ ] No performance regressions in Poetry commands

### Documentation & Submission
- [ ] Update CHANGELOG.md in Poetry
- [ ] Update docs about performance improvement
- [ ] Create PR with benchmark results
- [ ] Tag PR with "performance" label

---

## 🔍 Key Files to Check/Modify

### Must Create:
```
src/poetry/core/json/satya_adapter.py          # Compatibility layer
tests/json/test_satya_adapter.py               # Adapter tests
benchmarks/satya_vs_fastjsonschema.py          # Performance proof
```

### Must Modify:
```
pyproject.toml                                  # Dependencies
src/poetry/core/json/__init__.py               # Export adapter as fastjsonschema
```

### Likely Need to Check:
```
src/poetry/core/json/schemas.py
src/poetry/core/packages/package.py
src/poetry/core/pyproject/pyproject.py
src/poetry/core/pyproject/tables.py
```

---

## 🧪 Critical Test Commands

```bash
# 1. Basic functionality
poetry check
poetry show

# 2. Installation test
poetry install --dry-run

# 3. Lock file test
poetry lock --no-update

# 4. Run full test suite
poetry run pytest tests/ -v

# 5. Specific validation tests
poetry run pytest tests/ -v -k "schema or validate or json"

# 6. Performance benchmark
poetry run python benchmarks/satya_vs_fastjsonschema.py
```

---

## ⚡ Expected Results

### Benchmark Output:
```
Poetry Dependency Validation Benchmark
============================================================
Validating 1,000 package dependencies

fastjsonschema: 0.0012s (820,511 items/sec)
Satya:          0.0002s (4,241,065 items/sec)

Speedup: 5.2x faster with Satya! 🚀
```

### Test Output:
```
tests/json/test_satya_adapter.py::test_simple_schema_validation PASSED
tests/json/test_satya_adapter.py::test_compile_reuse PASSED
tests/json/test_satya_adapter.py::test_batch_validation PASSED
tests/json/test_satya_adapter.py::test_poetry_pyproject_schema PASSED

============================== 4 passed in 0.23s ==============================
```

---

## 🚨 Troubleshooting

### Issue: Import errors
**Solution**: Check that `satya_adapter.py` is in correct location and `__init__.py` exports are correct

### Issue: Validation errors
**Solution**: Check schema conversion logic in `_convert_jsonschema_to_satya()`

### Issue: Tests fail
**Solution**: Ensure ValidationError is raised correctly, matching fastjsonschema behavior

### Issue: Performance not improved
**Solution**: Ensure using `validate_batch_hybrid()` for batch operations

---

## 📊 Success Criteria

✅ All existing Poetry tests pass  
✅ No API changes needed in Poetry codebase  
✅ Benchmark shows >=5x improvement  
✅ `poetry install`, `poetry lock`, `poetry check` all work  
✅ Clean PR ready for submission  

---

## 🎯 Time Estimate

- **Setup & Analysis**: 15 minutes
- **Implementation**: 35 minutes
- **Testing**: 25 minutes
- **Benchmark & Documentation**: 15 minutes

**Total**: ~90 minutes for complete integration

---

## 🚀 Ready to Execute!

The guide is comprehensive and the adapter is battle-tested. This should be a smooth integration that gives Poetry a significant performance boost!

**Next Command**:
```bash
cd /Users/rachpradhan/oss-libs-to-mod/poetry && git checkout -b feat/satya-integration
```
