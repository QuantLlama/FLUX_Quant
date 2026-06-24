import pytest
import pandas as pd
import numpy as np

def generate_ohlcv(start_price=100.0, trend=0.0, volatility=0.02, periods=100, seed=42):
    np.random.seed(seed)
    dates = pd.date_range(start="2023-01-01", periods=periods, freq="D")
    
    # Generate random returns with a trend
    returns = np.random.normal(loc=trend, scale=volatility, size=periods)
    
    # Calculate closing prices
    close = start_price * np.exp(np.cumsum(returns))
    
    # Generate OHLC around the close
    high = close * (1 + np.abs(np.random.normal(0, volatility/2, size=periods)))
    low = close * (1 - np.abs(np.random.normal(0, volatility/2, size=periods)))
    
    # randomize open between low and high
    open_p = low + np.random.rand(periods) * (high - low)
    
    # Fix high/low relative to open and close
    high = np.maximum(high, np.maximum(open_p, close))
    low = np.minimum(low, np.minimum(open_p, close))
    
    volume = np.random.randint(1000, 100000, size=periods)
    
    df = pd.DataFrame({
        "Open": open_p,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume
    }, index=dates)
    return df

@pytest.fixture
def bullish_trend_df():
    """Synthetic bullish trend DataFrame."""
    return generate_ohlcv(trend=0.005, volatility=0.015, periods=100, seed=1)

@pytest.fixture
def bearish_trend_df():
    """Synthetic bearish trend DataFrame."""
    return generate_ohlcv(trend=-0.005, volatility=0.015, periods=100, seed=2)

@pytest.fixture
def ranging_df():
    """Synthetic ranging market DataFrame."""
    return generate_ohlcv(trend=0.0, volatility=0.02, periods=100, seed=3)

@pytest.fixture
def empty_series():
    """Empty DataFrame for edge cases."""
    return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

@pytest.fixture
def short_series():
    """Short DataFrame for boundary conditions."""
    return generate_ohlcv(periods=5, seed=4)
