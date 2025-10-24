# Changelog

All notable changes to Config-Stash will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive Makefile with development, testing, and release targets
- Type hints and docstrings throughout the codebase
- Thread-safe hook processor with RLock implementation
- Logging system replacing print statements
- CI/CD pipeline with GitHub Actions
- Pre-commit hooks configuration (Black, Ruff, MyPy, isort)
- CONTRIBUTING.md with detailed contribution guidelines
- Development dependencies in pyproject.toml
- Support for multiple pyproject.toml search paths
- Environment fallback warnings

### Changed
- Refactored CLI code to eliminate duplication
- Improved lazy loader with instance-level caching (fixes memory leak)
- Updated pre-commit hooks to latest versions
- Enhanced error handling with proper exception messages

### Fixed
- Critical @lru_cache memory leak and cache pollution bug
- Test file typo preventing direct execution (`__name__ == '__main__'`)
- Hardcoded pyproject.toml path now searches multiple locations
- Thread safety issues in HookProcessor

### Security
- Added input validation for CLI loader specifications
- Implemented proper error handling for malformed configurations
- Added security scanning in CI pipeline (bandit, safety)

## [0.0.1] - 2024-01-01

### Added
- Initial release of Config-Stash
- Support for YAML, JSON, TOML, and environment variable configuration sources
- Environment-specific configuration management
- Dynamic configuration reloading with file watching
- Lazy loading of configuration values
- Hook system for configuration value transformation
- CLI interface for configuration management
- Comprehensive test suite
- Basic documentation and README

### Features
- Multiple configuration loader support
- Configuration merging from multiple sources
- Attribute-style access to configuration values
- Environment variable expansion
- Automatic type casting
- Source tracking for configuration values
- Extensible plugin architecture

[Unreleased]: https://github.com/qatoolist/config-stash/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/qatoolist/config-stash/releases/tag/v0.0.1
