# Contributing to TTS Lite

Thank you for considering contributing to TTS Lite! This document provides guidelines and instructions for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Keep discussions professional and on-topic

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/tts-lite.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- pip or poetry

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tts-lite.git
cd tts-lite

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with development tools
pip install -e ".[dev,build]"

# Or using requirements.txt
pip install -r requirements.txt
```

### Project Structure

```
tts-lite/
├── main.py              # Application entry point
├── tts/                 # TTS engine implementations
├── ui/                  # User interface components
├── audio/               # Audio playback and export
├── utils/               # Utility functions
├── tests/               # Test suite
├── resources/           # Icons, translations, styles
└── docs/                # Documentation
```

## Code Style

We follow PEP 8 with some modifications:

- **Line length**: Maximum 100 characters
- **Type hints**: Required for all public APIs
- **Docstrings**: Required for public classes and functions
- **Formatting**: Use Black for automatic formatting
- **Imports**: Use isort for consistent import ordering

### Setting up linting tools

```bash
# Install pre-commit hooks (recommended)
pip install pre-commit
pre-commit install

# Manual formatting
black .
isort .

# Run linters
flake8 tts_lite/ tests/
mypy tts_lite/
```

### Example Code Style

```python
"""Module docstring."""
from typing import Optional, List
import logging

from utils.logger import get_logger

logger = get_logger(__name__)


class ExampleClass:
    """Example class demonstrating code style."""
    
    def __init__(self, name: str, value: int = 0):
        """
        Initialize ExampleClass.
        
        Args:
            name: The name of the instance
            value: Initial value (default: 0)
        """
        self.name = name
        self.value = value
        logger.debug(f"Initialized {name} with value {value}")
    
    def process(self, data: List[str]) -> Optional[str]:
        """
        Process input data.
        
        Args:
            data: List of strings to process
            
        Returns:
            Processed result or None if failed
        """
        if not data:
            logger.warning("No data provided")
            return None
        
        return " ".join(data)
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tts_lite --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run UI tests (requires display)
pytest tests/ui/

# Run tests in verbose mode
pytest -v
```

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`
- Mock external dependencies (APIs, file system, etc.)

Example test:

```python
"""Tests for configuration module."""
import pytest
from utils.config import Config, ConfigError


def test_config_default_values():
    """Test that config has correct default values."""
    config = Config()
    
    assert config.theme == "dark"
    assert config.language == "ru"
    assert config.volume == 80
    assert 0.5 <= config.speed <= 2.0


def test_config_validation_invalid_theme():
    """Test validation fails for invalid theme."""
    config = Config()
    config.set("theme", "invalid")
    
    assert not config.validate()


def test_config_set_volume():
    """Test volume setting with bounds checking."""
    config = Config()
    
    config.volume = 50
    assert config.volume == 50
    
    config.volume = -10  # Should clamp to 0
    assert config.volume == 0
    
    config.volume = 150  # Should clamp to 100
    assert config.volume == 100
```

## Pull Request Process

1. **Before submitting:**
   - Ensure all tests pass: `pytest`
   - Run linters: `flake8`, `mypy`
   - Format code: `black .`, `isort .`
   - Update documentation if needed
   - Add tests for new features

2. **PR Title:**
   - Use conventional commits format:
     - `feat: Add new voice engine`
     - `fix: Resolve crash on startup`
     - `docs: Update README installation steps`
     - `refactor: Improve config validation`
     - `test: Add unit tests for export`

3. **PR Description:**
   - Describe what changed and why
   - Reference related issues: `Fixes #123`
   - Include screenshots for UI changes
   - List testing performed

4. **Review Process:**
   - At least one maintainer approval required
   - Address all review comments
   - CI/CD pipeline must pass

## Reporting Bugs

Create a bug report with:

- **Title**: Clear and descriptive
- **Environment**: OS, Python version, TTS Lite version
- **Steps to Reproduce**: Detailed reproduction steps
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happened
- **Logs**: Attach relevant log files (`%TEMP%\tts_lite.log` on Windows)
- **Screenshots**: If applicable

## Feature Requests

Submit feature requests with:

- **Title**: Concise description
- **Use Case**: Why this feature is needed
- **Proposed Solution**: How it should work
- **Alternatives Considered**: Other approaches
- **Additional Context**: Any other relevant information

## Questions?

Feel free to open an issue for questions or join discussions in existing issues.

---

Thank you for contributing to TTS Lite! 🎉
