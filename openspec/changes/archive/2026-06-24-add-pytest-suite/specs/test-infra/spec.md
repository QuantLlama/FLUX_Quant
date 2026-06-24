# Test Infra Specification

## Purpose
Establishes the foundational pytest configuration, markers, and shared fixtures required to test the FLUX_Quant analysis engines.

## Requirements

### Requirement: Pytest Configuration
The system MUST configure pytest with strict markers.

#### Scenario: Running unit tests
- GIVEN a configured `pyproject.toml`
- WHEN the user runs `pytest -m unit`
- THEN only tests marked as `unit` are executed

#### Scenario: Running integration tests
- GIVEN a configured `pyproject.toml`
- WHEN the user runs `pytest -m integration`
- THEN only tests marked as `integration` are executed

### Requirement: Shared Fixtures
The system MUST provide shared base fixtures in `conftest.py`.

#### Scenario: Injecting OHLCV data
- GIVEN a test requiring market data
- WHEN the test requests the `ohlcv_base` fixture
- THEN pytest provides a standard pandas DataFrame with OHLCV columns
