import pytest
import pandas as pd
import numpy as np

from strategies.asian_session.range_calculator import (
    AsianSessionRangeCalculator,
    AsianSessionRange,
    calculate_asian_range,
)


def _asian_5m_bars(
    n_days: int = 1,
    start_price: float = 4500.0,
    volatility: float = 0.005,
    asian_only: bool = True,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic 5m OHLCV data for MES during Asian session (00:00-08:00 UTC)."""
    np.random.seed(seed)
    bars_per_day = 288  # 24h * 12
    total_bars = n_days * bars_per_day

    if asian_only:
        asian_start = 0  # 00:00
        asian_end = 96  # 08:00 = 8h * 12
        n_asian = asian_end - asian_start
        dates = pd.date_range(
            "2024-01-01 00:00", periods=n_asian * n_days, freq="5min", tz="UTC"
        )
        returns = np.random.normal(0, volatility, n_asian * n_days)
        close = start_price * np.exp(np.cumsum(returns))
        high = close * (1 + np.abs(np.random.normal(0, volatility / 3, n_asian * n_days)))
        low = close * (1 - np.abs(np.random.normal(0, volatility / 3, n_asian * n_days)))
        open_ = low + np.random.rand(n_asian * n_days) * (high - low)
        high = np.maximum(high, np.maximum(open_, close))
        low = np.minimum(low, np.minimum(open_, close))
        volume = np.random.randint(100, 5000, n_asian * n_days)
    else:
        dates = pd.date_range(
            "2024-01-01 00:00", periods=total_bars, freq="5min", tz="UTC"
        )
        returns = np.random.normal(0, volatility, total_bars)
        close = start_price * np.exp(np.cumsum(returns))
        high = close * (1 + np.abs(np.random.normal(0, volatility / 3, total_bars)))
        low = close * (1 - np.abs(np.random.normal(0, volatility / 3, total_bars)))
        open_ = low + np.random.rand(total_bars) * (high - low)
        high = np.maximum(high, np.maximum(open_, close))
        low = np.minimum(low, np.minimum(open_, close))
        volume = np.random.randint(100, 5000, total_bars)

    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=dates,
    )


@pytest.fixture
def asian_session_data():
    return _asian_5m_bars(n_days=1, seed=100)


@pytest.fixture
def multi_day_data():
    return _asian_5m_bars(n_days=30, seed=200)


@pytest.fixture
def full_day_data():
    return _asian_5m_bars(n_days=30, asian_only=False, seed=300)


@pytest.fixture
def calc():
    return AsianSessionRangeCalculator()


class TestAsianSessionRangeCalculator:
    def test_calculate_returns_range(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        assert result is not None
        assert isinstance(result, AsianSessionRange)

    def test_high_low_mid_values(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        expected_high = asian_session_data["High"].max()
        expected_low = asian_session_data["Low"].min()
        expected_mid = (expected_high + expected_low) / 2.0
        assert result.high == pytest.approx(expected_high)
        assert result.low == pytest.approx(expected_low)
        assert result.mid == pytest.approx(expected_mid)

    def test_range_size_and_pct(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        expected_size = result.high - result.low
        expected_pct = (expected_size / result.mid) * 100.0
        assert result.range_size == pytest.approx(expected_size)
        assert result.range_size_pct == pytest.approx(expected_pct)

    def test_vwap_calculation(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        bars = asian_session_data
        tp = (bars["High"] + bars["Low"] + bars["Close"]) / 3.0
        vol = bars["Volume"].replace(0, np.nan)
        expected_vwap = (tp * vol).sum() / vol.sum()
        assert result.vwap == pytest.approx(float(expected_vwap), rel=1e-6)

    def test_vwap_fallback_when_no_volume(self, calc):
        bars = _asian_5m_bars(seed=400)
        bars["Volume"] = 0
        result = calc.calculate(bars)
        assert result is not None
        expected_close = bars["Close"].iloc[-1]
        assert result.vwap == pytest.approx(expected_close)

    def test_volume_profile_poc_in_range(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        assert result.low <= result.poc <= result.high

    def test_vah_val_order(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        assert result.val <= result.poc <= result.vah

    def test_vah_val_within_range(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        assert result.low <= result.val <= result.vah <= result.high

    def test_volume_bar_count(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        expected_volume = asian_session_data["Volume"].sum()
        expected_bars = len(asian_session_data)
        assert result.volume == pytest.approx(expected_volume)
        assert result.bar_count == expected_bars

    def test_atr_positive(self, calc, full_day_data):
        result = calc.calculate(full_day_data)
        assert result.atr > 0

    def test_atr_percentile_between_0_and_100(self, calc, full_day_data):
        result = calc.calculate(full_day_data)
        assert 0 <= result.atr_percentile <= 100

    def test_atr_percentile_returns_50_when_insufficient_data(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        assert result.atr_percentile == 50.0

    def test_empty_dataframe(self, calc):
        empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        result = calc.calculate(empty)
        assert result is None

    def test_none_input(self, calc):
        result = calc.calculate(None)
        assert result is None

    def test_no_session_bars(self, calc):
        # Data outside Asian session hours
        dates = pd.date_range("2024-01-01 10:00", periods=10, freq="5min", tz="UTC")
        df = pd.DataFrame({"High": [100]*10, "Low": [99]*10, "Close": [99.5]*10, "Volume": [1000]*10}, index=dates)
        result = calc.calculate(df)
        assert result is None

    def test_timezone_naive_input(self, calc):
        dates = pd.date_range("2024-01-01 00:00", periods=96, freq="5min")
        df = pd.DataFrame({"High": [100]*96, "Low": [99]*96, "Close": [99.5]*96, "Volume": [1000]*96}, index=dates)
        result = calc.calculate(df)
        assert result is not None

    def test_custom_config(self):
        custom = AsianSessionRangeCalculator({"session_start_utc": "02:00", "session_end_utc": "06:00"})
        assert custom.session_start.hour == 2
        assert custom.session_end.hour == 6

    def test_custom_atr_lookback(self):
        custom = AsianSessionRangeCalculator({"atr_lookback_days": 10})
        assert custom.atr_lookback == 10

    def test_custom_value_area_pct(self):
        custom = AsianSessionRangeCalculator({"value_area_percent": 50.0})
        assert custom.value_area_pct == 50.0

    def test_custom_vpvr_bins(self):
        custom = AsianSessionRangeCalculator({"vpvr_bins": 100})
        assert custom.vpvr_bins == 100

    def test_is_breakout_valid_long(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        above_high = result.high + 1.0
        below_high = result.high - 0.01
        assert calc.is_breakout_valid(above_high, "LONG", result) is True
        assert calc.is_breakout_valid(below_high, "LONG", result) is False

    def test_is_breakout_valid_short(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        below_low = result.low - 1.0
        above_low = result.low + 0.01
        assert calc.is_breakout_valid(below_low, "SHORT", result) is True
        assert calc.is_breakout_valid(above_low, "SHORT", result) is False

    def test_is_breakout_invalid_direction(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        assert calc.is_breakout_valid(result.high + 1, "INVALID", result) is False

    def test_is_breakout_filters_tiny_range(self, calc):
        dates = pd.date_range("2024-01-01 00:00", periods=96, freq="5min", tz="UTC")
        prices = 4500 + np.sin(np.linspace(0, 0.5, 96)) * 0.5
        df = pd.DataFrame(
            {
                "Open": prices,
                "High": prices + 0.3,
                "Low": prices - 0.3,
                "Close": prices,
                "Volume": [1000] * 96,
            },
            index=dates,
        )
        result = calc.calculate(df)
        assert result is not None
        assert result.range_size_pct < 0.05
        assert calc.is_breakout_valid(result.high + 1, "LONG", result, min_range_pct=0.5) is False

    def test_get_stop_loss_long(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        sl = calc.get_stop_loss(result.high + 1, "LONG", result)
        assert sl < result.high + 1

    def test_get_stop_loss_short(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        sl = calc.get_stop_loss(result.low - 1, "SHORT", result)
        assert sl > result.low - 1

    def test_get_stop_loss_atr_fallback(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        zero_atr = AsianSessionRange(
            session_date=result.session_date,
            high=100, low=90, mid=95, vwap=95,
            poc=95, vah=98, val=92,
            range_size=10, range_size_pct=10.5,
            atr=0, atr_percentile=50,
            volume=1000, bar_count=96,
        )
        entry = 100
        sl = calc.get_stop_loss(entry, "LONG", zero_atr)
        assert sl < entry

    def test_get_targets_long(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        entry = result.high + 1
        sl = result.low - 1
        tp1, tp2 = calc.get_targets(entry, sl, "LONG", result)
        risk = abs(entry - sl)
        expected_tp2 = entry + risk * 3.0
        max_ext = result.range_size * 2
        expected_tp2_capped = min(expected_tp2, entry + max_ext)
        assert tp1 == pytest.approx(entry + risk * 2.0)
        assert tp2 == pytest.approx(expected_tp2_capped)

    def test_get_targets_short(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        entry = result.low - 1
        sl = result.high + 1
        tp1, tp2 = calc.get_targets(entry, sl, "SHORT", result)
        risk = abs(entry - sl)
        expected_tp2 = entry - risk * 3.0
        max_ext = result.range_size * 2
        expected_tp2_capped = max(expected_tp2, entry - max_ext)
        assert tp1 == pytest.approx(entry - risk * 2.0)
        assert tp2 == pytest.approx(expected_tp2_capped)

    def test_get_targets_tp2_capped(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        entry = result.high + 1
        sl = entry - 0.5  # very tight SL -> large risk multiplier
        tp1, tp2 = calc.get_targets(entry, sl, "LONG", result)
        max_ext = result.range_size * 2
        assert tp2 <= entry + max_ext

    def test_session_date_is_utc(self, calc, asian_session_data):
        result = calc.calculate(asian_session_data)
        assert result.session_date.tz is not None

    def test_volume_profile_single_price(self, calc):
        dates = pd.date_range("2024-01-01 00:00", periods=10, freq="5min", tz="UTC")
        df = pd.DataFrame(
            {"High": [100]*10, "Low": [100]*10, "Close": [100]*10, "Volume": [1000]*10},
            index=dates,
        )
        result = calc.calculate(df)
        assert result is not None
        assert result.poc == 100
        assert result.vah == 100
        assert result.val == 100

    def test_volume_profile_no_volume(self, calc, asian_session_data):
        bars = asian_session_data.copy()
        bars["Volume"] = 0
        result = calc.calculate(bars)
        assert result is not None
        assert result.poc == result.mid

    def test_calculate_convenience_function(self, asian_session_data):
        result = calculate_asian_range(asian_session_data)
        assert isinstance(result, AsianSessionRange)

    def test_calculate_convenience_with_config(self, asian_session_data):
        result = calculate_asian_range(asian_session_data, {"atr_lookback_days": 10})
        assert isinstance(result, AsianSessionRange)

    def test_small_range_no_breakout(self, calc):
        dates = pd.date_range("2024-01-01 00:00", periods=96, freq="5min", tz="UTC")
        df = pd.DataFrame(
            {"High": [100.05]*96, "Low": [99.95]*96, "Close": [100]*96, "Volume": [1000]*96},
            index=dates,
        )
        result = calc.calculate(df)
        assert result is not None
        assert calc.is_breakout_valid(101, "LONG", result, min_range_pct=0.2) is False
