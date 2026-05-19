# DST

> 本文档为 [English 原文](../../docs/concepts/dst.md) 的中文翻译版本。如有歧义请以英文原版为准。

**确定性模拟测试（DST，Deterministic simulation testing）** 在受种子控制的运行时下运行 NautilusTrader，
使时序敏感的执行行为可由一个整数比特级复现。本指南解释什么是 DST、NautilusTrader 如何支持它、
该支持提供的保证以及保证在哪里终止。

目标是提供一个可被外部用户和审计者验证的公开契约：NautilusTrader 所声明的确定性
由源码级证据支撑，并在提交时由 pre-commit 钩子（同样在 CI 中运行）强制执行。

## 简介

### 什么是 DST

DST 是面向并发系统的测试技术。单个种子完全决定一次执行，包括任务调度、定时器触发和随机值。
在相同种子、相同二进制、相同配置下的两次运行产生完全相同的可观测行为。
当某个属性失败时，种子就是复现：同一种子每次都重放相同失败。

异步运行时的调度决策来自环境进程状态：任务唤醒顺序、定时器分辨率、线程调度、哈希种子。
这些都不在测试框架的控制之下，因此 CI 中偶发的竞态条件通常难以按需复现。
DST 用一个种子伪随机序列替换上述环境源，使得交错成为种子的函数。

