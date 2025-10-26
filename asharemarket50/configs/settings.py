"""Project level settings for the CSI 50 A-share simulator."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass(slots=True)
class Settings:
    """Container for runtime configuration values.

    Attributes
    ----------
    data_cache_dir:
        Directory used to persist downloaded AKShare payloads.
    default_universe_path:
        Location of the JSON file describing the CSI 50 stock universe.
    trading_calendar:
        List of days that should be considered valid trading sessions.
    """

    data_cache_dir: Path = field(default_factory=lambda: Path.home() / ".asharemarket50" / "cache")
    default_universe_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "universe_csi50.json"
    )
    trading_calendar: List[str] = field(default_factory=list)

    def ensure_cache(self) -> Path:
        """Create the cache directory if it does not exist and return it."""

        self.data_cache_dir.mkdir(parents=True, exist_ok=True)
        return self.data_cache_dir
