import pytest
import pandas as pd
import numpy as np

from analysis.gann import (
    calculate_gann_fan,
    square_of_9,
    gann_time_cycles,
    full_gann_analysis
)

@pytest.mark.unit
def test_calculate_gann_fan(bullish_trend_df):
    res = calculate_gann_fan(bullish_trend_df)
    assert "pivot_idx" in res
    assert "fan_levels" in res
    assert "1x1" in res["fan_levels"]
    
    # 1x1 should have price_now
    assert "price_now" in res["fan_levels"]["1x1"]

@pytest.mark.unit
def test_square_of_9():
    price = 100.0
    res = square_of_9(price)
    
    assert res["base_price"] == price
    assert res["sqrt_price"] == 10.0
    assert "key_levels" in res
    # 360 degree offset from 10 is 10 + 2 = 12 -> 12^2 = 144
    assert res["key_levels"]["360°"] == pytest.approx(144.0)
    # 180 degree offset from 10 is 10 + 1 = 11 -> 11^2 = 121
    assert res["key_levels"]["180°"] == pytest.approx(121.0)

@pytest.mark.unit
def test_gann_time_cycles(bullish_trend_df):
    res = gann_time_cycles(bullish_trend_df)
    assert "current_bar" in res
    assert "past_cycles" in res
    assert "next_cycle_bars" in res
    assert len(res["past_cycles"]) > 0

@pytest.mark.unit
def test_full_gann_analysis(bullish_trend_df):
    res = full_gann_analysis(bullish_trend_df)
    assert "fan" in res
    assert "square_of_9" in res
    assert "time_cycles" in res
    assert "nearest_levels" in res
