# 入门指南

> 本文档为 [English 原文](../../docs/getting_started/index.md) 的中文翻译版本。如有歧义请以英文原版为准。

## 1. 安装

准备一个 Python 3.12-3.14 环境，然后安装该包：

```bash
pip install -U nautilus_trader
```

平台支持、源码构建和 Docker 镜像的相关说明，请参阅 [安装指南](installation)。

## 2. 运行快速上手示例

[快速上手（Quickstart）](quickstart) 使用合成数据，在五分钟内运行你的第一个回测。无需下载任何文件，也不需要搭建数据目录（catalog）。

入门系列教程统一使用一个简单的 EMA 交叉策略，这是有意为之的。这些教程的重点并非交易逻辑本身，而是介绍引擎是如何工作的：数据加载、交易场所模拟、订单生命周期，以及结果报告。在你熟悉引擎机制之后，[教程（tutorials）](../tutorials/) 部分会再介绍不同类型的策略（均值回归、订单簿失衡、网格做市等）。

## 3. 选择你的路径

- **回测**——先了解下面介绍的两种 API 层级，再通过 [教程](../tutorials/) 学习各种策略模式的完整演示。
- **实盘交易**——参阅 [配置实盘交易节点（Configure a live trading node）](../how_to/configure_live_trading.md) 操作指南，以及 [集成（Integrations）](../integrations/) 了解所支持的交易场所。
- **数据工作流**——参阅 [操作指南（how-to guides）](../how_to/)，学习如何加载外部数据并搭建 Parquet 数据目录。
- **构建适配器**——参阅 [开发者指南（Developer guide）](../developer_guide/)。

## 回测 API 层级

NautilusTrader 提供两种用于回测的 API 层级：

| API 层级                                       | 入口            | 适用场景                                                          |
|:-----------------------------------------------|:----------------|:------------------------------------------------------------------|
| [低阶 API](backtest_low_level)                  | `BacktestEngine`| 直接访问组件、库开发                                              |
| [高阶 API](backtest_high_level)                 | `BacktestNode`  | 生产环境工作流，更容易过渡到实盘交易（推荐）                      |

高阶 API 需要基于 Parquet 的数据目录。低阶 API 可以直接使用内存数据，但无法过渡到实盘交易。

:::warning[每个进程仅运行一个节点]
不支持在同一进程中并发运行多个 `BacktestNode` 或 `TradingNode` 实例，因为存在全局单例状态。允许顺序执行，但每次运行之间必须正确释放资源（dispose）。

详情参阅 [进程与线程](../concepts/architecture.md#processes-and-threads)。
:::

如需帮助选择 API 层级，请参阅 [回测](../concepts/backtesting.md) 概念指南。

## 仓库中的示例

在线文档仅展示一部分示例。完整示例请参阅 GitHub 仓库：

| 目录                                                                                                       | 内容                                                          |
|:-----------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------|
| [examples/](https://github.com/nautechsystems/nautilus_trader/tree/develop/examples)                       | 完整可运行、自包含的 Python 示例                              |
| [docs/tutorials/](../tutorials/)                                                                           | 演示常见工作流的教程                                          |
| [docs/concepts/](../concepts/)                                                                             | 概念指南，附带说明关键特性的代码片段                          |
| [nautilus_trader/examples/](../../nautilus_trader/examples/)                                                | 纯 Python 编写的策略、指标和执行算法示例                      |
| [tests/unit_tests/](../../tests/unit_tests/)                                                                | 覆盖核心功能与边界场景的单元测试                              |

## 在 Docker 中运行

自包含的 Docker 化 Jupyter notebook 服务器提供了体验 NautilusTrader 的最快方式，无需本地环境配置。删除容器即会一并删除其中的数据。

```bash
# Pull the latest image
docker pull ghcr.io/nautechsystems/jupyterlab:nightly --platform linux/amd64

# Run the container
docker run -p 8888:8888 ghcr.io/nautechsystems/jupyterlab:nightly
```

之后在浏览器中打开 <http://localhost:8888> 即可。

:::warning
示例中使用 `log_level="ERROR"`，因为 Nautilus 的日志输出会超过 Jupyter 的 stdout 速率限制，使用更低日志级别时会导致 notebook 卡住。
:::
