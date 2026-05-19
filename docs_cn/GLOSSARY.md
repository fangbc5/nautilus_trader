# NautilusTrader 中文翻译术语表

本术语表用于保证 `docs_cn/` 目录下中文翻译的一致性。译者请优先采用本表的标准译法。

## 翻译原则

1. **专有名词不译**：产品名（NautilusTrader）、人名、交易所名（Binance、Bybit 等）、协议名（FIX、WebSocket）、文件名、代码标识符保留英文原文。
2. **代码与命令保留英文**：所有代码块、命令行、配置示例、API 名称、类名、函数名保留英文不译。
3. **API 名称首次出现**：可在中文术语后括注英文原文，如"行情订阅（market data subscription）"。
4. **金融术语**：采用中国大陆主流金融行业译法。
5. **链接与图片路径**：保留原始 URL 与相对路径不变；若引用其他文档，链接到 docs_cn/ 对应中文版本。
6. **Markdown 结构**：保留所有 Markdown 标记、front matter、代码围栏、admonition（`!NOTE`、`!WARNING` 等）格式。

## 标准术语表

### 核心概念

| 英文 | 中文 |
| :--- | :--- |
| backtest / backtesting | 回测 |
| live trading | 实盘交易 |
| sandbox | 沙盒（模拟盘） |
| paper trading | 模拟交易 |
| event-driven | 事件驱动 |
| deterministic | 确定性的 |
| message bus | 消息总线 |
| actor | Actor（保留英文，首次可注"参与者"） |
| strategy | 策略 |
| engine | 引擎 |
| node | 节点 |
| trader | 交易员 / 交易者 |
| adapter | 适配器 |
| component | 组件 |
| platform | 平台 |
| controller | 控制器 |
| executor | 执行器 |
| runtime | 运行时 |

### 订单与执行

| 英文 | 中文 |
| :--- | :--- |
| order | 订单 |
| order book | 订单簿 |
| top-of-book | 最优盘口 |
| order type | 订单类型 |
| time in force (TIF) | 有效期（Time in Force） |
| post-only | 仅挂单（post-only） |
| reduce-only | 仅减仓（reduce-only） |
| iceberg | 冰山单 |
| stop loss / take profit | 止损 / 止盈 |
| market order | 市价单 |
| limit order | 限价单 |
| stop order | 止损单 |
| trailing stop | 跟踪止损 |
| OCO / OUO / OTO | OCO / OUO / OTO（保留缩写） |
| fill / partial fill | 成交 / 部分成交 |
| execution | 执行 |
| execution algorithm | 执行算法 |
| matching engine | 撮合引擎 |
| slippage | 滑点 |
| latency | 延迟 |
| latency model | 延迟模型 |
| order routing | 订单路由 |

### 行情与数据

| 英文 | 中文 |
| :--- | :--- |
| market data | 行情数据 |
| tick | Tick（保留） |
| quote tick | 报价 Tick |
| trade tick | 成交 Tick |
| bar | K 线（bar） |
| candle | K 线 |
| depth | 深度 |
| order book delta | 订单簿增量（delta） |
| L1 / L2 / L3 | L1 / L2 / L3（保留） |
| snapshot | 快照 |
| subscription | 订阅 |
| feed | 数据源 |
| catalog | 数据目录（catalog） |
| ingestion | 数据接入 |
| data client | 数据客户端 |
| historical data | 历史数据 |

### 账户与持仓

| 英文 | 中文 |
| :--- | :--- |
| account | 账户 |
| position | 持仓 |
| portfolio | 组合（portfolio） |
| balance | 余额 |
| margin | 保证金 |
| leverage | 杠杆 |
| PnL / P&L | 盈亏（PnL） |
| realized / unrealized PnL | 已实现 / 未实现盈亏 |
| equity | 权益 |
| funding rate | 资金费率 |
| settlement | 结算 |
| commission | 手续费 |
| cash account | 现金账户 |
| margin account | 保证金账户 |
| netting | 净额 |
| hedging | 对冲（hedging） |

