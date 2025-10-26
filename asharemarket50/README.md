# 🇨🇳 AShareMarket50 — CSI 50 Multi-Agent Simulator

The **asharemarket50** package is a self-contained project that mirrors the
capabilities of the original AI-Trader arena while specialising in the CSI 50
(A-share) universe. It bundles data acquisition powered by [AKShare], a
T+1-compliant backtesting engine, prompt scaffolding for multi-model
collaboration, and a CLI that can replay any date range with either heuristic or
LLM-driven agents.

> ✅ The project focuses on **simulation**. No real-money execution is included.

---

## 🧱 Project layout

```
asharemarket50/
├── agents/                     # LLM policies, ensemble coordinator, prompt templates
│   ├── __init__.py
│   ├── coordinator.py           # Multi-agent voting and risk clipping
│   ├── policy.py                # Prompt rendering, response parsing
│   └── prompts/
│       └── csi50_multi_agent_prompt.md
├── cli/
│   └── run_backtest.py          # Command line entry point for batch simulations
├── configs/
│   ├── __init__.py
│   ├── settings.py              # Cache folders & default configuration
│   └── universe_csi50.json      # CSI 50 constituents
├── core/
│   ├── __init__.py
│   ├── backtester.py            # T+1 execution loop & accounting
│   ├── data_feed.py             # Data shaping + indicator enrichment
│   ├── indicators.py            # MACD, Bollinger Bands, RSI, KDJ
│   └── portfolio.py             # Position & cash tracking
├── docs/
├── services/
│   ├── __init__.py
│   └── akshare_client.py        # Intraday downloader with on-disk cache
├── tests/                       # Hooks for future unit tests
├── __init__.py
└── README.md
```

The directory tree mirrors the structure of the upstream project (configs,
services, agents, CLI, docs, tests) so the module can be published as a standalone
repository without name clashes.

---

## 🚀 Quick start

1. **Install dependencies**
   - **Inside this monorepo**
     ```bash
     pip install -r requirements.txt
     ```
   - **As a standalone package**
     ```bash
     cd asharemarket50
     pip install -e .
     ```

   The module requires `akshare`, `pandas`, and `tabulate`. AKShare performs
   live HTTP requests — make sure outbound network access is available when
   fetching data.

2. **Run a demo backtest**
   ```bash
   python -m asharemarket50.cli.run_backtest --start 2024-01-08 --end 2024-01-15 --mode demo
   ```
   The demo mode uses an indicator-driven heuristic planner so it can operate
   without LLM credentials. Results print to STDOUT and can optionally be saved
   with `--output path/to/result.json`.

3. **Switch to LLM agents**
   - Implement a callback that invokes your preferred models (e.g. OpenAI,
     DeepSeek) and returns a JSON payload such as:
     ```json
     {
       "allocations": {
         "sh600519": 0.12,
         "sz000858": 0.10,
         "sh600036": 0.08
       }
     }
     ```
   - Update `create_llm_coordinator` in `cli/run_backtest.py` or wire the
     `EnsembleCoordinator` directly inside your orchestration layer.
   - Each agent receives the rendered prompt defined in
     `agents/prompts/csi50_multi_agent_prompt.md`, which already embeds
     full-day 5-minute bars plus MACD, Bollinger Bands, RSI, and KDJ values.

4. **Inspect cached market data**
   - AKShare downloads are cached to `~/.asharemarket50/cache/`. Delete files in
     that directory to force a refresh, or pass `refresh=True` to the client.

---

## 📊 Data workflow

1. **Universe definition**
   `configs/universe_csi50.json` lists all CSI 50 constituents with exchange
   prefixes. Utilities in `configs.universe` expose helper classes to iterate
   over symbols and feed them into AKShare.

2. **AKShare integration**
   - `services.akshare_client.AKShareClient.fetch_intraday(symbol, date)` pulls
     5-minute bars from `stock_zh_a_hist_min_em` and stores a normalised CSV.
   - A simple rate limiter and cache guard protect against repeated downloads.

