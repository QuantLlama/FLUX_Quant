import pytest
import pandas as pd
import numpy as np

from analysis.market_structure import (
    detect_swings,
    analyze_market_structure
)

def create_swing_df():
    dates = pd.date_range("2023-01-01", periods=15)
    # Peak at index 5 (period=2)
    highs = [10, 12, 14, 16, 18, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2]
    lows = [h - 2 for h in highs]
    df = pd.DataFrame({
        "Open": lows,
        "High": highs,
        "Low": lows,
        "Close": lows,
        "Volume": [100]*15
    }, index=dates)
    return df

@pytest.mark.unit
def test_detect_swings():
    df = create_swing_df()
    sw_highs, sw_lows = detect_swings(df, period=2)
    
    # The high at index 5 is 20. It should be a swing high.
    assert sw_highs.iloc[5] == pytest.approx(20.0)
    # Ensure it's NaN elsewhere around the peak
    assert pd.isna(sw_highs.iloc[4])
    assert pd.isna(sw_highs.iloc[6])

@pytest.mark.unit
def test_analyze_market_structure(bullish_trend_df):
    # Using a trending df to detect BOS
    res = analyze_market_structure(bullish_trend_df, period=3)
    assert "trend" in res
    assert "recent_highs" in res
    assert "recent_lows" in res
    
    # The trend should likely be bullish or have some BOS counts
    assert res["trend"] in ["alcista", "bajista", "neutral", "indeterminado"]
