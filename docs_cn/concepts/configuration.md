# 配置

> 本文档为 [English 原文](../../docs/concepts/configuration.md) 的中文翻译版本。如有歧义请以英文原版为准。

NautilusTrader 在整个平台中使用类型化的配置结构体。
每个组件（数据客户端、执行客户端、引擎、策略）都有一个专用的配置结构体来控制其行为。

## 设计原则

### 默认值在配置边界处解析

配置结构体为那些始终具有合理默认值的字段携带具体值。
超时、重试次数、退避延迟和心跳间隔都是诸如 `u64` 或 `u32` 这样的普通类型，并将默认值内置其中。下游代码接收已解析的值，不再重复默认值逻辑。

### Option 表示语义上的缺省，而非"使用默认值"

`Option<T>` 字段仅在 `None` 携带真实含义时出现：某个特性被关闭、回看窗口无界，或某个值在运行时从环境继承。如果某个字段始终能解析为具体值，就不会包装在 `Option` 中。

这种区分让配置的语义在类型中可见。一个普通的 `u64` 字段始终有值。一个 `Option<u64>` 字段则可能缺省，使用它的代码会基于此进行分支判断。

### 默认值的单一来源

每个配置结构体使用 `bon::Builder`，通过 `#[builder(default = value)]` 标注在一处定义默认值。`Default` 实现委托给 builder（`Self::builder().build()`），因此不存在第二份可能不同步漂移的默认值副本。

### 配置解码在遇到未知字段时失败

配置解码对未知字段快速失败。Nautilus 将额外的键视为 bug，而非无害输入。这样可以在节点或客户端以错误设置启动之前，捕获拼写错误、配置重命名后的过时名称以及复制粘贴失误。

## Python 配置

Python 配置类（msgspec 结构体）的可选参数接受 `None`。
对于普通 `T` 字段，`None` 表示"使用默认值"。对于 `Option<T>` 字段，`None` 保留该字段的可选含义（已禁用、无界等）。

所有 Python 配置类均继承自 `NautilusConfig`，它在底层 `msgspec.Struct` 上设置了 `forbid_unknown_fields=True`。未知键在解码时会抛出 `msgspec.ValidationError`。

```python
from nautilus_trader.adapters.bybit.config import BybitDataClientConfig

# All defaults: 60s timeout, 3 retries, etc.
config = BybitDataClientConfig()

# Override just the timeout
config = BybitDataClientConfig(http_timeout_secs=30)

# Disable instrument status polling
config = BybitDataClientConfig(instrument_status_poll_secs=None)
```

## Rust 配置

所有配置结构体均派生 [`bon::Builder`](https://bon-rs.com)，它会生成一个类型安全的 builder，并在编译期检查必需字段。带有 `#[builder(default = value)]` 的字段可以从 builder 调用中省略，使用其声明的默认值。构造配置有三种等价方式：

使用 Serde 反序列化的 Rust 配置结构体还设置了 `#[serde(deny_unknown_fields)]`。未知键现在会导致反序列化失败，而不会被忽略。

```rust
// Builder: only set what differs from defaults
let config = BybitDataClientConfig::builder()
    .http_timeout_secs(30)
    .build();

// Struct literal with default spread
let config = BybitDataClientConfig {
    http_timeout_secs: 30,
    ..Default::default()
};

// Full defaults
let config = BybitDataClientConfig::default();
```

对于未指定的字段，三种方式产生完全相同的结果。

## 通用配置字段

大多数适配器配置共享一组通用字段：

| 字段                                | 类型    | 默认值   | 用途                       |
|------------------------------------|--------|---------|-------------------------------|
| `http_timeout_secs`                | `u64`  | 60      | REST 请求超时。              |
| `max_retries`                      | `u32`  | 3       | 最大重试次数。                |
| `retry_delay_initial_ms`           | `u64`  | 1,000   | 初始退避延迟。                |
| `retry_delay_max_ms`               | `u64`  | 10,000  | 最大退避延迟。                |
| `heartbeat_interval_secs`          | `u64`  | 视情况  | WebSocket 保活间隔。          |
| `recv_window_ms`                   | `u64`  | 视情况  | 签名请求的过期窗口。          |
| `update_instruments_interval_mins` | 视情况 | 视情况  | 定期刷新标的信息。            |

适配器特有的字段（速率限制、轮询间隔、保证金模式）在每个适配器的集成指南中有详细说明。

## 引擎配置

引擎配置（`LiveExecEngineConfig`、`DataEngineConfig` 等）遵循相同的模式。诸如 `reconciliation`、`inflight_check_interval_ms` 和 `open_check_threshold_ms` 这样的字段是普通类型，带有 builder 默认值。真正可选的特性使用 `Option<T>`：

```python
from nautilus_trader.config import LiveExecEngineConfig

config = LiveExecEngineConfig(
    reconciliation=True,
    open_check_interval_secs=30.0,       # Enable open order polling
    open_check_lookback_mins=60,         # Look back 60 minutes
    # position_check_interval_secs=None  # Disabled by default
)
```
