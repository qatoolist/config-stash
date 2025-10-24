.PHONY: help install install-dev clean test test-cov test-fast lint format type-check security pre-commit docs build publish dev-setup check-all

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
PROJECT_NAME := config_stash
SRC_DIR := src/$(PROJECT_NAME)
TEST_DIR := tests
DOCS_DIR := docs

# Colors for terminal output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# Default target - show help
help: ## Show this help message
	@echo "$(GREEN)Config-Stash Development Makefile$(NC)"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick start: make dev-setup"

# Installation targets
install: ## Install the package in production mode
	$(PIP) install .

install-dev: ## Install the package in development mode with all dependencies
	$(PIP) install -e ".[dev,test,docs,cloud,validation]"
	$(PIP) install -r requirements-dev.txt
	pre-commit install

install-test: ## Install only test dependencies
	$(PIP) install -e .
	$(PIP) install -r requirements-test.txt

dev-setup: clean install-dev ## Complete development environment setup
	@echo "$(GREEN)✓ Development environment ready!$(NC)"
	@echo "Run 'make test' to run tests"
	@echo "Run 'make lint' to check code style"

# Testing targets
test: ## Run all tests with verbose output
	$(PYTEST) $(TEST_DIR)/ -v

test-cov: ## Run tests with coverage report
	$(PYTEST) $(TEST_DIR)/ -v \
		--cov=$(PROJECT_NAME) \
		--cov-report=html \
		--cov-report=term \
		--cov-report=xml \
		--cov-fail-under=70
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(NC)"

test-fast: ## Run tests in parallel for faster execution
	$(PYTEST) $(TEST_DIR)/ -n auto -q

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@command -v ptw >/dev/null 2>&1 || (echo "$(RED)Please install pytest-watch: pip install pytest-watch$(NC)" && exit 1)
	ptw -- -v

test-failed: ## Re-run only failed tests
	$(PYTEST) $(TEST_DIR)/ --lf -v

test-unit: ## Run only unit tests (exclude integration tests)
	$(PYTEST) $(TEST_DIR)/ -v -m "not integration"

test-integration: ## Run only integration tests
	$(PYTEST) $(TEST_DIR)/ -v -m integration

# Code quality targets
lint: ## Run linting checks with ruff
	ruff check $(SRC_DIR) $(TEST_DIR)

lint-fix: ## Run linting with automatic fixes
	ruff check $(SRC_DIR) $(TEST_DIR) --fix

format: ## Format code with black and isort
	black $(SRC_DIR) $(TEST_DIR) --line-length 100
	isort $(SRC_DIR) $(TEST_DIR) --profile black --line-length 100

format-check: ## Check code formatting without making changes
	black $(SRC_DIR) $(TEST_DIR) --line-length 100 --check
	isort $(SRC_DIR) $(TEST_DIR) --profile black --line-length 100 --check-only

type-check: ## Run type checking with mypy
	mypy $(SRC_DIR) --ignore-missing-imports

security: ## Run security checks with bandit and safety
	@echo "$(YELLOW)Running bandit security scan...$(NC)"
	-bandit -r $(SRC_DIR) -ll
	@echo "$(YELLOW)Running safety check on dependencies...$(NC)"
	-$(PIP) freeze | safety check --stdin

pre-commit-hooks: ## Run pre-commit hooks on all files
	pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks to latest versions
	pre-commit autoupdate

# Documentation targets
docs: ## Generate HTML documentation
	@echo "$(YELLOW)Building documentation...$(NC)"
	@mkdir -p $(DOCS_DIR)
	cd $(DOCS_DIR) && $(PYTHON) -m pydoc -w ../$(SRC_DIR)
	@echo "$(GREEN)Documentation generated in $(DOCS_DIR)/$(NC)"

docs-serve: ## Serve documentation locally
	@echo "$(GREEN)Serving documentation at http://localhost:8000$(NC)"
	$(PYTHON) -m http.server 8000 --directory $(DOCS_DIR)

# Build and release targets
build: clean ## Build distribution packages
	$(PYTHON) -m build
	@echo "$(GREEN)Build complete. Packages in dist/$(NC)"

