"""
strategies/asian_session — Asian Session Breakout Strategy for MES/MNQ futures.

Components:
  - RangeCalculator: Asian session range, VWAP, volume profile, ATR
  - TradeGuard: daily max trades, cooldown enforcement
  - NewsFilter: block trading around high-impact economic events
  - BreakoutLogic: breakout signal detection with confidence scoring
  - AsianBreakoutStrategy: orchestrator composing all components
"""
from strategies.asian_session.range_calculator import AsianSessionRangeCalculator, AsianSessionRange, calculate_asian_range
from strategies.asian_session.trade_guard import DailyTradeGuard, TradeGuardState, TradeGuardStatus
from strategies.asian_session.news_filter import NewsFilter, NewsEvent, NewsProvider, StaticNewsProvider
from strategies.asian_session.breakout_logic import BreakoutLogic, BreakoutSignal
from strategies.asian_session.asian_breakout_strategy import AsianBreakoutStrategy

__all__ = [
    "AsianSessionRangeCalculator", "AsianSessionRange", "calculate_asian_range",
    "DailyTradeGuard", "TradeGuardState", "TradeGuardStatus",
    "NewsFilter", "NewsEvent", "NewsProvider", "StaticNewsProvider",
    "BreakoutLogic", "BreakoutSignal",
    "AsianBreakoutStrategy",
]
