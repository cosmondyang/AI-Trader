"""Data feed helpers that bridge AKShare downloads and agent prompts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

import pandas as pd

from ..configs import Settings, load_universe
from ..services import AKShareClient
from .indicators import IndicatorLibrary


@dataclass(slots=True)
class DataFeed:
    """Load intraday data, attach indicators, and build prompt payloads."""

    akshare_client: AKShareClient
    indicator_library: IndicatorLibrary
    settings: Settings

    @classmethod
    def create_default(cls) -> "DataFeed":
        settings = Settings()
        client = AKShareClient(settings=settings)
        indicators = IndicatorLibrary()
        return cls(akshare_client=client, indicator_library=indicators, settings=settings)

    def load_for_date(self, trade_date: str, *, symbols: Iterable[str] | None = None) -> Dict[str, pd.DataFrame]:
        """Return a mapping of ``symbol -> DataFrame`` for ``trade_date``."""

        if symbols is None:
            universe = load_universe(self.settings.default_universe_path)
            symbols = universe.akshare_symbols()
        payload = self.akshare_client.fetch_batch(symbols, trade_date)
        return {symbol: self.indicator_library.apply(frame) for symbol, frame in payload.items()}

    def build_prompt_rows(self, frame: pd.DataFrame) -> list[dict]:
        """Return a list of dictionaries describing the most recent bars."""

        columns = [
            "timestamp", "open", "high", "low", "close", "volume",
            *self.indicator_library.feature_columns(),
        ]
        available_cols = [col for col in columns if col in frame.columns]
        subset = frame[available_cols].tail(78)  # roughly a trading day of 5-minute bars
        subset = subset.copy()
        subset["timestamp"] = subset["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
        return subset.to_dict(orient="records")

    def build_prompt_payload(
        self, trade_date: str, *, symbols: Iterable[str] | None = None
    ) -> Dict[str, list[dict]]:
        """Return serializable payload for prompts for ``trade_date``."""

        datasets = self.load_for_date(trade_date, symbols=symbols)
        return {symbol: self.build_prompt_rows(frame) for symbol, frame in datasets.items()}

    def latest_snapshot(self, trade_date: str, symbol: str) -> dict:
        """Return the last bar enriched with indicators for ``symbol``."""

        frame = self.load_for_date(trade_date, symbols=[symbol])[symbol]
        last_row = frame.iloc[-1]
        return last_row.to_dict()
