"""Performance analytics mirroring the NASDAQ simulator capabilities."""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Tuple

import pandas as pd


@dataclass(slots=True)
class PerformanceSummary:
    """Container describing headline performance statistics."""

    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_start: str | None
    max_drawdown_end: str | None


def compute_daily_returns(equity_curve: pd.DataFrame) -> pd.Series:
    """Return daily percentage returns from an equity curve."""

    if "equity" not in equity_curve.columns:
        raise ValueError("equity_curve must contain an 'equity' column")

    equity = equity_curve["equity"].astype(float)
    returns = equity.pct_change().fillna(0.0)
    if not isinstance(equity_curve.index, pd.DatetimeIndex):
        returns.index = pd.to_datetime(equity_curve.index)
    else:
        returns.index = equity_curve.index
    return returns


def _max_drawdown(equity_curve: pd.DataFrame) -> Tuple[float, str | None, str | None]:
    equity = equity_curve["equity"].astype(float)
    running_max = equity.cummax()
    drawdowns = equity / running_max - 1.0
    min_idx = drawdowns.idxmin()
    if pd.isna(min_idx):
        return 0.0, None, None
    min_drawdown = float(drawdowns.loc[min_idx])
    start_idx = equity.loc[:min_idx].idxmax()
    start_str = start_idx.strftime("%Y-%m-%d") if isinstance(start_idx, pd.Timestamp) else str(start_idx)
    end_str = min_idx.strftime("%Y-%m-%d") if isinstance(min_idx, pd.Timestamp) else str(min_idx)
    return min_drawdown, start_str, end_str


def summarize_performance(equity_curve: pd.DataFrame) -> PerformanceSummary:
    """Compute headline statistics from an equity curve DataFrame."""

    if equity_curve.empty:
        return PerformanceSummary(0.0, 0.0, 0.0, 0.0, 0.0, None, None)

    daily_returns = compute_daily_returns(equity_curve)
    total_return = float(equity_curve["equity"].iloc[-1] / equity_curve["equity"].iloc[0] - 1.0)

    trading_days = max(len(daily_returns), 1)
    annualized_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 1 else total_return

    std_dev = float(daily_returns.std(ddof=0))
    volatility = std_dev * sqrt(252)
    sharpe_ratio = float((daily_returns.mean() * 252) / (std_dev * sqrt(252))) if std_dev > 0 else 0.0

    max_drawdown, dd_start, dd_end = _max_drawdown(equity_curve)

    return PerformanceSummary(
        total_return=total_return,
        annualized_return=annualized_return,
        volatility=volatility,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        max_drawdown_start=dd_start,
        max_drawdown_end=dd_end,
    )

