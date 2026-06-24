# Apply Progress: add-pytest-suite

## Completed Tasks

- [x] 1.1 Update `requirements.txt` to include `pytest>=7.0` and `pytest-cov`.
- [x] 1.2 Update `pyproject.toml` with `[tool.pytest.ini_options]` to register `unit`, `integration`, and `slow` markers.
- [x] 1.3 Create `tests/data/` directory and add at least one placeholder or generated CSV snapshot (e.g., `tests/data/sample_ohlcv.csv`).
- [x] 1.4 Create `tests/conftest.py` with synthetic DataFrame fixtures: `bullish_trend_df`, `bearish_trend_df`, `ranging_df`, `empty_series`, and `short_series`.
- [x] 2.1 Create `tests/analysis/test_quant.py`. Write unit tests for `analysis/quant.py` using synthetic fixtures and `pytest.approx`.
- [x] 2.2 In `test_quant.py`, write edge case parametrized tests (empty DataFrames, NaN values).
- [x] 2.3 Create `tests/analysis/test_volatility.py`. Write unit tests for `analysis/volatility.py` using synthetic fixtures.
- [x] 2.4 In `test_volatility.py`, test the ATR and Bollinger calculations against known mathematical constants/bounds.
- [x] 3.1 Create `tests/analysis/test_fibonacci.py`. Test retracement and extension calculations using synthetic data.
- [x] 3.2 Create `tests/analysis/test_indicators.py`. Test RSI, MACD, Stochastic using synthetic trending and ranging fixtures.
- [x] 3.3 Create basic tests for `gann.py`, `imbalance.py`, and `market_structure.py` under `tests/analysis/`.
- [x] 4.1 Create `tests/analysis/test_integration.py`. Write a test that loads `tests/data/sample_ohlcv.csv` and runs it through the full analysis scoring engine.
- [x] 4.2 Verify that network calls (e.g., to yfinance) are properly mocked or completely bypassed during the integration test using `unittest.mock.patch`.
