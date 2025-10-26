"""Coordinator that combines multiple agent responses into a single allocation plan."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Sequence

import pandas as pd

from ..configs import Settings, load_universe
from ..core.backtester import AllocationPlanner
from ..core.data_feed import DataFeed
from ..core.portfolio import PortfolioState
from .policy import AgentDecision, AgentPolicy, AgentSpec, PromptBuilder


@dataclass(slots=True)
class CoordinatorConfig:
    """Configuration for the multi-agent voting mechanism."""

    agent_specs: Sequence[AgentSpec]
    risk_limits: Dict[str, float] = field(
        default_factory=lambda: {"max_position_pct": 0.2, "max_gross_exposure": 1.0}
    )


class EnsembleCoordinator(AllocationPlanner):
    """Aggregate recommendations from multiple large language models."""

    def __init__(
        self,
        data_feed: DataFeed,
        config: CoordinatorConfig,
        call_model: Callable[[AgentSpec, str], str],
        settings: Settings | None = None,
    ) -> None:
        self.data_feed = data_feed
        self.config = config
        self.settings = settings or Settings()
        prompt_path = Path(__file__).resolve().parent / "prompts" / "csi50_multi_agent_prompt.md"
        self.agents: List[AgentPolicy] = [
            AgentPolicy(
                spec=spec,
                call_model=call_model,
                prompt_builder=PromptBuilder(spec.prompt_path or prompt_path),
            )
            for spec in config.agent_specs
        ]

    def propose_allocations(
        self,
        trade_date: str,
        market_data: Dict[str, pd.DataFrame],
        portfolio: PortfolioState,
    ) -> Dict[str, float]:
        market_payload = self.data_feed.build_prompt_payload(trade_date, symbols=market_data.keys())
        decisions = [
            agent.invoke(trade_date, market_payload, portfolio, self.config.risk_limits)
            for agent in self.agents
        ]
        return self._combine(decisions)

    def _combine(self, decisions: Sequence[AgentDecision]) -> Dict[str, float]:
        if not decisions:
            return {}
        weights: Dict[str, List[float]] = {}
        for decision in decisions:
            for symbol, weight in decision.allocations.items():
                weights.setdefault(symbol, []).append(weight * decision.spec.weight)
        averaged = {symbol: statistics.mean(values) for symbol, values in weights.items() if values}
        total = sum(value for value in averaged.values() if value > 0)
        if total <= 0:
            return {}
        normalised = {symbol: max(value, 0) / total for symbol, value in averaged.items() if value > 0}
        clipped = {
            symbol: min(value, self.config.risk_limits.get("max_position_pct", 1.0))
            for symbol, value in normalised.items()
        }
        gross = sum(clipped.values())
        if gross > self.config.risk_limits.get("max_gross_exposure", 1.0):
            scale = self.config.risk_limits["max_gross_exposure"] / gross
            clipped = {symbol: value * scale for symbol, value in clipped.items()}
        return clipped

    def universe(self) -> Iterable[str]:
        return load_universe(self.settings.default_universe_path).akshare_symbols()
