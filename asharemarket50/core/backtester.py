"""Backtesting engine capable of simulating T+1 executions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, Protocol

import pandas as pd

from .portfolio import PortfolioState

if TYPE_CHECKING:  # pragma: no cover
    from .data_feed import DataFeed


class AllocationPlanner(Protocol):
    """Protocol describing an agent coordinator able to provide target weights."""

    def propose_allocations(
        self,
        trade_date: str,
        market_data: Dict[str, pd.DataFrame],
        portfolio: PortfolioState,
    ) -> Dict[str, float]:
        """Return target portfolio weights for execution on the next session."""


@dataclass(slots=True)
class TradeOrder:
    trade_date: str
    symbol: str
    side: str
    quantity: float
    price: float
    notional: float


@dataclass(slots=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    orders: List[TradeOrder]
    target_weights: Dict[str, Dict[str, float]]


class Backtester:
    """Run a T+1 backtest over a sequence of trading dates."""

    def __init__(self, data_feed: DataFeed) -> None:
        self.data_feed = data_feed

    def run(
        self,
        dates: Iterable[str],
        planner: AllocationPlanner,
        initial_cash: float = 1_000_000.0,
    ) -> BacktestResult:
        ordered_dates = sorted(set(dates))
        if len(ordered_dates) < 2:
            raise ValueError("At least two trading dates are required for a T+1 backtest.")

        portfolio = PortfolioState(cash=initial_cash)
        orders: List[TradeOrder] = []
        weight_history: Dict[str, Dict[str, float]] = {}
        equity_records: List[dict] = []

        for idx, trade_date in enumerate(ordered_dates[:-1]):
            execution_date = ordered_dates[idx + 1]
            market_data = self.data_feed.load_for_date(trade_date)
            target_weights = planner.propose_allocations(trade_date, market_data, portfolio)
            weight_history[trade_date] = target_weights

            execution_data = self.data_feed.load_for_date(execution_date)
            open_prices = {symbol: df.iloc[0]["open"] for symbol, df in execution_data.items()}
            close_prices = {symbol: df.iloc[-1]["close"] for symbol, df in execution_data.items()}

            orders.extend(
                self._rebalance(
                    execution_date,
                    portfolio,
                    target_weights,
                    open_prices,
                )
            )

            equity_records.append(
                {
                    "date": execution_date,
                    "equity": portfolio.total_value(close_prices),
                    "cash": portfolio.cash,
                }
            )

        equity_curve = pd.DataFrame(equity_records).set_index("date")
        return BacktestResult(equity_curve=equity_curve, orders=orders, target_weights=weight_history)

    def _rebalance(
        self,
        execution_date: str,
        portfolio: PortfolioState,
        target_weights: Dict[str, float],
        open_prices: Dict[str, float],
    ) -> List[TradeOrder]:
        orders: List[TradeOrder] = []
        tradable_symbols = set(open_prices)

        # Liquidate symbols no longer requested.
        for symbol in list(portfolio.positions.keys()):
            if symbol not in target_weights and symbol in tradable_symbols:
                price = open_prices[symbol]
                position = portfolio.positions[symbol]
                quantity = -position.quantity
                if quantity == 0:
                    continue
                cash_flow = quantity * price
                portfolio.adjust_cash(-cash_flow)
                portfolio.update_position(symbol, 0, price)
                orders.append(
                    TradeOrder(
                        trade_date=execution_date,
                        symbol=symbol,
                        side="SELL",
                        quantity=-quantity,
                        price=price,
                        notional=-(quantity * price),
                    )
                )

        price_lookup = open_prices.copy()
        total_value = portfolio.total_value(price_lookup)
        for symbol, weight in target_weights.items():
            if symbol not in tradable_symbols:
                continue
            price = price_lookup[symbol]
            target_value = total_value * weight
            position = portfolio.positions.get(symbol)
            current_quantity = position.quantity if position else 0.0
            target_quantity = target_value / price
            delta = target_quantity - current_quantity
            if abs(delta) < 1e-6:
                continue
            cash_flow = delta * price
            portfolio.adjust_cash(-cash_flow)
            portfolio.update_position(symbol, current_quantity + delta, price)
            orders.append(
                TradeOrder(
                    trade_date=execution_date,
                    symbol=symbol,
                    side="BUY" if delta > 0 else "SELL",
                    quantity=abs(delta),
                    price=price,
                    notional=abs(delta * price),
                )
            )

        return orders
