"""Core simulation primitives for the CSI 50 multi-agent project."""

from .backtester import Backtester, BacktestResult
from .data_feed import DataFeed
from .indicators import IndicatorLibrary
from .portfolio import PortfolioState
from .performance import (
    PerformanceSummary,
    compute_daily_returns,
    summarize_performance,
)

__all__ = [
    "Backtester",
    "BacktestResult",
    "DataFeed",
    "IndicatorLibrary",
    "PortfolioState",
    "PerformanceSummary",
    "compute_daily_returns",
    "summarize_performance",
]
