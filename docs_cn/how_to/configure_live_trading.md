# 配置一个实盘交易节点

> 本文档为 [English 原文](../../docs/how_to/configure_live_trading.md) 的中文翻译版本。如有歧义请以英文原版为准。

配置 `TradingNode` 以连接实盘行情。有关实盘交易架构与对账（reconciliation）的背景知识，请参阅 [实盘交易](../concepts/live.md) 概念指南。

:::danger[不推荐在 Jupyter notebook 中运行实盘交易]
不要在 Jupyter notebook 中运行实盘交易节点。事件循环冲突与运维风险使其不适合实盘场景：

- Jupyter 自己运行了一个 asyncio 事件循环，会与 `TradingNode` 的事件循环冲突。
- 像 `nest_asyncio` 这类变通方案不具备生产可用的健壮性。
- 单元格可能乱序执行，内核可能崩溃，状态可能丢失。
- Notebook 缺乏生产级交易所需的日志、监控以及优雅关停能力。

请将 Jupyter 用于回测、分析和实验。实盘交易请将节点作为独立的 Python 脚本或服务运行。
:::

:::warning[每个进程仅一个 TradingNode]
不支持在同一进程中并发运行多个 `TradingNode` 实例，因为存在全局单例状态。
请在一个节点中添加多个策略，或者在不同进程中运行额外的节点以实现并行执行。

