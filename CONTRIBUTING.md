# Contributing to Config-Stash

Thank you for your interest in contributing to Config-Stash! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Style Guidelines](#style-guidelines)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to maintain a welcoming and inclusive environment for all contributors.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/config-stash.git
   cd config-stash
   ```
3. Add the upstream repository as a remote:
   ```bash
   git remote add upstream https://github.com/qatoolist/config-stash.git
   ```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip and virtualenv (or conda)
- Git

### Setting Up Your Environment

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the package in development mode with all dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Running Tests

Run the test suite to ensure everything is working:
```bash
pytest tests/ -v
```

Run tests with coverage:
```bash
pytest tests/ -v --cov=config_stash --cov-report=html
```

## Making Changes

### Branch Naming

Create a new branch for your feature or fix:
- Features: `feature/your-feature-name`
- Bug fixes: `fix/issue-description`
- Documentation: `docs/what-you-updated`

```bash
git checkout -b feature/my-new-feature
```

### Development Workflow

1. Make your changes
2. Add or update tests as needed
3. Update documentation if necessary
4. Run tests to ensure they pass:
   ```bash
   pytest tests/
   ```
5. Run pre-commit hooks:
   ```bash
   pre-commit run --all-files
   ```

### Commit Messages

Follow conventional commit format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions or changes
- `refactor:` - Code refactoring
- `style:` - Code style changes
- `chore:` - Maintenance tasks

Example:
```bash
git commit -m "feat: add support for TOML configuration files"
```

## Testing

### Writing Tests

- Place tests in the `tests/` directory
- Follow the existing test structure
- Use descriptive test names that explain what is being tested
- Include both positive and negative test cases
- Test edge cases

Example test structure:
```python
import pytest
from config_stash import Config

def test_feature_description():
    """Test that feature works as expected."""
    config = Config(env="test")
    assert config.some_method() == expected_value

def test_feature_edge_case():
    """Test edge case handling."""
    with pytest.raises(ValueError):
        Config(invalid_parameter="value")
```

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/test_config.py

# Run a specific test
pytest tests/test_config.py::test_specific_function

# Run tests matching a pattern
pytest -k "test_pattern"
```

## Submitting Changes

### Pull Request Process

1. Update your fork with the latest upstream changes:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. Rebase your feature branch if needed:
   ```bash
   git checkout feature/my-new-feature
   git rebase main
   ```

3. Push your changes to your fork:
   ```bash
   git push origin feature/my-new-feature
   ```

4. Create a pull request on GitHub

### Pull Request Guidelines

- Provide a clear description of the changes
- Reference any related issues (e.g., "Fixes #123")
- Include tests for new functionality
- Ensure all tests pass
- Update documentation as needed
- Keep pull requests focused on a single feature or fix

### Code Review

- Be open to feedback and suggestions
- Respond to review comments promptly
- Make requested changes in new commits (don't force-push during review)
- Once approved, your PR will be merged

## Style Guidelines

### Python Style

We use several tools to maintain code quality:

- **Black** for code formatting (100 character line length)
- **isort** for import sorting
- **Ruff** for linting
- **MyPy** for type checking

These are automatically run via pre-commit hooks.

### Code Style Principles

- Use type hints for all function signatures
- Add docstrings to all public functions, classes, and modules
- Follow PEP 8 guidelines
- Keep functions small and focused
- Use descriptive variable names
- Add comments for complex logic

Example:
```python
from typing import Optional, Dict, Any

def process_config(data: Dict[str, Any], env: Optional[str] = None) -> Dict[str, Any]:
    """Process configuration data for the specified environment.

    Args:
        data: Raw configuration dictionary
        env: Environment name (e.g., 'production', 'development')

    Returns:
        Processed configuration dictionary

    Raises:
        ValueError: If configuration data is invalid
    """
    # Implementation here
    pass
```

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. Python version and operating system
2. Config-Stash version
3. Minimal code example that reproduces the issue
4. Full error message and stack trace
5. Expected vs actual behavior

### Feature Requests

For feature requests, please describe:

1. The use case for the feature
2. Expected behavior
3. Any examples from similar libraries
4. Why this would benefit other users

## Additional Resources

- [Project README](README.md)
- [API Documentation](docs/api.md) (if available)
- [GitHub Issues](https://github.com/qatoolist/config-stash/issues)

## Questions?

If you have questions about contributing, feel free to:
- Open a discussion on GitHub
- Ask in an existing issue
- Contact the maintainers

Thank you for contributing to Config-Stash!
