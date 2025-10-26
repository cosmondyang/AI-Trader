"""CSI 50 A-share multi-agent trading simulator package."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:  # pragma: no cover
    from .agents import AgentSpec, CoordinatorConfig, EnsembleCoordinator
    from .core import (
        Backtester,
        BacktestResult,
        DataFeed,
        IndicatorLibrary,
        PortfolioState,
    )
    from .services import AKShareClient


_IMPORT_TABLE = {
    "AgentSpec": ("asharemarket50.agents", "AgentSpec"),
    "CoordinatorConfig": ("asharemarket50.agents", "CoordinatorConfig"),
    "EnsembleCoordinator": ("asharemarket50.agents", "EnsembleCoordinator"),
    "Backtester": ("asharemarket50.core", "Backtester"),
    "BacktestResult": ("asharemarket50.core", "BacktestResult"),
    "DataFeed": ("asharemarket50.core", "DataFeed"),
    "IndicatorLibrary": ("asharemarket50.core", "IndicatorLibrary"),
    "PortfolioState": ("asharemarket50.core", "PortfolioState"),
    "AKShareClient": ("asharemarket50.services", "AKShareClient"),
}


def __getattr__(name: str) -> Any:  # pragma: no cover - mirrors ``import *`` semantics
    try:
        module_name, attr_name = _IMPORT_TABLE[name]
    except KeyError as exc:  # pragma: no cover - standard attribute hook behaviour
        raise AttributeError(f"module 'asharemarket50' has no attribute '{name}'") from exc
    module = import_module(module_name)
    return getattr(module, attr_name)


def __dir__() -> list[str]:  # pragma: no cover - keeps introspection tidy
    return sorted(set(globals().keys()) | set(__all__))
