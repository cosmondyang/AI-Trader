"""Load and validate 5-minute bar data for the CSI 50 universe."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd


@dataclass
class SymbolMeta:
    """Metadata describing an equity in the CSI 50 universe."""

    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    exchange: str = "SSE"


class DataNotFoundError(FileNotFoundError):
    """Raised when required market data is missing."""


def load_universe(path: Path) -> List[SymbolMeta]:
    """Load the CSI 50 universe metadata from a JSON file."""

    with path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    universe: List[SymbolMeta] = []
    for item in records:
        if isinstance(item, str):
            universe.append(SymbolMeta(symbol=item))
        elif isinstance(item, dict) and "symbol" in item:
            universe.append(
                SymbolMeta(
                    symbol=item["symbol"],
                    name=item.get("name"),
                    industry=item.get("industry"),
                    exchange=item.get("exchange", "SSE"),
                )
            )
        else:
            raise ValueError(f"Invalid universe entry: {item}")
    return universe


def _resolve_csv_path(data_root: Path, symbol: str, trade_date: str) -> Path:
    filename = f"{trade_date}.csv"
    return data_root / symbol / filename


def load_intraday_bars(
    symbol: str,
    trade_date: str,
    data_root: Path,
    expected_columns: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Load 5-minute bars for a symbol and trade date."""

    csv_path = _resolve_csv_path(data_root, symbol, trade_date)
    if not csv_path.exists():
        raise DataNotFoundError(f"Missing data file: {csv_path}")

    df = pd.read_csv(csv_path)
    df.columns = [col.strip().lower() for col in df.columns]

    if "timestamp" not in df.columns:
        raise ValueError(f"`timestamp` column is required in {csv_path}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    df = df.sort_values("timestamp").reset_index(drop=True)

    expected = set(expected_columns or [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
    ])
    missing = [col for col in expected if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns {missing} in {csv_path}")

    return df


def load_universe_bars(
    universe: Iterable[SymbolMeta],
    trade_date: str,
    data_root: Path,
    expected_columns: Optional[Iterable[str]] = None,
) -> Dict[str, pd.DataFrame]:
    """Load bars for every symbol in the provided universe."""

    bars: Dict[str, pd.DataFrame] = {}
    for meta in universe:
        bars[meta.symbol] = load_intraday_bars(
            symbol=meta.symbol,
            trade_date=trade_date,
            data_root=data_root,
            expected_columns=expected_columns,
        )
    return bars


__all__ = [
    "SymbolMeta",
    "load_universe",
    "load_intraday_bars",
    "load_universe_bars",
    "DataNotFoundError",
]
