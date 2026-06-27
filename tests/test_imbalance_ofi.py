import pytest
import pandas as pd
import numpy as np

# We'll import the functions to test. Note: these don't exist in analysis/imbalance.py yet.
# Under Strict TDD, writing the test first (RED) is mandatory.
from analysis.imbalance import (
    calculate_l2_ofi,
    calculate_tick_volume_ofi
)

@pytest.mark.unit
def test_calculate_l2_ofi_happy_path():
    # Bids and asks structures: list of dicts with price and size, or list of tuples. Let's design the API.
    # We can represent order book updates at t and t-1.
    # calculate_l2_ofi(bids_t, bids_t_1, asks_t, asks_t_1)
    
    # Bid cases:
    # 1. Pb(t) > Pb(t-1) -> delta Q_b = Q_b(t)
    # 2. Pb(t) == Pb(t-1) -> delta Q_b = Q_b(t) - Q_b(t-1)
    # 3. Pb(t) < Pb(t-1) -> delta Q_b = 0
    
    # Ask cases:
    # 1. Pa(t) > Pa(t-1) -> delta Q_a = 0
    # 2. Pa(t) == Pa(t-1) -> delta Q_a = Q_a(t) - Q_a(t-1)
    # 3. Pa(t) < Pa(t-1) -> delta Q_a = Q_a(t)
    
    # Setup 1 (Price equals, qty increases for bid, decreases for ask -> Positive OFI)
    bids_t = {"price": 100.0, "size": 15.0}
    bids_t_1 = {"price": 100.0, "size": 10.0}
    asks_t = {"price": 101.0, "size": 8.0}
    asks_t_1 = {"price": 101.0, "size": 12.0}
    
    # Delta Q_b = 15 - 10 = 5
    # Delta Q_a = 8 - 12 = -4
    # OFI = Delta Q_b - Delta Q_a = 5 - (-4) = 9
    ofi = calculate_l2_ofi(bids_t, bids_t_1, asks_t, asks_t_1)
    assert ofi == 9.0

@pytest.mark.unit
def test_calculate_l2_ofi_price_change():
    # Setup 2 (Bid price rises, Ask price falls -> Bid size fully counted, Ask size fully counted)
    bids_t = {"price": 100.5, "size": 12.0}
    bids_t_1 = {"price": 100.0, "size": 10.0}
    asks_t = {"price": 100.8, "size": 5.0}
    asks_t_1 = {"price": 101.0, "size": 12.0}
    
    # Pb(t) > Pb(t-1) -> Delta Q_b = 12
    # Pa(t) < Pa(t-1) -> Delta Q_a = 5
    # OFI = 12 - 5 = 7
    ofi = calculate_l2_ofi(bids_t, bids_t_1, asks_t, asks_t_1)
    assert ofi == 7.0

@pytest.mark.unit
def test_calculate_tick_volume_ofi_binance():
    # For Binance: OFI = V_taker_buy - V_taker_sell
    df = pd.DataFrame({
        "Volume": [10.0, 20.0],
        "Taker_Buy_Volume": [7.0, 15.0],
        "Taker_Sell_Volume": [3.0, 5.0]
    })
    # T1: 7 - 3 = 4
    # T2: 15 - 5 = 10
    # Expected series of OFIs
    ofi = calculate_tick_volume_ofi(df, source="binance")
    pd.testing.assert_series_equal(ofi, pd.Series([4.0, 10.0], name="ofi"))

@pytest.mark.unit
def test_calculate_tick_volume_ofi_mt5():
    # For MT5: OFI = Volume * (Close - Low)/(High - Low) - Volume * (High - Close)/(High - Low)
    # inside df: High, Low, Close, Volume
    df = pd.DataFrame({
        "High": [10.0, 10.0],
        "Low": [5.0, 8.0],
        "Close": [8.0, 9.0],
        "Volume": [100.0, 50.0]
    })
    # T1:
    # Close - Low = 3
    # High - Low = 5
    # Buy side = 100 * (3 / 5) = 60
    # High - Close = 2
    # Sell side = 100 * (2 / 5) = 40
    # OFI = 60 - 40 = 20
    
    # T2:
    # Close - Low = 1
    # High - Low = 2
    # Buy side = 50 * (1 / 2) = 25
    # High - Close = 1
    # Sell side = 50 * (1 / 2) = 25
    # OFI = 25 - 25 = 0
    
    ofi = calculate_tick_volume_ofi(df, source="mt5")
    pd.testing.assert_series_equal(ofi, pd.Series([20.0, 0.0], name="ofi"))
