# 集成（Integrations）
> 本文档为 [English 原文](../../docs/integrations/index.md) 的中文翻译版本。如有歧义请以英文原版为准。

NautilusTrader 通过模块化的 *适配器*（adapters）连接到交易场所和数据提供方，把原始 API 转换为统一的接口和标准化的领域模型。

当前支持以下集成：

| 名称                                                                         | ID                    | 类型                    | 状态                                                  | 文档                     |
| :--------------------------------------------------------------------------- | :-------------------- | :---------------------- | :------------------------------------------------------ | :----------------------- |
| [AX Exchange](https://architect.exchange)                                    | `AX`                  | 永续合约交易所     | ![status](https://img.shields.io/badge/stable-green)    | [指南](architect_ax.md) |
| [Betfair](https://betfair.com)                                               | `BETFAIR`             | 体育博彩交易所 | ![status](https://img.shields.io/badge/stable-green)    | [指南](betfair.md)      |
| [Binance](https://binance.com)                                               | `BINANCE`             | 加密货币交易所（CEX）   | ![status](https://img.shields.io/badge/stable-green)    | [指南](binance.md)      |
| [Coinbase](https://coinbase.com)                                             | `COINBASE`            | 加密货币交易所（CEX）   | ![status](https://img.shields.io/badge/beta-yellow)     | [指南](coinbase.md)     |
| [BitMEX](https://www.bitmex.com)                                             | `BITMEX`              | 加密货币交易所（CEX）   | ![status](https://img.shields.io/badge/stable-green)    | [指南](bitmex.md)       |
| [Bybit](https://www.bybit.com)                                               | `BYBIT`               | 加密货币交易所（CEX）   | ![status](https://img.shields.io/badge/stable-green)    | [指南](bybit.md)        |
| [Databento](https://databento.com)                                           | `DATABENTO`           | 数据提供方           | ![status](https://img.shields.io/badge/stable-green)    | [指南](databento.md)    |
| [Deribit](https://www.deribit.com)                                           | `DERIBIT`             | 加密货币交易所（CEX）   | ![status](https://img.shields.io/badge/stable-green)    | [指南](deribit.md)      |
| [dYdX](https://dydx.exchange/)                                               | `DYDX`                | 加密货币交易所（DEX）   | ![status](https://img.shields.io/badge/stable-green)    | [指南](dydx.md)         |
| [Hyperliquid](https://hyperliquid.xyz)                                       | `HYPERLIQUID`         | 加密货币交易所（DEX）   | ![status](https://img.shields.io/badge/stable-green)    | [指南](hyperliquid.md)  |
| [Interactive Brokers](https://www.interactivebrokers.com)                    | `INTERACTIVE_BROKERS` | 经纪商（多场所） | ![status](https://img.shields.io/badge/stable-green)    | [指南](ib.md)           |
| [Kraken](https://kraken.com)                                                 | `KRAKEN`              | 加密货币交易所（CEX）   | ![status](https://img.shields.io/badge/stable-green)    | [指南](kraken.md)       |
| [OKX](https://okx.com)                                                       | `OKX`                 | 加密货币交易所（CEX）   | ![status](https://img.shields.io/badge/stable-green)    | [指南](okx.md)          |
| [Polymarket](https://polymarket.com)                                         | `POLYMARKET`          | 预测市场（DEX） | ![status](https://img.shields.io/badge/stable-green)    | [指南](polymarket.md)   |
| [Tardis](https://tardis.dev)                                                 | `TARDIS`              | 加密货币数据提供方    | ![status](https://img.shields.io/badge/stable-green)    | [指南](tardis.md)       |

- **ID**：集成适配器客户端的默认客户端 ID。
- **类型**：集成的类型（通常是场所类型）。

## 状态

- `planned`：已规划，未来开发。
- `building`：建设中，可能尚未达到可用状态。
- `beta`：已完成到最小可用状态，处于 “beta” 测试阶段。
- `stable`：特性集和 API 已稳定，集成已经过开发者和用户的合理测试（可能仍存在少量 bug）。

## 实现目标

NautilusTrader 的主要目标是为多种集成提供统一的交易系统。为支持尽可能广泛的交易策略，将优先实现 *标准* 功能：

- 请求历史行情数据。
- 流式订阅实时行情数据。
- 调节执行状态（reconciling execution state）。
- 提交带有标准执行指令的标准订单类型。
- 修改已有订单（如交易所支持）。
- 取消订单。

每个集成的实现都旨在满足以下标准：

- 低层级客户端组件应尽可能贴近交易所 API。
- 交易所的完整功能范围（适用于 NautilusTrader 的部分）应 *最终* 得到支持。
- 将添加交易所特定的数据类型，以支持用户合理期望的功能和返回类型。
- 交易所或 NautilusTrader 不支持的操作，被调用时会以警告或错误的形式记入日志。

## API 统一化

所有集成都必须符合 NautilusTrader 的系统 API，这需要进行归一化和标准化：

- 标的（symbol）应使用交易所原生的符号格式，除非需要消除歧义（例如 Binance Spot 与 Binance Futures）。
- 时间戳必须使用 UNIX epoch 纳秒。如果使用毫秒，字段/属性名必须显式以 `_ms` 结尾。
