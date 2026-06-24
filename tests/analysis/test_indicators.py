import pytest
import pandas as pd
import numpy as np

from analysis.indicators import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_stochastic,
    calculate_adx,
    calculate_all_indicators
)

@pytest.mark.unit
def test_calculate_sma(bullish_trend_df):
    close = bullish_trend_df["Close"]
    sma20 = calculate_sma(close, 20)
    assert len(sma20) == len(close)
    # The first 19 elements should be NaN
    assert pd.isna(sma20.iloc[0])
    assert pd.isna(sma20.iloc[18])
    assert not pd.isna(sma20.iloc[19])
    
    # Check value manually for a small mock series
    mock_series = pd.Series([1, 2, 3, 4, 5])
    mock_sma = calculate_sma(mock_series, 3)
    assert mock_sma.iloc[2] == pytest.approx(2.0)
    assert mock_sma.iloc[4] == pytest.approx(4.0)

@pytest.mark.unit
def test_calculate_ema(bullish_trend_df):
    close = bullish_trend_df["Close"]
    ema20 = calculate_ema(close, 20)
    assert len(ema20) == len(close)
    # EMA uses ewm, adjust=False, so first element is not NaN
    assert not pd.isna(ema20.iloc[0])

@pytest.mark.unit
def test_calculate_rsi(bullish_trend_df, bearish_trend_df):
    rsi_bull = calculate_rsi(bullish_trend_df["Close"])
    rsi_bear = calculate_rsi(bearish_trend_df["Close"])
    
    assert len(rsi_bull) == len(bullish_trend_df)
    assert len(rsi_bear) == len(bearish_trend_df)
    
    # Bullish RSI should generally be higher than Bearish RSI at the end
    assert rsi_bull.iloc[-1] > rsi_bear.iloc[-1]
    
    # Values should be between 0 and 100
    assert (rsi_bull >= 0).all() and (rsi_bull <= 100).all()

@pytest.mark.unit
def test_calculate_macd(bullish_trend_df):
    close = bullish_trend_df["Close"]
    macd_res = calculate_macd(close)
    
    assert "macd" in macd_res
    assert "signal" in macd_res
    assert "hist" in macd_res
    
    assert len(macd_res["macd"]) == len(close)
    assert np.allclose(macd_res["macd"] - macd_res["signal"], macd_res["hist"], equal_nan=True)

@pytest.mark.unit
def test_calculate_stochastic(ranging_df):
    stoch = calculate_stochastic(ranging_df)
    assert "k" in stoch
    assert "d" in stoch
    
    # Check values between 0 and 100
    assert (stoch["k"] >= 0).all() and (stoch["k"] <= 100).all()
    assert (stoch["d"] >= 0).all() and (stoch["d"] <= 100).all()

@pytest.mark.unit
def test_calculate_adx(bullish_trend_df):
    adx_res = calculate_adx(bullish_trend_df)
    assert "adx" in adx_res
    assert "plus_di" in adx_res
    assert "minus_di" in adx_res
    
    # Strong bullish trend should have high ADX and high +DI
    assert adx_res["adx"].iloc[-1] > 20
    assert adx_res["plus_di"].iloc[-1] > adx_res["minus_di"].iloc[-1]

@pytest.mark.unit
def test_calculate_all_indicators(ranging_df, short_series):
    # Valid dataframe
    all_ind = calculate_all_indicators(ranging_df)
    assert "price" in all_ind
    assert "emas" in all_ind
    assert "smas" in all_ind
    assert "rsi" in all_ind
    assert "macd" in all_ind
    assert "stochastic" in all_ind
    assert "adx" in all_ind
    
    # Too short dataframe
    res_short = calculate_all_indicators(short_series)
    assert res_short == {}
    
    # Empty dataframe
    empty_df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    res_empty = calculate_all_indicators(empty_df)
    assert res_empty == {}

@pytest.mark.parametrize("df_fixture", ["bullish_trend_df", "bearish_trend_df", "ranging_df"])
@pytest.mark.unit
def test_indicators_no_nans_on_all_indicators(df_fixture, request):
    df = request.getfixturevalue(df_fixture)
    res = calculate_all_indicators(df)
    
    # Ensure no NaN is returned in the dictionaries
    assert not np.isnan(res["price"])
    assert not np.isnan(res["rsi"]["value"])
    assert not np.isnan(res["macd"]["macd"])
