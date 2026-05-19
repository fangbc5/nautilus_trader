# Rust

> 本文档为 [English 原文](../../docs/concepts/rust.md) 的中文翻译版本。如有歧义请以英文原版为准。

Nautilus 在 `crates/` 目录下提供完整的 Rust 实现。你可以无需 Python 即可编写 actor、策略、运行回测和实盘交易。
所有路径共享同一份领域模型，v2 PyO3 路径则直接让 Python 策略在 Rust 引擎上运行。

:::warning
Rust API 仍在积极开发中。方法签名和 trait 要求可能在版本之间变化。
:::

## 系统实现

Nautilus 有三种实现。理解它们各自的状态有助于为你的使用场景选择合适的实现。

- **v1 legacy**：位于 `nautilus_trader/` 下的 Cython/Python 类。功能最完整，组件覆盖最广。
- **v2 Rust**：位于 `crates/` 下的纯 Rust。无需 Python 即可运行。
- **v2 PyO3**：通过 PyO3 绑定，Python 用户组件（actor、策略）运行在 Rust 核心之上。
  兼具 Python 的便利与 Rust 引擎的性能。

### 能力矩阵

| 组件                  | v1 legacy (Cython) | v2 Rust        | v2 PyO3 (Python on Rust) |
|-----------------------|--------------------|----------------|--------------------------|
| Strategy              | ✓                  | ✓              | ✓                        |
| Actor                 | ✓                  | ✓              | ✓                        |
| DataEngine            | ✓                  | ✓              | ✓                        |
| ExecutionEngine       | ✓                  | ✓              | ✓                        |
| RiskEngine            | ✓                  | ✓              | ✓                        |
| BacktestEngine        | ✓                  | ✓              | ✓                        |
| BacktestNode          | ✓                  | ✓              | ✓                        |
| LiveNode              | ✓                  | ✓              | ✓                        |
| OrderEmulator         | ✓                  | ✓              | ✓                        |
| Matching engine       | ✓                  | ✓              | ✓                        |
| Portfolio             | ✓                  | ✓              | ✓                        |
| Accounts              | ✓                  | ✓              | ✓                        |
| Cache                 | ✓                  | ✓              | ✓                        |
| MessageBus            | ✓                  | ✓              | ✓                        |
| Data catalog          | ✓                  | ✓              | ✓                        |
| Indicators            | ✓                  | ✓              | ✓                        |
| Exec algorithms       | TWAP               | TWAP           | TWAP                     |
| Controller            | ✓                  | -              | -                        |
| Tearsheets            | ✓                  | -              | -                        |
| Config serialization  | ✓                  | -              | -                        |

### 适配器

| 适配器              | v1 legacy (Cython) | v2 Rust | v2 PyO3 |
|---------------------|--------------------|---------|---------|
| Architect AX        | ✓                  | ✓       | ✓       |
| Betfair             | ✓                  | ✓       | ✓       |
| Binance             | ✓                  | ✓       | ✓       |
| BitMEX              | ✓                  | ✓       | ✓       |
| Bybit               | ✓                  | ✓       | ✓       |
| Databento           | ✓                  | ✓       | ✓       |
| Deribit             | ✓                  | ✓       | ✓       |
| dYdX                | ✓                  | ✓       | ✓       |
| Hyperliquid         | ✓                  | ✓       | ✓       |
| Interactive Brokers | ✓                  | -       | -       |
| Kraken              | ✓                  | ✓       | ✓       |
| OKX                 | ✓                  | ✓       | ✓       |
| Polymarket          | ✓                  | ✓       | ✓       |
| Sandbox             | ✓                  | ✓       | ✓       |
| Tardis              | ✓                  | ✓       | ✓       |

### 选择一个实现路径

- **v1 legacy** 目前最完整。如果你需要 Controller、tearsheet、Interactive Brokers 或配置序列化，请使用它。
- **v2 Rust** 在没有 Python 运行时的情况下提供原生性能。所有核心交易功能均可用。
  适用于延迟敏感的部署或偏好编译型语言的团队。
