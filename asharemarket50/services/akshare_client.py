"""Thin wrapper around the `akshare` data provider."""
from __future__ import annotations

import importlib
import time
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd

from ..configs.settings import Settings

spec = importlib.util.find_spec("akshare")
if spec is None:  # pragma: no cover - runtime guard
    raise RuntimeError(
        "akshare is required for the CSI 50 simulator. Install it with `pip install akshare`."
    )

ak = importlib.import_module("akshare")


class AKShareUnavailable(RuntimeError):
    """Raised when the AKShare endpoint does not return data."""


class AKShareClient:
    """Client responsible for downloading and caching intraday OHLCV data."""

    def __init__(self, settings: Optional[Settings] = None, rate_limit: float = 0.0) -> None:
        self.settings = settings or Settings()
        self.cache_dir = self.settings.ensure_cache()
        self.rate_limit = rate_limit

    def _cache_path(self, symbol: str, trade_date: str, period: str) -> Path:
        safe_symbol = symbol.replace("/", "_").replace(":", "_")
        filename = f"{safe_symbol}_{trade_date}_{period}.csv"
        return self.cache_dir / filename

    def fetch_intraday(
        self,
        symbol: str,
        trade_date: str,
        *,
        period: str = "5",
        refresh: bool = False,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """Return 5-minute bars for ``symbol`` on ``trade_date``.

        Parameters
        ----------
        symbol:
            AKShare symbol string, e.g. ``sh600000``.
        trade_date:
            Trading date in ``YYYY-MM-DD`` format.
        period:
            Granularity in minutes. Defaults to ``"5"``.
        refresh:
            If ``True`` the cached payload is ignored.
        adjust:
            Adjustment type to request from AKShare.
        """

        cache_path = self._cache_path(symbol, trade_date, period)
        if cache_path.exists() and not refresh:
            return self._load_cached(cache_path)

        start = f"{trade_date} 09:30:00"
        end = f"{trade_date} 15:00:00"
        try:
            dataset = ak.stock_zh_a_hist_min_em(
                symbol=symbol,
                period=period,
                start_date=start,
                end_date=end,
                adjust=adjust,
            )
        except Exception as exc:  # pragma: no cover - dependent on network/runtime
            raise AKShareUnavailable(str(exc)) from exc

        if dataset is None or dataset.empty:
            raise AKShareUnavailable(f"AKShare returned no data for {symbol} on {trade_date}.")

        normalized = self._normalize_payload(dataset, trade_date)
        normalized.to_csv(cache_path, index=False)

        if self.rate_limit > 0:
            time.sleep(self.rate_limit)

        return normalized

    def fetch_batch(
        self,
        symbols: Iterable[str],
        trade_date: str,
        *,
        period: str = "5",
        refresh: bool = False,
    ) -> Dict[str, pd.DataFrame]:
        """Download and return datasets for multiple ``symbols``."""

        return {
            symbol: self.fetch_intraday(symbol, trade_date, period=period, refresh=refresh)
            for symbol in symbols
        }

    def _load_cached(self, path: Path) -> pd.DataFrame:
        return pd.read_csv(path, parse_dates=["timestamp"])

    @staticmethod
    def _normalize_payload(dataset: pd.DataFrame, trade_date: str) -> pd.DataFrame:
        frame = dataset.rename(
            columns={
                "时间": "timestamp",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
            }
        )
        if "timestamp" not in frame.columns:
            frame.rename(columns={"时间": "timestamp"}, inplace=True)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"].astype(str))
        frame.sort_values("timestamp", inplace=True)
        frame.reset_index(drop=True, inplace=True)
        frame["trade_date"] = trade_date
        numeric_cols = ["open", "close", "high", "low", "volume", "amount"]
        for column in numeric_cols:
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        desired_order = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "trade_date",
        ]
        available = [column for column in desired_order if column in frame.columns]
        return frame[available]
