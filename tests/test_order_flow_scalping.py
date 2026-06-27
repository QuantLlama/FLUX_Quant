import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

# Under TDD, we write the integration tests first (RED).
# This tests the event loop, ingestion flow, signals, and execution.
from strategies.order_flow_scalping.run import OrderFlowScalpingStrategy
from core.order_builder import OrderSpec

@pytest.fixture
def base_config():
    return {
        "ofi_threshold": 2.0,
        "max_slippage_pips": 2.0,
        "atr_period": 14,
        "sl_offset_multiplier": 0.5,
        "sweep_lookback_ticks": 10
    }

@pytest.mark.unit
def test_strategy_initialization(base_config):
    strategy = OrderFlowScalpingStrategy(base_config)
    assert strategy.config["ofi_threshold"] == 2.0
    assert strategy.config["max_slippage_pips"] == 2.0

@pytest.mark.unit
def test_slippage_filter_breached(base_config):
    strategy = OrderFlowScalpingStrategy(base_config)
    # If projected slippage is 3.2, max is 2.0 -> Should reject
    assert strategy.is_slippage_acceptable(projected_slippage=3.2) is False
    # If projected slippage is 1.5, max is 2.0 -> Should accept
    assert strategy.is_slippage_acceptable(projected_slippage=1.5) is True

@pytest.mark.unit
def test_swing_and_sweep_tracking(base_config):
    strategy = OrderFlowScalpingStrategy(base_config)
    # Simulate ticks to define swing points
    # Let's say a local low is at 100.0, highs around 102.0
    # A tick sweeps 100.0 (goes to 99.8) and recovers (closes at 100.1)
    # Ticks format: list/deque of dicts with price, high, low, close, volume, timestamp
    
    # Establish swing low
    ticks = [
        {"high": 101.5, "low": 100.5, "close": 101.0, "volume": 10},
        {"high": 101.0, "low": 100.0, "close": 100.2, "volume": 12}, # Swing low candidate
        {"high": 101.8, "low": 100.8, "close": 101.5, "volume": 15},
    ]
    for t in ticks:
        strategy.process_tick(t)
        
    assert len(strategy.swing_lows) > 0
    assert min(strategy.swing_lows) == 100.0
    
    # Simulate a bullish sweep tick: low drops below 100.0, close is above 100.0
    sweep_tick = {"high": 100.5, "low": 99.8, "close": 100.1, "volume": 20}
    is_sweep, sweep_type = strategy.detect_sweep(sweep_tick)
    assert is_sweep is True
    assert sweep_type == "BULLISH"

@pytest.mark.unit
def test_fvg_detection_alignment(base_config):
    strategy = OrderFlowScalpingStrategy(base_config)
    
    # Create a Fair Value Gap scenario:
    # Bar 1: High at 10.0
    # Bar 2: Gap up
    # Bar 3: Low at 12.0
    # FVG from 10.0 to 12.0
    bar1 = {"high": 10.0, "low": 8.0, "close": 9.5}
    bar2 = {"high": 11.8, "low": 10.1, "close": 11.5}
    bar3 = {"high": 13.0, "low": 12.0, "close": 12.5}
    
    strategy.process_bar(bar1)
    strategy.process_bar(bar2)
    strategy.process_bar(bar3)
    
    assert len(strategy.active_fvgs) == 1
    fvg = strategy.active_fvgs[0]
    assert fvg["type"] == "alcista"
    assert fvg["bottom"] == 10.0
    assert fvg["top"] == 12.0

@pytest.mark.unit
@patch("strategies.order_flow_scalping.run.order_executor")
def test_full_entry_trigger_flow(mock_executor, base_config):
    # Tests that when sweep + FVG + OFI threshold align, order is submitted
    mock_executor.send.return_value = {"ok": True, "order_id": "12345"}
    strategy = OrderFlowScalpingStrategy(base_config)
    
    # Set up swing low
    strategy.swing_lows.append(100.0)
    
    # Set up FVG
    strategy.active_fvgs.append({"type": "alcista", "bottom": 100.0, "top": 100.5, "mid": 100.25})
    
    # Simulate entry signal align:
    # 1. Sweep occurs
    tick = {"high": 100.5, "low": 99.9, "close": 100.1, "volume": 10, "symbol": "BTCUSDT"}
    # 2. OFI Z-score is 2.7 (threshold is 2.0)
    # 3. Projected slippage is 1.0 (acceptable)
    
    strategy.ofi_z_scores.append(2.7)
    
    # Execute cycle
    strategy.process_tick(tick, projected_slippage=1.0)
    
    # Verify order executor was called
    mock_executor.send.assert_called_once()
    args, kwargs = mock_executor.send.call_args
    spec = args[0]
    assert isinstance(spec, OrderSpec)
    assert spec.side == "BUY"
    assert spec.sl == 99.9 - 0.5 * strategy.calculate_atr() # SL below sweep low
