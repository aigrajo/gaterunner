# Gaterunner Test Suite

This directory contains the comprehensive test suite for Gaterunner, focusing on reliability, maintainability, and coverage of the core fingerprinting evasion functionality.

## Test Structure

```
tests/
├── conftest.py                     # Shared fixtures and configuration
├── requirements-test.txt           # Test-specific dependencies
├── test_unit/                      # Fast unit tests (no browser)
│   ├── test_config.py             # Configuration validation
│   ├── test_utils.py              # Utility functions
│   ├── test_spoof_manager.py      # Core orchestration logic
│   └── gates/                     # Individual gate testing
│       ├── test_base_gate.py      # Base gate interface
│       ├── test_useragent_gate.py # UserAgent spoofing
│       └── test_webgl_gate.py     # WebGL spoofing
└── README.md                      # This file
```

## Quick Start

### 1. Install Test Dependencies

```bash
# Install test dependencies
python run_tests.py install

# Or manually:
pip install -r tests/requirements-test.txt
```

### 2. Run Tests

```bash
# Run all unit tests
python run_tests.py unit

# Run with coverage analysis
python run_tests.py coverage

# Fast mode (stop on first failure)
python run_tests.py fast

# Watch mode (re-run on file changes)
python run_tests.py watch
```

## Test Categories

### Unit Tests (`test_unit/`)
- **Fast execution** (< 30 seconds total)
- **No external dependencies** (no browser automation)
- **Comprehensive mocking** of browser components
- **High coverage** of core business logic

**What's tested:**
- Configuration validation and parsing
- Gate interface contracts and implementations
- JavaScript template processing
- Spoofing manager orchestration
- Error handling and edge cases

### Test Fixtures (`conftest.py`)
Provides reusable test infrastructure:
- **Async test support** with proper event loop management
- **Mock browser components** (Page, Context, Browser)
- **Temporary file systems** for output testing
- **Sample data** (user agents, geolocation, etc.)
- **Helper utilities** for common test patterns

## Testing Approach

### Mocking Strategy
We use comprehensive mocking to avoid browser dependencies:

```python
# Example: Testing UserAgentGate without real browser
@pytest.mark.asyncio
async def test_useragent_headers(mock_context):
    gate = UserAgentGate()
    headers = await gate.get_headers(user_agent="Test Agent")
    assert headers["User-Agent"] == "Test Agent"
```

### Async Testing
All async functionality is properly tested:

```python
@pytest.mark.asyncio
async def test_spoofing_pipeline(mock_page, mock_context):
    manager = SpoofingManager()
    await manager.apply_spoofing(mock_page, mock_context, config)
    # Verify spoofing was applied...
```

### Template Testing
JavaScript template rendering is thoroughly tested:

```python
def test_template_rendering(sample_js_templates_dir):
    loader = TemplateLoader(js_dir=sample_js_templates_dir)
    result = loader.load_and_render_template("test.js", {"__VAR__": "value"})
    assert "value" in result
    assert "__VAR__" not in result
```

## Coverage Goals

- **Minimum 80% coverage** for core modules
- **90%+ coverage** for critical components:
  - `Config` class
  - `SpoofingManager` 
  - Gate implementations
  - Template processing

### Viewing Coverage

```bash
# Generate coverage report
python run_tests.py coverage

# View HTML report
open htmlcov/index.html
```

## Testing Best Practices

### 1. Fast and Isolated
- Tests run in < 30 seconds total
- No network dependencies
- No file system pollution
- Proper cleanup of resources

### 2. Descriptive Test Names
```python
def test_get_headers_with_client_hints_support():
    """Test client hints header generation for modern browsers."""
```

### 3. Comprehensive Mocking
```python
@pytest.fixture
def mock_context():
    context = AsyncMock()
    context.route = AsyncMock()
    context.add_init_script = AsyncMock()
    return context
```

### 4. Edge Case Coverage
- Invalid inputs
- Missing dependencies
- Error conditions
- Boundary values

### 5. Integration Boundaries
```python
def test_full_gate_lifecycle():
    """Test complete gate from config to JavaScript injection."""
    # Test the full pipeline without browser
```

## What We Test

### Covered Areas
- **Configuration parsing and validation**
- **Gate interface contracts**
- **JavaScript template processing**
- **Spoofing orchestration logic**
- **Error handling and recovery**
- **Header generation and injection**
- **Template variable substitution**

### Not Covered (Yet)
- End-to-end browser automation
- Actual fingerprint evasion effectiveness
- Performance under load
- Multi-platform compatibility

## Running Specific Tests

```bash
# Run only config tests
pytest tests/test_unit/test_config.py -v

# Run only UserAgent gate tests
pytest tests/test_unit/gates/test_useragent_gate.py -v

# Run tests matching pattern
pytest tests/ -k "test_template" -v

# Run with verbose output
pytest tests/ -v --tb=long

# Run in parallel
pytest tests/ -n auto
```

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Async Test Failures**
- Tests use `@pytest.mark.asyncio` decorator
- Event loop configured in `conftest.py`
- Check for proper `await` usage

**Mock-Related Failures**
- Verify mock setup in fixtures
- Check that mocks match actual interface
- Ensure proper `AsyncMock` vs `Mock` usage

### Debug Mode
```bash
# Run with debugging
pytest tests/ --pdb -v

# Stop on first failure
pytest tests/ -x
```

## Contributing to Tests

### Adding New Tests

1. **Create test file** in appropriate directory
2. **Use existing fixtures** from `conftest.py`
3. **Follow naming conventions** (`test_*.py`)
4. **Add docstrings** explaining test purpose
5. **Mock external dependencies** appropriately

### Test File Template

```python
"""
Test suite for NewComponent.

Brief description of what's being tested.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from src.new_component import NewComponent

class TestNewComponent:
    """Test NewComponent functionality."""
    
    @pytest.fixture
    def component(self):
        """Component instance for testing."""
        return NewComponent()
    
    def test_basic_functionality(self, component):
        """Test basic component behavior."""
        result = component.do_something()
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_async_functionality(self, component, mock_context):
        """Test async component behavior."""
        await component.async_method(mock_context)
        mock_context.some_method.assert_called_once()
```

## Test Strategy Summary

This minimum viable test suite focuses on:

1. **Critical path coverage** - Config, SpoofingManager, core gates
2. **Interface validation** - Ensuring contracts are maintained
3. **Error resistance** - Proper handling of edge cases
4. **Maintainability** - Easy to run, understand, and extend

The goal is ensuring the core fingerprinting evasion logic works correctly before adding browser automation complexity. 