- **v2 PyO3**：Python 用户组件（actor、策略）运行在 Rust 核心引擎上，
  数据处理与执行获得 Rust 的性能，同时保留 Python 的开发体验。

## 项目设置

Nautilus 各 crate 已发布到 [crates.io](https://crates.io/crates/nautilus-backtest)。将它们加入你的 `Cargo.toml`：

```toml
[dependencies]
nautilus-backtest = "0.55"
nautilus-common = "0.55"
nautilus-execution = "0.55"
nautilus-model = { version = "0.55", features = ["stubs"] }
nautilus-trading = { version = "0.55", features = ["examples"] }

anyhow = "1"
log = "0.4"
```

对于实盘交易，加上 live crate 和你所用 venue 的适配器：

```toml
[dependencies]
nautilus-live = "0.55"
nautilus-okx = "0.55"
```

要追踪最新开发分支，将所有 Nautilus 依赖指向相同的 git 源，以避免 crates.io 与 git 版本间的类型不匹配：

```toml
[dependencies]
nautilus-backtest = { git = "https://github.com/nautechsystems/nautilus_trader.git", branch = "develop" }
nautilus-common = { git = "https://github.com/nautechsystems/nautilus_trader.git", branch = "develop" }
nautilus-execution = { git = "https://github.com/nautechsystems/nautilus_trader.git", branch = "develop" }
nautilus-model = { git = "https://github.com/nautechsystems/nautilus_trader.git", branch = "develop", features = ["stubs"] }
nautilus-trading = { git = "https://github.com/nautechsystems/nautilus_trader.git", branch = "develop", features = ["examples"] }
```

最低支持的 Rust 版本（MSRV）为 **1.95.0**。

### 特性开关

| 开关             | Crate               | 效果                                                          |
|------------------|---------------------|---------------------------------------------------------------|
| `high-precision` | `nautilus-model`    | 16 位定点精度（默认 9 位）。加密货币所需。                    |
| `stubs`          | `nautilus-model`    | 测试 instrument 桩件（`audusd_sim` 等）。                     |
| `examples`       | `nautilus-trading`  | 示例策略（`EmaCross`、`GridMarketMaker`）。                   |
| `streaming`      | `nautilus-backtest` | 通过 `BacktestNode` 进行基于 catalog 的数据流式处理。         |
| `defi`           | `nautilus-model`    | DeFi 数据类型。隐含启用 `high-precision`。                    |

:::tip
标准的 9 位精度可以处理大多数传统金融标的。
对于价格小数位数较多（例如 `0.00000001`）的加密货币场所，请启用 `high-precision`。
:::

## Actor

actor 接收市场数据、自定义数据/信号以及系统事件，但不管理订单。
实现 `DataActor` trait，并通过 `Deref`/`DerefMut` 将你的 struct 绑定到 `DataActorCore`。
你的 struct 还必须实现 `Debug`（这是通用 `Component` impl 所要求的）。
core 直接在你的 struct 上提供订阅方法、缓存访问和时钟访问。

### 处理方法

重写 `DataActor` trait 上的任意处理方法以接收对应的数据或事件。
所有处理方法都有默认的空实现，因此你只需重写所需的部分。

| 处理方法               | 接收                       |
|------------------------|---------------------------|
| `on_start`             | Actor 启动                 |
| `on_stop`              | Actor 停止                 |
| `on_quote`             | `QuoteTick`               |
| `on_trade`             | `TradeTick`               |
| `on_bar`               | `Bar`                     |
| `on_book_deltas`       | `OrderBookDeltas`         |
| `on_book`              | `OrderBook`（按间隔）      |
| `on_instrument`        | `InstrumentAny`           |
| `on_mark_price`        | `MarkPriceUpdate`         |
| `on_index_price`       | `IndexPriceUpdate`        |
| `on_funding_rate`      | `FundingRateUpdate`       |
| `on_option_greeks`     | `OptionGreeks`            |
| `on_option_chain`      | `OptionChainSlice`        |
| `on_instrument_status` | `InstrumentStatus`        |
| `on_order_filled`      | `OrderFilled`             |
| `on_order_canceled`    | `OrderCanceled`           |
| `on_time_event`        | `TimeEvent`               |

分步演练请参见 [Write an Actor (Rust)](../how_to/write_rust_actor.md) how-to 指南。
完整示例请参见 [`BookImbalanceActor`](https://github.com/nautechsystems/nautilus_trader/tree/develop/crates/trading/src/examples/actors/imbalance)。

## 策略

策略在 actor 的基础上增加了订单管理。同时实现 `DataActor`（用于数据处理）和 `Strategy`（用于访问 `StrategyCore`）。
`StrategyCore` 包装了 `DataActorCore`，并加入了 `OrderFactory`、`OrderManager` 和组合集成。

### 订单管理

`Strategy` trait 通过 `StrategyCore` 提供订单方法：

| 方法                  | 操作                                      |
|-----------------------|-------------------------------------------|
| `submit_order`        | 向场所提交新订单。                        |
| `submit_order_list`   | 提交一组连带订单。                        |
| `modify_order`        | 修改价格、数量或触发价。                  |
| `cancel_order`        | 撤销指定订单。                            |
| `cancel_orders`       | 撤销经过过滤的一组订单。                  |
| `cancel_all_orders`   | 撤销某个标的的所有订单。                  |
| `close_position`      | 通过市价单平仓。                          |
| `close_all_positions` | 平掉所有未平仓持仓。                      |

`OrderFactory`（通过 `self.core.order_factory()` 访问）构建订单对象：`market`、`limit`、
`stop_market`、`stop_limit`、`market_if_touched`、`limit_if_touched`、`trailing_stop_market`。

分步演练请参见 [Write a Strategy (Rust)](../how_to/write_rust_strategy.md) how-to 指南。
完整示例请参见
[`EmaCross`](https://github.com/nautechsystems/nautilus_trader/tree/develop/crates/trading/src/examples/strategies/ema_cross)
和 [`GridMarketMaker`](https://github.com/nautechsystems/nautilus_trader/tree/develop/crates/trading/src/examples/strategies/grid_mm)。

### 运行 Rust 组件

Rust 策略和 actor 可以通过三种方式运行。下面的示例使用策略，但 actor 可通过 `add_actor`（纯 Rust）和
`add_native_actor`（来自 Python）使用同样的模式。

#### 纯 Rust

用 Rust 编写策略和 `main` 函数，然后用 `cargo build` 构建独立二进制。该路径不需要 Python 运行时。

```rust
let strategy = GridMarketMaker::new(config);
node.add_strategy(strategy)?;
node.run().await?;
```

完整演练参见 [Run Live Trading (Rust)](../how_to/run_rust_live_trading.md)。

#### 来自 Python 的原生配置

将配置传给 `add_native_strategy` 即可从 Python 注册一个内置的 Rust 策略。
Rust 一侧构造策略并向引擎注册。Python 提供配置；所有执行都发生在 Rust 中。

```python
from nautilus_trader.core.nautilus_pyo3.trading import GridMarketMakerConfig

config = GridMarketMakerConfig(
    instrument_id=InstrumentId.from_str("BTC-USDT-SWAP.OKX"),
    max_position=Quantity.from_str("10.0"),
    trade_size=Quantity.from_str("0.1"),
    num_levels=5,
    grid_step_bps=15,
)

node.add_native_strategy(config)
```

内置策略配置：

| 配置                    | 策略                  |
|-------------------------|-----------------------|
| `EmaCrossConfig`        | `EmaCross`            |
| `GridMarketMakerConfig` | `GridMarketMaker`     |
| `DeltaNeutralVolConfig` | `DeltaNeutralVol`     |

内置 actor 配置（通过 `add_native_actor`）：

| 配置                       | Actor                 |
|----------------------------|-----------------------|
| `BookImbalanceActorConfig` | `BookImbalanceActor`  |

从源码编译的用户可以将自己的组件加入这条路径。添加一个 `#[pyclass]` 配置以及
`add_native_strategy` 或 `add_native_actor` 中的一个分发分支。
之后该组件无需在类型本身上添加 PyO3 包装器，即可在 Python 中使用。

#### 插件加载（计划中）

未来的插件系统将在运行时加载已编译的共享库。
用户将策略和 actor 编译为 `cdylib` crate，节点无需重新编译即可加载它们。该路径暂不可用。

## 回测

两种 API 的注释式演练请参见 [Run a Backtest (Rust)](../how_to/run_rust_backtest.md) how-to 指南。

### `BacktestEngine`（低层 API）

构造引擎、添加 venue 和 instrument、加载数据、注册策略，然后运行。完整的可运行示例：

```bash
cargo run -p nautilus-backtest --features examples --example engine-ema-cross
```

源码：[`crates/backtest/examples/engine_ema_cross.rs`](https://github.com/nautechsystems/nautilus_trader/tree/develop/crates/backtest/examples/engine_ema_cross.rs)

### `BacktestNode`（高层 API）

从 `ParquetDataCatalog` 加载数据，并支持以可配置的块大小流式读取。需要在 `nautilus-backtest` 上启用 `streaming` 特性。
完整的可运行示例：

```bash
cargo run -p nautilus-backtest --features examples,streaming --example node-ema-cross
```

源码：[`crates/backtest/examples/node_ema_cross.rs`](https://github.com/nautechsystems/nautilus_trader/tree/develop/crates/backtest/examples/node_ema_cross.rs)

## 实盘交易

注释式演练请参见 [Run Live Trading (Rust)](../how_to/run_rust_live_trading.md) how-to 指南。

`LiveNode` 通过适配器客户端连接真实场所。Builder 模式用于配置数据和执行客户端，然后 `run()` 启动异步事件循环。
每个适配器都提供自己的工厂和配置类型。

| 适配器         | 示例                                                     |
|----------------|----------------------------------------------------------|
| Architect AX   | `crates/adapters/architect_ax/examples/`                 |
| Betfair        | `crates/adapters/betfair/examples/`                      |
| Binance        | `crates/adapters/binance/examples/`                      |
| BitMEX         | `crates/adapters/bitmex/examples/`                       |
| Blockchain     | `crates/adapters/blockchain/examples/`                   |
| Bybit          | `crates/adapters/bybit/examples/`                        |
| Databento      | `crates/adapters/databento/examples/`                    |
| Deribit        | `crates/adapters/deribit/examples/`                      |
| dYdX           | `crates/adapters/dydx/examples/`                         |
| Hyperliquid    | `crates/adapters/hyperliquid/examples/`                  |
| Kraken         | `crates/adapters/kraken/examples/`                       |
| OKX            | `crates/adapters/okx/examples/`                          |
| Polymarket     | `crates/adapters/polymarket/examples/`                   |
| Sandbox        | `crates/adapters/sandbox/examples/`                      |
| Tardis         | `crates/adapters/tardis/examples/`                       |

大多数适配器包含 `node_data_tester.rs` 和 `node_exec_tester.rs` 示例。
它们针对真实场所测试数据请求、流式订阅和订单执行。

## 相关指南

- [Write an Actor (Rust)](../how_to/write_rust_actor.md) - 分步 actor 演练。
- [Write a Strategy (Rust)](../how_to/write_rust_strategy.md) - 分步策略演练。
- [Run a Backtest (Rust)](../how_to/run_rust_backtest.md) - BacktestEngine 与 BacktestNode 用法。
- [Run Live Trading (Rust)](../how_to/run_rust_live_trading.md) - LiveNode 设置与场所连接。
- [Architecture](architecture.md) - 系统设计与数据/执行流。
- [Actors](actors.md) - Actor 概念（同时适用于 Python 与 Rust）。
- [Strategies](strategies.md) - 策略概念与处理方法参考。
- [Events](events.md) - 事件类型与处理函数分发。
- [Backtesting](backtesting.md) - 回测概念与撮合引擎行为。
