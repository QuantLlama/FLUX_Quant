"""
strategies/asian_session/range_calculator.py

Calculates Asian session range, VWAP, and volume profile for MES/MNQ futures.
Session: 00:00-08:00 UTC (Tokyo 09:00-17:00 JST)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Optional

import numpy as np
import pandas as pd

from core.config import config


@dataclass
class AsianSessionRange:
    """Results of Asian session range calculation."""
    session_date: pd.Timestamp
    high: float
    low: float
    mid: float
    vwap: float
    poc: float
    vah: float
    val: float
    range_size: float
    range_size_pct: float
    atr: float
    atr_percentile: float
    volume: float
    bar_count: int


class AsianSessionRangeCalculator:
    """
    Calculates Asian session range and volume profile metrics.
    
    Uses 5m bars for range calculation, computes:
    - High/Low/Mid of session
    - VWAP (Volume Weighted Average Price)
    - POC (Point of Control) - price with highest volume
    - VAH/VAL (Value Area High/Low) - 70% volume area
    - ATR and ATR percentile (20-day lookback)
    """
    
    def __init__(self, config_dict: Optional[dict] = None):
        self.config = config_dict or {
            "session_start_utc": "00:00",
            "session_end_utc": "08:00",
            "value_area_percent": 70.0,
            "atr_lookback_days": 20,
            "vpvr_bins": 50,
        }
        
        self._parse_session_times()
    
    def _parse_session_times(self) -> None:
        """Parse session time strings to time objects."""
        start_str = self.config.get("session_start_utc", "00:00")
        end_str = self.config.get("session_end_utc", "08:00")
        
        self.session_start = time(
            hour=int(start_str.split(":")[0]),
            minute=int(start_str.split(":")[1])
        )
        self.session_end = time(
            hour=int(end_str.split(":")[0]),
            minute=int(end_str.split(":")[1])
        )
        
        self.value_area_pct = self.config.get("value_area_percent", 70.0)
        self.atr_lookback = self.config.get("atr_lookback_days", 20)
        self.vpvr_bins = self.config.get("vpvr_bins", 50)
    
    def calculate(self, df: pd.DataFrame) -> Optional[AsianSessionRange]:
        """
        Calculate Asian session range from 5m bar data.
        
        Args:
            df: DataFrame with OHLCV data, index must be timezone-aware UTC DatetimeIndex
            
        Returns:
            AsianSessionRange or None if no session data
        """
        if df is None or df.empty:
            return None
        
        # Ensure UTC timezone
        if df.index.tz is None:
            df = df.tz_localize("UTC")
        elif str(df.index.tz) != "UTC":
            df = df.tz_convert("UTC")
        
        # Filter to Asian session hours
        session_mask = (df.index.time >= self.session_start) & (df.index.time < self.session_end)
        session_bars = df[session_mask].copy()
        
        if session_bars.empty:
            return None
        
        # Get session date (use first bar's date)
        session_date = session_bars.index[0].date()
        
        # Basic range metrics
        session_high = session_bars["High"].max()
        session_low = session_bars["Low"].min()
        session_mid = (session_high + session_low) / 2.0
        range_size = session_high - session_low
        range_size_pct = (range_size / session_mid) * 100.0 if session_mid > 0 else 0.0
        
        # VWAP
        vwap = self._calculate_vwap(session_bars)
        
        # Volume Profile (VPVR) - POC, VAH, VAL
        poc, vah, val = self._calculate_volume_profile(session_bars)
        
        # ATR (using full day data for context)
        atr = self._calculate_atr(df)
        
        # ATR Percentile (last N days)
        atr_percentile = self._calculate_atr_percentile(df)
        
        return AsianSessionRange(
            session_date=pd.Timestamp(session_date, tz="UTC"),
            high=session_high,
            low=session_low,
            mid=session_mid,
            vwap=vwap,
            poc=poc,
            vah=vah,
            val=val,
            range_size=range_size,
            range_size_pct=range_size_pct,
            atr=atr,
            atr_percentile=atr_percentile,
            volume=session_bars["Volume"].sum(),
            bar_count=len(session_bars),
        )
    
    def _calculate_vwap(self, bars: pd.DataFrame) -> float:
        """Calculate Volume Weighted Average Price."""
        typical_price = (bars["High"] + bars["Low"] + bars["Close"]) / 3.0
        volume = bars["Volume"].replace(0, np.nan)
        
        if volume.isna().all() or volume.sum() == 0:
            return bars["Close"].iloc[-1]
        
        vwap = (typical_price * volume).sum() / volume.sum()
        return float(vwap)
    
    def _calculate_volume_profile(
        self, 
        bars: pd.DataFrame
    ) -> tuple[float, float, float]:
        """
        Calculate Volume Profile: POC, VAH, VAL.
        
        Returns:
            (poc, vah, val) - Point of Control, Value Area High, Value Area Low
        """
        if bars.empty or bars["Volume"].sum() == 0:
            mid = (bars["High"].max() + bars["Low"].min()) / 2.0 if not bars.empty else 0.0
            return mid, mid, mid
        
        # Create price bins
        price_min = bars["Low"].min()
        price_max = bars["High"].max()
        
        if price_min == price_max:
            return price_min, price_min, price_min
        
        bins = np.linspace(price_min, price_max, self.vpvr_bins + 1)
        bin_centers = (bins[:-1] + bins[1:]) / 2.0
        
        # Distribute volume across bins for each bar
        volume_profile = np.zeros(self.vpvr_bins)
        
        for _, bar in bars.iterrows():
            bar_volume = bar["Volume"]
            if bar_volume <= 0:
                continue
            
            # Volume distributed uniformly across bar's high-low range
            bar_low_idx = np.searchsorted(bins, bar["Low"], side="right") - 1
            bar_high_idx = np.searchsorted(bins, bar["High"], side="left")
            
            bar_low_idx = max(0, min(bar_low_idx, self.vpvr_bins - 1))
            bar_high_idx = max(0, min(bar_high_idx, self.vpvr_bins))
            
            if bar_high_idx > bar_low_idx:
                bars_in_range = bar_high_idx - bar_low_idx
                vol_per_bin = bar_volume / bars_in_range
                volume_profile[bar_low_idx:bar_high_idx] += vol_per_bin
        
        total_volume = volume_profile.sum()
        if total_volume == 0:
            mid = (price_min + price_max) / 2.0
            return mid, mid, mid
        
        # POC - bin with highest volume
        poc_idx = np.argmax(volume_profile)
        poc = float(bin_centers[poc_idx])
        
        # Value Area (70% of volume around POC)
        target_volume = total_volume * (self.value_area_pct / 100.0)
        
        # Expand from POC outward
        vah_idx = poc_idx
        val_idx = poc_idx
        accumulated = volume_profile[poc_idx]
        
        while accumulated < target_volume and (vah_idx < self.vpvr_bins - 1 or val_idx > 0):
            # Expand to side with higher volume
            vol_up = volume_profile[vah_idx + 1] if vah_idx < self.vpvr_bins - 1 else -1
            vol_down = volume_profile[val_idx - 1] if val_idx > 0 else -1
            
            if vol_up >= vol_down and vah_idx < self.vpvr_bins - 1:
                vah_idx += 1
                accumulated += vol_up
            elif val_idx > 0:
                val_idx -= 1
                accumulated += vol_down
            else:
                break
        
        vah = float(bin_centers[vah_idx])
        val = float(bin_centers[val_idx])
        
        return poc, vah, val
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(df) < period + 1:
            return 0.0
        
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean().iloc[-1]
        
        return float(atr) if not pd.isna(atr) else 0.0
    
    def _calculate_atr_percentile(self, df: pd.DataFrame) -> float:
        """Calculate ATR percentile over lookback period."""
        if len(df) < self.atr_lookback * 288:  # ~288 5m bars per day
            return 50.0
        
        # Calculate daily ATRs
        daily_atrs = []
        days_checked = 0
        
        for i in range(1, min(self.atr_lookback + 5, len(df) // 288)):
            day_end = -(i * 288)
            day_start = day_end - 288
            if day_start < -len(df):
                break
            
            day_data = df.iloc[day_start:day_end]
            if len(day_data) < 50:
                continue
            
            atr = self._calculate_atr(day_data)
            if atr > 0:
                daily_atrs.append(atr)
                days_checked += 1
            
            if days_checked >= self.atr_lookback:
                break
        
        if len(daily_atrs) < 5:
            return 50.0
        
        current_atr = daily_atrs[0] if daily_atrs else 0.0
        if current_atr == 0:
            return 50.0
        
        # Percentile: what % of historical ATRs is current ATR above?
        percentile = (sum(1 for a in daily_atrs if a <= current_atr) / len(daily_atrs)) * 100
        return float(np.clip(percentile, 0, 100))
    
    def is_breakout_valid(
        self, 
        price: float, 
        direction: str, 
        range_data: AsianSessionRange,
        min_range_pct: float = 0.1
    ) -> bool:
        """
        Check if price has validly broken out of Asian session range.
        
        Args:
            price: Current price
            direction: "LONG" or "SHORT"
            range_data: AsianSessionRange object
            min_range_pct: Minimum range size as % of mid (filter tiny ranges)
            
        Returns:
            True if breakout is valid
        """
        if range_data.range_size_pct < min_range_pct:
            return False  # Range too small (choppy)
        
        if direction == "LONG":
            return bool(price > range_data.high)
        elif direction == "SHORT":
            return bool(price < range_data.low)
        
        return False
    
    def get_stop_loss(
        self, 
        entry: float, 
        direction: str, 
        range_data: AsianSessionRange
    ) -> float:
        """Calculate stop loss based on ATR and range."""
        atr = range_data.atr if range_data.atr > 0 else entry * 0.005
        mult = self.config.get("atr_sl_multiplier", 1.5)
        
        if direction == "LONG":
            # SL below entry, using ATR or range low
            sl_atr = entry - (atr * mult)
            sl_range = range_data.low - (range_data.range_size * 0.1)
            return min(sl_atr, sl_range)
        else:
            # SL above entry
            sl_atr = entry + (atr * mult)
            sl_range = range_data.high + (range_data.range_size * 0.1)
            return max(sl_atr, sl_range)
    
    def get_targets(
        self, 
        entry: float, 
        sl: float, 
        direction: str,
        range_data: AsianSessionRange
    ) -> tuple[float, float]:
        """Calculate TP1 and TP2 based on risk:reward ratios."""
        risk = abs(entry - sl)
        
        rr1 = self.config.get("rr_target_1", 2.0)
        rr2 = self.config.get("rr_target_2", 3.0)
        
        if direction == "LONG":
            tp1 = entry + (risk * rr1)
            tp2 = entry + (risk * rr2)
        else:
            tp1 = entry - (risk * rr1)
            tp2 = entry - (risk * rr2)
        
        # Cap TP2 at range extension (e.g., 2x range from breakout)
        max_ext = range_data.range_size * 2
        if direction == "LONG":
            tp2 = min(tp2, entry + max_ext)
        else:
            tp2 = max(tp2, entry - max_ext)
        
        return float(tp1), float(tp2)


def calculate_asian_range(
    df: pd.DataFrame,
    config_dict: Optional[dict] = None
) -> Optional[AsianSessionRange]:
    """Convenience function for direct calculation."""
    calc = AsianSessionRangeCalculator(config_dict)
    return calc.calculate(df)