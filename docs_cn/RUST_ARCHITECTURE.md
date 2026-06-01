# NautilusTrader Rust 架构分析文档

> 版本: v0.57.0 | Rust Edition: 2024 | MSRV: 1.95.0
>
> 本文档基于源码分析生成，涵盖所有 Rust 核心模块的功能、架构和协作流程。

---

## 目录

1. [项目概述](#1-项目概述)
2. [分层架构总览](#2-分层架构总览)
3. [核心模块详解](#3-核心模块详解)
4. [Adapter 适配器体系](#4-adapter-适配器体系)
5. [核心流程](#5-核心流程)
6. [模块依赖关系图](#6-模块依赖关系图)
7. [数据流全景](#7-数据流全景)
8. [构建与特性标志](#8-构建与特性标志)

---

## 1. 项目概述

NautilusTrader 是一个**生产级、Rust 原生的多资产多交易所交易引擎**，采用**确定性事件驱动架构**。

### 核心设计理念

| 特性 | 说明 |
|------|------|
| **确定性模拟** | 回测和实盘使用完全相同的事件驱动路径，保证语义一致性（research-to-live parity） |
| **零成本抽象** | Rust 的类型系统在编译期保证安全，运行时无额外开销 |
| **高精度模式** | 可选 128-bit 精度（`high-precision` feature），适合加密货币等高精度场景 |
| **Python 绑定** | 通过 PyO3 暴露完整 API，支持 Python 策略 + Rust 引擎的混合架构 |
| **C FFI** | 通过 cbindgen 导出 C 接口，支持 Cython/其他语言的集成 |
| **多资产** | 股票、期货、期权、加密货币、DeFi 全覆盖 |
| **多交易所** | 内置 17 个交易所/数据源适配器 |

### 技术栈

- **异步运行时**: Tokio（多线程）
- **序列化**: Cap'n Proto + Apache Arrow + Serde
- **持久化**: Parquet (DataFusion) + Redis + redb
- **网络**: reqwest (HTTP) + tokio-tungstenite (WebSocket) + rustls (TLS)
- **数据库**: PostgreSQL (sqlx)
- **Python 绑定**: PyO3 + pyo3-async-runtimes

---

## 2. 分层架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                    应用层 (Application Layer)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │   CLI    │  │   PyO3   │  │   Live   │  │   Backtest   │    │
│  │  命令行  │  │ Python绑 │  │  实盘运行 │  │   回测引擎   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                    系统层 (System Layer)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              System (内核/编排/Trader管理)                 │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                    业务层 (Business Layer)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ Trading  │  │   Data   │  │Execution │  │   Portfolio  │    │
│  │ 策略/算法 │  │ 数据引擎 │  │ 执行引擎 │  │   投资组合   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
│  ┌──────────┐  ┌──────────┐                                    │
│  │   Risk   │  │ Analysis │                                    │
│  │ 风控引擎 │  │  分析统计 │                                    │
│  └──────────┘  └──────────┘                                    │
├─────────────────────────────────────────────────────────────────┤
│                    基础层 (Infrastructure Layer)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │  Common  │  │ Network  │  │Persistence│ │Serialization │    │
│  │ 公共组件 │  │  网络层  │  │  持久化   │  │   序列化     │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │  Model   │  │   Core   │  │Crypto-   │  │ EventStore   │    │
│  │ 领域模型 │  │  核心类型 │  │ graphy   │  │  事件存储    │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块详解

### 3.1 `nautilus-core` — 核心基础类型

> **路径**: `crates/core/ | **依赖**: 无内部依赖（最底层）

**功能**: 提供整个框架的基础构建块。

| 组件 | 说明 |
|------|------|
| `datetime` | 时间处理（Unix 纳秒时间戳、UTC 转换） |
| `nanos` | 纳秒精度时间戳类型 |
| `uuid` | UUID v4 生成和管理 |
| `math` | 数学函数和插值工具 |
| `correctness` | 正确性校验函数（参数检查、不变量断言） |
| `collections` | 高性能集合类型抽象 |
| `serialization` | 序列化 trait 和辅助函数 |
| `hex` | 十六进制编解码 |
| `message` | 消息类型定义 |
| `paths` | 跨平台路径工具 |
| `env` | 环境变量工具 |
| `ffi/` | C FFI 绑定（字符串、时间、UUID 转换） |
| `python/` | Python 绑定（PyO3 类型转换） |

**关键设计**: 零依赖、零成本抽象。所有其他模块都依赖此 crate。

---

### 3.2 `nautilus-model` — 交易领域模型

> **路径**: `crates/model/` | **依赖**: `nautilus-core`

**功能**: 类型安全的交易领域模型，是整个框架的骨干。

#### 子模块结构

```
model/
├── accounts/        # 账户模型
│   ├── base.rs      # 账户基类
│   ├── cash.rs      # 现金账户
│   ├── margin.rs    # 保证金账户
│   └── betting.rs   # 投注账户（Betfair）
├── data/            # 市场数据模型
│   ├── bar.rs       # K线（OHLCV）
│   ├── quote.rs     # 报价（Bid/Ask）
│   ├── trade.rs     # 成交记录
│   ├── depth.rs     # 订单簿深度
│   ├── prices.rs    # 价格快照
│   ├── order.rs     # 订单簿委托
│   ├── greeks.rs    # 期权 Greeks
│   ├── delta.rs     # Delta 值
│   ├── black_scholes.rs # Black-Scholes 模型
│   ├── option_chain.rs  # 期权链
│   └── custom.rs    # 自定义数据类型
├── defi/            # DeFi 模型
│   ├── amm.rs       # AMM（自动做市商）
│   └── ...
├── enums/           # 枚举定义
├── events/          # 事件定义
├── identifiers/     # 标识符类型
├── instruments/     # 金融工具
│   ├── any.rs       # 工具统一类型
│   ├── equity.rs    # 股票
│   ├── futures.rs   # 期货
│   ├── option.rs    # 期权
│   └── crypto.rs    # 加密货币
├── orders/          # 订单模型
│   ├── any.rs       # 订单统一类型
│   ├── market.rs    # 市价单
│   ├── limit.rs     # 限价单
│   ├── stop.rs      # 止损单
│   └── ...
├── positions/       # 持仓模型
├── strategies/      # 策略基类
├── currencies.rs    # 货币定义
├── types/           # 值对象
│   ├── price.rs     # 价格（固定精度）
│   ├── quantity.rs  # 数量
│   ├── money.rs     # 货币金额
│   └── currency.rs  # 货币类型
└── venues/          # 交易所/场所定义
```

#### 核心类型

| 类型 | 说明 |
|------|------|
| `Price` | 固定精度价格（支持 64-bit 和 128-bit 模式） |
| `Quantity` | 固定精度数量 |
| `Money` | 货币金额（带币种） |
| `InstrumentAny` | 金融工具统一枚举（股票/期货/期权/加密货币等） |
| `OrderAny` | 订单统一枚举（市价/限价/止损等） |
| `Bar` | K线数据（OHLCV + 时间戳） |
| `QuoteTick` | 报价 Tick（Bid/Ask 价格和数量） |
| `TradeTick` | 成交 Tick |
| `OrderBookDelta` | 订单簿增量 |
| `Instrument` | 各类金融工具定义 |
| `Account` | 各类账户定义 |
| `Position` | 持仓 |

**关键设计**: 使用 `enum_dispatch` 实现零开销多态，避免 `dyn Trait` 的运行时开销。

---

### 3.3 `nautilus-common` — 公共组件

> **路径**: `crates/common/` | **依赖**: `nautilus-core`, `nautilus-model`

**功能**: 提供所有业务层模块共享的基础设施组件。

| 组件 | 说明 |
|------|------|
| `cache/` | **缓存系统** — 内存中存储所有领域对象的索引和引用 |
| `clock` | **时钟** — 可控时间源（实盘用系统时钟，回测用模拟时钟） |
| `actor/` | **Actor 模型** — 数据 Actor、指标 Actor、注册表 |
| `clients/` | **客户端抽象** — 数据客户端和执行客户端的 trait |
| `component/` | **组件基类** — 所有引擎组件的基础 trait |
| `factories/` | **工厂模式** — 订单工厂、事件工厂、客户端工厂 |
| `enums/` | **枚举** — 组件状态、运行模式等 |
| `defi/` | **DeFi 支持** — DeFi 缓存、数据 Actor |

#### Cache 子系统（关键）

```
cache/
├── config.rs      # 缓存配置（数据库支持）
├── database.rs    # redb 持久化缓存
├── fifo.rs        # FIFO 队列（用于订单簿维护）
├── index.rs       # 多维索引（按品种/交易所/策略等快速查询）
├── quote.rs       # 报价缓存
└── refs.rs        # 对象引用管理
```

Cache 是整个系统的**状态中心**，存储所有活跃的订单、持仓、账户、工具等信息。

---

### 3.4 `nautilus-system` — 系统编排

> **路径**: `crates/system/` | **依赖**: 几乎所有业务层模块

**功能**: 顶层编排器，管理整个交易系统的生命周期。

| 组件 | 说明 |
|------|------|
| `kernel.rs` | **内核** — 事件循环和消息调度 |
| `controller.rs` | **控制器** — 管理数据/执行引擎的启停 |
| `builder.rs` | **构建器** — 组装整个系统的各组件 |
| `trader.rs` | **Trader** — 交易员实例（包含策略集合） |
| `config.rs` | 系统级配置 |
| `registration/` | 组件注册机制 |
| `messages/` | 控制器消息协议 |
| `event_store.rs` | 事件存储接口 |

#### 系统启动流程

```
SystemBuilder::build()
    ├── 创建 TestClock（回测）或 LiveClock（实盘）
    ├── 创建 MessageBus（消息总线）
    ├── 创建 Cache（状态缓存）
    ├── 创建 DataEngine → 注册 DataClient
    ├── 创建 ExecutionEngine → 注册 ExecutionClient
    ├── 创建 RiskEngine → 连接 ExecutionEngine
    ├── 创建 Portfolio → 订阅事件
    ├── 创建 TradingNode → 注册 Strategies
    └── 创建 TradingStateController → 管理启停
```

---

### 3.5 `nautilus-trading` — 策略与算法

> **路径**: `crates/trading/` | **依赖**: `nautilus-common`, `nautilus-model`, `nautilus-execution`, `nautilus-portfolio`

**功能**: 策略框架和算法交易。

| 组件 | 说明 |
|------|------|
| `strategy/` | **策略基类** — 所有用户策略的抽象基类 |
| `algorithm/` | **算法引擎** — TWAP 等执行算法 |
| `sessions/` | **交易会话** — 管理策略的生命周期 |
| `macros.rs` | **宏** — 简化策略定义 |

#### 策略生命周期

```
Strategy::on_start()     → 策略启动，注册数据订阅
Strategy::on_bar()       → 收到 K 线回调
Strategy::on_quote_tick() → 收到报价回调
Strategy::on_trade_tick() → 收到成交回调
Strategy::on_order_filled() → 订单成交回调
Strategy::on_stop()      → 策略停止
```

---

### 3.6 `nautilus-data` — 数据引擎

> **路径**: `crates/data/` | **依赖**: `nautilus-common`, `nautilus-model`

**功能**: 管理市场数据的订阅、分发和处理。

| 组件 | 说明 |
|------|------|
| `engine/` | **数据引擎核心** |
| ├── `mod.rs` | 引擎主体（注册/取消订阅） |
| ├── `bar.rs` | K 线聚合和管理 |
| ├── `book.rs` | 订单簿管理 |
| ├── `commands.rs` | 命令处理 |
| ├── `handlers.rs` | 事件处理器 |
| ├── `pool.rs` | 对象池（减少分配） |
| └── `streaming.rs` | 流式数据处理 |
| `aggregation.rs` | **K 线聚合器**（Tick → Bar 转换） |
| `option_chains/` | **期权链管理** |
| ├── `manager.rs` | 期权链管理器 |
| ├── `aggregator.rs` | 期权数据聚合 |
| └── `atm_tracker.rs` | ATM 期权追踪 |
| `client.rs` | 数据客户端 trait |
| `defi/` | DeFi 数据引擎 |

#### 数据流

```
DataClient（交易所/数据源）
    ↓ 订阅响应
DataEngine
    ├── 分发给订阅者（策略/指标Actor）
    ├── K线聚合（Tick → Bar）
    ├── 订单簿维护
    └── 写入 Cache
```

---

### 3.7 `nautilus-execution` — 执行引擎

> **路径**: `crates/execution/` | **依赖**: `nautilus-common`, `nautilus-model`

**功能**: 订单管理和执行，包含撮合引擎和订单模拟器。

| 组件 | 说明 |
|------|------|
| `engine/` | **执行引擎** — 接收订单请求，管理订单生命周期 |
| `order_manager/` | **订单管理器** — 处理订单状态转换 |
| `matching_engine/` | **撮合引擎** — 模拟交易所撮合（回测用） |
| `matching_core/` | **撮合核心** — 高性能撮合算法 |
| `order_emulator/` | **订单模拟器** — 模拟止损/止盈等条件单 |
| `models/` | **执行模型** |
| ├── `fee.rs` | 手续费模型 |
| ├── `fill.rs` | 成交模型 |
| └── `latency.rs` | 延迟模拟 |
| `protection.rs` | **保护机制** — 防止重复提交等 |
| `client/` | **执行客户端** — 连接交易所的抽象 |

#### 订单执行流程

```
Strategy.submit_order()
    → RiskEngine.accept()         // 风控检查
    → ExecutionEngine.submit()    // 提交到执行引擎
    → OrderManager.handle()       // 订单管理
    → ExecutionClient.submit()    // 发送到交易所
    → 订单状态更新事件
    → Strategy.on_order_filled()  // 回调策略
```

---

### 3.8 `nautilus-portfolio` — 投资组合

> **路径**: `crates/portfolio/` | **依赖**: `nautilus-common`, `nautilus-model`, `nautilus-analysis`

**功能**: 管理账户状态、持仓和投资组合指标。

| 组件 | 说明 |
|------|------|
| `portfolio.rs` | **投资组合** — 维护账户、持仓、净值的统一视图 |
| `manager.rs` | **管理器** — 处理事件更新（订单成交→持仓更新→净值计算） |
| `config.rs` | 配置 |

#### 核心功能

- 实时计算各币种余额
- 跟踪未实现/已实现盈亏
- 维护持仓状态
- 计算投资组合总净值
- 支持多账户、多币种

---

### 3.9 `nautilus-risk` — 风控引擎

> **路径**: `crates/risk/` | **依赖**: `nautilus-common`, `nautilus-model`, `nautilus-execution`, `nautilus-portfolio`

**功能**: 订单提交前的风控检查。

| 组件 | 说明 |
|------|------|
| `engine/` | **风控引擎** — 拦截和检查所有订单 |
| `sizing.rs` | **仓位管理** — 根据规则计算下单数量 |

#### 风控规则

- 最大订单数量检查
- 最大持仓检查
- 最大名义价值检查
- 交易频率限制
- 价格合理性检查（偏离市场价格检查）

---

### 3.10 `nautilus-backtest` — 回测引擎

> **路径**: `crates/backtest/` | **依赖**: 几乎所有模块

**功能**: 确定性历史数据回测。

| 组件 | 说明 |
|------|------|
| `engine.rs` | **回测引擎** — 主入口 |
| `exchange.rs` | **模拟交易所** — 撮合、延迟模拟 |
| `data_client.rs` | **回测数据客户端** — 从文件读取历史数据 |
| `execution_client.rs` | **回测执行客户端** — 模拟订单执行 |
| `data_iterator.rs` | **数据迭代器** — 按时间顺序遍历数据 |
| `accumulator.rs` | **累加器** — 收集回测结果 |
| `result.rs` | **回测结果** — 统计指标 |
| `node.rs` | **回环节点** — 可组合的回测单元 |
| `config.rs` | 回测配置 |
| `modules/` | 扩展模块（如 FX 隔夜利息） |

#### 回测流程

```
1. 加载历史数据（Parquet/CSV/自定义）
2. 创建 BacktestEngine
   ├── 初始化 DataEngine + BacktestDataClient
   ├── 初始化 ExecutionEngine + BacktestExecClient
   ├── 初始化 RiskEngine
   ├── 初始化 Portfolio
   └── 注册 Strategies
3. 按时间顺序重放数据
   ├── 逐条事件推进
   ├── 策略收到回调 → 生成信号 → 提交订单
   ├── 模拟交易所撮合
   └── 更新持仓和净值
4. 输出回测结果（统计报告）
```

---

### 3.11 `nautilus-indicators` — 技术指标库

> **路径**: `crates/indicators/` | **依赖**: `nautilus-core`, `nautilus-model`

**功能**: 高性能技术指标计算。

| 分类 | 指标 |
|------|------|
| **均线 (average/)** | SMA, EMA, DEMA, HMA, WMA, AMA, RMA, VWAP, VIDYA, LR |
| **动量 (momentum/)** | MACD, RSI, ROC, CMO, OBV, Aroon, CCI, DM, PSL, KVO |
| **波动率 (volatility/)** | ATR, BB (布林带), Keltner Channel |
| **订单簿 (book/)** | Imbalance (不平衡度) |

每个指标都实现 `Indicator` trait：

```rust
pub trait Indicator {
    fn handle_bar(&mut self, bar: &Bar);
    fn reset(&mut self);
    fn name(&self) -> &str;
    fn is_initialized(&self) -> bool;
}
```

---

### 3.12 `nautilus-analysis` — 分析统计

> **路径**: `crates/analysis/` | **依赖**: `nautilus-core`, `nautilus-model`

**功能**: 交易绩效分析和统计计算。

- 收益率计算
- 夏普比率、索提诺比率
- 最大回撤
- 胜率统计
- 年化指标

---

### 3.13 `nautilus-serialization` — 序列化

> **路径**: `crates/serialization/` | **依赖**: `nautilus-core`, `nautilus-model`

**功能**: 高性能序列化/反序列化。

| 格式 | 说明 |
|------|------|
| **Cap'n Proto** | 零拷贝二进制序列化（主要格式） |
| **Apache Arrow** | 列式内存格式（用于 Parquet 和 DataFusion） |
| **Serde** | JSON/TOML 等通用序列化 |
| **SBE** | Simple Binary Encoding（市场数据解码） |

---

### 3.14 `nautilus-persistence` — 持久化

> **路径**: `crates/persistence/` | **依赖**: `nautilus-serialization`, `nautilus-model`

**功能**: 数据的读写和持久化。

| 功能 | 说明 |
|------|------|
| **Parquet 读写** | 通过 DataFusion + Arrow 高效读写 Parquet 文件 |
| **流式加载** | 使用对象池减少内存分配 |
| **自定义数据** | 支持加载自定义 Parquet/CSV 数据 |
| **CSV 解析** | 支持 Databento 等 CSV 格式 |

支持的数据源：Parquet 文件、CSV 文件、自定义 reader。

---

### 3.15 `nautilus-event-store` — 事件存储

> **路径**: `crates/event_store/` | **依赖**: `nautilus-common`, `nautilus-system`

**功能**: 持久化存储系统事件，支持事件回放。

- 将交易事件序列化存储
- 支持按时间/类型查询
- 用于审计和故障恢复

---

### 3.16 `nautilus-network` — 网络层

> **路径**: `crates/network/` | **依赖**: `nautilus-core`, `nautilus-cryptography`, `nautilus-common`

**功能**: HTTP 和 WebSocket 通信基础设施。

| 组件 | 说明 |
|------|------|
| HTTP 客户端 | 基于 reqwest + rustls 的 HTTPS 客户端 |
| WebSocket 客户端 | 基于 tokio-tungstenite 的 WSS 客户端 |
| 限流器 | HTTP API 限流（令牌桶算法） |
| TLS 配置 | rustls 安全连接配置 |

---

### 3.17 `nautilus-cryptography` — 加密

> **路径**: `crates/cryptography/` | **依赖**: `nautilus-core`

**功能**: 加密和签名工具。

| 功能 | 说明 |
|------|------|
| HMAC 签名 | API 请求签名 |
| RSA/Ed25519 | 数字签名 |
| TLS 配置 | 安全通信证书管理 |
| 编解码 | Base64 等编解码 |

---

### 3.18 `nautilus-infrastructure` — 基础设施

> **路径**: `crates/infrastructure/` | **依赖**: `nautilus-common`, `nautilus-persistence`, `nautilus-serialization`

**功能**: 运行时基础设施，为实盘和回测提供共享的底层服务。

- 数据 catalog 管理
- 配置加载
- 环境初始化

---

### 3.19 `nautilus-live` — 实盘运行

> **路径**: `crates/live/` | **依赖**: 几乎所有模块（通过 feature flag 控制）

**功能**: 实盘交易运行的容器。

| 组件 | 说明 |
|------|------|
| `runner` | **运行器** — 启动实盘系统 |
| `manager` | **管理器** — 管理多个 TradingNode |
| `node` | **节点** — 单个实盘交易节点 |

通过 feature flag 控制可选依赖：`data`, `persistence`, `portfolio`, `risk`, `system`, `trading`。

---

### 3.20 `nautilus-pyo3` — Python 绑定

> **路径**: `crates/pyo3/` | **依赖**: 所有模块（Python feature）

**功能**: 将所有 Rust API 暴露给 Python。

- 使用 PyO3 为每个类型生成 Python 类
- 支持 Python asyncio 异步操作
- 通过 `pyo3-stub-gen` 生成类型提示（`.pyi` 文件）
- 编译为 `nautilus_trader` Python 包

---

### 3.21 `nautilus-testkit` — 测试工具

> **路径**: `crates/testkit/` | **依赖**: 多个模块

**功能**: 测试辅助工具。

- 测试数据管理（自动下载和缓存）
- 文件完整性校验（SHA-256）
- 预置 stub 数据（账户、订单等）
- 通用测试模式

---

### 3.22 `nautilus-cli` — 命令行工具

> **路径**: `crates/cli/`

**功能**: NautilusTrader 命令行工具。

---

## 4. Adapter 适配器体系

NautilusTrader 内置 17 个交易所/数据源适配器：

### 交易所适配器

| 适配器 | 类型 | 说明 |
|--------|------|------|
| `binance` | 加密货币 | 币安（现货/期货/COIN-m/USDT-m） |
| `bybit` | 加密货币 | Bybit |
| `okx` | 加密货币 | OKX |
| `coinbase` | 加密货币 | Coinbase |
| `deribit` | 加密货币期权 | Deribit |
| `dydx` | DeFi | dYdX |
| `hyperliquid` | 加密货币 | Hyperliquid |
| `kraken` | 加密货币 | Kraken |
| `bitmex` | 加密货币期货 | BitMEX |
| `polymarket` | 预测市场 | Polymarket |
| `betfair` | 博彩交易所 | Betfair |
| `interactive_brokers` | 传统金融 | 盈透证券 |
| `blockchain` | 链上 | 区块链节点交互 |

### 数据源适配器

| 适配器 | 说明 |
|--------|------|
| `databento` | Databento 市场数据 |
| `tardis` | Tardis.dev 历史数据 |
| `sandbox` | 测试用模拟适配器 |
| `architect_ax` | Architect.ai 数据服务 |

---

## 5. 核心流程

### 5.1 回测流程

```
┌──────────────────────────────────────────────────────────────────┐
│                        回测流程                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  1. 配置阶段                                                      │
│     BacktestConfig                                                 │
│     ├── trading_node: Strategy列表                                 │
│     ├── venues: 模拟交易所配置                                     │
│     ├── data_clients: 数据源配置                                   │
│     └── data: 历史数据目录/文件                                    │
│                                                                    │
│  2. 构建阶段                                                      │
│     BacktestEngine::new(config)                                    │
│     ├── 创建 TestClock（可控时间）                                  │
│     ├── 创建 MessageBus                                            │
│     ├── 创建 Cache                                                 │
│     ├── 创建 DataEngine + BacktestDataClient                       │
│     ├── 创建 ExecutionEngine + BacktestExecClient                  │
│     │   └── 挂载 MatchingEngine（撮合引擎）                        │
│     ├── 创建 RiskEngine                                            │
│     ├── 创建 Portfolio                                             │
│     └── 创建 TradingNode + 注册 Strategies                        │
│                                                                    │
│  3. 数据加载                                                      │
│     PersistenceEngine                                              │
│     └── 从 Parquet/CSV 加载 → 数据迭代器                           │
│                                                                    │
│  4. 事件循环                                                      │
│     ┌─────────────────────────────────────┐                       │
│     │  for event in data_iterator:         │                       │
│     │    clock.set_time(event.ts_event)    │  ← 推进时间           │
│     │    DataEngine.process(event)         │  ← 处理数据           │
│     │    → Strategy.on_bar/on_tick()       │  ← 策略回调           │
│     │    → Strategy.submit_order()         │  ← 提交订单           │
│     │    → RiskEngine.check()              │  ← 风控检查           │
│     │    → ExecutionEngine.submit()        │  ← 执行引擎           │
│     │    → MatchingEngine.match()          │  ← 撮合               │
│     │    → OrderFilled 事件                │                        │
│     │    → Portfolio.update()              │  ← 更新持仓           │
│     └─────────────────────────────────────┘                       │
│                                                                    │
│  5. 结果输出                                                      │
│     BacktestResult                                                 │
│     ├── 总收益率、年化收益率                                       │
│     ├── 最大回撤、夏普比率                                         │
│     ├── 胜率、盈亏比                                               │
│     └── 交易记录                                                   │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 实盘流程

```
┌──────────────────────────────────────────────────────────────────┐
│                        实盘流程                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  1. 连接阶段                                                      │
│     LiveNode                                                       │
│     ├── 连接 DataClient（WebSocket/REST）                          │
│     ├── 连接 ExecClient（WebSocket/REST）                          │
│     ├── 认证签名（nautilus-cryptography）                          │
│     └── 订阅市场数据                                               │
│                                                                    │
│  2. 数据流                                                        │
│     交易所 WebSocket                                               │
│     → Network（WSS 解析）                                          │
│     → DataClient（协议解码）                                       │
│     → DataEngine（分发）                                           │
│     → Strategy.on_bar/on_tick()（策略处理）                        │
│                                                                    │
│  3. 交易流                                                        │
│     Strategy 生成信号                                              │
│     → Strategy.submit_order()                                      │
│     → RiskEngine.accept()（风控）                                  │
│     → ExecutionEngine.submit()（执行）                             │
│     → ExecClient.submit_order()（发送到交易所）                    │
│     → 交易所确认                                                   │
│     → ExecutionEngine 处理确认                                     │
│     → Portfolio 更新                                               │
│     → Strategy.on_order_filled()（回调）                          │
│                                                                    │
│  4. 持久化                                                        │
│     EventStore → 持久化所有交易事件                                │
│     Cache → 内存中维护实时状态                                     │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 5.3 事件驱动架构

```
                    ┌─────────────┐
                    │  MessageBus  │  ← 消息总线（发布/订阅）
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                   │
   ┌────▼────┐       ┌─────▼─────┐      ┌─────▼─────┐
   │ Data    │       │ Execution │      │ Portfolio │
   │ Engine  │       │ Engine    │      │           │
   └────┬────┘       └─────┬─────┘      └─────┬─────┘
        │                  │                   │
   ┌────▼────┐       ┌─────▼─────┐      ┌─────▼─────┐
   │Strategy │       │ Risk      │      │ Analysis  │
   │(N个)    │       │ Engine    │      │           │
   └─────────┘       └───────────┘      └───────────┘
```

**事件类型**:
- `DataEvent` — 市场数据（Bar、QuoteTick、TradeTick）
- `OrderEvent` — 订单状态变更
- `PositionEvent` — 持仓变更
- `AccountEvent` — 账户状态变更
- `SystemEvent` — 系统状态变更

---

## 6. 模块依赖关系图

```
                    ┌─────────┐
                    │  core   │ ← 无内部依赖
                    └────┬────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
     ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐
     │  model  │   │    core   │  │cryptography│
     └────┬────┘   │ (已展开)  │  └────┬────┘
          │        └───────────┘       │
          │                            │
     ┌────▼────────────────────────────▼────┐
     │              common                  │
     │  (cache, clock, actor, clients)      │
     └────┬───────┬───────┬───────┬────────┘
          │       │       │       │
     ┌────▼──┐ ┌──▼──┐ ┌──▼──┐ ┌─▼────────┐
     │ data  │ │exec │ │trade│ │ indicators│
     └────┬──┘ └──┬──┘ └──┬──┘ └────┬─────┘
          │       │       │         │
          │  ┌────▼──┐    │    ┌────▼────┐
          │  │ risk  │    │    │analysis │
          │  └───┬───┘    │    └────┬────┘
          │      │        │         │
          │  ┌───▼────────▼─────────▼──┐
          │  │       portfolio          │
          │  └───────────┬─────────────┘
          │              │
     ┌────▼──────────────▼─────┐
     │         system           │ ← 顶层编排
     └────┬────────────────┬───┘
          │                │
     ┌────▼────┐     ┌─────▼────┐
     │backtest │     │   live   │
     └─────────┘     └──────────┘
          │                │
          └───────┬────────┘
                  │
            ┌─────▼─────┐
            │   pyo3     │ ← Python 绑定
            └───────────┘
```

### 辅助模块依赖

```
persistence → serialization, model
network → core, cryptography, common
infrastructure → common, persistence, serialization
event_store → common, execution, system
testkit → common, model, network, portfolio, trading
```

---

## 7. 数据流全景

### 7.1 市场数据流

```
[外部数据源]
     │
     ├── Parquet 文件 ──→ PersistenceEngine ──→ 数据迭代器
     ├── REST API ──────→ Network(HTTP) ──→ DataClient
     └── WebSocket ─────→ Network(WSS) ──→ DataClient
                                                    │
                                              DataEngine
                                             ┌──┴──┬──┐
                                             │     │  │
                                         Strategy Cache Indicator
                                           │              │
                                        信号生成      指标计算
```

### 7.2 交易数据流

```
Strategy.submit_order()
        │
    RiskEngine ──→ 检查通过/拒绝
        │
    ExecutionEngine
        │
    ┌───┴────────────┐
    │                │
BacktestExec    LiveExecClient
(模拟撮合)      (发送到交易所)
    │                │
    MatchingEngine   交易所API
    │                │
    OrderFilled 事件回调
    │
    Portfolio 更新
    │
    Strategy.on_order_filled()
```

---

## 8. 构建与特性标志

### Feature Flags

| Feature | 说明 |
|---------|------|
| `python` | 启用 PyO3 Python 绑定 |
| `ffi` | 启用 C FFI（cbindgen） |
| `arrow` | 启用 Apache Arrow 支持 |
| `python-arrow` | Python + PyArrow |
| `stubs` | 启用测试 stub 数据 |
| `high-precision` | 128-bit 精度模式 |
| `defi` | 启用 DeFi 域模型 |
| `live` | 启用实盘交易功能 |
| `extension-module` | 编译为 Python 扩展模块 |

### 编译 Profile

| Profile | 用途 | opt-level | debug | LTO |
|---------|------|-----------|-------|-----|
| `dev` | 开发 | 0 | false | false |
| `test` | 测试 | 0 | true | false |
| `release` | 生产 | 3 | false | fat |
| `bench` | 基准测试 | 3 | full | false |

---

> 本文档基于 NautilusTrader v0.57.0 源码分析生成，如有更新请参考源码。