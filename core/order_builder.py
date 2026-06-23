"""
core/order_builder.py — Translates analysis results into actionable order parameters.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import numpy as np

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class OrderSpec:
    symbol: str
    side: str  # "BUY" | "SELL"
    order_type: str  # "MARKET" | "LIMIT"
    entry_price: Optional[float]
    sl: float
    tp1: float
    tp2: Optional[float]
    size_usd: float
    lots: Optional[float]
    source: str
    confidence: float
    rr: float
    notes: str

    def summary(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "type": self.order_type,
            "entry": self.entry_price,
            "sl": self.sl,
            "tp1": self.tp1,
            "tp2": self.tp2,
            "size_usd": self.size_usd,
            "lots": self.lots,
            "source": self.source,
            "confidence": self.confidence,
            "rr": self.rr,
        }

def extract_signal(source: str, results: dict) -> tuple[str, float]:
    """
    Extracts signal direction and confidence from analysis results.
    Returns: (direction, confidence)
        direction: "BUY" | "SELL" | "NEUTRAL"
        confidence: 0.0 to 1.0
    """
    if not results:
        return "NEUTRAL", 0.0

    if source == "quant":
        direction_raw = results.get("direction", "NEUTRAL")
        if "COMPRA" in direction_raw:
            return "BUY", 0.8
        elif "VENTA" in direction_raw:
            return "SELL", 0.8
        return "NEUTRAL", 0.0

    elif source == "mean_reversion":
        signal_type = results.get("signal_type", "NEUTRAL")
        score = abs(results.get("signal_score", 0.0))
        confidence = min(score / 3.0, 1.0) if score > 0 else 0.0
        
        if "ALCISTA" in signal_type: # Posible Corto o Extremo Alcista
            if "Corto" in signal_type or "Extremo" in signal_type:
                return "SELL", confidence
        elif "BAJISTA" in signal_type:
            if "Largo" in signal_type or "Extremo" in signal_type:
                return "BUY", confidence
                
        return "NEUTRAL", 0.0
        
    elif source == "structure":
        trend = results.get("trend", "neutral")
        if trend == "alcista":
            return "BUY", 0.6
        elif trend == "bajista":
            return "SELL", 0.6
        return "NEUTRAL", 0.0
        
    elif source == "manual":
        side = results.get("side", "NEUTRAL").upper()
        return side if side in ("BUY", "SELL") else "NEUTRAL", 1.0
        
    elif source == "report":
        direction = results.get("direction", "NEUTRAL")
        score = max(results.get("score_buy", 0), results.get("score_sell", 0))
        confidence = min(score / 100.0, 1.0)
        if "COMPRA" in direction:
            return "BUY", confidence
        elif "VENTA" in direction:
            return "SELL", confidence
        return "NEUTRAL", 0.0

    return "NEUTRAL", 0.0

# ─────────────────────────────────────────────────────────────
# Position sizing helpers
# ─────────────────────────────────────────────────────────────

# Point value per contract for common futures symbols (USD per 1-point move)
_FUTURES_POINT_VALUE: dict[str, float] = {
    "MES=F":  5.0,    # Micro E-mini S&P 500
    "ES=F":   50.0,   # E-mini S&P 500
    "MNQ=F":  2.0,    # Micro Nasdaq
    "NQ=F":   20.0,   # E-mini Nasdaq
    "MYM=F":  0.5,    # Micro Dow
    "YM=F":   5.0,    # E-mini Dow
    "RTY=F":  5.0,    # E-mini Russell
    "M2K=F":  0.5,    # Micro Russell
    "CL=F":   1000.0, # Crude Oil (USD per barrel × 1000 bbl)
    "GC=F":   100.0,  # Gold (USD per troy oz × 100 oz)
    "SI=F":   5000.0, # Silver
    "ZN=F":   1000.0, # 10-Year T-Note
    "ZB=F":   1000.0, # 30-Year T-Bond
}

FX_LOT_SIZE = 100_000  # 1 standard lot = 100,000 units


def _calc_position_size(
    risk_cash: float,
    risk_dist: float,
    entry: float,
    asset_type: str,
    symbol: str,
) -> tuple[float, str, float]:
    """
    Returns (position_size, position_unit, point_value).

    - Futuros:        contracts = risk_cash / (risk_dist * point_value)
    - Forex:          lots      = risk_cash / (risk_dist * FX_LOT_SIZE)
    - Crypto/Stocks:  units     = risk_cash / risk_dist
    """
    if risk_dist <= 0:
        return 0.0, "unidades", 1.0

    sym_upper = symbol.upper()

    if "Futuros" in asset_type or sym_upper.endswith("=F"):
        point_value = 1.0
        # Try finding prefix match for MT5 symbols (e.g. MESU26 -> MES) or exact match for Yahoo (MES=F)
        for k, v in _FUTURES_POINT_VALUE.items():
            prefix = k.replace("=F", "")
            if sym_upper == k or sym_upper.startswith(prefix):
                point_value = v
                break
                
        size = risk_cash / (risk_dist * point_value)
        return round(max(1.0, size), 2), "contratos", point_value

    if "Forex" in asset_type or sym_upper.endswith("=X"):
        # risk_dist is in quote currency per unit; 1 lot = 100k units
        size = risk_cash / (risk_dist * FX_LOT_SIZE)
        return round(max(0.01, size), 4), "lotes", FX_LOT_SIZE

    # Crypto, Stocks, ETFs, Indices — size in asset units
    size = risk_cash / risk_dist
    unit = "unidades"
    if "Crypto" in asset_type:
        unit = "unidades"
    elif "Acción" in asset_type or "ETF" in asset_type:
        unit = "acciones"
    elif "Índice" in asset_type:
        unit = "unidades"
    return round(size, 4), unit, 1.0


def build_order(
    symbol: str, 
    current_price: float, 
    df: pd.DataFrame, 
    analysis_results: dict, 
    source: str, 
    capital: float, 
    risk_pct: float, 
    order_type: str = "MARKET", 
    entry_price: Optional[float] = None, 
    rr_ratio: float = 2.0
) -> Optional[OrderSpec]:
    """
    Builds an OrderSpec based on current price, ATR, and analysis.
    Returns None if the signal is not actionable.
    """
    side, confidence = extract_signal(source, analysis_results)
    
    if side == "NEUTRAL" or confidence < 0.3:
        logger.info(f"Signal not actionable: side={side}, conf={confidence}")
        return None

    entry = entry_price if entry_price and order_type == "LIMIT" else current_price

    if source == "report" and "setup" in analysis_results and analysis_results["setup"].get("stop_loss", 0.0) > 0:
        setup = analysis_results["setup"]
        sl = float(setup["stop_loss"])
        sl_dist = abs(entry - sl)
        if side == "BUY":
            tp1 = entry + (sl_dist * rr_ratio)
            tp2 = entry + (sl_dist * rr_ratio * 1.5)
        else:
            tp1 = entry - (sl_dist * rr_ratio)
            tp2 = entry - (sl_dist * rr_ratio * 1.5)
    else:
        # Calculate ATR for SL distance
        if len(df) > 14:
            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]
        else:
            # Fallback if not enough data: 1% of price
            atr = entry * 0.01

        atr_mult = config.get("volatility.atr_sl_multiplier", 2.0)
        sl_dist = atr * atr_mult

        if side == "BUY":
            sl = entry - sl_dist
            tp1 = entry + (sl_dist * rr_ratio)
            tp2 = entry + (sl_dist * rr_ratio * 1.5)
        else: # SELL
            sl = entry + sl_dist
            tp1 = entry - (sl_dist * rr_ratio)
            tp2 = entry - (sl_dist * rr_ratio * 1.5)

    risk_usd = capital * (risk_pct / 100.0)
    
    # Avoid division by zero
    price_diff = abs(entry - sl)
    if price_diff <= 0:
        price_diff = entry * 0.001
        
    # Get asset_type
    asset_type = df.attrs.get("asset_type", "Acción/ETF")
    
    position_size, position_unit, point_value = _calc_position_size(
        risk_cash=risk_usd, 
        risk_dist=price_diff, 
        entry=entry, 
        asset_type=asset_type, 
        symbol=symbol
    )
    
    # max position size check in USD equivalent
    if position_unit == "contratos":
        size_usd = position_size * point_value * price_diff  # roughly risk
    elif position_unit == "lotes":
        size_usd = position_size * FX_LOT_SIZE * price_diff  # roughly risk
    else:
        size_usd = position_size * entry

    max_size = config.get("trading.max_position_usd", 5000.0)
    if size_usd > max_size:
        logger.warning(f"Position size exceeds max_size_usd ({size_usd} > {max_size}). Capping not fully implemented for all types yet.")
    
    actual_rr = abs(tp1 - entry) / price_diff

    notes = f"{source.upper()} signal ({confidence:.0%} conf). Risk: ${risk_usd:.2f} ({position_size} {position_unit})"

    return OrderSpec(
        symbol=symbol,
        side=side,
        order_type=order_type,
        entry_price=entry_price if order_type == "LIMIT" else None,
        sl=sl,
        tp1=tp1,
        tp2=tp2,
        size_usd=size_usd,
        lots=position_size, # CLI / Trader will use this as quantity (contracts/lots/units)
        source=source,
        confidence=confidence,
        rr=actual_rr,
        notes=notes
    )
