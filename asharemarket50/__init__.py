"""CSI 50 A-share multi-agent trading simulator package."""

from .agents import AgentSpec, CoordinatorConfig, EnsembleCoordinator
from .core import Backtester, BacktestResult, DataFeed, IndicatorLibrary, PortfolioState
from .services import AKShareClient

__all__ = [
    "AgentSpec",
    "CoordinatorConfig",
    "EnsembleCoordinator",
    "Backtester",
    "BacktestResult",
    "DataFeed",
    "IndicatorLibrary",
    "PortfolioState",
    "AKShareClient",
]
