# 适配器

> 本文档为 [English 原文](../../docs/concepts/adapters.md) 的中文翻译版本。如有歧义请以英文原版为准。

适配器将数据提供方与交易场所集成到 NautilusTrader 中。
它们位于顶层的 `adapters` 子包中。

一个适配器通常由以下组件构成：

```mermaid
flowchart LR
    subgraph Venue ["Trading Venue"]
        API[REST API]
        WS[WebSocket]
    end

    subgraph Adapter ["Adapter"]
        HTTP[HttpClient]
        WSC[WebSocketClient]
        IP[InstrumentProvider]
        DC[DataClient]
        EC[ExecutionClient]
    end

    subgraph Core ["Nautilus Core"]
        DE[DataEngine]
        EE[ExecutionEngine]
    end

    API <--> HTTP
    WS <--> WSC
    HTTP --> IP
    HTTP --> DC
    HTTP --> EC
    WSC --> DC
    WSC --> EC
    DC <--> DE
    EC <--> EE
```

| 组件                  | 用途                                                       |
|----------------------|------------------------------------------------------------|
| `HttpClient`         | REST API 通信。                                            |
| `WebSocketClient`    | 实时流式连接。                                              |
| `InstrumentProvider` | 从交易场所加载并解析标的定义。                                |
| `DataClient`         | 处理行情数据的订阅和请求。                                   |
| `ExecutionClient`    | 处理订单的提交、修改和撤销。                                 |

## 标的提供方（Instrument Providers）

标的提供方将交易场所的 API 响应解析为 Nautilus 的 `Instrument` 对象。

`InstrumentProvider` 服务于两种使用场景：

- 用于研究或回测的可用标的独立发现
- 在 `sandbox` 或 `live` [环境上下文](architecture.md#environment-contexts) 中为 actor 与策略提供运行时加载

### 研究与回测

下面是一个发现 Binance Futures 测试网当前标的的示例：

```python
import asyncio
import os

from nautilus_trader.adapters.binance.common.enums import BinanceAccountType
from nautilus_trader.adapters.binance.common.enums import BinanceEnvironment
from nautilus_trader.adapters.binance import get_cached_binance_http_client
from nautilus_trader.adapters.binance.futures.providers import BinanceFuturesInstrumentProvider
from nautilus_trader.common.component import LiveClock


async def main():
    clock = LiveClock()

    client = get_cached_binance_http_client(
        clock=clock,
        account_type=BinanceAccountType.USDT_FUTURES,
        api_key=os.getenv("BINANCE_FUTURES_TESTNET_API_KEY"),
        api_secret=os.getenv("BINANCE_FUTURES_TESTNET_API_SECRET"),
        environment=BinanceEnvironment.TESTNET,
    )

    provider = BinanceFuturesInstrumentProvider(
        client=client,
        account_type=BinanceAccountType.USDT_FUTURES,
    )

    await provider.load_all_async()

    # Access loaded instruments
    instruments = provider.list_all()
    print(f"Loaded {len(instruments)} instruments")


if __name__ == "__main__":
    asyncio.run(main())
```

### 实盘交易

每个集成处理这件事的方式不同。`TradingNode` 中的 `InstrumentProvider` 通常提供两种加载行为：

- 启动时加载全部标的：

```python
from nautilus_trader.config import InstrumentProviderConfig

InstrumentProviderConfig(load_all=True)
```

- 仅加载配置中指定的标的：

```python
InstrumentProviderConfig(load_ids=["BTCUSDT-PERP.BINANCE", "ETHUSDT-PERP.BINANCE"])
```

## 数据客户端

数据客户端处理某个交易场所的行情数据订阅与请求。它们连接到交易场所的 API，并将传入的数据规范化为 Nautilus 的类型。

### 请求数据

Actor 与策略可以使用内置方法请求数据。数据通过回调返回：

```python
from nautilus_trader.model import Instrument, InstrumentId
from nautilus_trader.trading.strategy import Strategy


class MyStrategy(Strategy):
    def on_start(self) -> None:
        # Request an instrument definition
        self.request_instrument(InstrumentId.from_str("BTCUSDT-PERP.BINANCE"))

        # Request historical bars
        self.request_bars(BarType.from_str("BTCUSDT-PERP.BINANCE-1-HOUR-LAST-EXTERNAL"))

    def on_instrument(self, instrument: Instrument) -> None:
        self.log.info(f"Received instrument: {instrument.id}")

    def on_historical_data(self, data) -> None:
        self.log.info(f"Received historical data: {data}")
```

### 订阅数据

对于实时数据，使用订阅方法：

```python
def on_start(self) -> None:
    # Subscribe to live trade updates
    self.subscribe_trade_ticks(InstrumentId.from_str("BTCUSDT-PERP.BINANCE"))

    # Subscribe to live bars
    self.subscribe_bars(BarType.from_str("BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL"))

def on_trade_tick(self, tick: TradeTick) -> None:
    self.log.info(f"Trade: {tick}")

def on_bar(self, bar: Bar) -> None:
    self.log.info(f"Bar: {bar}")
```

:::tip
关于可用的请求和订阅方法及其对应回调的完整参考，请参阅 [Actors](actors.md) 文档。
:::

## 执行客户端

执行客户端处理交易场所的订单管理。它们将 Nautilus 的订单命令翻译为场所特定的 API 调用，并将执行报告处理为 Nautilus 事件。

主要职责：

- 提交、修改和撤销订单。
- 处理成交与执行报告。
- 与交易场所对账订单状态。
- 处理账户与持仓更新。

`ExecutionEngine` 根据订单所属的交易场所，将命令路由到对应的执行客户端。关于从策略视角进行订单管理的细节，请参阅 [执行](execution.md) 指南。

:::tip
构建自定义适配器，请参阅 [适配器开发者指南](../developer_guide/adapters.md)。
:::

## 相关指南

- [实盘交易](live.md) —— 使用适配器配置并运行实盘交易。
- [执行](execution.md) —— 通过适配器进行订单执行。
- [数据](data.md) —— 适配器提供的行情数据。
