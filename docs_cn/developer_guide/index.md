# 开发者指南

> 本文档为 [English 原文](../../docs/developer_guide/index.md) 的中文翻译版本。如有歧义请以英文原版为准。

关于开发与扩展 NautilusTrader、或向项目回馈贡献的指引。

NautilusTrader 采用 **Rust 核心 + Python 绑定** 的架构：

- **Rust** 负责网络通信、数据解析、订单撮合以及其他对性能敏感的操作。
- **Python** 提供面向用户的 API，用于策略开发、配置以及系统集成。
- **PyO3** 在两者之间充当桥梁，以极低的开销将 Rust 功能暴露给 Python。

这种方式将 Python 的简洁性和丰富生态与 Rust 的高性能、内存安全特性结合起来。

## 目录

- [环境搭建](environment_setup.md)
- [设计原则](design_principles.md)
- [编码规范](coding_standards.md)
- [Rust](rust.md)
- [Python](python.md)
- [测试](testing.md)
- [测试数据集](test_datasets.md)
- [文档风格](docs.md)
- [发布说明](releases.md)
- [适配器](adapters.md)
- [数据测试规范](spec_data_testing.md)
- [执行测试规范](spec_exec_testing.md)
- [基准测试](benchmarking.md)
- [FFI 内存契约](ffi.md)
