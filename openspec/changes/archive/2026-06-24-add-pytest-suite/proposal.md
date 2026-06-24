# Proposal: Add Pytest Suite for Analysis Engines

## Intent

FLUX_Quant's 11 analysis modules (`analysis/`) contain critical financial math — Fibonacci retracements, volatility models, Gann angles, quant scoring, etc. — with zero automated tests. Regressions in these pure functions risk producing incorrect trading signals. This change bootstraps a pytest suite covering the analysis layer with synthetic and snapshot-based tests.

## Scope

### In Scope
- pytest infrastructure: `conftest.py`, `pyproject.toml` markers, directory layout
- Synthetic DataFrame fixtures (bullish, bearish, ranging, empty, short)
- Unit tests for all 11 `analysis/` modules
- Recorded-snapshot integration tests (`tests/data/`)
- Float-precision assertions via `pytest.approx` / `numpy.testing.assert_allclose`
- Edge-case coverage: empty DataFrames, single-row, NaN-heavy inputs

### Out of Scope
- Live API calls or network-dependent tests
- Tests for `connectors/`, `web/`, `ui/`, `strategies/`
- CI/CD pipeline configuration
- Coverage enforcement thresholds
- Performance / benchmark testing

## Capabilities

### New Capabilities
- `test-infra`: pytest config, markers (`unit`, `integration`, `slow`), `conftest.py` with shared OHLCV fixtures
- `synthetic-fixtures`: Deterministic DataFrame factories for bullish trend, bearish trend, ranging, empty, and short-series scenarios
- `snapshot-data`: Recorded CSV snapshots in `tests/data/` for reproducible integration tests
- `analysis-unit-tests`: Unit tests covering core functions in all 11 analysis modules
- `edge-case-coverage`: Parametrized tests for empty, single-row, and NaN-heavy DataFrames

### Modified Capabilities
- None — additive change only

## Approach

1. **Infrastructure**: Add `tests/` directory with `conftest.py` housing shared fixtures. Configure pytest in `pyproject.toml` with markers.
2. **Fixtures**: Build deterministic OHLCV DataFrames using numpy/pandas (seeded RNG). Store 2-3 real-market CSV snapshots under `tests/data/`.
3. **Unit Tests**: One test module per analysis module (`test_quant.py`, `test_volatility.py`, etc.). Test return types, value ranges, and known mathematical identities.
4. **Integration Tests**: Validate full analysis pipelines against snapshot data with recorded expected outputs.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `tests/` | **New** | Entire test directory, conftest, fixtures |
| `tests/data/` | **New** | Recorded CSV snapshots |
| `pyproject.toml` | **New/Modified** | pytest configuration and markers |
| `requirements.txt` | **Modified** | Add pytest, pytest-cov dev dependencies |
| `analysis/` | **Read-only** | Modules under test — no code changes |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Snapshot data becomes stale | Low | Snapshots are static historical data, not live |
| Float precision failures across platforms | Medium | Use `pytest.approx(rel=1e-6)` consistently |
| Large test surface slows initial development | Medium | Prioritize core modules (quant, volatility, fibonacci) first |

## Rollback Plan

Delete `tests/` directory and revert `pyproject.toml` / `requirements.txt` changes. No production code is modified.

## Dependencies

- `pytest >= 7.0`
- `pytest-cov` (optional, for coverage reports)
- Existing `pandas`, `numpy` already in project

## Success Criteria

- [ ] `pytest` runs from project root with zero failures
- [ ] All 11 analysis modules have at least one test module
- [ ] Synthetic fixtures cover bullish, bearish, ranging, empty, and short scenarios
- [ ] Edge cases (empty DF, single row, NaN) are tested for each module
- [ ] No test makes network calls
- [ ] `pytest -m unit` and `pytest -m integration` selectors work correctly
