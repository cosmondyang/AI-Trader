# AShare AI-Trader 项目实施步骤

本说明基于当前 `AI-Trader` 仓库的结构与实践经验，给出构建 A 股中证50 模拟盘、多智能体问答决策系统的落地路线。整体目标是复用/改造现有的多 AI 竞赛框架，在 A 股 T+1 制度和日 K 线数据下完成每日调仓。建议按以下阶段推进：

## 1. 项目初始化
1. **复制基础框架**：Fork 或复制本仓库，保留核心目录结构（如 `main.py`、`agent/`、`configs/`、`agent_tools/`、`prompts/`）。这些模块在现有系统中负责调度、Agent 生命周期和工具调用。
2. **环境准备**：沿用 `requirements.txt` 安装依赖，确认可运行主程序 `python main.py`（详见 `README.md` 快速上手部分）。
3. **配置命名空间**：为 A 股版本建立独立配置集（如 `configs/ashare/`），便于后续维护。

## 2. 数据与市场层
1. **交易标的**：梳理中证50成分股列表（可写入 `data/ashare/index_csi50.json`）。设置股票代码映射（如 `600000.SH` → 同花顺/聚宽接口格式）。
2. **行情数据**：
   - 收集日线（开、高、低、收、量、额）+ 复权因子，存储在 `data/ashare/kline/` 目录，命名规则类似现有 `data/daily_prices_*.json`。
   - 若使用第三方 API（TuShare、AkShare 等），实现新的工具模块 `agent_tools/tool_get_price_ashare.py`，继承现有 `tool_get_price_local.py` 的接口规范。
3. **交易日历**：构建上交所/深交所日历文件（如 `data/ashare/trading_calendar.csv`），用于模拟时跳过节假日。
4. **资讯数据（可选）**：如果希望保留新闻检索功能，需将 `tool_jina_search.py` 改造为国内资讯源或本地知识库。

## 3. 交易撮合与风险控制
1. **T+1 规则**：在交易执行工具 `agent_tools/tool_trade.py` 的 A 股版本中，实现买入当日不可卖出的检查；卖出时需判断持仓冻结量。
2. **手续费与滑点**：根据 A 股规则设置印花税、佣金、过户费等参数（写入 `configs/ashare/trading_rules.json`）。
3. **涨跌停限制**：在下单校验阶段加入涨跌幅限制，拒绝超出涨跌停价格的委托。
4. **持仓上限**：约束单票/单日最大仓位比例，必要时实现风控工具（例如 `agent_tools/tool_risk_guard.py`）。

## 4. 多 Agent 决策体系
1. **Agent 定义**：在 `agent/` 下为每个模型建立子目录（如 `agent/ashare_agent/deepseek/`），复用 `BaseAgent` 抽象类。每个 Agent 包括：
   - Prompt（`prompts/ashare/deepseek_prompt.md`）
   - 策略说明、问答模板（仿照 `prompts/` 现有文件）
   - 模型配置（`configs/ashare/agents/deepseek.yaml`）
2. **问答流程**：沿用原项目的“多 AI 问答→生成交易指令”流程，每日由调度器调用各 Agent：
   - 输入：昨日持仓、可用资金、最新行情、市场资讯
   - 输出：目标股票（中证50 内）、买卖方向、目标仓位
3. **结果整合**：实现投票/加权机制。可以：
   - 直接并行执行各 Agent 提议；
   - 或者设置裁决 Agent 汇总结果，输出最终指令集。

## 5. 回测与实时模拟流程
1. **时间驱动器**：仿照 `main.py` 中的日度循环逻辑，针对日 K 数据实现 `for trade_date in trading_calendar`：
   - 装载当日行情
   - 调用多 Agent 决策
   - 根据 T+1 规则执行交易
   - 更新资产净值、持仓和日志（`docs/` 可新增报表模板）
2. **日志与可视化**：
   - 记录每笔交易（`data/ashare/trade_logs/{agent}.csv`）
   - 输出每日资产曲线，复用 `tools/plot_performance.py` 或新增脚本
   - 设计排行榜（仿照 `assets/rank.png` 生成逻辑）
3. **评估指标**：净值、最大回撤、胜率、换手率等，输出到 `docs/ashare/weekly_report.md`。

## 6. 测试与验证
1. **单元测试**：为关键工具编写测试（例如 `tests/test_ashare_trade.py`），覆盖 T+1、手续费计算等规则。
2. **集成测试**：使用少量交易日回放，确保多 Agent 协同正常。
3. **压力测试**：验证在 6–8 个 Agent 并行下的性能，必要时引入异步/多进程调度。

## 7. 快速迭代建议
- **版本 0（MVP）**：单 Agent、静态策略、手动行情文件，确保交易闭环。
- **版本 1**：引入多 Agent 问答、自动化数据更新、性能分析报表。
- **版本 2**：扩展更多模型、加入实时资讯、丰富风险管理。

## 8. 交付物与运维
1. **部署脚本**：提供 `main_ashare.py` 或在 `main.py` 中通过参数 `--market ashare` 切换。
2. **文档**：整理用户指南（如 `docs/ashare_user_guide.md`），包括配置说明、运行命令、数据更新方法。
3. **自动化**：可设置每日定时任务（crontab/CI）执行仿真并生成日报。

按照以上步骤推进，即可在最短周期内完成 A 股中证50 多 Agent 模拟盘的初版实现，并在此基础上迭代策略与工具能力。
