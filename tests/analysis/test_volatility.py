import pytest
import pandas as pd
import numpy as np
from analysis.volatility import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_keltner,
    detect_squeeze,
    calculate_stops_targets,
    volatility_percentile,
    intraday_range_estimate,
    full_volatility_analysis
)

@pytest.fixture
def flat_df():
    return pd.DataFrame({
        'Open': [100]*30,
        'High': [100]*30,
        'Low': [100]*30,
        'Close': [100]*30,
        'Volume': [1000]*30
    })

@pytest.fixture
def steady_range_df():
    return pd.DataFrame({
        'Open': [100]*30,
        'High': [105]*30,
        'Low': [95]*30,
        'Close': [100]*30,
        'Volume': [1000]*30
    })

@pytest.mark.unit
def test_calculate_atr_flat(flat_df):
    atr = calculate_atr(flat_df, period=14)
    assert atr.iloc[-1] == pytest.approx(0.0)

@pytest.mark.unit
def test_calculate_atr_steady(steady_range_df):
    atr = calculate_atr(steady_range_df, period=14)
    assert atr.iloc[-1] == pytest.approx(10.0)

@pytest.mark.unit
def test_bollinger_bands_flat(flat_df):
    bb = calculate_bollinger_bands(flat_df, period=20, std=2.0)
    assert bb['upper'] == pytest.approx(100.0)
    assert bb['lower'] == pytest.approx(100.0)
    assert bb['middle'] == pytest.approx(100.0)
    assert bb['width'] == pytest.approx(0.0)

@pytest.mark.unit
def test_calculate_keltner(steady_range_df):
    kc = calculate_keltner(steady_range_df, period=20, atr_mult=1.5)
    assert kc['middle'] == pytest.approx(100.0)
    assert kc['upper'] == pytest.approx(115.0)
    assert kc['lower'] == pytest.approx(85.0)

@pytest.mark.unit
def test_detect_squeeze_active():
    bb = {'upper': 110, 'lower': 90}
    kc = {'upper': 115, 'lower': 85}
    sq = detect_squeeze(bb, kc)
    assert sq['in_squeeze'] is True

@pytest.mark.unit
def test_detect_squeeze_inactive():
    bb = {'upper': 120, 'lower': 80}
    kc = {'upper': 115, 'lower': 85}
    sq = detect_squeeze(bb, kc)
    assert sq['in_squeeze'] is False

@pytest.mark.unit
def test_calculate_stops_targets(steady_range_df):
    res = calculate_stops_targets(100.0, 'long', steady_range_df, atr_period=14, sl_mult=1.0, tp1_mult=2.0, tp2_mult=3.0)
    assert res['stop_loss'] == pytest.approx(90.0)
    assert res['take_profit_1'] == pytest.approx(120.0)
    assert res['take_profit_2'] == pytest.approx(130.0)

@pytest.mark.unit
def test_intraday_range_estimate(steady_range_df):
    res = intraday_range_estimate(steady_range_df)
    assert res['atr'] == pytest.approx(10.0)
    assert res['expected_range'] == pytest.approx(20.0)

@pytest.mark.unit
def test_full_volatility_analysis(steady_range_df):
    res = full_volatility_analysis(steady_range_df)
    assert 'atr' in res
    assert 'bollinger' in res
    assert 'keltner' in res
    assert 'squeeze' in res
    assert 'stops_long' in res
    assert 'stops_short' in res
