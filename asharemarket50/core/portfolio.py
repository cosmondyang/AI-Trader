"""Lightweight portfolio accounting for the CSI 50 simulator."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import pandas as pd


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0

    def market_value(self, price: float) -> float:
        return self.quantity * price


@dataclass(slots=True)
class PortfolioState:
    """Represent current holdings, cash balance, and valuation metrics."""

    cash: float = 1_000_000.0
    positions: Dict[str, Position] = field(default_factory=dict)

    def equity_curve(self, prices: Dict[str, pd.Series]) -> pd.Series:
        if not prices:
            return pd.Series(dtype=float)
        iterator = iter(prices.values())
        index = next(iterator).index
        total_positions = pd.Series(0.0, index=index)
        for symbol, series in prices.items():
            quantity = self.positions.get(symbol, Position(symbol)).quantity
            total_positions = total_positions.add(series * quantity, fill_value=0.0)
        cash_series = pd.Series(self.cash, index=index)
        return cash_series + total_positions

    def total_value(self, price_lookup: Dict[str, float]) -> float:
        position_value = sum(
            pos.market_value(price_lookup.get(symbol, pos.avg_price))
            for symbol, pos in self.positions.items()
        )
        return self.cash + position_value

    def update_position(self, symbol: str, quantity: float, price: float) -> None:
        position = self.positions.get(symbol, Position(symbol))
        if quantity == 0:
            self.positions.pop(symbol, None)
            return
        position.quantity = quantity
        position.avg_price = price
        self.positions[symbol] = position

    def adjust_cash(self, amount: float) -> None:
        self.cash += amount
