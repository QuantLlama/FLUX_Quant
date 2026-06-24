import pytest
import pandas as pd
import numpy as np

from analysis.fibonacci import (
    calculate_retracements,
    calculate_extensions,
    auto_detect_swings,
    fibonacci_fan,
    confluence_zones,
    full_fibonacci_analysis,
    FIB_LEVELS,
    FIB_EXTENSIONS
)

@pytest.mark.unit
def test_calculate_retracements_up():
    swing_high = 150.0
    swing_low = 100.0
    res = calculate_retracements(swing_high, swing_low, direction="up")
    
    assert res["type"] == "retracement"
    assert res["direction"] == "up"
    assert res["range"] == pytest.approx(50.0)
    
    # 0.0 -> swing_high, 1.0 -> swing_low for up direction
    assert res["levels"][0.0] == pytest.approx(150.0)
    assert res["levels"][1.0] == pytest.approx(100.0)
    assert res["levels"][0.5] == pytest.approx(125.0)

@pytest.mark.unit
def test_calculate_retracements_down():
    swing_high = 150.0
    swing_low = 100.0
    res = calculate_retracements(swing_high, swing_low, direction="down")
    
    assert res["direction"] == "down"
    # 0.0 -> swing_low, 1.0 -> swing_high for down direction
    assert res["levels"][0.0] == pytest.approx(100.0)
    assert res["levels"][1.0] == pytest.approx(150.0)
    assert res["levels"][0.5] == pytest.approx(125.0)

@pytest.mark.unit
def test_calculate_extensions_up():
    swing_high = 150.0
    swing_low = 100.0
    res = calculate_extensions(swing_high, swing_low, direction="up", custom_levels=FIB_EXTENSIONS)
    
    assert res["type"] == "extension"
    assert res["direction"] == "up"
    # 1.0 -> swing_low + 1.0 * range -> 150.0 for up direction
    assert res["levels"][1.0] == pytest.approx(150.0)
    assert res["levels"][2.0] == pytest.approx(200.0)

@pytest.mark.unit
def test_calculate_extensions_down():
    swing_high = 150.0
    swing_low = 100.0
    res = calculate_extensions(swing_high, swing_low, direction="down", custom_levels=FIB_EXTENSIONS)
    
    assert res["direction"] == "down"
    # 1.0 -> swing_high - 1.0 * range -> 100.0 for down direction
    assert res["levels"][1.0] == pytest.approx(100.0)
    assert res["levels"][2.0] == pytest.approx(50.0)

@pytest.mark.unit
def test_auto_detect_swings_up():
    # Make a dataframe where low is early and high is late -> 'up'
    df = pd.DataFrame({
        "High": [10, 20, 30, 40, 35],
        "Low": [5, 15, 25, 35, 30]
    }, index=pd.date_range("2023-01-01", periods=5))
    
    high, low, direction = auto_detect_swings(df)
    assert high == pytest.approx(40.0)
    assert low == pytest.approx(5.0)
    assert direction == "up"

@pytest.mark.unit
def test_auto_detect_swings_down():
    # Make a dataframe where high is early and low is late -> 'down'
    df = pd.DataFrame({
        "High": [40, 30, 20, 10, 15],
        "Low": [35, 25, 15, 5, 10]
    }, index=pd.date_range("2023-01-01", periods=5))
    
    high, low, direction = auto_detect_swings(df)
    assert high == pytest.approx(40.0)
    assert low == pytest.approx(5.0)
    assert direction == "down"

@pytest.mark.unit
def test_fibonacci_fan():
    res = fibonacci_fan(pivot_price=100.0, pivot_date_idx=0, swing_price=150.0, swing_date_idx=10, current_idx=20)
    assert res["type"] == "fan"
    # slope = 50 / 10 = 5
    # level 0.5: 100 + 5 * 0.5 * 20 = 100 + 50 = 150
    assert res["levels"][0.5] == pytest.approx(150.0)

@pytest.mark.unit
def test_confluence_zones():
    retracement = {
        "levels": {
            0.5: 125.0,
            0.618: 119.1
        }
    }
    other_levels = [124.5, 120.0, 150.0]
    # 124.5 is within 0.5% of 125.0 (diff: 0.5/124.5 = 0.4%) -> confluence
    # 120.0 is not within 0.5% of 119.1 (diff: 0.9/120.0 = 0.75%) -> no confluence
    # 150.0 is far
    
    res = confluence_zones(retracement, other_levels, tolerance_pct=0.5)
    assert len(res) == 1
    assert res[0]["fib_level"] == 0.5
    assert res[0]["other_price"] == 124.5

@pytest.mark.unit
def test_full_fibonacci_analysis(bullish_trend_df):
    res = full_fibonacci_analysis(bullish_trend_df)
    
    assert "swing_high" in res
    assert "swing_low" in res
    assert res["direction"] in ["up", "down"]
    assert "retracements" in res
    assert "extensions" in res
    assert "closest_level" in res
