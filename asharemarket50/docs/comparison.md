# CSI 50 vs. NASDAQ 100 Simulator

This note summarises the structural differences between the upstream NASDAQ arena
and the new AShareMarket50 module, plus areas now aligned through the recent
refactor.

## Key gaps previously observed

1. **Reporting parity** – The NASDAQ stack exposes `calculate_performance.py`
   and a static leaderboard to surface risk/return analytics, while the CSI 50
   package only printed raw equity curves.
2. **Data providers** – NASDAQ relies on Alpha Vantage equities + Jina search.
   The A-share module now integrates AKShare 5-minute bars and indicator
   enrichment to keep prompts at feature parity.
3. **Tooling footprint** – Upstream agents converse with MCP trade/price/search
   servers. Our design keeps a pluggable callback so you can reuse the same LLM
   orchestration without standing up those servers if you only need backtests.

## Enhancements shipped in this revision

- Added `core.performance` to compute total return, annualised return, Sharpe
  ratio, volatility, and maximum drawdown directly from any backtest run.
- Updated `cli/run_backtest.py` to emit a JSON-formatted performance summary so
  downstream dashboards or notebooks can slot into the workflow just like the
  NASDAQ leaderboard ingestion pipeline.
- Documented a feature comparison table in the package README for quick
  reference when switching between the U.S. and A-share modules.

## Suggested next steps

- If you wish to mimic the live MCP competitions, connect the
  `EnsembleCoordinator` to the same MCP trade/search servers used by the NASDAQ
  arena. The prompt payload already contains the richer intraday data needed by
  those agents.
- Build a lightweight static dashboard (e.g., with Plotly or Streamlit) that
  consumes the exported equity curve + summary JSON to match the upstream
  leaderboard UX.

---

## Isolation from the NASDAQ stack

- `asharemarket50` includes its own `pyproject.toml` and dependency list so it
  can be packaged or installed without pulling in the U.S. market assets.
- Python modules are namespaced under `asharemarket50.*`, avoiding collisions
  with `agent`, `tools`, or other NASDAQ-focused packages.
- Imports are lazy where possible (e.g., AKShare is only required once you
  instantiate the data feed), ensuring the two ecosystems coexist without
  interfering with each other.
