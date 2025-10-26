import pandas as pd

from asharemarket50.core.performance import (
    PerformanceSummary,
    compute_daily_returns,
    summarize_performance,
)


def build_equity_curve() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    equity = pd.Series([1_000_000, 1_010_000, 1_020_000, 980_000, 1_050_000], index=dates)
    return pd.DataFrame({"equity": equity}, index=dates)


def test_compute_daily_returns_shape():
    curve = build_equity_curve()
    returns = compute_daily_returns(curve)
    assert len(returns) == len(curve)
    assert abs(returns.iloc[1] - 0.01) < 1e-6


def test_summarize_performance_outputs_metrics():
    curve = build_equity_curve()
    summary = summarize_performance(curve)
    assert isinstance(summary, PerformanceSummary)
    assert summary.total_return > 0
    assert summary.max_drawdown < 0
    assert summary.max_drawdown_start is not None
    assert summary.max_drawdown_end is not None