3. **Indicator enrichment**
   - `core.indicators.IndicatorLibrary` appends MACD (DIF/DEA/HIST), Bollinger
     Bands, RSI, and KDJ columns to each DataFrame.
   - `core.data_feed.DataFeed.build_prompt_payload()` returns JSON-ready records
     so prompts can present full intraday context to each model.

4. **Backtesting**
   - `core.backtester.Backtester` simulates T+1 behaviour: allocations proposed
     on `D` execute at the open of `D+1`, and equity is marked on the close of
     `D+1`.
   - Portfolio valuation and cash accounting are handled by
     `core.portfolio.PortfolioState`.

---

## 🤖 Multi-agent orchestration

- `agents.policy.AgentPolicy` loads prompt templates, renders context
  (portfolio snapshot, risk limits, intraday data), calls the supplied LLM, and
  extracts allocations from any JSON block in the response.
- `agents.coordinator.EnsembleCoordinator` averages proposals from multiple
  `AgentPolicy` instances, clips positions against `risk_limits`, and produces a
  consolidated weight vector for the backtester.
- The default prompt template encourages agents to output both qualitative
  analysis and a machine-readable allocation block. Customise the file or point
  each `AgentSpec` to its own prompt via the `prompt_path` attribute.

---

## 🔁 How it differs from the NASDAQ simulator

| Feature | NASDAQ Arena (original) | AShareMarket50 |
| --- | --- | --- |
| Market coverage | NASDAQ 100 (US) | CSI 50 (A-share) |
| Data provider | Alpha Vantage + Jina | AKShare intraday (5-minute) |
| Execution mode | Historical replay, MCP live orchestration | Historical replay with T+1 settlement |
| Tooling | MCP tool servers (trade, price, search, math) | Lightweight coordinator + pluggable LLM callback |
| Reporting | HTML leaderboard & calculate_performance.py | 📈 Built-in performance summary (total/annualized return, Sharpe, drawdown) |

The A-share module focuses on reproducible backtests and prompt payloads for
domestic exchanges. It reuses the upstream layout (agents/configs/core/docs)
but swaps data providers and execution rules to respect the T+1 constraint. To
parity-match the U.S. benchmark arena, we added analytics in `core.performance`
so every run emits the same quality of risk/return diagnostics that the NASDAQ
toolchain computes via `calculate_performance.py` and feeds into its leaderboard.

---

## ❓ FAQ

- **Does this module trade live capital?**
  No. The toolkit is entirely simulation-oriented. Hook it to a broker or mock
  execution engine if you require paper trading.

- **Can every model be evaluated on a fixed date?**
  Yes. Run the CLI with `--start YYYY-MM-DD --end YYYY-MM-DD` (a single date) or
  provide a range. The backtester automatically chains sessions, executes
  decisions on T+1, and records equity plus orders so you can compare agents on
  the same historical windows.

- **What else do you need from me?**
  - AKShare-compatible network access (no token required) or alternative data
    credentials if you prefer a different provider.
  - Optional: a curated trading calendar if you want to avoid relying on the
    generic business-day index.
  - Optional: fundamental metadata (industries, concepts) to enrich prompts.

---

## 📌 Next steps

- Wire in your own LLM callback and agent roster.
- Extend `IndicatorLibrary` with custom factors (e.g. VWAP, ATR).
- Add unit tests under `asharemarket50/tests/` to validate allocation parsers and
  execution logic.
- Connect visual dashboards or notebooks that consume the equity curve JSON.

---

## 🧩 Coexistence & isolation

- The package exports its public API lazily, so importing `asharemarket50` does
  not alter the surrounding project nor require optional dependencies until you
  actually instantiate the AKShare client or data feed.
- Installing the package with `pip install -e asharemarket50` registers the CLI
  entry point `ashare50-backtest` without touching the original (NASDAQ-focused)
  code paths in this repository.
- If you want to spin out a dedicated repository, copy the entire
  `asharemarket50/` directory — the included `pyproject.toml` already contains
  the metadata and dependency declarations required by most Python packaging
  tooling.

If you need additional automation (calendar ingestion, richer risk management,
visualisation), open an issue or drop a note in the README — the package is
structured for fast iteration.

[AKShare]: https://github.com/akfamily/akshare
