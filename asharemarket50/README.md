# 🇨🇳 AShareMarket50 多智能体交易场 README

> **目标**：在现有 `AI-Trader` 架构上快速搭建一个支持中证 50 的多模型问答竞赛版本，提供 5 分钟级别的日内数据、技术指标计算工具以及 Prompt 模板，做到“拷贝即用，快速跑通”。

---

## 🧱 目录结构

```
asharemarket50/
├── README.md                         # 当前说明文档
├── __init__.py                       # 包初始化
├── data_loader.py                    # 5 分钟级数据加载与校验
├── indicators.py                     # MACD / 布林带 / RSI / KDJ 指标函数
├── pipeline.py                       # 数据汇总、指标计算与 Prompt Payload 生成
├── universe_csi50.json               # 中证 50 股票列表
└── prompts/
    └── a50_agent_prompt.md           # 面向模型的问答模板示例
```

---

## 🚀 快速开始（建议流程）

1. **复制目录**：将 `asharemarket50/` 放入你的项目根目录，保持与现有美股版本平级。
2. **准备环境**：
   - 安装依赖：`pip install -r requirements.txt`
   - 若需要新增库（如 `akshare`、`tushare`），请在根目录 `requirements.txt` 中补充。
3. **填充数据**：按照下文规范写入 5 分钟线 CSV；支持本地文件或 API 拉取。
4. **执行流水线**：
   ```bash
   python -m asharemarket50.pipeline --date 2025-01-10 --data-root data/ashare/5min --output tmp/a50_payload.json
   ```
   - 该命令会读取中证 50 全部股票的当日 5 分钟线，计算指标并输出给 Agent 使用的 JSON。
5. **对接主程序**：在原有调度中，引入 `asharemarket50.pipeline.prepare_prompt_payload` 生成多模型输入。
6. **多 Agent Prompt**：为每个模型复制 `prompts/a50_agent_prompt.md` 并按需微调语气、风格。

---

## 📊 数据规范

### 1. 文件命名

```
<data_root>/<symbol>/<trade_date>.csv
例：data/ashare/5min/600519.SH/2025-01-10.csv
```

### 2. CSV 字段要求

| 列名          | 类型      | 说明                               |
|---------------|-----------|------------------------------------|
| `timestamp`   | str/datetime | 5 分钟级时间戳，格式 `YYYY-MM-DD HH:MM:SS` |
| `open`        | float     | 开盘价                             |
| `high`        | float     | 最高价                             |
| `low`         | float     | 最低价                             |
| `close`       | float     | 收盘价                             |
| `volume`      | float/int | 成交量（手）                       |
| `amount`      | float     | 成交额（人民币）                   |

> ⚠️ **注意**：请使用复权数据或在 Pipeline 中自行做前复权，以保证指标连续性。

### 3. 数据获取建议

- **TuShare Pro**：`tushare.pro_api(token)` 获取 `ts_code`, `freq='5min'`。
- **AkShare**：`ak.stock_zh_a_minute(symbol, period='5')`。
- **申万/聚宽**：如使用其他券商数据源，请在 `data_loader.py` 中自定义转换。

在 `pipeline.py` 中预留了 `--source tushare` 选项，用于后续扩展自动抓取逻辑（默认读取本地 CSV）。

---

## 🛠️ 指标函数

`indicators.py` 提供以下函数，可直接 import 使用：

- `compute_macd(df, fast=12, slow=26, signal=9)`
- `compute_bollinger_bands(df, window=20, num_std=2)`
- `compute_rsi(df, period=14)`
- `compute_kdj(df, n=9, k_period=3, d_period=3)`

所有函数均返回带新列的数据副本，默认输入 `df` 必须包含 `close / high / low` 列。若需要更多指标，请在同文件继续扩展。

---

## 🧠 Prompt 设计

