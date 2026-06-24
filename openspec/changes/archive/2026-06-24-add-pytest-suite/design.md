# Design: Add Pytest Suite for Analysis Engines

## Technical Approach

The implementation will introduce a structured `pytest` suite focused on validating the 11 analysis modules within `FLUX_Quant/analysis/`. This test suite relies heavily on deterministic synthetic fixtures to generate market conditions (bullish, bearish, ranging) and edge cases (NaNs, empty DataFrames) dynamically without relying on external network calls.

The core infrastructure will reside in a new `tests/` directory at the project root. Shared OHLCV fixtures and synthetic data generators will be defined in `tests/conftest.py`. The `pyproject.toml` file will be updated to configure `pytest`, registering custom markers (`unit`, `integration`, `slow`) to allow granular test execution. 

Integration tests will use recorded snapshot data stored as CSV files in `tests/data/` to validate full analytical pipelines without triggering live API requests (e.g., bypassing `yfinance`). A strict policy of network isolation will be enforced by mocking any outward-facing clients during the test session.

All floating-point assertions will utilize `pytest.approx` or `numpy.testing.assert_allclose` to prevent precision-related flakiness across different execution environments.

## Architecture Decisions

### 1. Market Data Simulation Strategy

*   **Choice:** Algorithmic synthetic generation via `pytest` fixtures for unit tests, combined with static CSV snapshots for integration tests.
*   **Alternatives:** 
    *   *Option A:* Use live `yfinance` API calls for all tests.
    *   *Option B:* Mock all data generation locally using only static JSON/CSV files.
*   **Rationale:** Live API calls (Option A) are flaky, slow, and violate deterministic testing principles. Relying entirely on static files (Option B) makes testing edge cases (like extreme volatility or empty datasets) cumbersome. The hybrid approach gives us the flexibility to test mathematical correctness via synthetic data boundaries while validating end-to-end integration using realistic historical snapshots.

### 2. Float Precision Assertion Mechanism

*   **Choice:** Use `pytest.approx` for scalar values and `numpy.testing.assert_allclose` for Series/DataFrame comparisons.
*   **Alternatives:** 
    *   *Option A:* Exact equality `==`.
    *   *Option B:* Manual delta checks (`abs(a - b) < 1e-6`).
*   **Rationale:** Financial calculations (like Fibonacci retracements and Gann angles) inherently suffer from floating-point arithmetic imprecision. Exact equality (Option A) will fail randomly. Manual checks (Option B) result in bloated test code. Standardizing on `pytest.approx` and `assert_allclose` provides robust, readable precision management natively tailored for our `pandas` and `numpy` stack.

### 3. Test File Organization

*   **Choice:** Mirror the `analysis/` directory structure under `tests/analysis/` (e.g., `tests/analysis/test_quant.py`, `tests/analysis/test_volatility.py`).
*   **Alternatives:** 
    *   *Option A:* Group tests by feature (e.g., `tests/test_trends.py`).
    *   *Option B:* Put all analysis tests in a single `test_analysis.py` file.
*   **Rationale:** Mirroring the source tree minimizes cognitive load for developers trying to locate corresponding tests. It also scales perfectly as new analysis modules are added, preventing the creation of monolithic, hard-to-maintain test files.

## File Changes

*   **`pyproject.toml`**: (Modified) Add `[tool.pytest.ini_options]` section to register `unit`, `integration`, and `slow` markers, and configure base test discovery paths.
*   **`requirements.txt`**: (Modified) Add `pytest>=7.0` and `pytest-cov`.
*   **`tests/conftest.py`**: (New) Defines reusable synthetic fixtures (e.g., `bullish_trend`, `bearish_trend`, `empty_series`, `short_series`).
*   **`tests/data/*.csv`**: (New) Static snapshot files for integration testing (e.g., `tests/data/aapl_2023_snapshot.csv`).
*   **`tests/analysis/test_quant.py`**: (New) Unit tests and edge case parametrized tests for the `quant` module.
*   **`tests/analysis/test_volatility.py`**: (New) Unit tests for the `volatility` module.
*   (Additional `test_*.py` files will be created for the remaining 9 analysis modules.)

## Testing Strategy

1.  **Test Levels**: 
    *   **Unit Tests (`@pytest.mark.unit`)**: Validate individual analysis functions using synthetic data fixtures. Ensure mathematical accuracy and proper edge-case handling (NaNs, empty inputs).
    *   **Integration Tests (`@pytest.mark.integration`)**: Validate data flows from simulated data ingestion (using snapshot CSVs) through complex indicator computations.
2.  **Parametrization**: Leverage `@pytest.mark.parametrize` to run identical tests across boundary conditions (e.g., passing 1-row DataFrames, empty DataFrames, and NaNs) to ensure consistent failure modes without crashing.
3.  **Mocking & Isolation**: Any accidental calls to `connectors/` or `yfinance` will be intercepted and mocked using `unittest.mock.patch` to guarantee complete network isolation.
