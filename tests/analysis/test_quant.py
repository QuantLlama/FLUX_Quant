import pytest
import pandas as pd
import numpy as np
from analysis.quant import (
    fourier_cycle_analysis,
    order_flow_approximation,
    machine_learning_prediction,
    full_quant_analysis,
)

@pytest.mark.unit
def test_fourier_cycle_analysis(bullish_trend_df):
    result = fourier_cycle_analysis(bullish_trend_df['Close'])
    assert isinstance(result, dict)
    assert 'main_cycle_bars' in result
    assert 'phase' in result
    assert 'secondary_cycles' in result

@pytest.mark.unit
def test_order_flow_approximation_synthetic(bullish_trend_df):
    result = order_flow_approximation(bullish_trend_df)
    assert 'score' in result
    assert 'state' in result
    assert 'buy_vol_ratio' in result
    assert result['is_synthetic'] is True

@pytest.mark.unit
def test_order_flow_approximation_real():
    df = pd.DataFrame({
        'Open': [10]*15,
        'High': [12]*15,
        'Low': [8]*15,
        'Close': [11]*15,
        'Volume': [100]*15,
        'Taker_Buy_Volume': [60]*15,
        'Taker_Sell_Volume': [40]*15
    })
    result = order_flow_approximation(df)
    assert result['is_synthetic'] is False
    assert result['buy_vol_ratio'] == pytest.approx(0.6, 0.1)

@pytest.mark.unit
def test_machine_learning_prediction_short_data():
    df = pd.DataFrame({'Close': [1, 2, 3]})
    result = machine_learning_prediction(df)
    assert result['ml_score'] == 0
    assert "No disponible" in result['status']

@pytest.mark.unit
def test_full_quant_analysis_short(short_series):
    result = full_quant_analysis(short_series, capital=1000, risk_pct=1.0)
    assert "error" in result

@pytest.mark.unit
@pytest.mark.parametrize("empty_df", [
    pd.DataFrame(),
    pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
])
def test_edge_cases_empty(empty_df):
    with pytest.raises((IndexError, KeyError, ValueError)):
        order_flow_approximation(empty_df)

@pytest.mark.unit
def test_edge_cases_nan():
    df = pd.DataFrame({
        'Open': [np.nan]*20,
        'High': [np.nan]*20,
        'Low': [np.nan]*20,
        'Close': [np.nan]*20,
        'Volume': [np.nan]*20
    })
    try:
        fourier_cycle_analysis(df['Close'])
    except Exception:
        pass