- `prompts/a50_agent_prompt.md` 提供了一个**多模态问答模板**，其中会注入：
  - 全量 5 分钟 K 线序列（JSON/Markdown 表格二选一，可在 `pipeline.py` 中设置）
  - 四大技术指标计算结果（末值 + 统计摘要）
  - 资金持仓、风险约束、T+1 限制说明
- 建议为每个模型复制一份模板，根据模型偏好调整语气或策略倾向。
- Prompt 核心段落示例：
  ```text
  ### 600519.SH — 贵州茅台
  - 昨日收盘：1785.34
  - 5min 序列（09:30-15:00）：...
  - MACD(12,26,9)：DIF=..., DEA=..., HIST=...
  - 布林带(20,2)：中轨=..., 上轨=..., 下轨=...
  - RSI14：...
  - KDJ：K=..., D=..., J=...
  ```

---

## 🔄 与主项目集成建议

| 集成点 | 操作 | 参考文件 |
|--------|------|----------|
| 市场配置 | 在 `configs/default_config.json` 中新增 `market: ashare` | `configs/README.md` |
| Agent 注册 | 在 `main.py` 的 Agent 列表中增加 `ashare` 模型配置 | `main.py` |
| 工具层 | 基于 `agent_tools/tool_get_price_local.py` 新建 A 股版工具 | `agent_tools/` |
| 交易执行 | 复制 `tool_trade.py`，实现 T+1 限制与涨跌停校验 | `agent_tools/` |
| 绩效展示 | 在 `docs/` 下新增 A 股排行榜页面 | `docs/` |

---

## 📦 输出结构

默认输出 `tmp/a50_payload.json`，格式如下：

```json
{
  "trade_date": "2025-01-10",
  "universe": ["600519.SH", "600036.SH", ...],
  "bars": {
    "600519.SH": {
      "meta": {"industry": "白酒", "name": "贵州茅台"},
      "bars": [
        {"timestamp": "2025-01-09 09:30:00", "open": 1783.0, "high": 1785.0, ...},
        ...
      ],
      "indicators": {
        "macd": {"dif": 1.23, "dea": 0.98, "hist": 0.25},
        "bollinger": {"upper": 1805.1, "mid": 1780.2, "lower": 1755.3},
        "rsi": 56.7,
        "kdj": {"k": 62.3, "d": 58.1, "j": 70.7}
      }
    }
  }
}
```

该 JSON 可直接喂给多 Agent Prompt（或进一步裁剪为 Markdown 表格）。

---

## 🤝 需要你提供的内容

1. **行情 API Token**：若需自动拉取，请提供 TuShare / AkShare / 雪球等接口授权。
2. **交易日历**：若已有可靠 A 股交易日历文件，请共享，以便我们在 Pipeline 内做校验。
3. **行业/主题标签**：如果希望在 Prompt 中展示行业分类，请提供映射表，格式 `symbol -> {industry, concept}`。
4. **实盘/仿真接口**：若最终要接券商仿真或模拟盘，请告知 API 规范（REST / WebSocket）。
5. **运行资源**：若需在云端跑，提供服务器配置或容器镜像需求，我们可以在 README 中补充部署说明。

> ✅ 收到以上信息后，我们可以快速补齐自动拉取数据、回测、可视化等扩展能力，确保“开箱即跑”。

---

## 🧭 下一步建议

- [ ] 在 `pipeline.py` 中实现 `fetch_from_tushare()`，直接落地自动抓取流程。
- [ ] 扩展 `indicators.py` 支持成交量指标（OBV、VOL Ratio）。
- [ ] 根据多 Agent 策略风格，分别定制 Momentum / Mean Reversion / Macro 版 Prompt。
- [ ] 与原项目一致，编写 `docs/ashare_market_walkthrough.md` 展示每日执行日志。

---

如需进一步协作或定制，请随时留言，我们会第一时间响应并补充所需脚本/说明，帮助你尽快完成一个“能跑、能看、能迭代”的中证 50 多模型竞赛版本。💪
