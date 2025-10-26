"""Command line utility to run CSI 50 backtests."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd

from ..agents import CoordinatorConfig, EnsembleCoordinator, AgentSpec
from ..core.backtester import Backtester, AllocationPlanner
from ..core.performance import summarize_performance
from ..core.data_feed import DataFeed
from ..core.portfolio import PortfolioState


@dataclass(slots=True)
class HeuristicPlanner(AllocationPlanner):
    """Fallback planner that mimics a simplistic quant strategy for demos."""

    top_n: int = 4

    def propose_allocations(
        self,
        trade_date: str,
        market_data: Dict[str, pd.DataFrame],
        portfolio: PortfolioState,
    ) -> Dict[str, float]:
        scores = {}
        for symbol, frame in market_data.items():
            last_row = frame.iloc[-1]
            macd = last_row.get("macd_hist", 0.0)
            kdj = last_row.get("kdj_j", 0.0) / 100
            rsi = last_row.get("rsi", 50.0)
            scores[symbol] = macd + kdj - (rsi - 50) / 100
        winners = [symbol for symbol, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[: self.top_n]]
        if not winners:
            return {}
        weight = 1.0 / len(winners)
        return {symbol: weight for symbol in winners}


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a CSI 50 T+1 backtest.")
    parser.add_argument("--start", required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end", required=True, help="End date in YYYY-MM-DD format")
    parser.add_argument("--mode", choices=["demo", "llm"], default="demo")
    parser.add_argument("--output", help="Optional path to persist the equity curve JSON")
    return parser.parse_args(list(argv) if argv is not None else None)


def build_date_range(start: str, end: str) -> List[str]:
    dates = pd.date_range(start=start, end=end, freq="B")
    return [date.strftime("%Y-%m-%d") for date in dates]


def create_llm_coordinator(data_feed: DataFeed) -> AllocationPlanner:
    specs = [
        AgentSpec(name="growth", description="Growth style analyst"),
        AgentSpec(name="value", description="Value rotation analyst"),
        AgentSpec(name="risk", description="Risk controller"),
    ]

    def _call_model(spec: AgentSpec, prompt: str) -> str:  # pragma: no cover - placeholder
        raise RuntimeError(
            "Please provide an LLM callback. For example integrate OpenAI's client and return a JSON response."
        )

    config = CoordinatorConfig(agent_specs=specs)
    return EnsembleCoordinator(data_feed=data_feed, config=config, call_model=_call_model)


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    dates = build_date_range(args.start, args.end)

    data_feed = DataFeed.create_default()
    backtester = Backtester(data_feed)

    if args.mode == "demo":
        planner: AllocationPlanner = HeuristicPlanner()
    else:
        planner = create_llm_coordinator(data_feed)

    result = backtester.run(dates, planner)
    print("Equity curve:")
    print(result.equity_curve)

    summary = summarize_performance(result.equity_curve)
    print("\nPerformance summary:")
    print(
        json.dumps(
            {
                "total_return": summary.total_return,
                "annualized_return": summary.annualized_return,
                "volatility": summary.volatility,
                "sharpe_ratio": summary.sharpe_ratio,
                "max_drawdown": summary.max_drawdown,
                "max_drawdown_window": {
                    "start": summary.max_drawdown_start,
                    "end": summary.max_drawdown_end,
                },
            },
            indent=2,
        )
    )

    print("\nOrders executed:")
    for order in result.orders:
        print(order)

    if args.output:
        payload = {
            "equity_curve": result.equity_curve.reset_index().to_dict(orient="records"),
            "orders": [order.__dict__ for order in result.orders],
            "weights": result.target_weights,
        }
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        print(f"Results written to {args.output}")


if __name__ == "__main__":  # pragma: no cover
    main()
