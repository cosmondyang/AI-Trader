"""Technical indicator computations used by the simulator."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(slots=True)
class IndicatorLibrary:
    """Bundle of indicator calculators that can be applied to price data."""

    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    boll_window: int = 20
    boll_std: float = 2.0
    rsi_period: int = 14
    kdj_period: int = 9
    kdj_smooth: int = 3

    def apply(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Return ``frame`` with indicator columns appended."""

        enriched = frame.copy()
        enriched = self._macd(enriched)
        enriched = self._bollinger(enriched)
        enriched = self._rsi(enriched)
        enriched = self._kdj(enriched)
        return enriched

    def feature_columns(self) -> Iterable[str]:
        return [
            "macd", "macd_signal", "macd_hist",
            "boll_upper", "boll_middle", "boll_lower",
            "rsi",
            "kdj_k", "kdj_d", "kdj_j",
        ]

    def _macd(self, frame: pd.DataFrame) -> pd.DataFrame:
        ema_fast = frame["close"].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = frame["close"].ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        hist = macd_line - signal_line
        frame["macd"] = macd_line
        frame["macd_signal"] = signal_line
        frame["macd_hist"] = hist
        return frame

    def _bollinger(self, frame: pd.DataFrame) -> pd.DataFrame:
        rolling = frame["close"].rolling(window=self.boll_window)
        middle = rolling.mean()
        std = rolling.std(ddof=0)
        frame["boll_middle"] = middle
        frame["boll_upper"] = middle + self.boll_std * std
        frame["boll_lower"] = middle - self.boll_std * std
        return frame

    def _rsi(self, frame: pd.DataFrame) -> pd.DataFrame:
        delta = frame["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=self.rsi_period).mean()
        avg_loss = loss.rolling(window=self.rsi_period).mean()
        rs = avg_gain / avg_loss
        frame["rsi"] = 100 - (100 / (1 + rs))
        return frame

    def _kdj(self, frame: pd.DataFrame) -> pd.DataFrame:
        low_min = frame["low"].rolling(window=self.kdj_period).min()
        high_max = frame["high"].rolling(window=self.kdj_period).max()
        rsv = (frame["close"] - low_min) / (high_max - low_min) * 100
        k = rsv.ewm(alpha=1 / self.kdj_smooth, adjust=False).mean()
        d = k.ewm(alpha=1 / self.kdj_smooth, adjust=False).mean()
        j = 3 * k - 2 * d
        frame["kdj_k"] = k
        frame["kdj_d"] = d
        frame["kdj_j"] = j
        return frame
