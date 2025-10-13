# Strategic Build Planner - Test Suite

This directory contains automated tests for the Strategic Build Planner project.

## Structure

```
tests/
├── unit/                    # Unit tests (fast, no external dependencies)
│   ├── conftest.py         # Shared fixtures
│   └── test_context_pack.py # Tests for context_pack module
└── integration/             # Integration tests (coming soon)
```

## Running Tests

### Quick Run (all tests)
```powershell
pytest
```

### Run specific test file
```powershell
pytest tests/unit/test_context_pack.py
```

### Run with verbose output
```powershell
pytest -v
```

### Run with coverage report
```powershell
pytest tests/unit/test_context_pack.py --cov=server.lib.context_pack --cov-report=term-missing
```

### Run and generate HTML coverage report
```powershell
pytest tests/unit/test_context_pack.py --cov=server.lib.context_pack --cov-report=html
# Then open htmlcov/index.html in your browser
```

### Run specific test class
```powershell
pytest tests/unit/test_context_pack.py::TestFactConflictResolution -v
```

### Run specific test
```powershell
pytest tests/unit/test_context_pack.py::TestFactConflictResolution::test_drawing_beats_quote_same_topic -v
```

## Test Coverage

### Unit Tests - context_pack.py

**Coverage: 87%** (166 statements, 21 missed)

The missed lines are primarily in the `if __name__ == "__main__"` demo section at the end of the module.

**Test Categories:**
- ✅ Source kind detection (12 tests) - All document types covered
- ✅ Precedence and authority resolution (18 tests) - All rules validated
- ✅ Build source registry (4 tests) - File and Confluence integration
- ✅ Fact conflict resolution (6 tests) - Canonical selection logic
- ✅ Scope filtering (5 tests) - applies_if conditional logic
- ✅ Context pack structure (4 tests) - Serialization and validation
- ✅ Edge cases (4 tests) - Error conditions and malformed data

**Total: 53 passing tests**

## Known Issues Documented by Tests

The tests document several known quirks in the source detection logic:

1. **Underscore handling** - `Purchase_Order_1001.pdf` doesn't match because underscores prevent "purchase order" from being detected as a phrase
2. **Substring matching** - `"Proposal"` incorrectly matches `"po"` substring before checking for `"proposal"` keyword

These are marked with TODO comments in the test file for future fixes.

## Writing New Tests

### Use the fixtures in conftest.py

```python
def test_my_scenario(sample_sources, sample_project, make_fact):
    # sample_sources: List of 5 standard test sources
    # sample_project: Dict with customer/family/name
    # make_fact: Factory to create Fact objects easily

    fact = make_fact("Topic", "Claim", "DWG-001", "mandatory", 1)
    pack = freeze_context_pack(sample_sources, [fact], sample_project)

    assert len(pack.facts) == 1
```

### Follow the test structure

```python
class TestYourFeature:
    """Test description."""

    def test_specific_behavior(self):
        """Should do X when Y."""
        # Arrange
        input_data = {...}

        # Act
        result = function_under_test(input_data)

        # Assert
        assert result == expected
```

### Naming conventions

- Test files: `test_*.py`
- Test classes: `Test*` (PascalCase)
- Test functions: `test_*` (snake_case, descriptive)
- Use docstrings to explain what's being tested

## CI/CD Integration

Tests are automatically run on:
- Every commit (pre-commit hook)
- Pull requests (GitHub Actions)
- Scheduled nightly builds

**Minimum coverage threshold: 80%**

## Dependencies

The test suite requires:
- `pytest >= 8.0`
- `pytest-cov >= 4.0`
- `pytest-asyncio >= 0.23` (for future async tests)

Install with:
```powershell
pip install pytest pytest-cov pytest-asyncio
```

## Troubleshooting

### Tests fail with import errors
Make sure you're running from the project root directory:
```powershell
cd "c:\Users\tsmith\OneDrive - Northern Manufacturing Co., Inc\Documents\GitHub\StrategicBuildPlanner"
pytest
```

### Coverage report not generated
Install pytest-cov:
```powershell
pip install pytest-cov
```

### Tests run but skip some
Check for missing dependencies:
```powershell
pytest --collect-only
```

## Future Test Plans

- [ ] Unit tests for specialist agents (QMA, PMA, EMA, SCA)
- [ ] Unit tests for rendering module
- [ ] Unit tests for session_store
- [ ] Integration tests with mocked OpenAI responses
- [ ] End-to-end API tests with test fixtures
- [ ] Performance/load tests for /agents/run endpoint

## Contributing

When adding new functionality:
1. Write tests first (TDD approach recommended)
2. Ensure existing tests still pass
3. Maintain > 80% coverage
4. Document any known issues with TODO comments
5. Add docstrings explaining test intent