FoundationDB 大约从 2009 年起将该模式应用于一个生产级分布式数据库；
在 Rust 生态中，[madsim](https://github.com/madsim-rs/madsim) 拦截 `tokio` 原语以提供确定性调度器。

DST 针对的 bug 是那些逃过单元、集成、属性和验收测试的：通道唤醒顺序、关停时的 drain 竞态、
启动时序、对账顺序、恢复路径正确性。这些都涉及其他测试层无法穷举覆盖的交错，
而确定性调度器可以系统性地探索。

### 本指南的范围

NautilusTrader 的 DST 支持分两部分：

- **契约**：运行时在受种子控制执行下保证什么，以及在哪些条件下保证。
- **强制实施**：实现契约的源码级缝隙，以及让其保持稳固的 pre-commit 钩子。

## 目标

- 对 NautilusTrader 运行时的范围内部分提供**种子可复现执行**。
- **如实声明范围**。契约列出覆盖了什么、未覆盖什么。不悄悄回退到真实墙钟时间或未播种的 RNG；
  明确列举会弱化保证的条件。
- **在源码中强制实施**。pre-commit 钩子拒绝在 DST 路径上添加被禁止模式的提交，
  让契约不依赖审阅者注意力即可保持真实。
- **最少必要的插桩**。这些缝隙仅在契约要求的位置把时间、任务调度和随机性引导到确定性源；其余保持不变。

## 方法

`madsim` 只让通过其别名子模块（`time`、`task`、`runtime`、`signal`）路由的 `tokio` 原语具有确定性。
墙钟读取、单调读取、RNG 抽样、哈希迭代和 `select!` 轮询完全绕过 `tokio`，需要各自的缝隙。
Layer 1 将这些别名子模块替换为 `madsim`；Layer 2 提供其他缝隙。

### Layer 1：运行时替换

在 `nautilus-common` 的 `simulation` Cargo 特性下，当设置 `RUSTFLAGS="--cfg madsim"` 时，
四个 `tokio` 子模块通过 `madsim` 路由：

- `time`（定时器、interval、单调 `Instant`）。
- `task`（生成与 join 异步任务）。
- `runtime`（runtime builder 与 handle）。
- `signal`（进程信号如 `ctrl_c`；re-export 可用，调用点适配部分完成，详见
  [范围边界](#signal-handling)）。

这些 re-export 位于 `nautilus_common::live::dst`。DST 路径上 `time`、`task`、`runtime`
的调用点从该模块导入，而不是直接从 `tokio` 导入，这样切换特性就能在单一位置切换异步运行时
（对于已完全路由的原语）。普通构建下，re-export 解析到真实 `tokio`。
在 `simulation` + `cfg(madsim)` 下，它们解析到 `madsim` 的确定性对应物。

`tokio` 提供的其余部分（`sync`、`io`、作为宏的 `select!`、`fs`、`net`）在所有情况下都使用真实 `tokio`。
传递依赖的 crate（`tokio-tungstenite`、`tokio-rustls`、`reqwest`）不受影响。

### Layer 2：非确定性替换

异步运行时之外的非确定性通过显式缝隙重定向：

- **墙钟读取**通过 `nautilus_core::time::duration_since_unix_epoch`。模拟下路由至
  `madsim::time::TimeHandle::try_current()`，保留订单和成交时间戳的 Unix 纪元语义。
  当在 madsim 运行时之外调用时（普通 `#[rstest]` 测试体），它回退到 `SystemTime::now()`，
  在 `cfg(madsim)` 下由 libc 拦截到与普通构建相同的真实系统调用。
  模拟下的生产路径总是在运行时内运行，因此持续接收虚拟时间。
- **单调读取**通过 `nautilus_common::live::dst::time::Instant`。该类型在普通构建中解析为
  `tokio::time::Instant`（与 `tokio::test(start_paused)` 测试辅助函数兼容），
  在模拟下解析为 `madsim::time::Instant`。
- **网络本地的单调读取**通过 `nautilus_network::dst::time`。该 crate 在依赖图中位于 `nautilus-common`
  之下，并暴露具有相同语义的本地 re-export 模块。
- **对账管理器和订单撮合引擎中的哈希迭代顺序**使用 `IndexMap` 与 `IndexSet`，而非
  `AHashMap` 与 `AHashSet`。`AHash` 按进程随机化其 hasher；在顺序驱动下游事件发布或
  种子 `FillModel` RNG 消费顺序的位置需要插入顺序迭代。
- **`tokio::select!` 轮询顺序**在 DST 路径上的每个生产位置都使用 `biased;` 修饰符。
  非偏置的 `select!` 按未被拦截的 RNG 决定的顺序轮询分支。

## 确定性契约

在下列条件下，由 `(seed, binary hash, configuration hash)` 标识的一次运行在同一平台上产生比特级一致的：

1. 异步任务的调度顺序。
2. 定时器触发（虚拟单调与虚拟墙钟）。
3. 来自 `madsim::rand` 的 RNG 输出。
4. `tokio` 原语上的通道投递顺序。

### 必要条件

契约仅在以下全部为真时成立：

1. `simulation` Cargo 特性启用且设置 `RUSTFLAGS="--cfg madsim"`。两者缺一不可。
   特性激活确定性运行时；cfg 标志激活 `madsim` 的 libc 级 `clock_gettime` 与 `getrandom` 拦截。
   只设置其中一个会悄悄回退到真实 `tokio` 且不报错，导致确定性失效。
2. DST 路径上每个 `tokio::select!` 调用位置都使用 `biased;` 修饰符。
3. 单调时间读取通过 DST 缝隙路由（`nautilus_common::live::dst::time` 或
   `nautilus_network::dst::time`），而不是直接 `std::time::Instant::now`。
4. 墙钟时间读取通过 `nautilus_core::time::duration_since_unix_epoch`。
5. 随机性通过 `madsim::rand` 路由。`rand::thread_rng`、`rand::rng()`、`fastrand`、`getrandom`、
   `OsRng` 都不会被拦截。
6. 迭代顺序敏感的集合使用 `IndexMap` 或 `IndexSet`，而非 `AHashMap` 或 `AHashSet`。
7. `tokio::task::LocalSet` 构造在模拟下通过 cfg 排除。`madsim` 不提供 `LocalSet`；
   `spawn_local` 无需它即可工作。
8. `tokio::task::spawn_blocking` 调用位置被 cfg 排除或移除。阻塞调用会逃离确定性调度器。

## 静态强制实施

名为 `check-dst-conventions` 的 pre-commit 钩子在源码中强制结构性条件。
钩子位于 `.pre-commit-hooks/check_dst_conventions.sh`，作为标准 pre-commit 套件的一部分运行，
也在持续集成中运行。它覆盖 16 个在范围内的 workspace crate，
当检测到以下任意情况时使提交失败：

- 原始的 `std::time::Instant::now()` 或 `SystemTime::now()` 读取，
  包括当包含的文件从 `std::time` 导入该类型时的裸调用形式。
- 未经 cfg 限制的原始 RNG 使用（`rand::thread_rng`、`rand::rng()`、`fastrand::`、`getrandom::`、`OsRng`）。
- `tokio::select!` 块前三行缺失 `biased;`。
- `std::thread::spawn`、`std::thread::Builder::new` 或 `tokio::task::spawn_blocking` 调用
  之前缺少 `#[cfg(test)]`、`#[cfg(not(madsim))]` 或 `#[cfg(not(all(feature = "simulation", madsim)))]` 属性。
- DST 路径上迭代顺序敏感文件中的 `AHashMap` 或 `AHashSet`。完整文件集合在审查中；
  当前强制覆盖 `crates/live/src/manager.rs` 与 `crates/execution/src/matching_engine/engine.rs`，
  并随更多文件被审查而扩展。
- 直接的 `tokio::net::TcpStream::connect` / `tokio::net::TcpListener::bind` 调用绕过
  `nautilus_network::net`。该缝隙在普通构建下 re-export `tokio::net` 类型，
  在 `turmoil` 特性下切换到 `turmoil::net`，因此所有 TCP 入口共享单一 cfg 限制的切换点。

钩子支持两种例外形式：

- 特定行的内联 `// dst-ok` 标记，通常附带简短理由
  （例如：只影响日志输出、不影响状态的墙钟计时）。
- 钩子脚本自身的一小份文件级允许列表，用于代码库审计中归类为"维持现状"的位置
  （缓存模块的日志计时、DeFi 模块的进度报告）。

测试文件、`tests/`、`python/`、`ffi/` 目录下的文件，以及位于内联 `#[cfg(test)]` 模块内的行被排除，
因为它们不在 DST 路径上。

### 范围内的 crate

钩子作用于 `nautilus-live` 传递闭包内的 16 个 workspace crate：

- `analysis`、`common`、`core`、`cryptography`、`data`、`execution`、`indicators`、`live`、
  `model`、`network`、`persistence`、`portfolio`、`risk`、`serialization`、`system`、`trading`。

适配器 crate 与基础设施 crate（Redis、Postgres）不在范围内。
它们进入 DST 路径前需要独立审计 DST 适配性。

## 实现笔记

本仓库中 DST 审计产出的具体改动。调查某代码路径是否在 DST 路径上以及当前如何路由时，从此处开始。

### 迭代顺序缝隙

DST 路径上迭代顺序可观测，从而把 `AHashMap` / `AHashSet` 切换为 `IndexMap` / `IndexSet` 的生产位置：

- **撮合引擎**（`crates/execution/src/matching_engine/engine.rs`）：九个字段
  （`execution_bar_types`、`execution_bar_deltas`、`account_ids`、`cached_filled_qty`、
  `bid_consumption`、`ask_consumption`、`queue_ahead`、`queue_excess`、`queue_pending`）。
  迭代时的移除使用 `.shift_remove()`。关闭
  [#3914](https://github.com/nautechsystems/nautilus_trader/issues/3914)。
- **对账管理器**（`crates/live/src/manager.rs`）：钩子强制，再加上
  `ReconciliationResult.orders` 与 `ReconciliationResult.fills`。
- **Account trait**（`crates/model/src/accounts/`）：`balances`、`balances_total`、
  `balances_free`、`balances_locked`、`starting_balances` 返回值。`BaseAccount`
  与 `MarginAccount` 上的存储字段为 `IndexMap`。
- **持仓事件**（`crates/model/src/position.rs`）：`Position::commissions` 切换为 `IndexMap`
  （在 `events/position/snapshot.rs` 中通过 `.values()` 消费）。
- **组合聚合**（`crates/portfolio/src/portfolio.rs`）：`unrealized_pnls`、`realized_pnls`、
  `net_positions` 存储；`accumulate_mark_values` 构建 `IndexMap<Currency, f64>`。
- **数据引擎**（`crates/data/src/engine/`）：`book_snapshot_counts`、`bar_aggregators`、
  `BookSnapshotInfos`。迭代时移除使用 `.shift_remove()`。
- **执行引擎**（`crates/execution/src/engine/`）：`ExecutionEngine.clients`，
  加上 `get_clients_for_orders()` 中的 `client_ids` / `venues` 累加器。
- **交易算法**（`crates/trading/src/algorithm/core.rs`）：`strategy_event_handlers`
  （驱动有序 `msgbus::unsubscribe_*` 扇出）。
- **分析器**（`crates/analysis/src/analyzer.rs`）：`account_balances`、`account_balances_starting`。
- **Cache API**（`crates/common/src/cache/mod.rs`）：`get_orders_for_ids` 与
  `get_positions_for_ids` 在返回前按 `client_order_id` / `position_id` 对其 `Vec` 返回值排序。
  存储保留为 `AHashSet`（集合语义）。

范围内 crate 的其余 `AHashMap` / `AHashSet` 位置要么仅用于查找，要么位于并发共享所有权包装
（`Arc<DashMap>`、`AtomicMap`）之后，要么进入交换聚合。任何驱动可观测迭代顺序的新范围内位置
都是退化，按区域审计加以防范。

### 时间缝隙

仍在 DST 路径上的 `Instant::now` / `SystemTime::now` 调用位置要么位于 `#[cfg(test)]`、
要么列入钩子文件允许名单、要么带有内联 `// dst-ok` 标记与理由：

- `crates/common/src/testing.rs:81,108` `wait_until` / `wait_until_async`
- `crates/execution/src/engine/mod.rs:822,847` 初始化日志计时
- `crates/common/src/cache/mod.rs:569,904,3895` 日志与审计计时（文件允许）
- `crates/model/src/defi/reporting.rs:59,123` 进度日志（文件允许）
- `crates/core/src/time.rs` 缝隙定义位置（文件允许）

`chrono::Utc::now` 在范围内 crate 中被钩子禁用。剩余调用位置是日志桥与写入器
（"日志运行在真实 OS 线程上"中范围外）。`crates/core/src/datetime.rs::is_within_last_24_hours`
辅助函数之前从非日志路径调用 `chrono::Utc::now`；现在通过
`nautilus_core::time::nanos_since_unix_epoch()` 路由并直接在 `u64` 纳秒下比较。

### 随机性缝隙

DST 路径上的生产 RNG 位置：

- `crates/core/src/uuid.rs::UUID4::new()` 在模拟下、于 madsim 运行时内调用时路由到
  `madsim::rand::thread_rng()`，运行时外（以及普通构建下）回退到 `rand::rng()`。
  模拟下的生产路径总是在运行时内运行，因此消费种子字节；
  `cfg(madsim)` 下的普通 `#[rstest]` 测试使用主机 RNG。
  `nautilus-common` 与 `nautilus-risk` 的订单和事件工厂可达。
- `crates/execution/src/models/fill.rs::default_std_rng()` 按相同方式路由。
  在未提供种子时由 `ProbabilisticFillState::new()` 调用。提供种子时，
  `StdRng::seed_from_u64` 按构造确定。
- `crates/execution/src/matching_engine/ids_generator.rs:167,179` 在 `use_random_ids`
  路径下使用 `nautilus_core::UUID4::new()`。默认 ID 方案
  （`{venue}-{raw_id}-{count}`）无需它即为确定性。

带标记允许：`crates/network/src/backoff.rs:105` 用于重连抖动，
`// dst-ok`（传输层）。

### Tokio 子模块拆分

`madsim` 别名 `time`、`task`、`runtime` 与 `signal`。其他 tokio 子模块
（`sync`、`io`、`select!`、`fs`、`net`）在模拟下仍使用真实 tokio。
进一步扩展替换将要求基于 shim 的 `tokio::net::TcpStream` 重建 `tokio-tungstenite`、
`tokio-rustls` 与 `reqwest`，审计认为过于侵入而排除。

直接接触真实 `tokio::net` / `tokio::io` 的范围内位置：

- `crates/network/src/net.rs:37` re-export `tokio::net::{TcpListener, TcpStream}`
- `crates/network/src/socket/client.rs:46,356` `tokio::io::{AsyncReadExt, AsyncWriteExt}`
- `crates/network/src/tls.rs:22` `tokio::io::{AsyncRead, AsyncWrite}`
- `crates/network/src/websocket/types.rs:26,29` 别名 `MaybeTlsStream<tokio::net::TcpStream>`

这些即便在模拟下也运行在真实套接字上。`tokio::sync` 上的通道投递顺序保持确定性，
因为即便通道实现是真实的，发送方和接收方任务也由 madsim 执行器调度。

### 原始线程逃逸规则

钩子规则 4 禁止在三种逃逸情况之外原始线程生成：

- `#[cfg(test)]` 测试模块。
- `#[cfg(not(madsim))]` 或 `#[cfg(not(all(feature = "simulation", madsim)))]` 生产位置
  （例如日志写入器线程）。
- 内联 `// dst-ok` 标记。

`tokio::task::LocalSet` 与 `tokio::task::spawn_blocking` 在 `madsim` 下不受支持。
代码库审计在范围内 crate 中未发现两者的生产位置；新位置必须带 cfg 限制或 `// dst-ok` 标记。

### 模拟下的日志测试

日志写入器线程在模拟下通过 cfg 排除；`cfg(madsim)` 下日志事件被丢弃。
初始化文件日志写入器的测试要么会挂起，要么对空日志文件断言失败，
因此受影响的子模块在模块边界整体 gate 出：

- `crates/common/src/logging/logger.rs::tests::serial_tests`（八个测试）。
- `crates/common/src/logging/macros.rs::tests`（两个测试）。

`logger.rs::tests::sim_tests::test_init_under_madsim_skips_writer_thread_and_forces_bypass`
在模拟下运行，并固定 gate 后行为。

## 范围边界

契约有意保持狭窄。下列削弱是明确的，而非疏漏。

### Python 不在 DST 范围内

DST 在原生 Rust 测试框架下运行。DST 运行期间不启动 Python 解释器。
`crates/*/src/python/` 下的 PyO3 绑定、`ffi/` 目录以及 `nautilus_trader/`
下的 Python 包按策略被排除在契约之外，而非作为弱点。
仅可通过 Python 调用路径到达的任何代码不在范围内；
原生 DST 框架可达的任何 Rust 路径即使其类型也导出到 Python，也必须满足契约。

`check-dst-conventions` 钩子通过跳过范围内 crate 中的 `/python/` 与 `/ffi/`
路径来编码此策略。位于这些路径之后的时钟、RNG、线程调用位置不适用契约。

DST 的主要目标是 Rust 引擎本身的可靠性：订单生命周期、对账、撮合、风险和执行状态机。
用户策略的确定性回放是次要目标，将在策略以 Rust 编写或通过 Rust 原生测试框架运行后才可用。
在此之前，调用 `time.time()`、发任意网络请求或依赖线程调度的 Python 策略，其命令流可能在不同次运行间变化；
Rust 核心会确定性地处理变化的流，但从 Python 入口点起的端到端回放并不保证。

### 平台范围

`madsim` 对 `clock_gettime` 与 `getrandom` 的 libc 覆盖是平台特定的。
跨平台比特级复现性不予声明。在 Linux x86_64 上复现某失败的种子在 macOS aarch64 上可能不复现。

### 未别名依赖会静默逃逸

任何通过未别名路径访问 OS 的依赖（直接 `libc` 调用、绕过 `std::net`、使用 `fastrand` 或 `OsRng` 的 crate）
会逃出模拟器且不报错。范围内 crate 已经审计；适配器 crate 与基础设施 crate
在进入 DST 路径前需要各自审计。

### 传输层 I/O 不被模拟

`tokio-tungstenite`、`tokio-rustls`、`reqwest`、`redis`、`sqlx` 在内部使用真实 `tokio`。
在模拟下，WebSocket 与 HTTP I/O 在真实网络上运行。这是有意为之：初始目标是订单生命周期确定性，
而非传输故障注入。传输层确定性需要目前不存在的 per-crate `madsim` shim。

驱动真实 localhost 套接字的测试模块（`crates/network/src/socket/client.rs::tests`、
`::rust_tests`；`crates/network/src/websocket/client.rs::tests`、`::rust_tests`；
`crates/network/tests/websocket_proxy.rs`）在 `all(feature = "simulation", madsim)`
下通过 cfg 排除，因为它们的生产代码路径会调用 `dst::time::*`（madsim 时间原语），
从 `#[tokio::test]` 运行时调用时会 panic。
重试测试模块（`crates/network/src/retry.rs::tests`、`::proptest_tests`）在模拟下运行：
每个测试属性通过 `cfg_attr` 在 `#[tokio::test(start_paused = true)]` 与 `#[madsim::test]` 间切换，
时间读取与 sleep 通过 `crate::dst::time` 路由，显式虚拟时间推进通过 `cfg`
限制的 `advance_clock` 辅助函数，从而同一测试体覆盖两种运行时。

### 信号处理

`nautilus_common::live::dst::signal` 暴露一个路由的 `ctrl_c` re-export。
`crates/live/src/node.rs` 的运行循环通过它路由，因此由 `ctrl_c` 驱动的节点关停
可在 `cfg(madsim)` 下通过 `madsim::runtime::Handle::send_ctrl_c` 在测试代码中注入。
适配器二进制入口仍直接调用 `tokio::signal::ctrl_c`，因此仍在范围外。

### 日志运行在真实 OS 线程上

日志子系统通过 `std::thread::Builder` 生成写入器线程，并使用 `std::sync::mpsc`。
模拟下不生成该线程，日志事件被丢弃。日志输出在确定性契约之外：
写入器只写入，不读取或修改模拟状态。

### 适配器

适配器 crate 不在初始 DST 契约范围内。每个适配器都有自己的 `chrono::Utc::now`、
`SystemTime::now`、`Uuid::new_v4` 与传输层调用点集合。
适配器进入 DST 路径前必须审计直接时钟、RNG 和传输使用。

### 进程全局惰性状态在首次调用时消费 RNG 字节

契约在单次运行时实例内成立。少数进程全局惰性初始化在首次调用时消费 RNG 字节，
这对在一个进程中运行两次种子执行并对比跟踪的框架有影响。

- `Ustr::from()` interner 在首次使用时分配并播种其内部 map。
- `ahash::RandomState` 在首次实例创建时通过 `getrandom` 自播种
  （`madsim` 在 `cfg(madsim)` 下钩入）。

单运行时测试（每个种子一次体调用、新进程）不受影响：消费是种子执行的一部分，可确定性复现。

在一个进程中两次调用测试体以对比跟踪的"相同种子相等性"框架，会在两次运行间看到漂移。
第一次运行付出惰性初始化代价并消费 RNG 字节；第二次运行继承已热的状态，
从 RNG 序列中的不同偏移开始。

变通：在进行对比前在运行时外预热进程全局状态，例如在进程启动时调用 `Ustr::from("")`
并构造一个 `ahash::RandomState`。两次运行随后都从热状态开始并以相同方式消费 RNG 序列。

### 适配器工厂不再暴露 `Rc<RefCell<Cache>>`

提交 `f0ea66da15`（"Standardize adapter cache access via `CacheView`"）将
`DataClientFactory::create` 与 `ExecutionClientFactory::create` 上的可变 `Rc<RefCell<Cache>>`
参数替换为 `CacheView`。`CacheView` 暴露 `borrow()` 用于只读访问，但不暴露内部 `Rc` handle。

这阻碍了需要在工厂内联构造 `OrderMatchingEngine` 的 DST 风格框架工厂，
因为 `OrderMatchingEngine::new` 仍接收 `Rc<RefCell<Cache>>`，而 `CacheView`
没有公共访问器恢复该 handle。

变通：

- 将框架消费者固定到 `f0ea66da15` 之前的提交。
- 重构框架，让其在工厂外（kernel `Cache` handle 仍可达）构建 `OrderMatchingEngine`，
  并将构造好的引擎传给客户端。

长期出口是要么在 `CacheView` 上提供内部 handle 的访问器，要么提供接受 `CacheView`
的备选 `OrderMatchingEngine` 构造函数。两者目前都不在代码树中。

## 与其他测试层的关系

DST 补充现有测试；并不取代任何一种。

| 层                      | 覆盖                                                  | 与 DST 的关系                                    |
|-------------------------|-------------------------------------------------------|-------------------------------------------------|
| 单元测试                | 纯逻辑、计算、解析器、转换器。                        | 不变。                                          |
| 集成测试                | 组件交互、I/O 边界。                                  | 不变。DST 并行运行，不替代。                    |
| 属性测试                | 输入域上的不变式（解析器、往返）。                    | 不变。                                          |
| 验收测试                | 端到端的回测与实盘场景。                              | 不变。                                          |
| 确定性模拟 (DST)        | 异步时序、调度、恢复正确性。                          | 增加种子可重放的探索。                          |

DST 的独特价值在于异步并发与状态机正确性的交集。
诸如"关停时某条消息在特定唤醒顺序下丢失"或"迭代顺序反转时某对账事件丢失"是其目标类别。
对其他场景，已有测试层才是合适的工具。

## 状态

截至当前仓库状态：

- Layer 1（运行时替换）已实现。`nautilus_common::live::dst` 暴露针对 `time`、`task`、
  `runtime`、`signal` 的路由 re-export。`time`、`task`、`runtime` 的生产调用位置通过缝隙路由；
  signal 的调用点适配部分完成（参见"范围边界"中的"信号处理"）。
- Layer 2（非确定性替换）在 16 个范围内 crate 中实现。墙钟时间、单调时间、随机性、迭代顺序均存在缝隙。
  审计闭包和剩余允许调用位置在"实现笔记"中枚举。
- 通过 `check-dst-conventions` 的静态强制实施在 pre-commit 与 CI 中启用。
  钩子覆盖承重条件；`// dst-ok` 标记约定允许在有理由时进行单行例外。
- `cfg(madsim)` 下的构建与测试冒烟门控通过 `dst` 工作流
  （`.github/workflows/dst.yml`，调用 `make cargo-test-sim`）运行。
  它用 `--features simulation` 编译范围内 crate，并运行当前所有兼容 sim 的测试。
  使用 `nautilus-model` 类型的 crate（`nautilus-common`、`nautilus-execution`）
  还以 `--features "simulation,high-precision"` 运行第二轮，以便在两种定点宽度下
  （`QuantityRaw` / `PriceRaw` 为 `u64` 与 `u128`）演练经缝隙路由的代码路径。
  - 全部的 `nautilus-common`。此轮以传递的 `nautilus-core/simulation` 编译，
    因此显式的 `wall_clock_now` cfg 分支在套件中每个测试都被选中。
    普通 `#[rstest]` 测试在 madsim 运行时外运行，通过缝隙的 `SystemTime::now()`
    回退路由（与 madsim 的 libc shim 在运行时外的路径相同）。
    本轮中的 `live::dst::tests::test_dst_wall_clock_advances_with_virtual_time` 测试
    使用 `#[madsim::test]` 并断言 `nanos_since_unix_epoch` 随 `madsim::time::sleep` 推进，
    因此虚拟墙钟行为在 common 轮端到端验证。
  - 全部的 `nautilus-network`（受传输绑定的测试模块在源码处被排除）。
    包含 sleep / timeout 虚拟时间与限速器的缝隙固定测试，以及在虚拟时间下演练退避计时的重试套件。
  - 全部的 `nautilus-execution`。撮合引擎、成交模型与执行引擎状态机在确定性调度器下、以种子 RNG 运行。
  - `nautilus-core` 中的跨 crate 缝隙固定测试（`wall_clock_now` 虚拟时间）。
    每轮以各 crate 自身的 `--features simulation` 运行，并在适用处使用 `#[madsim::test]`，
    从而显式的 cfg 分支和虚拟时间都被验证。

  这些合起来捕获 cfg-gated DST 缝隙的漂移，并在确定性调度器下演练范围内状态机；
  它尚不端到端演练确定性。
- 端到端运行时验证（在范围内代码路径上的相同种子差异）在本仓库中不在范围。
  结构性条件（规则 1 至规则 6）已强制实施；
  "种子在多次运行间产生相同可观测行为"的声明从缝隙设计上可信，但尚未通过回归门控验证。

## 延伸阅读

- `.pre-commit-hooks/check_dst_conventions.sh` 完整定义五条强制规则并文档化 `// dst-ok` 标记约定。
- 外部参考：[FoundationDB 测试哲学](https://apple.github.io/foundationdb/testing.html)、
  [TigerBeetle 模拟测试博客](https://tigerbeetle.com/blog/)，以及确定性运行时的
  [madsim 仓库](https://github.com/madsim-rs/madsim)。
