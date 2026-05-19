# 教程

> 本文档为 [English 原文](../../docs/tutorials/index.md) 的中文翻译版本。如有歧义请以英文原版为准。

逐步演示特定功能与工作流的实操指引。

:::info
每篇教程都是位于文档
[tutorials 目录](https://github.com/nautechsystems/nautilus_trader/tree/develop/docs/tutorials) 下的
Jupytext percent 格式 Python 文件。
你可以直接以脚本方式运行，也可以借助 Jupytext 作为 notebook 打开。
:::

:::tip

- **Latest**：基于 `master` 分支构建的稳定发布版本文档。
  参见 <https://nautilustrader.io/docs/latest/tutorials/>。
- **Nightly**：基于 `nightly` 分支构建的实验性功能文档。
  参见 <https://nautilustrader.io/docs/nightly/tutorials/>。

:::

## 推荐学习顺序

初次接触 NautilusTrader？建议按以下顺序逐步学习：

1. [快速开始](../getting_started/quickstart) - 使用合成数据在五分钟内运行你的第一个回测
2. [回测（低级 API）](../getting_started/backtest_low_level) - 直接使用
   `BacktestEngine`，搭配真实行情数据与执行算法
3. [回测（高级 API）](../getting_started/backtest_high_level) - 通过 `BacktestNode`
   与 Parquet 数据目录（catalog）进行配置驱动的回测
4. [加载外部数据][loading_external_data] - 将 CSV 或其他外部数据加载到
   `ParquetDataCatalog`（操作指南）
5. [使用 FX K 线（bar）数据进行回测][backtest_fx_bars] - 包含滚动利率模拟的 FX K 线回测
6. 从下方挑选一篇与你主题相关的教程

## 回测

| 教程                                                                                | 描述                                              | 数据          |
|:------------------------------------------------------------------------------------|:--------------------------------------------------|:--------------|
| [使用 FX K 线数据进行回测][backtest_fx_bars]                                        | 在 FX K 线上运行 EMA 交叉策略，包含滚动模拟。     | 已内置        |
| [使用订单簿深度数据进行回测（Binance）][backtest_orderbook_binance]                 | 在深度数据上运行订单簿失衡策略。                  | 用户自备      |
| [使用订单簿深度数据进行回测（Bybit）][backtest_orderbook_bybit]                     | 在深度数据上运行订单簿失衡策略。                  | 用户自备      |

## 数据工作流

任务导向的数据处理范例请参考 [操作指南](../how_to/)：

| 指南                                                                                | 描述                                              | 数据              |
|:------------------------------------------------------------------------------------|:--------------------------------------------------|:------------------|
| [加载外部数据][loading_external_data]                                               | 将外部数据加载到 `ParquetDataCatalog`。           | 用户自备          |
| [配合 Databento 使用数据目录][data_catalog_databento]                               | 基于 Databento schema 搭建数据目录。              | Databento API key |

## 策略模式

| 教程                                                                                | 描述                                              | 数据              |
|:------------------------------------------------------------------------------------|:--------------------------------------------------|:------------------|
| [使用代理 FX 数据的均值回归策略（AX Exchange）](fx_mean_reversion_ax)               | 在 EURUSD-PERP 上运行 Bollinger 带均值回归策略。  | TrueFX 代理       |
| [黄金永续合约的订单簿失衡策略（AX Exchange）](gold_book_imbalance_ax)               | 在 XAU-PERP 上运行订单簿失衡策略。                | Databento API key |
| [带 Deadman's Switch 的网格做市策略（BitMEX）](grid_market_maker_bitmex)            | 在 XBTUSD 上运行带服务端安全机制的网格做市。      | Tardis.dev        |
| [使用短期订单的链上网格做市策略（dYdX）](grid_market_maker_dydx)                    | 在 dYdX v4 永续合约上运行网格做市。               | 用户自备          |

## 期权

| 教程                                                                                | 描述                                              | 数据              |
|:------------------------------------------------------------------------------------|:--------------------------------------------------|:------------------|
| [期权数据与希腊字母（Bybit）](options_data_bybit)                                   | 推送希腊字母及期权链快照。                        | 实盘 API          |
| [Delta 中性期权策略（Bybit）](delta_neutral_options_bybit)                          | 卖出宽跨式组合配合永续合约 delta 对冲。           | 实盘 API          |

## Rust

| 教程                                                                                | 描述                                              | 数据           |
|:------------------------------------------------------------------------------------|:--------------------------------------------------|:---------------|
| [订单簿失衡回测（Betfair）](backtest_book_imbalance_betfair)                        | 在 Betfair L2 数据上运行订单簿失衡 Actor。        | 用户自备       |
| [Hurst/VPIN 方向性策略（Kraken Futures）](hurst_vpin_kraken)                        | 在 PF_XBTUSD 上运行经市场状态过滤的知情流策略。   | Tardis.dev     |

[backtest_fx_bars]: https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/tutorials/backtest_fx_bars.py
[backtest_orderbook_binance]: https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/tutorials/backtest_orderbook_binance.py
[backtest_orderbook_bybit]: https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/tutorials/backtest_orderbook_bybit.py
[loading_external_data]: https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/how_to/loading_external_data.py
[data_catalog_databento]: https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/how_to/data_catalog_databento.py
