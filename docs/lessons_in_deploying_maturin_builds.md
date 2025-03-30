# Lessons Learned in Deploying Rust-Python Extensions with Maturin

This document captures key lessons learned while setting up and deploying Python packages with Rust extensions using Maturin and GitHub Actions. These insights should help you avoid common pitfalls when working with similar projects.

## Table of Contents

- [Understanding the Architecture](#understanding-the-architecture)
- [Environment Setup](#environment-setup)
- [Cross-Platform Considerations](#cross-platform-considerations)
- [GitHub Actions CI/CD](#github-actions-cicd)
- [Release Management](#release-management)
- [MacOS-Specific Considerations](#macos-specific-considerations)
- [Linux-Specific Considerations](#linux-specific-considerations)
- [Windows-Specific Considerations](#windows-specific-considerations)
- [Best Practices](#best-practices)

## Understanding the Architecture

When building Python packages with Rust extensions:

1. **PyO3**: The Rust library that provides bindings between Rust and Python. It handles the conversion between Python and Rust types.

2. **Maturin**: The build tool that compiles Rust code and packages it into Python wheels. It handles the complexities of cross-platform builds and ensures the resulting wheels work on different operating systems.

3. **Python Package Structure**: Your project will typically have:
   - Rust code in `/src` (compiled into a binary Python extension)
   - Python code (usually in the same `/src` directory) that imports and wraps the Rust functionality
   - `pyproject.toml` for package metadata and build configuration
   - `Cargo.toml` for Rust dependencies and configuration

## Environment Setup

### Local Development

For local development with Rust Python extensions:

```bash
# Create a Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install maturin pytest

# Build in development mode (fast)
maturin develop

# For a release build
maturin develop --release
```

Lesson: Always develop inside a virtual environment to avoid conflicts with system packages.

## Cross-Platform Considerations

### Platform-Specific Wheels

- Python wheels are platform-specific for packages with compiled extensions
- You need separate wheels for:
  - Different operating systems (Windows, macOS, Linux)
  - Different CPU architectures (x86_64, aarch64/ARM64)
  - Different Python versions (3.8, 3.9, 3.10, 3.11, 3.12)

### Universal2 Wheels for macOS

For macOS, you can build universal2 wheels that work on both Intel and Apple Silicon:

```yaml
- name: Build wheels
  uses: PyO3/maturin-action@v1
  with:
    target: aarch64
    args: --release --out dist
    universal2: true
```

Lesson: Universal2 wheels simplify distribution for macOS users, regardless of their CPU architecture.

## GitHub Actions CI/CD

### Setting Up Matrix Builds

Matrix builds allow you to build wheels for multiple platforms and Python versions:

```yaml
strategy:
  matrix:
    python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]
    target: [x86_64, aarch64]
  fail-fast: false  # Continue other builds even if one fails
```

Lesson: Always set `fail-fast: false` to ensure some wheels are built even if others fail.

### Separating Jobs by Platform

Separate jobs for each platform/architecture combination provides better error isolation:

```yaml
jobs:
  linux-x86_64:
    # Configuration for Linux x86_64
  
  linux-aarch64:
    # Configuration for Linux ARM64
    
  windows:
    # Configuration for Windows
    
  macos:
    # Configuration for macOS
```

Lesson: Keep platform-specific configurations in separate jobs for better maintainability and debugging.

### Using the Latest GitHub Actions

Always use the latest versions of GitHub Actions for better compatibility:

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
- uses: actions/upload-artifact@v4
- uses: actions/download-artifact@v4
```

Lesson: Older versions of actions may not be compatible with newer GitHub Actions runners.

## Release Management

### Automating Version Bumping

Version bumping can be automated with tools like bump2version, but watch out for macOS compatibility:

```bash
# BSD grep (macOS) vs GNU grep (Linux) compatibility
# Instead of:
CURRENT_VERSION=$(grep -Po '(?<=version = ")[^"]*' pyproject.toml)

# Use:
CURRENT_VERSION=$(grep 'version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
```

Lesson: Shell scripts should be tested on both Linux and macOS due to differences in command-line tools.

### GitHub Releases Automation

To automatically create GitHub Releases with attached wheels:

```yaml
- name: Extract version from tag
  if: startsWith(github.ref, 'refs/tags/v')
  id: get_version
  run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

- name: Generate Release Notes
  if: startsWith(github.ref, 'refs/tags/v')
  run: |
    # Generate changelog from git commits since last tag
    git log --pretty=format:"* %s (%h)" $(git describe --tags --abbrev=0 HEAD^)..HEAD > release_notes.md
    # Add header and details
    echo "## My Project v${{ steps.get_version.outputs.VERSION }}" | cat - release_notes.md > temp && mv temp release_notes.md

- name: Create GitHub Release
  if: startsWith(github.ref, 'refs/tags/v')
  uses: softprops/action-gh-release@v1
  with:
    files: dist/*
    body_path: release_notes.md
    draft: false
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Lesson: Include `fetch-depth: 0` in the checkout step to access git history for generating release notes. Use conditional execution with `if: startsWith(github.ref, 'refs/tags/v')` to only create releases for tag events.

### PyPI Publishing

Secure PyPI publishing with GitHub Actions:

```yaml
- name: Publish to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    password: ${{ secrets.PYPI_API_TOKEN }}
    skip_existing: true  # Prevents errors if a wheel already exists
```

Lesson: Always use `skip_existing: true` to prevent publishing failures if some wheels were already uploaded.

## MacOS-Specific Considerations

### Building for Apple Silicon

For Apple Silicon (M1/M2/etc.), use:

```yaml
- name: Build wheels
  uses: PyO3/maturin-action@v1
  with:
    target: aarch64
    args: --release --out dist
    universal2: true  # Creates wheels that work on both Intel and ARM Macs
```

Lesson: Universal2 wheels are preferred over separate x86_64 and aarch64 wheels for macOS.

### BSD vs GNU Tool Differences

MacOS uses BSD versions of common command-line tools which have different syntax from GNU tools found on Linux:

```bash
# GNU (Linux) syntax
grep -Po '(?<=pattern)'

# BSD (macOS) compatible alternative
grep 'pattern' | sed 's/pattern \(.*\)/\1/'
```

Lesson: Test your shell scripts on both platforms or use more portable tools like Python scripts.

## Linux-Specific Considerations

### manylinux Compatibility

Linux wheels should be built with manylinux containers to ensure compatibility across Linux distributions:

```yaml
- name: Build wheels
  uses: PyO3/maturin-action@v1
  with:
    target: x86_64
    args: --release --out dist
    manylinux: auto  # Use "auto" to get the most appropriate manylinux version
```

### ARM64/aarch64 Cross-compilation

For ARM64 builds on Linux, you need special configuration with QEMU emulation:

```yaml
# Set up QEMU for cross-platform emulation
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3
  with:
    platforms: arm64

- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

# Use cross-compilation container with platform specified
- name: Build wheels
  uses: PyO3/maturin-action@v1
  with:
    target: aarch64
    args: --release --out dist --find-interpreter
    manylinux: 2_28
    container: quay.io/pypa/manylinux_2_28_aarch64
    docker-options: "--platform linux/arm64"
```

Lesson: When cross-compiling for ARM64 on x86_64 hosts:
1. Use QEMU emulation through docker/setup-qemu-action
2. Set up Docker Buildx for multi-platform builds
3. Specify `--platform linux/arm64` in docker-options
4. Use the `--find-interpreter` flag to help maturin locate Python in the container

### Controlling Python Versions in manylinux Containers

By default, maturin will build for all Python versions found in a container. To build for a specific Python version in a matrix configuration:

```yaml
- name: Build wheels
  uses: PyO3/maturin-action@v1
  with:
    target: aarch64
    args: >-
      --release 
      --out dist 
      --interpreter /opt/python/cp310-cp310/bin/python  # Use specific Python interpreter
    manylinux: 2_28
    container: quay.io/pypa/manylinux_2_28_aarch64
```

The path to Python interpreters in manylinux containers follows this pattern:
- Python 3.8: `/opt/python/cp38-cp38/bin/python`
- Python 3.9: `/opt/python/cp39-cp39/bin/python`
- Python 3.10: `/opt/python/cp310-cp310/bin/python`
- Python 3.11: `/opt/python/cp311-cp311/bin/python`
- Python 3.12: `/opt/python/cp312-cp312/bin/python`
- Python 3.13: `/opt/python/cp313-cp313/bin/python`

Lesson: Specify `--interpreter` explicitly in matrix builds to avoid building for all Python versions in each job.

## Windows-Specific Considerations

For Windows, specify the architecture in the python setup:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: ${{ matrix.python-version }}
    architecture: ${{ matrix.target }}  # x64 for Windows
```

Lesson: Windows builds are generally simpler but be explicit about architecture.

## Best Practices

1. **Separate Linux ARM builds**: ARM builds on Linux require special handling and should be in a separate job.

2. **Unique artifact names**: Use descriptive artifact names to avoid collisions:
   ```yaml
   - name: Upload wheels
     uses: actions/upload-artifact@v4
     with:
       name: wheels-linux-${{ matrix.python-version }}-${{ matrix.target }}
       path: dist
   ```

3. **Collection job**: Use a separate job to collect all wheels before publishing:
   ```yaml
   collect-wheels:
     needs: [linux-x86_64, linux-aarch64, windows, macos]
     # Configuration for collecting all wheels
   ```

4. **Resilient workflows**: Make workflows resilient to failures:
   - Use `fail-fast: false` in matrix strategies
   - Use `continue-on-error: true` for non-critical steps
   - Use `skip_existing: true` when publishing to PyPI

5. **Local distribution script**: Create a local script (`distribution.sh`) that handles:
   - Version bumping
   - Changelog generation
   - Building wheels for the current platform
   - Creating git tags and commits
   - This provides a consistent release process for both local and CI builds

6. **Testing in virtual environments**: Always test installations in clean virtual environments to ensure dependencies are correctly specified.

By following these lessons, you can create a robust deployment pipeline for your Rust-Python packages that works reliably across platforms and Python versions.