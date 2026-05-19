# AX Exchange
> 本文档为 [English 原文](../../docs/integrations/architect_ax.md) 的中文翻译版本。如有歧义请以英文原版为准。

[AX Exchange](https://architect.exchange) 是全球首家针对传统标的资产类别的永续期货中心化、受监管交易所。由 Architect Bermuda Ltd. 运营，并获得 [百慕大金融管理局（BMA）](https://www.bma.bm/) 的牌照许可，AX 将加密风格的永续合约带入传统金融市场，包括外汇、金属、能源、股指和利率。

本集成支持与 AX Exchange 的实时行情数据接入和订单执行。

## 示例

实时示例脚本可在 [此处](https://github.com/nautechsystems/nautilus_trader/tree/develop/examples/live/architect_ax/) 找到。

## 概览

本指南假设交易者要同时配置实时行情数据源和交易执行。AX Exchange 适配器包含多个组件，可根据用例一起或单独使用。

- `AxHttpClient`：低层级的 HTTP API 连接。
- `AxMdWebSocketClient`：行情数据 WebSocket 连接。
- `AxOrdersWebSocketClient`：订单 WebSocket 连接。
- `AxInstrumentProvider`：标的解析和加载功能。
- `AxDataClient`：行情数据源管理器。
- `AxExecutionClient`：账户管理和交易执行网关。
- `AxLiveDataClientFactory`：AX 数据客户端工厂（由 trading node builder 使用）。
- `AxLiveExecClientFactory`：AX 执行客户端工厂（由 trading node builder 使用）。

:::note
大多数用户只需为实时交易节点定义配置（如下所示），不必直接处理这些低层级组件。
:::

## AX Exchange 文档

AX Exchange 为用户提供文档，位于 [Architect 文档站](https://docs.architect.exchange/)。建议你在使用 NautilusTrader 集成指南时同时参考 AX Exchange 文档。

## 产品

AX Exchange 专注于传统资产类别的永续期货合约。永续合约永不到期，消除了标准期货所关联的滚仓成本。

| 资产类别         | 示例                               | 备注                         |
|------------------|------------------------------------|------------------------------|
| 外汇 | GBPUSD-PERP、EURUSD-PERP           | 主要和次要的外汇货币对。    |
| 股票指数    | 股指永续合约            |                              |
| 金属           | XAU-PERP（黄金）、XAG-PERP（白银） | 贵金属永续合约。  |
| 能源           | 原油、天然气             | 能源商品永续合约。 |
| 利率   | SOFR、国债收益率              | 利率永续合约。             |

### 永续合约

永续合约（perpetual swap）是一种不会到期、跟踪标的资产价格的衍生品。与标准期货不同，它没有结算日期，从而消除了滚仓成本并简化了仓位管理。资金费率机制通过多空持仓者之间的周期性支付，使合约价格与底层指数价格保持一致。有关资金费率机制和合约规格的详细信息，请参阅 [Architect 文档](https://docs.architect.exchange/)。

AX 永续合约的特点：

- **以 USD 现金结算**：不进行实物交割，所有盈亏均以 USD 结算。
- **资金费率**：通过周期性支付保持合约价格与标的资产对齐。
- **乘数为 1**：每张合约代表一份对标的资产的敞口。
- **仅支持整数合约**：不支持小数数量。
- **保证金**：开仓需要初始保证金（initial margin），维持仓位需要维持保证金（maintenance margin）。

在 NautilusTrader 中，所有 AX 标的都表示为 `PerpetualContract`，这是一种与资产类别无关的永续 swap 类型。资产类别（外汇、商品、股权等）从标的资产自动推断。该适配器使用 `MARGIN` 账户类型和 `NETTING` 订单管理。

## 标的命名约定（Symbology）

AX Exchange 使用简单直观的命名约定。所有标的都是永续期货，通过在标的资产符号后追加 `-PERP` 后缀来标识。

**格式**：`{SYMBOL}-PERP`

| 标的资产       | AX 符号        | Nautilus InstrumentId |
|----------------|----------------|-----------------------|
| GBP/USD        | `GBPUSD-PERP`  | `GBPUSD-PERP.AX`      |
| EUR/USD        | `EURUSD-PERP`  | `EURUSD-PERP.AX`      |
| 黄金           | `XAU-PERP`     | `XAU-PERP.AX`         |
| 白银           | `XAG-PERP`     | `XAG-PERP.AX`         |

场所标识符为 `AX`。构造 Nautilus `InstrumentId` 的方法：

```python
from nautilus_trader.model.identifiers import InstrumentId

instrument_id = InstrumentId.from_str("GBPUSD-PERP.AX")
```

## 环境

AX Exchange 提供两种交易环境。使用客户端配置中的 `environment` 参数选择合适的环境。

| 环境           | 配置                                   | 说明                                   |
|----------------|----------------------------------------|----------------------------------------|
| **Sandbox**    | `environment=AxEnvironment.SANDBOX`    | 使用模拟资金的测试环境。 |
| **Production** | `environment=AxEnvironment.PRODUCTION` | 使用真实资金的实盘交易。          |

### Sandbox

用于开发和测试的默认环境，使用模拟资金。设置 `environment=AxEnvironment.SANDBOX` 时，所有 sandbox 端点会自动解析。

#### 1. 创建 sandbox 账户

按照 [Architect 文档](https://docs.architect.exchange/) 创建 sandbox 账户。注册时需要邀请码。

#### 2. 创建 API key 并为账户充值

使用 AX sandbox UI 生成 API key 并向账户存入模拟资金。请妥善保管 `api_key` 和 `api_secret`。

#### 3. 设置环境变量

```bash
export AX_API_KEY="your-sandbox-api-key"
export AX_API_SECRET="your-sandbox-api-secret"
```

#### 4. 配置交易节点

```python
config = TradingNodeConfig(
    ...,  # Omitted
    data_clients={
        AX: AxDataClientConfig(
            environment=AxEnvironment.SANDBOX,
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
    exec_clients={
        AX: AxExecClientConfig(
            environment=AxEnvironment.SANDBOX,
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
)
```

### Production

用于实盘交易的环境，使用真实资金。需要已验证的 AX Exchange 账户。

```python
config = AxExecClientConfig(
    environment=AxEnvironment.PRODUCTION,
)
```

:::warning
下单前请确保使用正确的环境。默认使用 Sandbox 是为了防止意外地进行实盘交易。
:::

## 行情数据

适配器通过 WebSocket 订阅提供实时行情数据，并通过 HTTP 端点支持历史数据回填。

### 数据类型

| AX 数据           | Nautilus 数据类型   | 备注                                                              |
|-------------------|----------------------|--------------------------------------------------------------------|
| 订单簿（L1）   | `QuoteTick`          | 从 L1 订单簿订阅获取的最优买卖盘口。                |
| 订单簿（L2）   | `OrderBookDelta`     | 按价格层级聚合。                                           |
| 订单簿（L3）   | `OrderBookDelta`     | 单笔订单数量。                                       |
| 成交            | `TradeTick`          | 来自 L1 订阅的实时成交事件。                       |
| 标记价格        | `MarkPriceUpdate`    | 从 L1 ticker 订阅中提取。                             |
| K 线（bar）      | `Bar`                | OHLCV 数据（仅总成交量，无买卖分项）。             |
| 资金费率     | `FundingRateUpdate`  | 通过 HTTP 轮询（非实时 WebSocket）；间隔可配置。  |
| 标的状态 | `InstrumentStatus`   | 来自 L1 ticker 订阅的状态变化（open、halted、closed）。  |

:::note
AX Exchange 不支持历史报价 Tick 请求。只能通过 WebSocket L1 订单簿订阅获取实时报价数据。
:::

### K 线间隔

| 间隔     | 描述        |
|----------|-------------|
| `1s`     | 1 秒    |
| `5s`     | 5 秒    |
| `1m`     | 1 分钟    |
| `5m`     | 5 分钟    |
| `15m`    | 15 分钟   |
| `1h`     | 1 小时      |
| `1d`     | 1 天       |

## 订单能力

AX Exchange 支持市价和限价订单类型，并支持止损触发。

### 订单类型

| 订单类型               | 是否支持 | 备注                                              |
|------------------------|-----------|----------------------------------------------------|
| `MARKET`               | ✓         | 以最优可用价格立即执行。       |
| `LIMIT`                | ✓         | 按指定价格或更优价格执行。              |
| `STOP_LIMIT`           | ✓         | 触发价被突破时，触发一个限价单。 |
| `LIMIT_IF_TOUCHED`     | -         | *AX Exchange 当前未实现*。        |
| `STOP_MARKET`          | -         | *不支持*。                                   |
| `MARKET_IF_TOUCHED`    | -         | *不支持*。                                   |
| `TRAILING_STOP_MARKET` | -         | *不支持*。                                   |

### 执行指令

| 指令          | 是否支持 | 备注                                               |
|---------------|-----------|-----------------------------------------------------|
| `post_only`   | ✓         | 仅挂单（maker‑only）；若订单会吃单则被拒绝。 |
| `reduce_only` | -         | *不支持*。                                    |

### 有效期（Time in Force）

| 有效期        | 是否支持 | 备注                                        |
|---------------|-----------|----------------------------------------------|
| `GTC`         | ✓         | 撤销前一直有效（Good Till Canceled）。                          |
| `GTD`         | -         | *AX Exchange 不支持*。              |
| `DAY`         | ✓         | 当日交易日结束前有效。              |
| `IOC`         | ✓         | 立即成交或取消（Immediate or Cancel）。                         |
| `FOK`         | ✓         | 全部成交或取消（Fill or Kill）。                                |
| `AT_THE_OPEN` | ✓         | 在开盘时执行，否则失效。            |
| `AT_THE_CLOSE`| ✓         | 在收盘时执行，否则失效。           |

### 高级订单特性

| 特性               | 是否支持 | 备注                                                              |
|--------------------|-----------|--------------------------------------------------------------------|
| 订单修改 | ✓         | 通过 `POST /replace_order` 原子替换。返回一个新的订单 ID。  |
| 取消订单       | ✓         | 单订单取消。                                         |
| 取消全部订单  | ✓         | 取消某个标的的所有挂单。                          |
| 批量取消       | -         | *AX Exchange 不支持*。改为使用单个取消。   |
| 订单列表        | ✓         | 顺序提交（订单逐个提交，非原子）。 |

### 持仓管理

| 特性             | 是否支持 | 备注                                |
|------------------|-----------|--------------------------------------|
| 查询持仓  | ✓         | 实时持仓更新。          |
| 持仓模式    | -         | 仅支持净额（netting）模式。                   |
| 跨保证金     | ✓         | 所有标的的跨保证金。 |

### 订单查询

| 特性                 | 是否支持 | 备注                                                   |
|----------------------|-----------|---------------------------------------------------------|
| 查询挂单    | ✓         | 列出所有活动订单。                                 |
| 查询单个订单   | ✓         | 通过场所订单 ID 或客户端订单 ID 查询（任意订单状态）。 |
| 订单状态报告 | ✓         | 从挂单进行调节；见下方说明。        |
| 成交报告         | ✓         | 执行与成交历史。                             |

:::note
用于调节的订单状态报告由挂单端点生成。已成交或已取消的订单不会包含在调节快照中。通过 `query_order` 进行的单订单查询使用专门的 `/order-status` 端点，可用于任意订单状态。
:::

## 认证

AX Exchange 使用 bearer token 认证：

1. API key 和 secret 通过 `/authenticate` 获取一个 session token。
2. session token 作为 bearer token 用于后续的 REST 和 WebSocket 请求。
3. session token 在可配置的时间后过期（默认 86400 秒）。

## 配置

### 环境与端点

| 环境  | HTTP API（行情）                           | HTTP API（订单）                                   | 行情 WS                                   | 订单 WS                                            |
|-------------|--------------------------------------------------|-----------------------------------------------------|--------------------------------------------------|------------------------------------------------------|
| Sandbox     | `https://gateway.sandbox.architect.exchange/api` | `https://gateway.sandbox.architect.exchange/orders` | `wss://gateway.sandbox.architect.exchange/md/ws` | `wss://gateway.sandbox.architect.exchange/orders/ws` |
| Production  | `https://gateway.architect.exchange/api`         | `https://gateway.architect.exchange/orders`         | `wss://gateway.architect.exchange/md/ws`         | `wss://gateway.architect.exchange/orders/ws`         |

:::info
订单管理 HTTP 端点（下单、取消、订单状态）使用与行情端点不同的 base URL。这一切由适配器配置自动处理。
:::

### 数据客户端配置选项

| 选项                               | 默认值    | 说明                                                         |
|------------------------------------|-----------|---------------------------------------------------------------------|
| `api_key`                          | `None`    | API key；省略时从 `AX_API_KEY` 环境变量加载。             |
| `api_secret`                       | `None`    | API secret；省略时从 `AX_API_SECRET` 环境变量加载。       |
| `environment`                      | `SANDBOX` | 交易环境（`SANDBOX` 或 `PRODUCTION`）。                    |
| `base_url_http`                    | `None`    | REST base URL 的覆盖值。                                     |
| `base_url_ws_public`               | `None`    | 行情 WebSocket URL 的覆盖值。                         |
| `base_url_ws_private`              | `None`    | 订单 WebSocket URL 的覆盖值。                              |
| `proxy_url`                        | `None`    | 用于 HTTP 和 WebSocket 传输的可选代理 URL。               |
| `http_timeout_secs`                | `60`      | REST 请求的超时时间（秒）。                                |
| `max_retries`                      | `3`       | REST 请求的最大重试次数。                           |
| `retry_delay_initial_ms`           | `1000`    | 重试之间的初始延迟（毫秒）。                       |
| `retry_delay_max_ms`               | `10000`   | 重试之间的最大延迟（毫秒，使用指数退避）。 |
| `heartbeat_interval_secs`          | `20`      | WebSocket 连接的心跳间隔（秒）。             |
| `recv_window_ms`                   | `5000`    | 签名请求的 receive window（毫秒）。                  |
| `update_instruments_interval_mins` | `60`      | 标的目录刷新的间隔（分钟）。            |
| `funding_rate_poll_interval_mins`  | `15`      | 资金费率轮询请求的间隔（分钟）。              |

### 执行客户端配置选项

| 选项                      | 默认值    | 说明                                                         |
|---------------------------|-----------|---------------------------------------------------------------------|
| `api_key`                 | `None`    | API key；省略时从 `AX_API_KEY` 环境变量加载。             |
| `api_secret`              | `None`    | API secret；省略时从 `AX_API_SECRET` 环境变量加载。       |
| `environment`             | `SANDBOX` | 交易环境（`SANDBOX` 或 `PRODUCTION`）。                    |
| `base_url_http`           | `None`    | REST base URL 的覆盖值。                                     |
| `base_url_orders`         | `None`    | 订单 REST base URL 的覆盖值。                              |
| `base_url_ws_private`     | `None`    | 订单 WebSocket URL 的覆盖值。                              |
| `proxy_url`               | `None`    | 用于 HTTP 和 WebSocket 传输的可选代理 URL。               |
| `http_timeout_secs`       | `60`      | REST 请求的超时时间（秒）。                                |
| `max_retries`             | `3`       | REST 请求的最大重试次数。                           |
| `retry_delay_initial_ms`  | `1000`    | 重试之间的初始延迟（毫秒）。                       |
| `retry_delay_max_ms`      | `10000`   | 重试之间的最大延迟（毫秒，使用指数退避）。 |
| `heartbeat_interval_secs` | `30`      | WebSocket 连接的心跳间隔（秒）。             |
| `recv_window_ms`          | `5000`    | 签名请求的 receive window（毫秒）。                  |
| `cancel_on_disconnect`    | `false`   | 当订单 WebSocket 断开时取消所有挂单。       |

最常见的用例是配置一个实时 `TradingNode`，包含 AX Exchange 的数据和执行客户端。为此，请在客户端配置中添加 `AX` 部分：

```python
from nautilus_trader.adapters.architect_ax import AX
from nautilus_trader.adapters.architect_ax import AxDataClientConfig
from nautilus_trader.adapters.architect_ax import AxEnvironment
from nautilus_trader.adapters.architect_ax import AxExecClientConfig
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import TradingNodeConfig

config = TradingNodeConfig(
    ...,  # Omitted
    data_clients={
        AX: AxDataClientConfig(
            environment=AxEnvironment.SANDBOX,
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
    exec_clients={
        AX: AxExecClientConfig(
            environment=AxEnvironment.SANDBOX,
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
)
```

然后，创建一个 `TradingNode` 并添加客户端工厂：

```python
from nautilus_trader.adapters.architect_ax import AX
from nautilus_trader.adapters.architect_ax import AxLiveDataClientFactory
from nautilus_trader.adapters.architect_ax import AxLiveExecClientFactory
from nautilus_trader.live.node import TradingNode

# Instantiate the live trading node with a configuration
node = TradingNode(config=config)

# Register the client factories with the node
node.add_data_client_factory(AX, AxLiveDataClientFactory)
node.add_exec_client_factory(AX, AxLiveExecClientFactory)

# Finally build the node
node.build()
```

### API 凭据

向 AX Exchange 客户端提供凭据有两种方式。要么把对应的 `api_key` 和 `api_secret` 值传递给配置对象，要么设置以下环境变量：

- `AX_API_KEY`
- `AX_API_SECRET`

:::tip
我们建议使用环境变量来管理凭据。
:::

启动交易节点时，你会立即收到凭据是否有效以及是否具备交易权限的确认。

## 实现说明

- **只支持整数合约**：AX Exchange 使用整数合约数量。不支持小数数量，否则会被拒绝。
- **限流**：适配器采用保守的限流策略：10 请求/秒，遇到限流响应时自动指数退避。
- **市价单**：AX 不支持原生市价单。适配器使用预览端点确定吃单价格，然后提交一个激进的 IOC 限价单。
- **订单修改**：AX 通过 `POST /replace_order` 支持原子订单替换。适配器将 `modify_order` 映射到该端点。交易所会取消原订单并以更新后的字段创建一个新订单，并返回一个新的订单 ID。
- **断开时取消**：在执行客户端配置中设置 `cancel_on_disconnect=True`，当订单 WebSocket 断开时让交易所取消所有挂单。
- **成交手续费**：来自 WebSocket 的实时成交事件不包含手续费数据。流式成交的手续费报告为零。在调节期间，REST `/fills` 端点提供准确的手续费信息。

## 贡献

:::info
如需添加更多功能或为 AX Exchange 适配器做出贡献，请参阅我们的
[贡献指南](https://github.com/nautechsystems/nautilus_trader/blob/develop/CONTRIBUTING.md)。
:::
