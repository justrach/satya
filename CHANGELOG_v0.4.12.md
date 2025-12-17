# Changelog v0.4.12

## Fixed: Universal Binary Wheels for macOS

### Problem
Previous releases built separate wheels for macOS x86_64 and arm64 with platform tags like `macosx_11_0_arm64`. This caused pip to fall back to building from source on newer macOS versions (e.g., macOS 15.0), defeating the purpose of pre-built binary wheels.

### Solution
- **Universal2 wheels**: Now building universal2 wheels that work on both Intel and Apple Silicon Macs across all macOS versions
- **No compilation required**: Users can now install Satya instantly without needing Rust toolchain
- **Faster installs**: Installation time reduced from ~60 seconds (compilation) to <1 second (binary wheel)

### Changes
- Modified `.github/workflows/build-wheels.yml` to build universal2 wheels for macOS
- Removed separate x86_64/aarch64 targets in favor of single universal2 build per Python version
- Wheels now work seamlessly on macOS 10.12+ for both architectures

### Impact
- ✅ `pip install satya` now uses pre-built binaries on all platforms
- ✅ No more "Built satya==x.x.x" messages during installation
- ✅ Consistent with how other PyO3 packages (like orjson) distribute binaries

### Verification
After this release, installation should show:
```
Installed 1 package in 1ms
 + satya==0.4.12
```

Instead of:
```
Built satya==0.4.12
Installed 1 package in 1ms
 + satya==0.4.12
```
