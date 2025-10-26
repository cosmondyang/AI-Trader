# AShare AI-Trader 项目实施路线（更新版）

本指南结合最新的 `asharemarket50` 子项目，给出基于中证 50（CSI 50）的多智能体
问答模拟盘搭建步骤。新版模块已经按照独立 GitHub 项目的结构重构，可单独发布
或直接在本仓库中运行。

---

## 1. 目录与命名空间规划

1. **保持与主工程一致的分层**：`asharemarket50/` 已包含 `agents/`、`core/`、`configs/`、
   `services/`、`cli/`、`docs/`、`tests/` 等目录，避免与美股实现冲突。
2. **若需拆仓独立维护**：直接复制该目录即可形成独立仓库；根部的 `__init__.py`
   暴露了数据馈送、回测、代理协调等主要接口。
3. **命名约定**：新的 Python 模块与原仓库不重名（例如 `core.backtester`
   替代旧的 `pipeline`），确保二者可同时导入。

---

## 2. 数据接入（AKShare）

1. **依赖安装**：`requirements.txt` 已新增 `akshare`、`pandas`、`tabulate`。
   ```bash
   pip install -r requirements.txt
   ```
2. **行情拉取**：`services.akshare_client.AKShareClient` 使用
   `stock_zh_a_hist_min_em` 获取 5 分钟 K 线（默认 09:30–15:00）。
   - 数据按股票+日期缓存到 `~/.asharemarket50/cache/`，支持重复调用。
   - 如需强制更新，可传入 `refresh=True` 或手动删除缓存文件。
3. **指标计算**：`core.indicators.IndicatorLibrary` 为每个时间序列添加
   MACD、布林带、RSI、KDJ 四类指标，可扩展自定义因子。
4. **Prompt 数据**：`core.data_feed.DataFeed.build_prompt_payload()` 会返回
   5 分钟全量数据 + 指标的 JSON，直接供多模型提示词引用。

> 📌 若需要替换为其他数据源，只需实现新的 service 并注入 `DataFeed`。

---

## 3. 回测与交易逻辑

1. **模拟类型**：当前实现仅支持**仿真回测**，不包含实盘接口。
2. **T+1 执行**：`core.backtester.Backtester` 约束当日指令在次日开盘成交，
   并在次日收盘估值，完全符合 A 股交易制度。
3. **组合管理**：`core.portfolio.PortfolioState` 记录现金、仓位及市值，
   可按需扩展费用、滑点等规则。
4. **命令行入口**：
   ```bash
   python -m asharemarket50.cli.run_backtest --start 2024-01-08 --end 2024-01-15 --mode demo
   ```
   - `demo` 模式使用内置的指标策略生成权重，方便快速验通。
   - `llm` 模式需要提供 LLM 回调（详见 `cli/run_backtest.py` 中的注释）。
   - 支持单日或区间复盘，结果可导出为 JSON 便于可视化。

---

## 4. 多 Agent 策略框架

1. **Prompt 模板**：`agents/prompts/csi50_multi_agent_prompt.md` 已升级，
   会注入 5 分钟全量数据与四项指标。可为不同模型复制并定制。
2. **AgentPolicy**：负责渲染模板、调用大模型、解析返回的 JSON
   (`{"allocations": {...}}`)。
3. **EnsembleCoordinator**：聚合多模型意见，执行加权平均与风控剪裁。
   - `risk_limits` 默认限制单票 20%、总仓 100%。
   - 支持自定义 `AgentSpec`，为不同模型指定独立 prompt。
4. **回测集成**：Backtester 直接调用 Coordinator 的 `propose_allocations`
   获取目标仓位，并输出实际成交、权益曲线，可对比 6–8 个模型在
   固定日期上的表现。

---

## 5. 与主工程对接建议

| 模块 | 操作建议 | 说明 |
|------|----------|------|
| 调度层 | 在主 `main.py` 中增加 `ashare` 市场入口或独立脚本 | 复用现有命令行参数体系 |
| 工具层 | 若需要下单/风控工具，按照 `agent_tools/` 接口新建 A 股版本 | 保持 T+1 校验、涨跌停检查 |
| 配置层 | 在 `configs/` 下新增 A 股专属 YAML/JSON | 包含交易日历、手续费、风控阈值 |
| 文档 | `docs/` 目录中补充运行手册与复盘报告模板 | 便于持续运营 |

---

## 6. 你可能需要提供的额外资源

1. **网络条件**：AKShare 访问东方财富数据，需要外网访问权限。
2. **交易日历**：可选地提供官方交易日 CSV，替换默认工作日推算。
3. **行业/主题标签**：若希望在 prompt 中体现行业约束，请提供映射表。
4. **LLM 接入信息**：当需要正式启用多模型投票时，请告知 API
   使用方式（OpenAI、阿里通义、DeepSeek 等）。

---

## 7. 快速演进路线

- **阶段 0**：使用 demo 模式跑通数据拉取、指标计算、回测闭环。
- **阶段 1**：接入 3–6 个大模型，通过 EnsembleCoordinator 输出实际指令。
- **阶段 2**：扩展风险模块（仓位上限、行业集中度、回撤控制）、
  增加绩效报告与可视化。
- **阶段 3**（可选）：接入实盘或券商模拟接口，复用相同的策略输出。

---

## 常见问题解答

- **Q: 原始项目是否支持实盘？**
  - A: 官方版本以模拟/回测为主，不包含券商下单。`asharemarket50`
    延续这一设定，专注于仿真回测。
- **Q: 每个大模型能否按固定日期直接回测？**
  - A: 可以。CLI 支持任意日期区间，Backtester 会自动串联日历并在
    T+1 执行。多模型的表现与权重记录在 `BacktestResult` 中，可用于
    对比评估。
- **Q: 是否仍需原始项目内的大量目录？**
  - A: `asharemarket50/` 已重构为完整子项目，包含所有关键层次。
    继续沿用主项目中的其他模块时，只需关注命名冲突与路径配置。

---

通过上述流程，即可快速搭建一个功能完备的 CSI 50 多智能体问答回测系统，
并在后续阶段扩展至更多指标、策略与可视化需求。如需额外支持，请在
`asharemarket50/docs/` 中记录需求或直接联系维护者。
