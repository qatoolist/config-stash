# Requirements Files

This directory contains various requirement files for different purposes:

## Core Requirements

### `../requirements.txt`
Core dependencies required to run Config-Stash in production.

```bash
pip install -r requirements.txt
```

## Development Requirements

### `../requirements-dev.txt`
Complete set of dependencies for development, including:
- All testing frameworks
- Code quality tools (black, ruff, mypy)
- Documentation tools (sphinx)
- Cloud SDKs for testing
- Development utilities

```bash
pip install -r requirements-dev.txt
```

### `../requirements-test.txt`
Minimal set of dependencies needed to run the test suite:
- Testing frameworks (pytest and plugins)
- Cloud SDKs (for cloud loader tests)
- Validation libraries (for validator tests)

```bash
pip install -r requirements-test.txt
```

## Installation Options

### For Production
```bash
pip install config-stash
```

### For Development
```bash
# Clone the repository
git clone https://github.com/qatoolist/config-stash.git
cd config-stash

# Install in development mode with all dependencies
make install-dev

# Or manually:
pip install -e ".[dev,test,docs,cloud,validation]"
pip install -r requirements-dev.txt
```

### For Testing Only
```bash
make install-test

# Or manually:
pip install -e .
pip install -r requirements-test.txt
```

### Using Tox for Multi-Version Testing
```bash
pip install tox
tox  # Run tests on all Python versions
tox -e py311  # Run tests on Python 3.11 only
tox -e lint  # Run linting checks
tox -e type  # Run type checking
```

## Optional Dependencies

Config-Stash supports optional dependencies that can be installed as needed:

```bash
# YAML support
pip install config-stash[yaml]

# TOML support
pip install config-stash[toml]

# Validation support (Pydantic + JSON Schema)
pip install config-stash[validation]

# Cloud storage support (AWS, Azure, GCP, IBM)
pip install config-stash[cloud]

# All optional dependencies
pip install config-stash[all]
```

## Dependency Management

### Updating Dependencies
```bash
# Update all dependencies to latest compatible versions
pip install --upgrade -r requirements-dev.txt

# Use pip-tools for more control
pip-compile requirements.in -o requirements.txt
pip-compile requirements-dev.in -o requirements-dev.txt
```

### Security Checks
```bash
# Check for known vulnerabilities
safety check -r requirements.txt
safety check -r requirements-dev.txt

# Or use the Makefile
make security
```