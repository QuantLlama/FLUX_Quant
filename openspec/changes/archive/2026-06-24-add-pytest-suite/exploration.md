## Exploration: Integrate Pytest testing framework and define testing architecture for analysis engines

### Current State
Currently, the codebase contains multiple mathematical analysis engines under the `analysis/` directory (e.g., `quant.py`, `volatility.py`, `fibonacci.py`, `indicators.py`). These modules consist of pure functions that take Pandas DataFrames containing financial OHLCV data and calculate indicators, cycles, squeeze conditions, and order flow approximations. However, there is no formal testing architecture in place to validate these calculations.

### Affected Areas
- `tests/` — New directory that will contain the test suite.
- `tests/conftest.py` — Will be created to define shared pytest fixtures (e.g., mock OHLCV DataFrames, synthetic data generators).
- `tests/analysis/` — Directory to house test files specifically for the analysis engines (e.g., `test_quant.py`, `test_volatility.py`).
- `pytest.ini` or `pyproject.toml` — Needed to configure pytest markers (e.g., `unit`, `integration`, `slow`) and standard options.

### Approaches
1. **Fixture-based Synthetic Data Testing (Unit)** — Use `pytest` fixtures to generate static, predictable Pandas DataFrames (OHLCV) with known values and trends to test specific edge cases (e.g., a perfect bullish trend, a flat range, or divergence).
   - Pros: Extremely fast, fully deterministic, no network dependencies, easy to test exact boundary conditions.
   - Cons: Synthetic data might not perfectly replicate the noise and complexity of real market data.
   - Effort: Medium

2. **Recorded Real-Market Data Snapshots (Integration)** — Save actual historical data snippets (e.g., in CSV or Parquet files under `tests/data/`) and use fixtures to load them. Test if the analysis functions return expected structures/values.
   - Pros: Tests real-world scenarios, guarantees functions don't break under realistic market conditions.
   - Cons: Harder to manually verify exact numeric outputs (requires snapshot testing or verifying broad properties), inflates repository size slightly.
   - Effort: Medium

3. **Live API Fetching** — Fetch data directly from yfinance or Binance API during tests.
   - Pros: Ensures the whole pipeline works end-to-end.
   - Cons: Slow, brittle, prone to failure due to API rate limits or network issues.
   - Effort: Low to implement, High to maintain.

### Recommendation
**Hybrid Approach (Synthetic Unit + Snapshot Integration)**
Start with **Approach 1 (Synthetic Fixtures)** for the core mathematical engines in `analysis/`. By configuring `tests/conftest.py` to provide a few robust synthetic DataFrame fixtures (`bullish_trend_df`, `bearish_trend_df`, `ranging_df`), we can rapidly validate `quant.py` and `volatility.py` logic.

### Risks
- Floating point precision differences across different OS/environments can cause strict `assert`s to fail. (Mitigation: use `pytest.approx` or `numpy.testing.assert_allclose`).
- Empty DataFrame edge cases may crash analysis functions if not handled properly. Testing must include empty or very short DataFrames.

### Ready for Proposal
Yes — the orchestrator can tell the user we're ready to proceed with setting up pytest, fixtures, and the initial tests for the analysis engines.
