"""Build prompt payloads for the CSI 50 multi-agent arena."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, Literal, Optional

import pandas as pd

from .data_loader import DataNotFoundError, SymbolMeta, load_universe, load_universe_bars
from .indicators import (
    compute_bollinger_bands,
    compute_kdj,
    compute_macd,
    compute_rsi,
)

BarFormat = Literal["json", "markdown"]


def enrich_with_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Append all supported indicators to the input DataFrame."""

    enriched = compute_macd(df)
    enriched = compute_bollinger_bands(enriched)
    enriched = compute_rsi(enriched)
    enriched = compute_kdj(enriched)
    return enriched


def _last_valid_row(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        raise ValueError("Indicator DataFrame is empty; cannot build snapshot")
    return df.iloc[-1]


def summarize_indicators(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Extract the latest indicator snapshot for prompt consumption."""

    row = _last_valid_row(df.dropna(subset=["close"], how="any"))
    summary = {
        "macd": {
            "dif": float(row.get("macd_dif", float("nan"))),
            "dea": float(row.get("macd_dea", float("nan"))),
            "hist": float(row.get("macd_hist", float("nan"))),
        },
        "bollinger": {
            "upper": float(row.get("boll_upper", float("nan"))),
            "mid": float(row.get("boll_mid", float("nan"))),
            "lower": float(row.get("boll_lower", float("nan"))),
        },
        "rsi": float(row.get("rsi", float("nan"))),
        "kdj": {
            "k": float(row.get("kdj_k", float("nan"))),
            "d": float(row.get("kdj_d", float("nan"))),
            "j": float(row.get("kdj_j", float("nan"))),
        },
    }
    return summary


def dataframe_to_markdown(df: pd.DataFrame, precision: int = 2) -> str:
    """Convert the DataFrame into a markdown table string."""

    numeric_df = df.copy()
    for col in numeric_df.columns:
        if pd.api.types.is_numeric_dtype(numeric_df[col]):
            numeric_df[col] = numeric_df[col].map(lambda v: f"{v:.{precision}f}" if pd.notna(v) else "")
    return numeric_df.to_markdown(index=False)


def build_symbol_payload(
    symbol: str,
    bars: pd.DataFrame,
    meta: Optional[SymbolMeta] = None,
    bar_format: BarFormat = "json",
) -> Dict[str, object]:
    enriched = enrich_with_indicators(bars)
    indicators = summarize_indicators(enriched)

    payload = {
        "meta": asdict(meta) if meta else {"symbol": symbol},
        "indicators": indicators,
    }

    if bar_format == "json":
        payload["bars"] = enriched.to_dict(orient="records")
    elif bar_format == "markdown":
        payload["bars_markdown"] = dataframe_to_markdown(
            enriched[[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "macd_dif",
                "macd_dea",
                "macd_hist",
                "boll_upper",
                "boll_mid",
                "boll_lower",
                "rsi",
                "kdj_k",
                "kdj_d",
                "kdj_j",
            ]]
        )
    else:
        raise ValueError(f"Unsupported bar format: {bar_format}")

    return payload


def prepare_prompt_payload(
    trade_date: str,
    data_root: Path,
    universe_path: Path,
    bar_format: BarFormat = "json",
    minimum_rows: int = 20,
) -> Dict[str, object]:
    """Build the complete prompt payload for all CSI 50 constituents."""

    universe = load_universe(universe_path)
    bars_map = load_universe_bars(universe, trade_date, data_root)

    payload = {
        "trade_date": trade_date,
        "universe": [meta.symbol for meta in universe],
        "bars": {},
    }

    for meta in universe:
        bars = bars_map[meta.symbol]
        if len(bars) < minimum_rows:
            raise ValueError(
                f"{meta.symbol} only has {len(bars)} rows for {trade_date}; expected >= {minimum_rows}"
            )
        payload["bars"][meta.symbol] = build_symbol_payload(
            symbol=meta.symbol,
            bars=bars,
            meta=meta,
            bar_format=bar_format,
        )

    return payload


def _parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="Trade date in YYYY-MM-DD format")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data/ashare/5min"),
        help="Directory containing <symbol>/<date>.csv files",
    )
    parser.add_argument(
        "--universe",
        type=Path,
        default=Path("asharemarket50/universe_csi50.json"),
        help="Path to the CSI 50 universe definition JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the payload JSON",
    )
    parser.add_argument(
        "--bar-format",
        choices=["json", "markdown"],
        default="json",
        help="Whether to embed raw bars as JSON or Markdown table",
    )
    parser.add_argument(
        "--minimum-rows",
        type=int,
        default=20,
        help="Minimum number of rows required per symbol",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> Dict[str, object]:
    args = _parse_args(argv)

    try:
        payload = prepare_prompt_payload(
            trade_date=args.date,
            data_root=args.data_root,
            universe_path=args.universe,
            bar_format=args.bar_format,
            minimum_rows=args.minimum_rows,
        )
    except DataNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    return payload


if __name__ == "__main__":
    main()