详情参阅 [进程与线程](../concepts/architecture.md#processes-and-threads)。
:::

:::warning[不要阻塞事件循环]
事件循环线程上的用户代码（策略回调、actor 处理器、`on_event` 方法）必须快速返回。这一点对 Python 和 Rust 都适用。诸如模型推理、重计算或同步 I/O 等阻塞操作会导致漏单、行情过期以及订单提交延迟。请将耗时较长的工作转移到 executor 或独立线程/进程中执行。
:::

:::info[平台差异]
Windows 的信号处理与类 Unix 系统不同。如果你在 Windows 上运行，请阅读 [Windows 信号处理](#windows-signal-handling) 一节，了解优雅关停行为以及对 Ctrl+C（SIGINT）的支持。
:::

## TradingNodeConfig

`TradingNodeConfig` 继承自 `NautilusKernelConfig`，并新增了实盘相关的选项。
关于配置结构体如何处理默认值与 `Option<T>` 语义的背景，请参阅 [配置](../concepts/configuration.md) 概念指南。

```python
from nautilus_trader.config import TradingNodeConfig

config = TradingNodeConfig(
    trader_id="MyTrader-001",

    # Component configurations
    cache=CacheConfig(),
    message_bus=MessageBusConfig(),
    data_engine=LiveDataEngineConfig(),
    risk_engine=LiveRiskEngineConfig(),
    exec_engine=LiveExecEngineConfig(),
    portfolio=PortfolioConfig(),

    # Client configurations
    data_clients={
        "BINANCE": BinanceDataClientConfig(),
    },
    exec_clients={
        "BINANCE": BinanceExecClientConfig(),
    },
)
```

### 核心配置参数

| 配置项                    | 默认值       | 说明                                          |
|--------------------------|--------------|-----------------------------------------------|
| `trader_id`              | "TRADER-001" | 唯一的交易者标识符（name-tag 格式）。         |
| `instance_id`            | `None`       | 可选的唯一实例标识符。                        |
| `timeout_connection`     | 30.0         | 连接超时时间（秒）。                          |
| `timeout_reconciliation` | 10.0         | 对账超时时间（秒）。                          |
| `timeout_portfolio`      | 10.0         | 组合（portfolio）初始化超时时间。             |
| `timeout_disconnection`  | 10.0         | 断开连接的超时时间。                          |
| `timeout_post_stop`      | 5.0          | 关停后清理的超时时间。                        |

### 缓存数据库配置

```python
from nautilus_trader.config import CacheConfig
from nautilus_trader.config import DatabaseConfig

cache_config = CacheConfig(
    database=DatabaseConfig(
        host="localhost",
        port=6379,
        username="nautilus",
        password="pass",
        connection_timeout=2,
        response_timeout=2,
    ),
    encoding="msgpack",  # or "json"
    timestamps_as_iso8601=True,
    buffer_interval_ms=100,
    flush_on_start=False,
)
```

### MessageBus 配置

```python
from nautilus_trader.config import MessageBusConfig
from nautilus_trader.config import DatabaseConfig

message_bus_config = MessageBusConfig(
    database=DatabaseConfig(
        connection_timeout=2,
        response_timeout=2,
    ),
    timestamps_as_iso8601=True,
    use_instance_id=False,
    types_filter=[QuoteTick, TradeTick],  # Filter specific message types
    stream_per_topic=False,
    autotrim_mins=30,  # Automatic message trimming
    heartbeat_interval_secs=1,
)
```

## 多交易场所配置

一个节点可以同时连接多个交易场所。下面的示例同时配置了 Binance 的现货和期货市场：

```python
config = TradingNodeConfig(
    trader_id="MultiVenue-001",

    # Multiple data clients for different market types
    data_clients={
        "BINANCE_SPOT": BinanceDataClientConfig(
            account_type=BinanceAccountType.SPOT,
            environment=BinanceEnvironment.LIVE,
        ),
        "BINANCE_FUTURES": BinanceDataClientConfig(
            account_type=BinanceAccountType.USDT_FUTURES,
            environment=BinanceEnvironment.LIVE,
        ),
    },

    # Corresponding execution clients
    exec_clients={
        "BINANCE_SPOT": BinanceExecClientConfig(
            account_type=BinanceAccountType.SPOT,
            environment=BinanceEnvironment.LIVE,
        ),
        "BINANCE_FUTURES": BinanceExecClientConfig(
            account_type=BinanceAccountType.USDT_FUTURES,
            environment=BinanceEnvironment.LIVE,
        ),
    },
)
```

## ExecutionEngine 配置

`LiveExecEngineConfig` 用于控制订单处理、执行事件以及与交易场所的对账。完整说明请参阅 [API Reference](/docs/python-api-latest/config.html#nautilus_trader.live.config.LiveExecEngineConfig)。

### 对账（Reconciliation）

恢复丢失的订单和持仓事件，使系统状态与交易场所保持一致。

| 配置项                          | 默认值  | 说明                                                                                |
|---------------------------------|---------|-------------------------------------------------------------------------------------|
| `reconciliation`                | True    | 启动时执行对账，使内部状态与交易场所对齐。                                          |
| `reconciliation_lookback_mins`  | None    | 向前查询多少分钟的历史事件，用于对账未缓存的状态。                                  |
| `reconciliation_instrument_ids` | None    | 需要对账的标的 ID 白名单。                                                          |
| `filtered_client_order_ids`     | None    | 对账期间需要跳过的客户端订单 ID（用于处理交易场所侧重复的订单）。                    |

详情参阅 [Execution reconciliation](../concepts/live.md#execution-reconciliation)。

### 订单过滤

控制系统处理哪些订单事件与报告，避免多个交易节点之间发生冲突。

| 配置项                              | 默认值  | 说明                                                                            |
|------------------------------------|---------|---------------------------------------------------------------------------------|
| `filter_unclaimed_external_orders` | False   | 丢弃未被任何策略认领的外部订单，避免其影响策略。                                |
| `filter_position_reports`          | False   | 丢弃持仓状态报告。在多个节点共用同一账户时有用。                                |

:::note[订单标签行为]
对账过程会按来源给订单打标签：

- **`VENUE` 标签**：在交易场所发现的外部订单（在本系统之外提交）。
- **`RECONCILIATION` 标签**：为对齐持仓差异而生成的合成订单。

启用 `filter_unclaimed_external_orders` 时只会过滤 `VENUE` 标签的订单。
`RECONCILIATION` 标签的订单永远不会被过滤，从而保证持仓对齐总能成功。
:::

### 持续对账（Continuous reconciliation）

启动对账完成后，后台会启动一个持续运行的循环。它会：

- 监控延迟超过设定阈值的在途（in-flight）订单。
- 按可配置的间隔与交易场所对账未成交订单（open orders）。
- 将内部 *自有（own）* 订单簿与交易场所的公开订单簿进行比对核查。

该循环会等待启动对账完成后再开始周期性检查。
`reconciliation_startup_delay_secs` 参数会在启动对账完成 *之后* 再额外等待一段时间，让系统先稳定下来。

当重试次数用尽时，引擎按以下方式解决订单状态：

**在途订单超时解决方案**（达到最大重试次数后交易场所仍无响应）：

| 当前状态         | 解决为      | 理由                                       |
|------------------|-------------|--------------------------------------------|
| `SUBMITTED`      | `REJECTED`  | 未收到交易场所的确认。                     |
| `PENDING_UPDATE` | `CANCELED`  | 修改请求未被确认。                         |
| `PENDING_CANCEL` | `CANCELED`  | 交易场所从未确认取消。                     |

**订单一致性检查**（当缓存状态与交易场所状态不一致时）：

| 缓存状态           | 交易场所状态 | 解决结果    | 理由                                                                |
|--------------------|--------------|-------------|---------------------------------------------------------------------|
| `SUBMITTED`        | 未找到        | `REJECTED`  | 订单从未被交易场所确认（例如网络错误导致丢失）。                    |
| `ACCEPTED`         | 未找到        | `REJECTED`  | 订单在交易场所不存在，很可能从未成功提交。                          |
| `ACCEPTED`         | `CANCELED`   | `CANCELED`  | 交易场所取消了订单（用户操作或交易场所主动取消）。                  |
| `ACCEPTED`         | `EXPIRED`    | `EXPIRED`   | 订单在交易场所到达 GTD 过期时间。                                   |
| `ACCEPTED`         | `REJECTED`   | `REJECTED`  | 交易场所在最初接受之后又拒绝了该订单（罕见但确实可能）。            |
| `PARTIALLY_FILLED` | `CANCELED`   | `CANCELED`  | 订单在交易场所被取消，已成交部分保留。                              |
| `PARTIALLY_FILLED` | 未找到        | `CANCELED`  | 订单在交易场所不存在，但已有成交（对账成交记录）。                  |

:::note
**对账注意事项：**

- **"未找到" 类的解决方案** 只有在全量历史模式（`open_check_open_only=False`）下才会应用。
  默认的 open-only 模式会跳过这些检查，因为交易场所的 "未成交订单（open orders）" 接口在设计上就会排除已关闭订单，无法区分 "确实缺失的订单" 和 "刚刚关闭的订单"。
- **近期订单保护**：对于最近一次事件落在 `open_check_threshold_ms` 时间窗口（默认 5 秒）内的订单，引擎会跳过对账。这样可以避免在交易场所仍在处理中时，因为竞态条件而出现误报。
- **针对性查询保护**：在因 "未找到" 而将订单标记为 `REJECTED` 或 `CANCELED` 之前，引擎会向交易场所发起一次针对单个订单的查询。
  这可以避免因批量查询限制或时序延迟造成的误判。
- **`FILLED` 订单** 在交易场所 "未找到" 时会被静默忽略。交易场所通常会把已完成的订单从查询结果中剔除。

:::

### 重试协调与回看行为

在途订单循环和未成交订单循环共享同一个重试计数器（`_recon_check_retries`），分别受 `inflight_check_retries` 与 `open_check_missing_retries` 的限制。较严格的那个限制生效，从而避免对同一订单状态发起重复的交易场所查询。

当未成交订单循环耗尽重试次数时，引擎会先向交易场所发起一次针对单个订单的 `GenerateOrderStatusReport` 探测查询，然后再决定是否应用终止状态。如果交易场所返回了该订单，则继续对账并重置重试计数器。

**单订单查询保护**：引擎通过 `max_single_order_queries_per_cycle`（默认 10）限制每个周期内的单订单查询数量。剩余订单将推迟到下一个周期。可配置的延迟 `single_order_query_delay_ms`（默认 100 ms）用于在连续查询之间留出间隔，避免触发限频。
这样在面对成百上千个订单的批量查询失败时，也不会让交易场所 API 过载。

超过 `open_check_lookback_mins` 的旧订单会依赖这种针对性的探测查询。对于历史时间窗口较短的交易场所，请将该回看时间设置得宽松一些。如果交易场所的时间戳相比本地时钟存在滞后，可以增大 `open_check_threshold_ms`，避免最近更新过的订单被过早标记为缺失。

| 配置项                                | 默认值          | 说明                                                                                              |
|--------------------------------------|----------------|---------------------------------------------------------------------------------------------------|
| `inflight_check_interval_ms`         | 2,000&nbsp;ms  | 检查在途订单状态的频率。设为 0 表示禁用。                                                         |
| `inflight_check_threshold_ms`        | 5,000&nbsp;ms  | 在途订单触发交易场所状态查询前的等待时间。如系统与交易场所同机房，可适当调小。                    |
| `inflight_check_retries`             | 5&nbsp;次       | 与交易场所核对在途订单时的重试次数。                                                              |
| `open_check_interval_secs`           | None           | 向交易场所查询未成交订单的频率（秒）。None 或 0.0 表示禁用。推荐值：5-10 秒。                     |
| `open_check_open_only`               | True           | 为 true 时仅查询未成交订单；为 false 时拉取完整历史（资源消耗较大）。                              |
| `open_check_lookback_mins`           | 60&nbsp;分钟   | 订单状态轮询的回看窗口（分钟）。仅检查在该窗口内有过修改的订单。                                  |
| `open_check_threshold_ms`            | 5,000&nbsp;ms  | 距离最近缓存事件的最小时间，超过该阈值后才会对交易场所差异采取动作。                              |
| `open_check_missing_retries`         | 5&nbsp;次       | 缓存中显示未成交但交易场所中未找到时，解决前的最大重试次数。                                      |
| `max_single_order_queries_per_cycle` | 10             | 每个周期内单订单查询数量上限。防止触发限频。                                                      |
| `single_order_query_delay_ms`        | 100&nbsp;ms    | 连续单订单查询之间的延迟（毫秒），避免触发限频。                                                  |
| `reconciliation_startup_delay_secs`  | 10.0&nbsp;s    | 启动对账完成 *之后* 再开始持续检查前的延迟（秒）。                                                |
| `own_books_audit_interval_secs`      | None           | 将自有订单簿与公开订单簿核对的间隔（秒）。                                                        |
| `position_check_interval_secs`       | None           | 持仓一致性检查的间隔（秒）。若发现差异，会查询缺失的成交记录。None 表示禁用。推荐值：30-60 秒。 |
| `position_check_lookback_mins`       | 60&nbsp;分钟   | 出现持仓差异时，查询成交报告的回看窗口（分钟）。                                                  |
| `position_check_threshold_ms`        | 5,000&nbsp;ms  | 距离上次本地活动的最小时间，超过该阈值后才会对持仓差异采取动作。                                  |
| `position_check_retries`             | 3&nbsp;次       | 引擎在停止重试某个标的的差异之前，每个标的的最大重试次数。一旦超过该次数，会记录一条错误日志，并且在该差异自行消失之前，不会再主动进行对账。 |

:::warning

- **`open_check_lookback_mins`**：不要降到 60 分钟以下。窗口太短会导致订单落在查询范围之外，进而触发误报性质的 "缺失订单" 解决方案。
- **`reconciliation_startup_delay_secs`**：在生产环境中不要降到 10 秒以下。
  该延迟可以让系统在启动对账之后、持续检查之前先完成稳定。

:::

### 其他选项

| 配置项                              | 默认值  | 说明                                                                                              |
|------------------------------------|---------|---------------------------------------------------------------------------------------------------|
| `allow_overfills`                  | False   | 允许成交数量超过订单数量（会输出警告日志）。在对账与成交发生竞态时有用。                          |
| `generate_missing_orders`          | True    | 对账过程中生成 LIMIT 订单以对齐持仓差异（策略 `EXTERNAL`，标签 `RECONCILIATION`）。               |
| `snapshot_orders`                  | False   | 在订单事件发生时为订单生成快照。                                                                  |
| `snapshot_positions`               | False   | 在持仓事件发生时为持仓生成快照。                                                                  |
| `snapshot_positions_interval_secs` | None    | 持仓快照之间的时间间隔（秒）。                                                                    |
| `debug`                            | False   | 启用执行相关的 debug 日志。                                                                       |

### 内存管理

周期性地清理（purge）内存缓存中已关闭的订单、已平仓的持仓以及账户事件，在长时间运行或高频交易场景下控制内存占用。

| 配置项                                  | 默认值  | 说明                                                                                |
|----------------------------------------|---------|-------------------------------------------------------------------------------------|
| `purge_closed_orders_interval_mins`    | None    | 清理已关闭订单的频率（分钟）。推荐值：10-15 分钟。                                  |
| `purge_closed_orders_buffer_mins`      | None    | 订单关闭后多久（分钟）才会被清理。推荐值：60 分钟。                                 |
| `purge_closed_positions_interval_mins` | None    | 清理已平仓持仓的频率（分钟）。推荐值：10-15 分钟。                                  |
| `purge_closed_positions_buffer_mins`   | None    | 持仓平仓后多久（分钟）才会被清理。推荐值：60 分钟。                                 |
| `purge_account_events_interval_mins`   | None    | 清理账户事件的频率（分钟）。推荐值：10-15 分钟。                                    |
| `purge_account_events_lookback_mins`   | None    | 账户事件多久（分钟）以前才会被清理。推荐值：60 分钟。                               |
| `purge_from_database`                  | False   | 同时从后端数据库（Redis/PostgreSQL）中删除。**请谨慎使用**。                        |

设置了间隔即可启用清理循环；不设置则禁用调度与删除。除非 `purge_from_database` 为 true，否则数据库记录不会受到影响。每个循环最终都会调用 [Cache](../concepts/cache.md) 中描述的缓存 API。

### 队列管理

| 配置项                            | 默认值  | 说明                                                                                |
|----------------------------------|---------|-------------------------------------------------------------------------------------|
| `qsize`                          | 100,000 | 内部队列缓冲区的大小。                                                              |
| `graceful_shutdown_on_exception` | False   | 在队列处理过程中遇到非预期异常（不包括用户代码）时，进行优雅关停。                  |

## 策略配置

完整参数列表请参阅 `StrategyConfig` 的 [API Reference](/docs/python-api-latest/config.html#nautilus_trader.trading.config.StrategyConfig)。

### 标识

| 配置项          | 默认值  | 说明                                                            |
|----------------|---------|-----------------------------------------------------------------|
| `strategy_id`  | None    | 唯一的策略标识符。                                              |
| `order_id_tag` | None    | 附加到该策略订单 ID 的唯一标签。                                |

### 订单管理

| 配置项                       | 默认值  | 说明                                                                                       |
|-----------------------------|---------|--------------------------------------------------------------------------------------------|
| `oms_type`                  | None    | [OMS 类型](../concepts/execution#oms-configuration)，用于持仓 ID 与订单处理。              |
| `use_uuid_client_order_ids` | False   | 使用 UUID4 作为客户端订单 ID。                                                             |
| `external_order_claims`     | None    | 该策略要认领其外部订单的标的 ID 列表。                                                     |
| `manage_contingent_orders`  | False   | 自动管理 OTO、OCO 和 OUO 等关联订单。                                                      |
| `manage_gtd_expiry`         | False   | 管理订单的 GTD（Good-Till-Date）到期。                                                     |

## Windows 信号处理

:::warning
Windows：asyncio 事件循环没有实现 `loop.add_signal_handler`。因此，`TradingNode` 在 Windows 上无法通过 asyncio 接收操作系统信号。请使用 Ctrl+C（SIGINT）处理或编程方式触发关停；Windows 上不能期望与 SIGTERM 等价的行为。
:::

在 Windows 上，asyncio 事件循环没有实现 `loop.add_signal_handler`，因此 Unix 风格的信号集成不可用。`TradingNode` 在 Windows 上不会通过 asyncio 接收到操作系统信号，如果你不手动干预，它就无法优雅停止。

推荐的做法：

- 用 `try/except KeyboardInterrupt` 包裹 `run`，然后调用 `node.stop()` 再调用 `node.dispose()`。
  Ctrl+C 会在主线程中抛出 `KeyboardInterrupt`，提供一条干净的停机路径。
- 通过编程方式发布 `ShutdownSystem` 命令（或在 actor/组件中调用 `shutdown_system(...)`），触发与上面同样的关停路径。

"inflight check loop task still pending" 信息出现的原因是没有触发正常的优雅关停路径。该问题被追踪在 [#2785](https://github.com/nautechsystems/nautilus_trader/issues/2785)。

v2 的 `LiveNode` 已经通过 `tokio::signal::ctrl_c()` 与一个 Python SIGINT 桥接处理 Ctrl+C，因此 runner 和任务可以干净地关停。

Windows 上的示例模式：

```python
try:
    node.run()
except KeyboardInterrupt:
    pass
finally:
    try:
        node.stop()
    finally:
        node.dispose()
```
