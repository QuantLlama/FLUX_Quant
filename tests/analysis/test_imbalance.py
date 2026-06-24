import pytest
import pandas as pd
import numpy as np

from analysis.imbalance import (
    detect_fvg,
    detect_order_blocks,
    detect_liquidity_pools,
    full_imbalance_analysis
)

def create_fvg_df():
    # Create a synthetic dataframe with a clear FVG
    dates = pd.date_range("2023-01-01", periods=5)
    # Candle 1: High at 10
    # Candle 2: Big gap up
    # Candle 3: Low at 20
    # Gap from 10 to 20 -> Bullish FVG
    df = pd.DataFrame({
        "Open": [5, 12, 22, 22, 22],
        "High": [10, 18, 25, 25, 25],
        "Low": [2, 11, 20, 20, 20],
        "Close": [8, 17, 24, 24, 24],
        "Volume": [100]*5
    }, index=dates)
    return df

@pytest.mark.unit
def test_detect_fvg():
    df = create_fvg_df()
    res = detect_fvg(df)
    assert "bullish" in res
    assert res["total_bull"] > 0
    fvg = next((x for x in res["bullish"] if x["bottom"] == 10.0), None)
    assert fvg is not None, "Expected FVG with bottom=10.0 not found"
    assert fvg["top"] == pytest.approx(20.0)
    assert fvg["size"] == pytest.approx(10.0)

@pytest.mark.unit
def test_detect_order_blocks(bullish_trend_df):
    # order blocks logic requires some movement. A strong synthetic trend should have some.
    res = detect_order_blocks(bullish_trend_df)
    assert "bullish" in res
    assert "bearish" in res

@pytest.mark.unit
def test_detect_liquidity_pools():
    dates = pd.date_range("2023-01-01", periods=5)
    # Equal highs at ~100
    df = pd.DataFrame({
        "Open": [90, 90, 90, 90, 90],
        "High": [100.0, 100.1, 95.0, 100.0, 98.0],
        "Low": [80, 80, 80, 80, 80],
        "Close": [95, 95, 95, 95, 95],
        "Volume": [100]*5
    }, index=dates)
    
    res = detect_liquidity_pools(df, tolerance_pct=0.2)
    assert "equal_highs" in res
    assert len(res["equal_highs"]) > 0
    assert res["equal_highs"][0]["touches"] >= 2
    assert res["equal_highs"][0]["price"] == pytest.approx(100.0, rel=0.01)

@pytest.mark.unit
def test_full_imbalance_analysis(bullish_trend_df):
    res = full_imbalance_analysis(bullish_trend_df)
    assert "fvg" in res
    assert "order_blocks" in res
    assert "liquidity_pools" in res
    assert "bias" in res
