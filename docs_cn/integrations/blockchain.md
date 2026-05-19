# Blockchain
> 本文档为 [English 原文](../../docs/blockchain.md) 的中文翻译版本。如有歧义请以英文原版为准。

## 核心原语（Core Primitives）

NautilusTrader 的区块链集成构建在 DeFi 领域模型（`nautilus_model::defi`）中定义的基础原语之上。这些构件为基于 EVM 的区块链提供了类型安全的抽象。

### Chain

`Chain` 结构表示一条区块链网络，包含其连接端点和元数据。每个 chain 实例包含：

**字段：**

- `name` (`Blockchain`)：区块链网络类型（包含 80+ 条已支持链的枚举）
- `chain_id` (`u32`)：唯一的 EVM 链标识符（例如 Ethereum 为 1，Arbitrum 为 42161）
- `hypersync_url` (`String`)：用于高性能 Hypersync 数据流的端点
- `rpc_url` (`Option<String>`)：可选的 HTTP/WSS RPC 端点，用于直接与节点通信
- `native_currency_decimals` (`u8`)：该链原生 gas 代币的小数精度（通常为 18）

**Chain 检索：**

可以通过数字 ID 或字符串名称（不区分大小写）来检索 chains：

- **按 Chain ID：** 通过 `from_chain_id` 使用 EVM 链标识符查找
- **按名称：** 通过 `from_chain_name` 使用区块链名称查找（不区分大小写："ethereum"、"Ethereum"、"ETHEREUM" 均可）
- **静态实例：** 预配置的 chains 以常量形式提供

每条链都有一个用于支付 gas 费的原生货币。`native_currency()` 方法返回一个正确配置的 Currency 实例：

| 链系列                                          | 代码 | 名称         | 小数位 |
|-------------------------------------------------|------|--------------|----------|
| Ethereum 及 L2（Arbitrum、Base、Optimism 等） | ETH  | Ethereum     | 18       |
| Polygon                                         | POL  | Polygon      | 18       |
| Avalanche                                       | AVAX | Avalanche    | 18       |
| BSC                                             | BNB  | Binance Coin | 18       |

## 合约（Contracts）

通过类型安全的 Rust 抽象，提供查询 EVM 智能合约的高性能接口。通过高效的批量操作支持 token 元数据、DEX 池以及 DeFi 协议。

### Base（Multicall3）

使用 Multicall3（`0xcA11bde05977b3631167028862bE2a173976CA11`）将多个合约调用批处理到单个 RPC 请求中。

- 始终使用 `allow_failure: true` 以支持部分成功和详细错误信息
- 在同一区块中原子地执行
- 错误：`RpcError`（网络问题）、`AbiDecodingError`（解码失败）

### ERC20

继承自 `BaseContract`，使用 Multicall3 进行高效的批量操作。获取 token 元数据，并处理非标准实现。

**方法：**

- `fetch_token_info`：获取单个 token 元数据（内部使用 multicall 获取 name、symbol、decimals）
- `batch_fetch_token_info`：在一次 multicall 中获取多个 token（每个 token 3 次调用）
- `enforce_token_fields`：校验 name/symbol 不为空

**错误类型：**

1. **`CallFailed`** —— 合约缺失或未实现函数 -> 跳过该 token
2. **`DecodingError`** —— 返回原始字节而非 ABI 编码（例如 `0x5269636f...`） -> 跳过该 token
3. **`EmptyTokenField`** —— 函数返回空字符串 -> 启用强制校验时跳过

**最佳实践：**

- 跳过任一 token 出错的池
- `raw_data` 字段保留原始响应以便调试
- 非标准 token 通常还存在其他问题（转账手续费、rebase 等）

## 配置

| 选项                            | 默认值 | 说明 |
|---------------------------------|---------|-------------|
| `chain`                         | 必填 | 要同步的 `nautilus_trader.model.Chain`（例如 `Chain.ETHEREUM`）。 |
| `dex_ids`                       | 必填 | 描述要启用哪些 DEX 集成的 `DexType` 标识符序列。 |
| `http_rpc_url`                  | 必填 | 用于 EVM 调用和 Multicall 请求的 HTTPS RPC 端点。 |
| `wss_rpc_url`                   | `None`  | 可选的 WSS 端点，用于流式接收实时更新。 |
| `rpc_requests_per_second`       | `None`  | 出站 RPC 调用的可选限流（请求数/秒）。 |
| `multicall_calls_per_rpc_request` | `200` | 每个 RPC 请求批处理的 Multicall 目标的最大数量。 |
| `use_hypersync_for_live_data`   | `True`  | 为 `True` 时，使用 Hypersync 引导启动并流式接收以获得更低延迟的增量。 |
| `from_block`                    | `None`  | 历史回填的可选起始区块高度。 |
| `pool_filters`                  | `DexPoolFilters()` | 选择要监控的 DEX 池时应用的过滤规则。 |
| `postgres_cache_database_config`| `None`  | 可选的 `PostgresConnectOptions`，启用已解码池状态的本地磁盘缓存。 |
| `proxy_url`                     | `None`  | 用于 HTTP 和 WebSocket 传输的可选代理 URL。 |

## 贡献

:::info
如需添加更多功能或为 Blockchain 适配器做出贡献，请参阅我们的
[贡献指南](https://github.com/nautechsystems/nautilus_trader/blob/develop/CONTRIBUTING.md)。
:::
