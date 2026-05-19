# 概览

> 本文档为 [English 原文](../../docs/concepts/overview.md) 的中文翻译版本。如有歧义请以英文原版为准。

## 简介

NautilusTrader 是一个开源、生产级、以 Rust 为原生底层的引擎，面向多资产、多交易所的交易系统。

该系统在单一的事件驱动架构内贯穿了研究、确定性仿真与实盘执行，Python 则作为策略逻辑、配置与编排的控制平面。

这种分离将编译型交易引擎的性能与安全性，与 Python 在系统组合与策略开发上的灵活性结合起来。对于关键任务工作负载，交易系统也可以完全由 Rust 编写。

研究系统与实盘系统使用相同的执行语义与确定性时间模型。策略可以从研究环境直接部署到生产环境，无需修改代码，实现研究到实盘的一致性，减少通常会带来部署风险的差异。

NautilusTrader 与资产类别无关。任何提供 REST API 或 WebSocket 数据源的交易所都可以通过模块化适配器接入。目前已集成的交易所涵盖加密货币交易所（CEX 与 DEX）、传统市场（外汇、股票、期货、期权）以及博彩交易所。

## 特性

- **快速**：Rust 内核，并使用 [tokio](https://crates.io/crates/tokio) 进行异步网络。
- **可靠**：由 Rust 提供的类型与线程安全保障，可选 Redis 后端的状态持久化。
- **可移植**：可在 Linux、macOS 与 Windows 上运行。可通过 Docker 部署。
- **灵活**：模块化适配器可集成任意 REST API 或 WebSocket 数据源。
- **高级**：有效期（Time in Force）支持 `IOC`、`FOK`、`GTC`、`GTD`、`DAY`、`AT_THE_OPEN`、`AT_THE_CLOSE`，以及高级订单类型与条件触发。执行指令支持 `post-only`、`reduce-only` 与冰山单。条件订单包括 `OCO`、`OUO`、`OTO`。
- **可定制**：用户自定义组件，或使用[缓存](cache.md)与[消息总线](message_bus.md)从零组装整个系统。
- **回测**：使用纳秒级精度的历史报价 Tick、成交 Tick、K 线、订单簿与自定义数据，同时回测多个交易所、多个标的与多个策略。
- **实盘**：研究与实盘部署使用完全相同的策略实现。
- **多交易所**：可同时在多个交易所运行做市与跨交易所策略。
- **AI 训练**：引擎足够快，可用于训练 AI 交易智能体（强化学习 / 进化策略）。

## 为什么选择 NautilusTrader？

交易策略研究通常在 Python 中使用向量化方法进行，而生产交易系统则使用编译型语言中的事件驱动架构单独构建。

NautilusTrader 消除了这种分离。

Rust 原生内核为研究与实盘执行提供确定性的事件驱动运行时，Python 则作为控制平面。两种环境下使用相同的架构、执行语义与时间模型，策略可以从研究迁移到生产，无需重新实现。

Python 绑定通过 [PyO3](https://pyo3.rs) 提供，并正在持续从 Cython 迁移。安装时无需安装 Rust 工具链。

## 使用场景

本软件包主要有三类使用场景：

- 在历史数据上回测交易系统（`backtest`）。
- 使用实时数据与虚拟执行模拟交易系统（`sandbox`）。
- 在真实账户或模拟账户上部署实盘交易系统（`live`）。

代码库提供了构建上述系统软件层的框架。默认的 `backtest` 与 `live` 系统实现位于各自的同名子包中。`sandbox` 环境可通过 sandbox 适配器构建。

:::note

- 所有示例都会使用这些默认系统实现。
- 我们将交易策略视为端到端交易系统的子组件，这些系统包括应用层与基础设施层。

:::

## 分布式

平台可集成到更大的分布式系统中。几乎所有配置与领域对象都通过 JSON、MessagePack 或 Apache Arrow（Feather）进行序列化，以便在网络间通信。

## 公共内核

公共系统内核被所有节点的[环境上下文](architecture.md#environment-contexts)（`backtest`、`sandbox` 与 `live`）共用。用户定义的 `Actor`、`Strategy` 与 `ExecAlgorithm` 组件在这些环境上下文中以一致的方式被管理。

## 回测

通过直接将数据送入 `BacktestEngine`，或通过更高层的 `BacktestNode` 与 `ParquetDataCatalog`，以纳秒级精度让数据流经系统。

## 实盘交易

`TradingNode` 从多个数据与执行客户端摄取数据与事件，既支持演示/模拟交易账户，也支持真实账户。它在单一[事件循环](https://docs.python.org/3/library/asyncio-eventloop.html)上异步运行，提供高性能，并可选择使用 [uvloop](https://github.com/MagicStack/uvloop) 实现（适用于 Linux 与 macOS）以获得额外的吞吐量。

## 领域模型

平台具备一个交易领域模型，包括 `Price`、`Quantity` 等各种数值类型，以及更复杂的实体如 `Order` 和 `Position` 对象，这些对象用于聚合多个事件以确定状态。

## 时间戳

所有时间戳均采用 UTC 纳秒精度。

时间戳字符串遵循 ISO 8601（RFC 3339）格式，小数部分为 9 位（纳秒）或 3 位（毫秒）精度（但大多数情况下为纳秒），并始终保留所有位数（包括末尾的 0）。它们可见于日志消息以及对象的 debug/display 输出。

时间戳字符串由以下部分组成：

- 始终包含完整的日期部分：`YYYY-MM-DD`。
- 在日期与时间部分之间使用 `T` 分隔。
- 始终使用纳秒精度（9 位小数），或在某些情况下（例如 GTD 过期时间）使用毫秒精度（3 位小数）。
- 始终使用以 `Z` 后缀指定的 UTC 时区。

示例：`2024-01-05T15:30:45.123456789Z`

完整规范请参阅 [RFC 3339: Date and Time on the Internet](https://datatracker.ietf.org/doc/html/rfc3339)。

## UUID

平台使用通用唯一标识符（UUID）版本 4（RFC 4122）作为唯一标识。我们的高性能实现使用 `uuid` crate 在从字符串解析时进行正确性校验，以确保输入 UUID 符合规范。

有效的 UUID v4 由以下部分组成：

- 32 个十六进制字符，分为 5 组显示。
- 各组用连字符分隔：`8-4-4-4-12` 格式。
- 版本 4 标识（由第三组以 "4" 开头来指示）。
- RFC 4122 变体标识（由第四组以 "8"、"9"、"a" 或 "b" 开头来指示）。

示例：`2d89666b-1a1e-4a75-b193-4eb3b454c757`

完整规范请参阅 [RFC 4122: A Universally Unique Identifier (UUID) URN Namespace](https://datatracker.ietf.org/doc/html/rfc4122)。

## 数据类型

以下行情数据类型可用于历史请求，并在交易所/数据提供方支持且在集成适配器中实现的情况下作为实时流进行订阅。

- `OrderBookDelta`（L1/L2/L3）
- `OrderBookDeltas`（容器类型）
- `OrderBookDepth10`（每侧固定 10 档深度）
- `QuoteTick`
- `TradeTick`
- `Bar`
- `Instrument`
- `InstrumentStatus`
- `InstrumentClose`

以下 `PriceType` 选项可用于 K 线聚合：

- `BID`
- `ASK`
- `MID`
- `LAST`

## K 线聚合

可用的 `BarAggregation` 方法如下：

- `MILLISECOND`
- `SECOND`
- `MINUTE`
- `HOUR`
- `DAY`
- `WEEK`
- `MONTH`
- `YEAR`
- `TICK`
- `VOLUME`
- `VALUE`（也称为美元 K 线）
- `RENKO`（基于价格的砖图）
- `TICK_IMBALANCE`
- `TICK_RUNS`
- `VOLUME_IMBALANCE`
- `VOLUME_RUNS`
- `VALUE_IMBALANCE`
- `VALUE_RUNS`

上述所有聚合都已实现为内部聚合。信息驱动型聚合需要 `TradeTick` 数据。

价格类型与 K 线聚合可以通过 `BarSpecification` 以任意方式与 >= 1 的步长组合。这使得替代性 K 线可以用于实盘交易的聚合。

## 账户类型

以下账户类型在实盘与回测环境中均可用：

- `Cash` 单一货币（基础货币）
- `Cash` 多货币
- `Margin` 单一货币（基础货币）
- `Margin` 多货币
- `Betting` 单一货币

## 订单类型

以下订单类型可用（在交易所支持的情况下）：

- `MARKET`
- `LIMIT`
- `STOP_MARKET`
- `STOP_LIMIT`
- `MARKET_TO_LIMIT`
- `MARKET_IF_TOUCHED`
- `LIMIT_IF_TOUCHED`
- `TRAILING_STOP_MARKET`
- `TRAILING_STOP_LIMIT`

## 数值类型

以下数值类型由 128 位或 64 位原始整数值支撑，具体取决于编译时使用的[精度模式](../getting_started/installation.md#precision-mode)。

- `Price`
- `Quantity`
- `Money`

### 高精度模式（128 位）

当 `high-precision` 特性开关**启用**（默认）时，数值使用以下规格：

| 类型         | 原始底层      | 最大精度 | 最小值              | 最大值             |
|:-------------|:------------|:--------------|:--------------------|:-------------------|
| `Price`      | `i128`      | 16            | -17,014,118,346,046 | 17,014,118,346,046 |
| `Money`      | `i128`      | 16            | -17,014,118,346,046 | 17,014,118,346,046 |
| `Quantity`   | `u128`      | 16            | 0                   | 34,028,236,692,093 |

### 标准精度模式（64 位）

当 `high-precision` 特性开关**禁用**时，数值使用以下规格：

| 类型         | 原始底层      | 最大精度 | 最小值              | 最大值             |
|:-------------|:------------|:--------------|:--------------------|:-------------------|
| `Price`      | `i64`       | 9             | -9,223,372,036      | 9,223,372,036      |
| `Money`      | `i64`       | 9             | -9,223,372,036      | 9,223,372,036      |
| `Quantity`   | `u64`       | 9             | 0                   | 18,446,744,073     |
