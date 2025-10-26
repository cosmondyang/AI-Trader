"""Utilities for loading the CSI 50 asset universe."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass(frozen=True, slots=True)
class UniverseSymbol:
    """Metadata describing a single equity instrument."""

    symbol: str
    name: str
    exchange: str

    @property
    def akshare_symbol(self) -> str:
        """Return the AKShare symbol string."""

        if self.exchange.lower().startswith("sh"):
            return f"sh{self.symbol}"
        if self.exchange.lower().startswith("sz"):
            return f"sz{self.symbol}"
        return self.symbol


@dataclass(slots=True)
class Universe:
    """Collection of :class:`UniverseSymbol` entries."""

    members: List[UniverseSymbol]

    def by_symbol(self) -> Dict[str, UniverseSymbol]:
        return {member.symbol: member for member in self.members}

    def akshare_symbols(self) -> Iterable[str]:
        return (member.akshare_symbol for member in self.members)


def load_universe(path: Path | str) -> Universe:
    """Load CSI 50 definitions from ``path``."""

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    members = [UniverseSymbol(**item) for item in payload]
    return Universe(members=members)
