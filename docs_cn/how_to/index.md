# 操作指南（How-to Guides）

> 本文档为 [English 原文](../../docs/how_to/index.md) 的中文翻译版本。如有歧义请以英文原版为准。

面向具体目标的实用配方，聚焦于完成常见任务。每篇指南都假设你已经熟悉 Nautilus 的概念，目标是帮助你达成某个具体结果。

刚接触 Nautilus？请先阅读 [入门指南（getting started）](../getting_started/) 路径与 [教程（tutorials）](../tutorials/)。

## 数据工作流

| 指南                                                  | 说明                                           |
|:------------------------------------------------------|:-----------------------------------------------|
| [加载外部数据][loading_external_data]                  | 将 CSV 数据加载到 Parquet 数据目录中。         |
| [使用 Databento 配置数据目录][data_catalog_databento]  | 基于 Databento 行情数据搭建数据目录。          |

## 实盘交易

| 指南                                                          | 说明                                                              |
|:--------------------------------------------------------------|:------------------------------------------------------------------|
| [配置实盘交易节点](configure_live_trading)                     | 配置 TradingNodeConfig、执行引擎以及交易场所。                    |

## Rust

| 指南                                                      | 说明                                                          |
|:----------------------------------------------------------|:--------------------------------------------------------------|
| [编写 Actor（Rust）](write_rust_actor)                     | 构建带订阅与处理器的数据 Actor。                              |
| [编写策略（Rust）](write_rust_strategy)                    | 构建带订单管理功能的策略。                                    |
| [运行回测（Rust）](run_rust_backtest)                      | 使用 BacktestEngine 或搭配数据目录的 BacktestNode。           |
| [运行实盘交易（Rust）](run_rust_live_trading)              | 使用 LiveNode 连接交易场所。                                  |

[loading_external_data]: https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/how_to/loading_external_data.py
[data_catalog_databento]: https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/how_to/data_catalog_databento.py