### 工具与产品

| 英文 | 中文 |
| :--- | :--- |
| instrument | 标的 / 工具（instrument） |
| spot | 现货 |
| futures | 期货 |
| perpetual | 永续合约 |
| options | 期权 |
| swaps | 掉期 |
| CFD | 差价合约（CFD） |
| FX / Forex | 外汇 |
| equities | 股票 |
| crypto | 加密货币 |
| synthetic instrument | 合成标的 |
| continuous futures | 连续期货 |
| greeks | 希腊字母（Greeks） |
| underlying | 标的资产 |
| contract size | 合约规模 |
| tick size | 最小价格变动 |
| price precision | 价格精度 |
| lot size | 手数 |

### 系统与架构

| 英文 | 中文 |
| :--- | :--- |
| cache | 缓存（cache） |
| persistence | 持久化 |
| serialization | 序列化 |
| identifier | 标识符 |
| event | 事件 |
| command | 命令 |
| topic | 主题（topic） |
| publish / subscribe | 发布 / 订阅 |
| handler | 处理器 |
| trigger | 触发 |
| callback | 回调 |
| clock | 时钟 |
| timer | 定时器 |
| timestamp | 时间戳 |
| nanosecond | 纳秒 |
| concurrency | 并发 |
| async / asynchronous | 异步 |
| sync / synchronous | 同步 |
| FFI | FFI（外部函数接口） |
| binding | 绑定 |
| wrapper | 包装器 |
| build | 构建 |
| dependency | 依赖 |
| crate | crate（Rust 包） |
| feature flag | 特性开关（feature flag） |
| logger / logging | 日志 / 日志记录 |
| log level | 日志级别 |
| benchmark | 基准测试 |
| profiling | 性能剖析 |

### 风控与分析

| 英文 | 中文 |
| :--- | :--- |
| risk | 风险 / 风控 |
| risk engine | 风控引擎 |
| risk model | 风险模型 |
| analyzer | 分析器 |
| analytics | 分析（analytics） |
| indicator | 指标 |
| technical indicator | 技术指标 |
| validation | 校验 |
| circuit breaker | 熔断器 |

### 加密货币与 DeFi

| 英文 | 中文 |
| :--- | :--- |
| CEX | 中心化交易所（CEX） |
| DEX | 去中心化交易所（DEX） |
| on-chain | 链上 |
| off-chain | 链下 |
| token | 代币（token） |
| stablecoin | 稳定币 |
| liquidity pool | 流动性池 |
| AMM | 自动做市商（AMM） |
| market maker | 做市商 |

### 开发与流程

| 英文 | 中文 |
| :--- | :--- |
| issue | issue（保留） |
| pull request / PR | PR（保留） |
| release | 发布版本 |
| changelog | 变更日志 |
| breaking change | 破坏性变更 |
| deprecation | 弃用 |
| roadmap | 路线图 |
| contribution | 贡献 |
| contributor | 贡献者 |
| maintainer | 维护者 |
| review | 评审 / 审阅 |
| repository / repo | 仓库 |
| branch | 分支 |
| merge | 合并 |
| rebase | rebase（保留） |
| fork | fork（保留） |
| upstream | 上游 |
| commit | 提交 |
| test / testing | 测试 |
| unit test | 单元测试 |
| integration test | 集成测试 |
| end-to-end test | 端到端测试 |
| CI / CD | CI / CD（保留） |
| coverage | 覆盖率 |
| linting | lint 检查 |
| formatting | 格式化 |

### 风格约定

- "you" → "你"（保持开发者文档的对话语气）
- "we" → "我们"
- 列表项末尾原文有句号则保留；原文为短语则不加句号
- 中英文混排时使用半角空格分隔（如"使用 Python 编写"）
- 数字与单位之间使用半角空格（如"100 ms"、"2 GB"）
- 长句优先拆分为短句
- 被动语态优先转为主动语态
