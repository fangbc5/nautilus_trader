# Databento
> 本文档为 [English 原文](../../docs/integrations/databento.md) 的中文翻译版本。如有歧义请以英文原版为准。

NautilusTrader 包含一个用于 [Databento](https://databento.com/) API 的适配器，
并支持以 [Databento Binary Encoding (DBN)](https://databento.com/docs/standards-and-conventions/databento-binary-encoding)
格式提供的数据。Databento 仅是行情数据提供商。该适配器不包含执行客户端，
但可以将其与沙盒搭配使用以进行模拟执行。
你也可以将 Databento 数据与 Interactive Brokers 执行配合使用，
或为加密货币交易计算传统资产类别的信号。

该适配器支持：

- 从 DBN 文件加载历史数据，并解码为 Nautilus 对象，用于回测或数据目录（catalog）存储。
- 请求历史数据并解码为 Nautilus 对象，用于实盘交易和回测。
- 订阅实时数据源，解码为 Nautilus 对象，用于实盘交易和沙盒环境。

:::tip
[Databento](https://databento.com/signup) 为新注册用户提供 $125 的免费数据额度。
Databento 目前允许将这些额度用于历史数据，或用于订阅计划的首月费用。

只要请求得当，这些额度足以覆盖测试与评估。请在请求数据前先调用
[/metadata.get_cost](https://databento.com/docs/api-reference-historical/metadata/metadata-get-cost)
端点。
:::

## 概览

该适配器使用 [databento-rs](https://crates.io/crates/databento) crate，
即 Databento 官方的 Rust 客户端库。

:::info
你无需单独安装 `databento`。该适配器以静态库形式编译，并在构建过程中自动链接。
:::

提供以下适配器类：

- `DatabentoDataLoader`：从文件加载 DBN 数据。
- `DatabentoInstrumentProvider`：通过 Databento HTTP API 获取最新或历史的标的定义。
- `DatabentoHistoricalClient`：通过 Databento HTTP API 获取历史行情数据。
- `DatabentoLiveClient`：通过 Databento 的原始 TCP API 订阅实时数据源。
- `DatabentoDataClient`：用于实盘交易节点的 `LiveMarketDataClient` 实现。

:::info
大多数用户会配置实盘交易节点（如下所述），而不直接使用这些组件。
:::

## 示例

参见 [实盘示例](https://github.com/nautechsystems/nautilus_trader/tree/develop/examples/live/databento/)。

## Databento 文档

参见 [Databento 新用户指南](https://databento.com/docs/quickstart/new-user-guides)。
请将其与本集成指南一同参考。

## Databento Binary Encoding (DBN)

Databento Binary Encoding (DBN) 是一种快速的消息编码与存储格式，用于规范化的行情数据。
[DBN 规范](https://databento.com/docs/standards-and-conventions/databento-binary-encoding)
包含自描述的元数据头以及一组固定的结构体定义，用以标准化行情数据的规范化方式。

该适配器将 DBN 数据解码为 Nautilus 对象。同一个 Rust 解码器处理以下场景：

- 从磁盘加载并解码 DBN 文件。
- 实时解码历史数据与实时数据。

## 支持的 Schema

NautilusTrader 支持以下 Databento schema：

| Databento schema                                                              | Nautilus 数据类型                  | 描述                              |
|:------------------------------------------------------------------------------|:-----------------------------------|:----------------------------------|
| [MBO](https://databento.com/docs/schemas-and-data-formats/mbo)                | `OrderBookDelta`                   | Market by order (L3)。            |
| [MBP_1](https://databento.com/docs/schemas-and-data-formats/mbp-1)            | `(QuoteTick, TradeTick \| None)`   | Market by price (L1)。            |
| [MBP_10](https://databento.com/docs/schemas-and-data-formats/mbp-10)          | `OrderBookDepth10`                 | 市场深度 (L2)。                   |
| [BBO_1S](https://databento.com/docs/schemas-and-data-formats/bbo-1s)          | `QuoteTick`                        | 1 秒最优买卖盘口。                |
| [BBO_1M](https://databento.com/docs/schemas-and-data-formats/bbo-1m)          | `QuoteTick`                        | 1 分钟最优买卖盘口。              |
| [CMBP_1](https://databento.com/docs/schemas-and-data-formats/cmbp-1)          | `(QuoteTick, TradeTick \| None)`   | 跨场所合并的 MBP。                |
| [CBBO_1S](https://databento.com/docs/schemas-and-data-formats/cbbo-1s)        | `QuoteTick`                        | 合并的 1 秒 BBO。                 |
| [CBBO_1M](https://databento.com/docs/schemas-and-data-formats/cbbo-1m)        | `QuoteTick`                        | 合并的 1 分钟 BBO。               |
| [TCBBO](https://databento.com/docs/schemas-and-data-formats/tcbbo)            | `(QuoteTick, TradeTick)`           | 按成交采样的合并 BBO。            |
| [TBBO](https://databento.com/docs/schemas-and-data-formats/tbbo)              | `(QuoteTick, TradeTick)`           | 按成交采样的最优买卖盘口。        |
| [TRADES](https://databento.com/docs/schemas-and-data-formats/trades)          | `TradeTick`                        | 成交 Tick。                       |
| [OHLCV_1S](https://databento.com/docs/schemas-and-data-formats/ohlcv-1s)      | `Bar`                              | 1 秒 K 线。                       |
| [OHLCV_1M](https://databento.com/docs/schemas-and-data-formats/ohlcv-1m)      | `Bar`                              | 1 分钟 K 线。                     |
| [OHLCV_1H](https://databento.com/docs/schemas-and-data-formats/ohlcv-1h)      | `Bar`                              | 1 小时 K 线。                     |
| [OHLCV_1D](https://databento.com/docs/schemas-and-data-formats/ohlcv-1d)      | `Bar`                              | 日 K 线。                         |
| [DEFINITION](https://databento.com/docs/schemas-and-data-formats/definition)  | `Instrument`（多种类型）           | 标的定义。                        |
| [IMBALANCE](https://databento.com/docs/schemas-and-data-formats/imbalance)    | `DatabentoImbalance`               | 集合竞价不平衡数据。              |
| [STATISTICS](https://databento.com/docs/schemas-and-data-formats/statistics)  | `DatabentoStatistics`              | 市场统计信息。                    |
| [STATUS](https://databento.com/docs/schemas-and-data-formats/status)          | `InstrumentStatus`                 | 市场状态更新。                    |

:::note
Databento 还提供参考 schema，包括公司行为（corporate actions）、调整因子（adjustment factors）和
证券主数据（security master data）。当前该适配器仅将上述列出的 schema 映射到 Nautilus 数据类型。
Databento DBN crate 还公开了 `ohlcv-eod`；Nautilus 在适配器层为日 K 线保留了覆盖项，
而 Databento 公开 schema 文档中将日 OHLCV 列为 `ohlcv-1d`。
:::

:::info
对于不支持的 `instrument_class` 值（`'I'` 指数、`'B'` 债券、`'X'` FX spot），标的定义会被跳过并给出警告，
而不会中止整个批次。会发布指数的发布商包括 CGIF.TITANIUM (110)、IEX Options (108) 以及 MEMX MX2 (109)。
如需 Nautilus 对这些类别建模，请提交 issue。

`stat_type` 值超出建模范围（当前为 1-20）的统计消息也会被跳过并给出警告。这包括场所特定值
`VenueSpecificVolume1` (10001) 和 `VenueSpecificPrice1` (10002)，它们超过了持久化所用 Arrow 列的
`u8` 宽度。
:::

### Schema 注意事项

- **TBBO 与 TCBBO**：按成交采样的数据源，将每笔成交与该成交*之前*的 BBO 配对。
  适用于需要将成交与同期报价对齐而又不想管理两条数据流的场景。
- **MBP-1 与 CMBP-1 (L1)**：事件级更新，只在出现成交事件时发送成交。
  选择它们用于完整的最优盘口事件流。若需报价与成交的对齐，请优先选 TBBO 或 TCBBO。
- **MBP-10 (L2)**：包含成交的前 10 档深度。适用于需要深度感知但不需要完整 MBO 数据的策略。
  含每档订单数。
- **MBO (L3)**：逐订单事件，用于队列位置建模与精确的订单簿重建。
  在节点初始化时启动，以获得正确的回放上下文。
- **BBO_1S/BBO_1M 与 CBBO_1S/CBBO_1M**：固定间隔（1 秒或 1 分钟）的采样最优盘口更新。
  这些 schema 适配器仅发送 `QuoteTick`。适用于监控、价差和低成本信号。
  它们不适合微观结构研究。
- **TRADES**：仅成交。可与 MBP-1（`include_trades=True`）配合使用，或使用 TBBO 或 TCBBO 以同时获得报价上下文。
- **OHLCV**：由成交聚合而来的 K 线。适用于更长周期的分析。设置 `bars_timestamp_on_close=True` 可使用收盘时间戳。
- **不平衡、统计与状态**：场所运营数据。通过 `subscribe_data` 并附带携带 `instrument_id` 元数据的 `DataType` 进行订阅。

:::tip
合并 schema（CMBP_1、CBBO_1S、CBBO_1M、TCBBO）会跨多个场所聚合数据。适用于跨场所分析。
:::

:::info
另请参见 Databento [Schemas and data formats](https://databento.com/docs/schemas-and-data-formats) 指南。
:::

## 实盘订阅的 Schema 选择

Nautilus 订阅方法与 Databento schema 的映射关系如下：

| Nautilus 订阅方法                | 默认 schema     | 可用的 Databento schema                                                       | Nautilus 数据类型  |
|:--------------------------------|:----------------|:-----------------------------------------------------------------------------|:-------------------|
| `subscribe_quote_ticks()`       | `mbp-1`         | `mbp-1`, `bbo-1s`, `bbo-1m`, `cmbp-1`, `cbbo-1s`, `cbbo-1m`, `tbbo`, `tcbbo` | `QuoteTick`        |
| `subscribe_trade_ticks()`       | `trades`        | `trades`, `tbbo`, `tcbbo`, `mbp-1`, `cmbp-1`                                 | `TradeTick`        |
| `subscribe_order_book_depth()`  | `mbp-10`        | `mbp-10`                                                                     | `OrderBookDepth10` |
| `subscribe_order_book_deltas()` | `mbo`           | `mbo`                                                                        | `OrderBookDeltas`  |
| `subscribe_bars()`              | 因情况而定      | `ohlcv-1s`, `ohlcv-1m`, `ohlcv-1h`, `ohlcv-1d`                               | `Bar`              |

:::note
下面的示例假定处于 `Strategy` 或 `Actor` 上下文中，`self` 提供订阅方法。请导入所需类型：

```python
from nautilus_trader.adapters.databento import DATABENTO_CLIENT_ID
from nautilus_trader.model import BarType
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.identifiers import InstrumentId
```

:::

### 报价订阅（MBP 与 L1）

```python
# Default MBP-1 quotes (may include trades)
self.subscribe_quote_ticks(instrument_id, client_id=DATABENTO_CLIENT_ID)

# Explicit MBP-1 schema
self.subscribe_quote_ticks(
    instrument_id=instrument_id,
    params={"schema": "mbp-1"},
    client_id=DATABENTO_CLIENT_ID,
)

# 1-second BBO snapshots (adapter emits QuoteTick only)
self.subscribe_quote_ticks(
    instrument_id=instrument_id,
    params={"schema": "bbo-1s"},
    client_id=DATABENTO_CLIENT_ID,
)

# Consolidated quotes across venues
self.subscribe_quote_ticks(
    instrument_id=instrument_id,
    params={"schema": "cbbo-1s"},  # or "cmbp-1" for consolidated MBP
    client_id=DATABENTO_CLIENT_ID,
)

# Trade-sampled BBO (includes quotes and trades)
self.subscribe_quote_ticks(
    instrument_id=instrument_id,
    params={"schema": "tbbo"},  # Receives QuoteTick and TradeTick on the message bus
    client_id=DATABENTO_CLIENT_ID,
)
```

### 成交订阅

```python
# Trade ticks only
self.subscribe_trade_ticks(instrument_id, client_id=DATABENTO_CLIENT_ID)

# Trades from MBP-1 feed (only when trade events occur)
self.subscribe_trade_ticks(
    instrument_id=instrument_id,
    params={"schema": "mbp-1"},
    client_id=DATABENTO_CLIENT_ID,
)

# Trade-sampled data (includes quotes at trade time)
self.subscribe_trade_ticks(
    instrument_id=instrument_id,
    params={"schema": "tbbo"},  # Also provides quotes at trade events
    client_id=DATABENTO_CLIENT_ID,
)
```

### 订单簿深度订阅（MBP 与 L2）

```python
# Subscribe to top 10 levels of market depth
self.subscribe_order_book_depth(
    instrument_id=instrument_id,
    depth=10  # MBP-10 schema is automatically selected
)

# The depth parameter must be 10 for Databento
# Receives OrderBookDepth10 updates
```

### 订单簿增量订阅（MBO 与 L3）

```python
# Subscribe to full order book updates (market by order)
self.subscribe_order_book_deltas(
    instrument_id=instrument_id,
    book_type=BookType.L3_MBO  # Uses MBO schema
)

# Make MBO subscriptions at node startup so Databento can replay from session start
```

### K 线订阅

```python
# Subscribe to 1-minute bars (automatically uses ohlcv-1m schema)
self.subscribe_bars(
    bar_type=BarType.from_str(f"{instrument_id}-1-MINUTE-LAST-EXTERNAL")
)

# Subscribe to 1-second bars (automatically uses ohlcv-1s schema)
self.subscribe_bars(
    bar_type=BarType.from_str(f"{instrument_id}-1-SECOND-LAST-EXTERNAL")
)

# Subscribe to hourly bars (automatically uses ohlcv-1h schema)
self.subscribe_bars(
    bar_type=BarType.from_str(f"{instrument_id}-1-HOUR-LAST-EXTERNAL")
)

# Subscribe to daily bars (automatically uses ohlcv-1d schema)
self.subscribe_bars(
    bar_type=BarType.from_str(f"{instrument_id}-1-DAY-LAST-EXTERNAL")
)

# Subscribe to daily bars with the adapter's end-of-day override
self.subscribe_bars(
    bar_type=BarType.from_str(f"{instrument_id}-1-DAY-LAST-EXTERNAL"),
    params={"schema": "ohlcv-eod"},
)
```

### 自定义数据类型订阅

不平衡、统计和状态数据需要使用通用的 `subscribe_data` 方法：

```python
from nautilus_trader.adapters.databento import DATABENTO_CLIENT_ID
from nautilus_trader.adapters.databento import DatabentoImbalance
from nautilus_trader.adapters.databento import DatabentoStatistics
from nautilus_trader.model import DataType

# Subscribe to imbalance data
self.subscribe_data(
    data_type=DataType(DatabentoImbalance, metadata={"instrument_id": instrument_id}),
    client_id=DATABENTO_CLIENT_ID,
)

# Subscribe to statistics data
self.subscribe_data(
    data_type=DataType(DatabentoStatistics, metadata={"instrument_id": instrument_id}),
    client_id=DATABENTO_CLIENT_ID,
)

# Subscribe to instrument status updates
from nautilus_trader.model.data import InstrumentStatus
self.subscribe_data(
    data_type=DataType(InstrumentStatus, metadata={"instrument_id": instrument_id}),
    client_id=DATABENTO_CLIENT_ID,
)
```

## 标的 ID 与符号体系

Databento 行情数据包含 `instrument_id` 字段：多数情况下由发布商分配的数字 ID，
或当发布商不提供时由 Databento 合成。Databento 仅保证该 ID 在给定日期内唯一。
这与 Nautilus 的 `InstrumentId` 不同，后者是用句点分隔的 symbol + venue 字符串：`"{symbol}.{venue}"`。

解码器将 Databento `raw_symbol` 映射为 Nautilus `symbol`，并使用定义消息中的
[ISO 10383 市场标识码](https://www.iso20022.org/market-identifier-codes)作为 Nautilus `venue`。

Databento 使用*数据集 ID*（dataset ID）来标识数据集，与场所标识符分离。
详见 [Databento 数据集命名规范](https://databento.com/docs/api-reference-historical/basics/datasets)。

对于 CME Globex MDP 3.0（`GLBX.MDP3`），这些交易所归在 `GLBX` 场所下。
具体映射由标的的 `exchange` 字段决定：

- `CBCM`：XCME-XCBT 跨所价差
- `NYUM`：XNYM-DUMX 跨所价差
- `XCBT`：芝加哥期货交易所（CBOT）
- `XCEC`：商品交易中心（COMEX）
- `XCME`：芝加哥商品交易所（CME）
- `XFXS`：CME FX Link 价差
- `XNYM`：纽约商品交易所（NYMEX）

:::info
其他场所的 MIC 位于 [metadata.list_publishers](https://databento.com/docs/api-reference-historical/metadata/metadata-list-publishers)
端点响应中的 `venue` 字段。
:::

## 时间戳

Databento 数据包含以下时间戳字段：

- `ts_event`：撮合引擎收到时的时间戳（自 UNIX 纪元起的纳秒）。
- `ts_in_delta`：撮合引擎发送时间戳，在 `ts_recv` 之前的纳秒数。
- `ts_recv`：采集服务器收到时的时间戳（自 UNIX 纪元起的纳秒）。
- `ts_out`：Databento 发送时间戳（仅实时数据）。

Nautilus 数据至少需要两个时间戳（按 `Data` 契约）：

- `ts_event`：数据事件发生时的 UNIX 时间戳（纳秒）。
- `ts_init`：创建数据实例时的 UNIX 时间戳（纳秒）。

解码器将 Databento `ts_recv` 映射为 Nautilus `ts_event`。该时间戳更可靠，
且每个 Databento 符号的取值单调递增。例外是 `DatabentoImbalance` 和 `DatabentoStatistics`，
它们携带所有时间戳字段，因为它们是适配器特有的类型。

:::info
详见 Databento 文档：

- [Databento 标准与规范 - 时间戳](https://databento.com/docs/standards-and-conventions/common-fields-enums-types#timestamps)
- [Databento 时间戳指南](https://databento.com/docs/architecture/timestamping-guide)

:::

## 数据类型

本节描述 Databento schema 到 Nautilus 数据类型的映射。

:::info
参见 Databento [schemas and data formats](https://databento.com/docs/schemas-and-data-formats)。
:::

### 标的定义

Databento 对所有标的类别使用同一个 schema。解码器会将其映射到对应的 Nautilus `Instrument` 类型。

| Databento 标的类别 | 代码  | Nautilus 标的类型        |
|---------------------|------|--------------------------|
| Stock               | `K`  | `Equity`                 |
| Future              | `F`  | `FuturesContract`        |
| Call                | `C`  | `OptionContract`         |
| Put                 | `P`  | `OptionContract`         |
| Future spread       | `S`  | `FuturesSpread`          |
| Option spread       | `T`  | `OptionSpread`           |
| Mixed spread        | `M`  | `OptionSpread`           |
| FX spot             | `X`  | `CurrencyPair`           |
| Bond                | `B`  | 暂不可用                 |

### 价格精度

Databento 原始价格是定点整数，按 1e-9 缩放。适配器会根据定义消息中的标的最小价格变动推导价格精度。

对于实时数据源，数据源处理器会维护一个按标的的精度映射，由到达的 `InstrumentDefMsg` 记录填充。
行情数据处理器按以下顺序解析精度：

1. 与 Databento 记录 `instrument_id` 对应的 `InstrumentDefMsg` 元数据。
2. 由 Python 订阅路径传入的缓存标的精度。
3. 传入直连实时客户端的显式 `price_precisions`。
4. USD 默认精度 2。

回退映射按符号映射后的 Databento 记录 `instrument_id` 为键，因此对父符号、连续符号
等非原始符号体系请求，在定义元数据到达前仍可使用缓存或显式精度。

**标的定义必须先于行情数据到达**，才能保证非标准最小价格变动的标的（如最小变动为 1/256 的国债期货）
的精度正确。在订阅行情数据之前或同时，请订阅 `DEFINITION` schema。

对于历史数据请求和基于文件的加载，每条记录的精度按以下顺序解析：

1. 调用时显式传入的 `price_precision` 参数。
2. 由按符号缓存填充的精度（通过文件加载器的 `load_instruments`、
   历史客户端的 `get_range_instruments`，或显式调用 `set_price_precision(symbol, precision)`）。

Python 数据客户端会在每次请求前从标的提供者填充历史客户端的缓存，因此已加载的标的无需额外配置。
当无法解析精度时，加载会以显式错误失败，而不会默默回退到 USD 精度。

:::tip
Python 适配器会在行情数据之前自动订阅标的定义，并将缓存的标的精度作为回退传入，
因此精度映射会在无额外配置的情况下自动填充。若直接使用 Rust 客户端，请在行情数据之前订阅
`DEFINITION` schema，或显式传入精度回退值。
:::

### MBO（market by order）

MBO 是 Databento 颗粒度最高的数据，代表完整的订单簿深度。部分消息包含成交数据。
解码器会生成 `OrderBookDelta`，并在适用时生成 `TradeTick`。

实时客户端会缓冲 MBO 消息，直到看到 `F_LAST` 标志，然后将一个 `OrderBookDeltas` 容器交给处理器。

客户端在回放启动序列中也会将订单簿快照缓冲为 `OrderBookDeltas`。

### MBP-1（market by price，最优盘口）

MBP-1 表示最优盘口的报价与成交。部分消息携带成交数据。
解码器会生成 `QuoteTick`，并在消息为成交时同时生成 `TradeTick`。

### TBBO 与 TCBBO（最优盘口含成交）

TBBO 和 TCBBO 在每条消息中同时提供报价和成交数据。两种 schema 每条消息都会发出
`QuoteTick` 和 `TradeTick`，比分别订阅报价和成交更高效。TCBBO 提供跨场所的合并数据。

#### Trade ID 派生（CMBP-1 与 TCBBO）

CMBP-1 和 TCBBO schema 不发布原生的成交标识符。解码器通过对标的 ID、`ts_event`、`ts_recv`、
价格、数量与主动方进行 FNV-1a 哈希来派生确定性的 `TradeId`。同一个场所事件在多次回放中会
产生相同的 trade ID，下游去重依然有效。两条字段完全相同但逻辑上不同的成交会冲突；
这与场所本身无法区分它们一致。

### OHLCV（K 线聚合）

Databento 将 K 线消息的时间戳标记在区间**开盘**时刻。解码器会将 `ts_event` 归一化为 K 线**收盘**
时刻（原始 `ts_event` + 区间长度）。

### 不平衡与统计

`imbalance` 和 `statistics` schema 在 Nautilus 中没有内置等价物。
适配器在 Rust 中定义了 `DatabentoImbalance` 和 `DatabentoStatistics`。

PyO3 绑定将这些类型公开到 Python 中。它们的属性是 PyO3 对象，可能与期望 Cython 类型的方法不兼容。
PyO3 与 Cython 之间的转换方法请参阅 API 参考。

将 PyO3 的 `Price` 转换为 Cython 的 `Price`：

```python
price = Price.from_raw(pyo3_price.raw, pyo3_price.precision)
```

请求与订阅这些类型需要使用通用的 `subscribe_data` 方法。订阅 `AAPL.XNAS` 的 `imbalance`：

```python
from nautilus_trader.adapters.databento import DATABENTO_CLIENT_ID
from nautilus_trader.adapters.databento import DatabentoImbalance
from nautilus_trader.model import DataType

instrument_id = InstrumentId.from_str("AAPL.XNAS")
self.subscribe_data(
    data_type=DataType(DatabentoImbalance, metadata={"instrument_id": instrument_id}),
    client_id=DATABENTO_CLIENT_ID,
)
```

请求 `ES.FUT` 父符号（所有活跃的 E-mini S&P 500 期货）的前一日 `statistics` 数据：

```python
from nautilus_trader.adapters.databento import DATABENTO_CLIENT_ID
from nautilus_trader.adapters.databento import DatabentoStatistics
from nautilus_trader.model import DataType

instrument_id = InstrumentId.from_str("ES.FUT.GLBX")
metadata = {
    "instrument_id": instrument_id,
    "start": "2024-03-06",
}
self.request_data(
    data_type=DataType(DatabentoStatistics, metadata=metadata),
    client_id=DATABENTO_CLIENT_ID,
)
```

### 数据目录持久化

两种类型都支持 Arrow 序列化以存入数据目录。当你导入适配器包时，Arrow 序列化器会自动注册。

#### 写入数据目录

```python
from nautilus_trader.adapters.databento import DatabentoDataLoader
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.persistence.catalog import ParquetDataCatalog

catalog = ParquetDataCatalog.from_env()
loader = DatabentoDataLoader()

imbalances = loader.from_dbn_file(
    path="aapl-imbalance.dbn.zst",
    instrument_id=InstrumentId.from_str("AAPL.XNAS"),
    as_legacy_cython=False,  # Required for Databento-specific types
)

catalog.write_data(imbalances)
```

#### 从数据目录读取

```python
from nautilus_trader.adapters.databento import DatabentoImbalance

results = catalog.query(DatabentoImbalance, identifiers=["AAPL.XNAS"])

for imbalance in results:
    print(imbalance.ref_price)  # DatabentoImbalance fields
```

:::warning
数据目录持久化支持这些类型的写入与查询，但目前还不支持通过 `BacktestNode` 或 `BacktestEngine`
对它们进行流式处理。若需用不平衡或统计数据进行回测，请直接查询数据目录，并在策略或分析代码中处理结果。
:::

#### Rust 中的编码与解码

`nautilus_databento::arrow` 模块提供 Arrow 记录批（record batch）的编码与解码。
需启用 `arrow` 特性开关（feature flag）。

```rust
use nautilus_databento::arrow::imbalance::{
    decode_imbalance_batch,
    imbalance_to_arrow_record_batch,
};

let batch = imbalance_to_arrow_record_batch(imbalances)?;

let metadata = batch.schema().metadata().clone();
let decoded = decode_imbalance_batch(&metadata, batch)?;
```

`statistics` 模块遵循相同模式，对应函数为 `decode_statistics_batch` 与 `statistics_to_arrow_record_batch`。

## 性能考量

使用 DBN 数据进行回测有两种方式：

- 将数据保存为 DBN 文件（`.dbn.zst`），每次运行时都解码为 Nautilus 对象。
- 将 DBN 文件一次性转换为 Nautilus 对象，并写入数据目录（Nautilus Parquet 格式）。

DBN 解码器使用经过优化的 Rust 实现，但一次性写入数据目录可获得最佳回测性能。

[DataFusion](https://arrow.apache.org/datafusion/) 可从磁盘以高吞吐流式读取 Nautilus Parquet 数据，
速度至少比每次运行解码 DBN 快一个数量级。

:::note
性能基准测试仍在开发中。
:::

## 加载 DBN 数据

`DatabentoDataLoader` 类用于加载 DBN 文件并将记录转换为 Nautilus 对象。主要有两种用途：

- 将数据传给 `BacktestEngine.add_data` 用于回测。
- 将数据写入 `ParquetDataCatalog`，以便通过 `BacktestNode` 进行流式处理。

### 将 DBN 数据导入 BacktestEngine

加载 DBN 数据并传给 `BacktestEngine`。引擎需要一个标的。
本例使用 `TestInstrumentProvider`（也可以使用从 DBN 文件解析得到的标的）。
数据涵盖纳斯达克上一个月的 TSLA 成交：

```python
# Add instrument
TSLA_NASDAQ = TestInstrumentProvider.equity(symbol="TSLA")
engine.add_instrument(TSLA_NASDAQ)

# Decode data to Cython objects
loader = DatabentoDataLoader()
trades = loader.from_dbn_file(
    path=TEST_DATA_DIR / "databento" / "temp" / "tsla-xnas-20240107-20240206.trades.dbn.zst",
    instrument_id=TSLA_NASDAQ.id,
)

# Add data
engine.add_data(trades)
```

### 将 DBN 数据导入 ParquetDataCatalog

加载 DBN 数据并写入 `ParquetDataCatalog`。设置 `as_legacy_cython=False` 将其解码为 PyO3 对象。

### 加载标的

**重要**：在将行情数据加载到数据目录之前，先从 DEFINITION schema 文件加载标的定义。
数据目录需要先有标的，才能存储行情数据。行情数据文件本身不包含标的定义。

```python
# Initialize the catalog interface
# (will use the `NAUTILUS_PATH` env var as the path)
catalog = ParquetDataCatalog.from_env()

loader = DatabentoDataLoader()

# Step 1: Load instrument definitions first
# Obtain DEFINITION schema files from Databento for your instruments
instruments = loader.from_dbn_file(
    path=TEST_DATA_DIR / "databento" / "temp" / "tsla-xnas-definition.dbn.zst",
    as_legacy_cython=False,  # Use PyO3 for optimal performance
)

# Write instruments to catalog
catalog.write_data(instruments)

# Step 2: Now load and write market data
instrument_id = InstrumentId.from_str("TSLA.XNAS")

# Decode trades to PyO3 objects
trades = loader.from_dbn_file(
    path=TEST_DATA_DIR / "databento" / "temp" / "tsla-xnas-20240107-20240206.trades.dbn.zst",
    instrument_id=instrument_id,
    as_legacy_cython=False,  # This is an optimization for writing to the catalog
)

# Write market data
catalog.write_data(trades)
```

#### 加载多种数据类型用于回测

务必先加载标的，再加载行情数据：

```python
from nautilus_trader.adapters.databento.loaders import DatabentoDataLoader
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.persistence.catalog import ParquetDataCatalog

catalog = ParquetDataCatalog.from_env()
loader = DatabentoDataLoader()

# Step 1: Load instrument definitions from DEFINITION files
instruments = loader.from_dbn_file(
    path="equity-definitions.dbn.zst",
    as_legacy_cython=False,
)
catalog.write_data(instruments)

# Step 2: Load market data (MBO, trades, quotes, etc.)
instrument_id = InstrumentId.from_str("AAPL.XNAS")

# Load MBO order book deltas
deltas = loader.from_dbn_file(
    path="aapl-mbo.dbn.zst",
    instrument_id=instrument_id,  # Optional but improves performance
    as_legacy_cython=False,
)
catalog.write_data(deltas)

# Load trades
trades = loader.from_dbn_file(
    path="aapl-trades.dbn.zst",
    instrument_id=instrument_id,
    as_legacy_cython=False,
)
catalog.write_data(trades)

# Verify instruments are in the catalog
print(catalog.instruments())  # Shows your loaded instruments
```

:::tip
调用 `catalog.instruments()` 进行验证。若返回空列表，说明你需要先加载 DEFINITION 文件。
:::

:::info
请通过 Databento API 或 CLI 下载对应符号与日期范围的 DEFINITION schema 文件。
详见 [Databento 文档](https://databento.com/docs/api-reference-historical/timeseries/timeseries-get-range)。
:::

:::info
另请参见 [数据概念指南](../concepts/data.md)。
:::

### 历史加载器选项

`from_dbn_file` 的参数：

- `instrument_id`：跳过符号体系查找以加快解码。
- `price_precision`：应用于每条读取记录的覆盖值。当省略时，加载器会从其按符号缓存（由
  `load_instruments` 或 `set_price_precision` 填充）解析精度；若无法解析则加载失败。
- `include_trades`：对于 MBP-1/CMBP-1 schema，设置为 `True` 时若包含成交数据则同时发出
  `QuoteTick` 与 `TradeTick`。
- `as_legacy_cython`：对 IMBALANCE/STATISTICS schema 设置为 `False`（必需），
  或为获得更好的数据目录写入性能而设置。

:::warning
IMBALANCE 与 STATISTICS schema 必须使用 `as_legacy_cython=False`（仅 PyO3 类型）。
设置为 `True` 会抛出 `ValueError`。
:::

### 加载合并数据

合并 schema 会跨多个场所聚合数据：

```python
# Load consolidated MBP-1 quotes
loader = DatabentoDataLoader()
cmbp_quotes = loader.from_dbn_file(
    path="consolidated.cmbp-1.dbn.zst",
    instrument_id=InstrumentId.from_str("AAPL.XNAS"),
    include_trades=True,  # Includes both quotes and trades if available
    as_legacy_cython=True,
)

# Load consolidated BBO quotes
cbbo_quotes = loader.from_dbn_file(
    path="consolidated.cbbo-1s.dbn.zst",
    instrument_id=InstrumentId.from_str("AAPL.XNAS"),
    as_legacy_cython=False,  # Use PyO3 for better performance
)

# Load TCBBO (trade-sampled consolidated BBO) with quotes and trades
# include_trades=True loads quotes, include_trades=False loads trades
tcbbo_quotes = loader.from_dbn_file(
    path="consolidated.tcbbo.dbn.zst",
    instrument_id=InstrumentId.from_str("AAPL.XNAS"),
    include_trades=True,  # Loads quotes
    as_legacy_cython=True,
)

tcbbo_trades = loader.from_dbn_file(
    path="consolidated.tcbbo.dbn.zst",
    instrument_id=InstrumentId.from_str("AAPL.XNAS"),
    include_trades=False,  # Loads trades
    as_legacy_cython=True,
)
```

:::tip
不要为同一个标的同时订阅 TBBO/TCBBO 与单独的成交数据源。这些 schema 已经包含成交数据。
重复订阅会浪费费用并产生重复数据。
:::

## 实时客户端架构

`DatabentoDataClient` 封装了其他 Databento 适配器类。每个数据集使用两个 `DatabentoLiveClient` 实例：

- 一个用于 MBO（订单簿增量）实时数据源
- 另一个用于所有其他实时数据源

:::warning
在节点启动时为某数据集发起所有 MBO 订阅，才能从会话开始进行回放。客户端在启动之后接收的订阅
会被记录为错误并忽略。

此限制不适用于其他 schema。
:::

单个 `DatabentoHistoricalClient` 同时为 `DatabentoInstrumentProvider` 与 `DatabentoDataClient`
的历史请求服务。

## 配置

在你的 `TradingNode` 客户端配置中添加 `DATABENTO` 段：

```python
from nautilus_trader.adapters.databento import DATABENTO
from nautilus_trader.live.node import TradingNode

config = TradingNodeConfig(
    data_clients={
        DATABENTO: {
            "api_key": None,  # 'DATABENTO_API_KEY' env var
            "http_gateway": None,  # Override for the default HTTP historical gateway
            "live_gateway": None,  # Override for the default raw TCP real-time gateway
            "instrument_provider": InstrumentProviderConfig(load_all=True),
            "instrument_ids": None,  # Nautilus instrument IDs to load on start
            "parent_symbols": None,  # Databento parent symbols to load on start
        },
    },
)
```

创建 `TradingNode` 并注册工厂：

```python
from nautilus_trader.adapters.databento.factories import DatabentoLiveDataClientFactory
from nautilus_trader.live.node import TradingNode

# Create the live trading node with the configuration
node = TradingNode(config=config)

# Register the client factory with the node
node.add_data_client_factory(DATABENTO, DatabentoLiveDataClientFactory)

# Build the node
node.build()
```

### 配置参数

| 选项                       | 默认值   | 描述                                                                                                                |
|---------------------------|---------|----------------------------------------------------------------------------------------------------------------------|
| `api_key`                 | `None`  | Databento API 密钥。当为 `None` 时回退到 `DATABENTO_API_KEY` 环境变量。                                              |
| `http_gateway`            | `None`  | 用于测试自定义端点的历史 HTTP 网关覆盖。                                                                             |
| `live_gateway`            | `None`  | 原始 TCP 实时网关覆盖，通常仅用于测试。                                                                              |
| `use_exchange_as_venue`   | `True`  | 使用交易所 MIC 作为 Nautilus 场所（例如 `XCME`）。`False` 保留默认的 GLBX 映射。                                     |
| `timeout_initial_load`    | `15.0`  | 每个数据集在继续前等待标的定义的秒数。                                                                               |
| `mbo_subscriptions_delay` | `3.0`   | 在启用 MBO/L3 流之前的缓冲秒数，以便初始快照按顺序回放。                                                            |
| `bars_timestamp_on_close` | `True`  | K 线以收盘时刻打时间戳（`ts_event`/`ts_init`）。`False` 则以开盘时刻打时间戳。                                       |
| `reconnect_timeout_mins`  | `10`    | 放弃前尝试重连的分钟数。`None` 表示无限重试。参见[连接稳定性](#connection-stability)。                              |
| `venue_dataset_map`       | `None`  | 可选的 Nautilus 场所到 Databento 数据集代码映射。                                                                    |
| `parent_symbols`          | `None`  | 可选的 `{dataset: {parent symbols}}`，用于预加载定义树（例如 `{"GLBX.MDP3": {"ES.FUT", "ES.OPT"}}`）。              |
| `instrument_ids`          | `None`  | 启动时预加载定义的 Nautilus `InstrumentId` 值。                                                                      |

:::tip
请使用环境变量来管理凭证。
:::

### 连接稳定性

实时客户端会在以下情况下自动重连：

- **网络中断**：临时连接问题。
- **网关重启**：Databento 周日维护。参见
  [维护时间表](https://databento.com/docs/api-reference-live/basics#maintenance-schedule)。
- **市场休市**：在休市时段结束的会话。

#### 重连策略

退避策略取决于超时配置：

**带超时**（默认 10 分钟）：

- 指数退避，最高 **60 秒**。
- 模式：1s、2s、4s、8s、16s、32s、60s、60s 等（含抖动）。
- 在超时窗口内快速重连。

**不带超时**（`reconnect_timeout_mins=None`）：

- 指数退避，最高 **10 分钟**。
- 模式：1s、2s、4s、8s、16s、32s、64s、128s、256s、512s、600s、600s 等（含抖动）。
- 适合需要跨越隔夜休市和计划维护的无人值守系统。

所有重连都包括：

- **抖动**：随机延迟（最多 1 秒），防止同时重连风暴。
- **自动重新订阅**：重连后恢复所有活跃订阅。
- **周期重置**：每次成功会话（>60s）会重置超时计时。

#### 超时配置

`reconnect_timeout_mins` 参数控制客户端尝试重连的时长：

**默认（10 分钟）**：适用于大多数场景。

- 处理瞬时网络问题。
- 能熬过计划内网关重启。
- 在市场夜间关闭时停止重试。
- 较长时间的中断需要人工介入。

:::warning
设置 `reconnect_timeout_mins=None` 会无限重试。仅在必须熬过隔夜休市的无人值守系统中使用。
这可能掩盖持续存在的配置或认证问题。
:::

#### 计划维护

Databento 每周日重启实时网关（所有客户端会断开）：

| 数据集             | 维护时间（UTC） |
|--------------------|------------------------|
| CME Globex         | 09:30                  |
| 所有 ICE 场所      | 09:45                  |
| 所有其他数据集     | 10:30                  |

默认的 10 分钟超时足以覆盖典型重启。对于无人值守系统，请使用 `reconnect_timeout_mins=None`
或更长的值。详见 [Databento 维护时间表](https://databento.com/docs/api-reference-live/basics/maintenance-schedule)。

## 贡献

:::info
要贡献代码，请参阅 [贡献指南](https://github.com/nautechsystems/nautilus_trader/blob/develop/CONTRIBUTING.md)。
:::