publish-test: build ## Publish to TestPyPI
	$(PYTHON) -m twine upload --repository testpypi dist/*

publish: build ## Publish to PyPI (use with caution!)
	@echo "$(RED)Warning: About to publish to PyPI!$(NC)"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read dummy
	$(PYTHON) -m twine upload dist/*

# Cleaning targets
clean: ## Clean up build artifacts and cache files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-all: clean ## Deep clean including virtual environments
	rm -rf venv/
	rm -rf .venv/
	rm -rf env/
	rm -rf .tox/
	@echo "$(GREEN)✓ Deep cleanup complete$(NC)"

clean-commit: ## Clean repository before committing (removes temp files, caches, and analysis docs)
	@echo "$(CYAN)🧹 Cleaning repository for commit...$(NC)"
	@if [ -x scripts/clean_before_commit.sh ]; then \
		./scripts/clean_before_commit.sh; \
	else \
		echo "$(YELLOW)Running inline cleanup...$(NC)"; \
		find . -type f -name "*.pyc" -delete; \
		find . -type f -name "*.pyo" -delete; \
		find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true; \
		find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true; \
		find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true; \
		find . -type f -name ".coverage*" -delete; \
		find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true; \
		rm -rf build/ dist/ *.egg-info; \
		find . -type f -name "*~" -delete; \
		find . -type f -name "*.bak" -delete; \
		find . -type f -name ".DS_Store" -delete; \
		echo "$(GREEN)✓ Repository cleaned$(NC)"; \
	fi

# Development workflow targets
check-all: lint format-check type-check test ## Run all checks (lint, format, type, test)
	@echo "$(GREEN)✓ All checks passed!$(NC)"

fix-all: lint-fix format ## Fix all auto-fixable issues
	@echo "$(GREEN)✓ Auto-fixes applied$(NC)"

pre-commit: clean-commit fix-all test ## Prepare for commit (clean, fix, test)
	@echo "$(CYAN)📋 Pre-commit checklist:$(NC)"
	@echo "  ✅ Repository cleaned"
	@echo "  ✅ Code formatted"
	@echo "  ✅ Linting issues fixed"
	@echo "  ✅ Tests passing"
	@echo ""
	@echo "$(GREEN)✨ Ready to commit!$(NC)"
	@echo ""
	@echo "$(CYAN)Next steps:$(NC)"
	@echo "  1. Review changes: git diff"
	@echo "  2. Stage changes: git add ."
	@echo "  3. Commit: git commit -m \"your message\""

# Dependency management targets
deps-update: ## Update all dependencies to latest versions
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install --upgrade -r requirements-dev.txt

deps-check: ## Check for outdated dependencies
	$(PIP) list --outdated

deps-freeze: ## Freeze current dependencies
	$(PIP) freeze > requirements-frozen.txt
	@echo "$(GREEN)Dependencies frozen to requirements-frozen.txt$(NC)"

# Git workflow targets
git-clean: ## Clean git repository (remove untracked files)
	@echo "$(RED)Warning: This will remove all untracked files!$(NC)"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read dummy
	git clean -fdx

git-hooks: ## Install git hooks
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "$(GREEN)✓ Git hooks installed$(NC)"

# Docker targets (if you add Docker support later)
docker-build: ## Build Docker image
	docker build -t $(PROJECT_NAME):latest .

docker-run: ## Run Docker container
	docker run -it --rm $(PROJECT_NAME):latest

docker-test: ## Run tests in Docker container
	docker run --rm $(PROJECT_NAME):latest pytest

# Utility targets
version: ## Display current package version
	@$(PYTHON) -c "from $(PROJECT_NAME) import __version__; print(__version__)"

info: ## Display project information
	@echo "$(GREEN)Project: Config-Stash$(NC)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Location: $$(pwd)"
	@echo "Package: $(PROJECT_NAME)"
	@$(PYTHON) -c "from $(PROJECT_NAME) import __version__; print(f'Version: {__version__}')" 2>/dev/null || echo "Version: Not installed"

requirements: ## Generate requirements files from pyproject.toml
	pip-compile pyproject.toml -o requirements.txt
	pip-compile --extra dev pyproject.toml -o requirements-dev.txt

# CI/CD targets
ci-test: ## Run tests as they would run in CI
	$(PYTEST) $(TEST_DIR)/ -v --cov=$(PROJECT_NAME) --cov-report=xml --cov-report=term

ci-lint: ## Run linting as it would run in CI
	ruff check $(SRC_DIR) $(TEST_DIR)
	mypy $(SRC_DIR) --ignore-missing-imports

# Performance targets
profile: ## Profile the code with cProfile
	$(PYTHON) -m cProfile -o profile.stats -m $(PROJECT_NAME)
	$(PYTHON) -m pstats profile.stats

benchmark: ## Run performance benchmarks
	$(PYTEST) $(TEST_DIR)/benchmarks/ -v --benchmark-only

# Debug targets
debug-test: ## Run tests with debugging enabled
	$(PYTEST) $(TEST_DIR)/ -vvv --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb

debug-shell: ## Start an IPython shell with the package loaded
	@command -v ipython >/dev/null 2>&1 || (echo "$(RED)Please install ipython: pip install ipython$(NC)" && exit 1)
	ipython -i -c "from $(PROJECT_NAME) import *; print('$(GREEN)Config-Stash loaded. Available: Config$(NC)')"

# Release targets
changelog: ## Generate/update CHANGELOG.md
	@echo "$(YELLOW)Generating changelog...$(NC)"
	@echo "# Changelog\n" > CHANGELOG.md
	@echo "## [Unreleased]\n" >> CHANGELOG.md
	@git log --pretty=format:"- %s (%h)" --reverse >> CHANGELOG.md
	@echo "\n$(GREEN)✓ CHANGELOG.md updated$(NC)"

release-patch: ## Create a patch release (x.x.+1)
	bump2version patch
	git push && git push --tags

release-minor: ## Create a minor release (x.+1.0)
	bump2version minor
	git push && git push --tags

release-major: ## Create a major release (+1.0.0)
	bump2version major
	git push && git push --tags

# Advanced targets
complexity: ## Check code complexity
	radon cc $(SRC_DIR) -s -v

metrics: ## Generate code metrics report
	@echo "$(YELLOW)Generating code metrics...$(NC)"
	radon cc $(SRC_DIR) -s
	radon mi $(SRC_DIR) -s
	radon hal $(SRC_DIR)

todo: ## List all TODOs and FIXMEs in the code
	@grep -rn "TODO\|FIXME\|XXX\|HACK\|BUG" $(SRC_DIR) $(TEST_DIR) || echo "$(GREEN)No TODOs found$(NC)"

contributors: ## List all contributors
	@git log --format='%aN' | sort -u

.DEFAULT_GOAL := help
