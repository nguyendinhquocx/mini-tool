# File Rename Tool - Cross-platform Build Makefile

# Variables
APP_NAME = FileRenameTool
PYTHON = python
VENV_PATH = venv
PIP = $(VENV_PATH)/bin/pip
PYTHON_VENV = $(VENV_PATH)/bin/python

# Windows specific paths
ifeq ($(OS),Windows_NT)
	PYTHON = py
	PIP = $(VENV_PATH)/Scripts/pip.exe
	PYTHON_VENV = $(VENV_PATH)/Scripts/python.exe
	PYINSTALLER = $(VENV_PATH)/Scripts/pyinstaller.exe
else
	PYINSTALLER = $(VENV_PATH)/bin/pyinstaller
endif

# Default target
.PHONY: all
all: build

# Help target
.PHONY: help
help:
	@echo "File Rename Tool - Build System"
	@echo "================================"
	@echo ""
	@echo "Available targets:"
	@echo "  setup     - Create virtual environment and install dependencies"
	@echo "  clean     - Remove build artifacts"
	@echo "  build     - Build executable using PyInstaller"
	@echo "  test      - Run tests"
	@echo "  lint      - Run code quality checks"
	@echo "  dev-deps  - Install development dependencies"
	@echo "  all       - Build executable (default)"
	@echo "  help      - Show this help message"

# Setup virtual environment
.PHONY: setup
setup:
	@echo "Setting up development environment..."
	$(PYTHON) -m venv $(VENV_PATH)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# Install development dependencies
.PHONY: dev-deps
dev-deps: setup
	@echo "Installing development dependencies..."
	$(PIP) install pytest pytest-qt black flake8 mypy

# Clean build artifacts
.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build dist *.spec
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache .mypy_cache
	rm -f *.pyc */*.pyc */*/*.pyc

# Build executable
.PHONY: build
build:
	@echo "Building $(APP_NAME) executable..."
	$(PYTHON_VENV) packaging/build.py --onefile --clean

# Quick build without cleaning
.PHONY: build-quick
build-quick:
	@echo "Quick building $(APP_NAME)..."
	$(PYINSTALLER) --onefile --name $(APP_NAME) --noconsole file.py

# Run tests
.PHONY: test
test:
	@echo "Running tests..."
	$(PYTHON_VENV) -m pytest tests/ -v --cov=src/

# Code quality checks
.PHONY: lint
lint:
	@echo "Running code quality checks..."
	$(PYTHON_VENV) -m black --check .
	$(PYTHON_VENV) -m flake8 .
	$(PYTHON_VENV) -m mypy .

# Format code
.PHONY: format
format:
	@echo "Formatting code..."
	$(PYTHON_VENV) -m black .

# Install package in development mode
.PHONY: install-dev
install-dev:
	$(PIP) install -e .

# Check if virtual environment exists
.PHONY: check-venv
check-venv:
	@if [ ! -d "$(VENV_PATH)" ]; then \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi

# Validate build
.PHONY: validate
validate: build
	@echo "Validating executable..."
	@if [ -f "dist/$(APP_NAME).exe" ] || [ -f "dist/$(APP_NAME)" ]; then \
		echo "✓ Executable created successfully"; \
	else \
		echo "✗ Executable not found"; \
		exit 1; \
	fi

# Development workflow
.PHONY: dev
dev: setup dev-deps
	@echo "Development environment ready!"
	@echo "Run 'make build' to create executable"

# Distribution build with all checks
.PHONY: dist
dist: clean lint test build validate
	@echo "Distribution build completed!"

# Watch for changes and rebuild (requires entr or similar)
.PHONY: watch
watch:
	@echo "Watching for changes (requires 'entr')..."
	find . -name "*.py" | entr make build-quick