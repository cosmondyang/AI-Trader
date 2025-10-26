"""Technical indicator helpers for 5-minute bar datasets."""

from __future__ import annotations

import pandas as pd


def compute_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Return a DataFrame with MACD columns appended."""

    output = df.copy()
    ema_fast = output["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = output["close"].ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = dif - dea
    output["macd_dif"] = dif
    output["macd_dea"] = dea
    output["macd_hist"] = hist
    return output


def compute_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Return a DataFrame with Bollinger Band columns appended."""

    output = df.copy()
    rolling_mean = output["close"].rolling(window=window, min_periods=window).mean()
    rolling_std = output["close"].rolling(window=window, min_periods=window).std()
    output["boll_mid"] = rolling_mean
    output["boll_upper"] = rolling_mean + num_std * rolling_std
    output["boll_lower"] = rolling_mean - num_std * rolling_std
    return output


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Return a DataFrame with the RSI column appended."""

    output = df.copy()
    delta = output["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    output["rsi"] = 100 - (100 / (1 + rs))
    return output


def compute_kdj(
    df: pd.DataFrame,
    n: int = 9,
    k_period: int = 3,
    d_period: int = 3,
) -> pd.DataFrame:
    """Return a DataFrame with stochastic oscillator (KDJ) columns appended."""

    output = df.copy()
    low_min = output["low"].rolling(window=n, min_periods=n).min()
    high_max = output["high"].rolling(window=n, min_periods=n).max()
    rsv = (output["close"] - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(alpha=1 / k_period, adjust=False).mean()
    d = k.ewm(alpha=1 / d_period, adjust=False).mean()
    j = 3 * k - 2 * d
    output["kdj_k"] = k
    output["kdj_d"] = d
    output["kdj_j"] = j
    return output


__all__ = [
    "compute_macd",
    "compute_bollinger_bands",
    "compute_rsi",
    "compute_kdj",
]
