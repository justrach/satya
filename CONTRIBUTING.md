# Contributing to Satya

Thank you for your interest in contributing to Satya! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Release Process](#release-process)

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Add the original repository as a remote named "upstream"
4. Create a branch for your changes

```bash
git clone https://github.com/YOUR_USERNAME/satya.git
cd satya
git remote add upstream https://github.com/rachpradhan/satya.git
git checkout -b feature/your-feature-name
```

## Development Environment Setup

### Prerequisites

- Python 3.8 or newer
- Rust toolchain 1.70.0 or newer
- Maturin

### Install Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### Install Development Dependencies

```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install maturin pytest pytest-cov black isort mypy
```

### Build the Project

```bash
maturin develop --release
```

## Making Changes

1. Make your changes to the codebase
2. Format Rust code with `cargo fmt`
3. Format Python code with `black` and `isort`
4. Ensure your code passes all linters (`cargo clippy`, `mypy`)
5. Add or update tests as necessary
6. Update documentation if needed

## Testing

Run tests to ensure your changes don't break existing functionality:

```bash
# Run Rust tests
cargo test

# Run Python tests
pytest
```

## Submitting a Pull Request

1. Commit your changes with a descriptive commit message
2. Push your branch to your fork on GitHub
3. Create a pull request against the main repository's `main` branch
4. Fill out the pull request template with detailed information

```bash
git add .
git commit -m "Add a descriptive message about your changes"
git push origin feature/your-feature-name
```

Then go to GitHub and create a pull request from your branch.

## Release Process

The Satya release process is automated through GitHub Actions:

1. Maintainers trigger the release workflow
2. The workflow:
   - Bumps version numbers in all necessary files
   - Generates a changelog
   - Creates a GitHub release
   - Builds wheels for multiple platforms
   - Publishes to PyPI

If you're a maintainer and need to make a release:

1. Ensure all tests pass and the main branch is in a releasable state
2. Go to the "Actions" tab on GitHub
3. Select the "Release Process" workflow
4. Click "Run workflow"
5. Select the version bump type (patch, minor, or major)
6. Click "Run workflow"

The rest is handled automatically.

Thank you for contributing to Satya! 