"""LLM policy abstraction for the CSI 50 simulator."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

from ..core.portfolio import PortfolioState


@dataclass(slots=True)
class AgentSpec:
    """Definition of a single LLM-based decision maker."""

    name: str
    description: str
    weight: float = 1.0
    prompt_path: Optional[Path] = None


class PromptBuilder:
    """Render prompt templates with contextual information."""

    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        self.template = template_path.read_text(encoding="utf-8")

    def render(self, context: Dict[str, str]) -> str:
        rendered = self.template
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{ {key} }}}}", value)
        return rendered


@dataclass(slots=True)
class AgentDecision:
    spec: AgentSpec
    response_text: str
    allocations: Dict[str, float]


class AgentPolicy:
    """High level wrapper to call an LLM with structured prompts."""

    def __init__(
        self,
        spec: AgentSpec,
        call_model: Callable[[AgentSpec, str], str],
        prompt_builder: PromptBuilder,
    ) -> None:
        self.spec = spec
        self._call_model = call_model
        self.prompt_builder = prompt_builder

    def invoke(
        self,
        trade_date: str,
        market_payload: Dict[str, list[dict]],
        portfolio: PortfolioState,
        risk_limits: Dict[str, float],
    ) -> AgentDecision:
        prompt_context = {
            "trade_date": trade_date,
            "portfolio_state": json.dumps(portfolio_summary(portfolio), ensure_ascii=False, indent=2),
            "risk_limits": json.dumps(risk_limits, ensure_ascii=False, indent=2),
            "market_payload": json.dumps(market_payload, ensure_ascii=False)[:120000],
        }
        prompt = self.prompt_builder.render(prompt_context)
        response = self._call_model(self.spec, prompt)
        allocations = extract_allocations(response)
        return AgentDecision(spec=self.spec, response_text=response, allocations=allocations)


def portfolio_summary(portfolio: PortfolioState) -> Dict[str, dict]:
    return {
        "cash": portfolio.cash,
        "positions": {
            symbol: {"quantity": pos.quantity, "avg_price": pos.avg_price}
            for symbol, pos in portfolio.positions.items()
        },
    }


def extract_allocations(response: str) -> Dict[str, float]:
    """Parse allocation JSON from the LLM response."""

    json_block = extract_json_block(response)
    if not json_block:
        return {}
    try:
        payload = json.loads(json_block)
    except json.JSONDecodeError:
        return {}
    allocations = payload.get("allocations")
    if isinstance(allocations, dict):
        return {symbol: float(value) for symbol, value in allocations.items()}
    return {}


def extract_json_block(text: str) -> Optional[str]:
    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    bracket = re.search(r"(\{.*\})", text, re.DOTALL)
    return bracket.group(1) if bracket else None
