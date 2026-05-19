# 基准测试

> 本文档为 [English 原文](../BENCHMARKING.md) 的中文翻译版本。如有歧义请以英文原版为准。

NautilusTrader 是对性能敏感的软件。本文档描述项目对基准测试的整体方针：我们测量什么、为什么测量、何时测量，以及使用什么工具。其目标读者是需要在编写或评估性能相关工作之前理解相关政策的贡献者和评审者。

如需了解实践层面的细节（如何编写基准测试、如何在本地运行、如何生成火焰图、已注册的模板），请参阅 [`docs/developer_guide/benchmarking.md`](docs/developer_guide/benchmarking.md)。

---

## 目的

基准测试的存在是为了回答以下两个问题之一：

1. **这段代码当前在绝对意义上有多快？** 在评估工作负载规模、比较替代方案，或判断一项优化是否值得引入额外复杂度时使用。
2. **这次变更是否在任一方向上影响了性能？** 用作变更检测信号：捕获性能回退，确认性能提升。主要存在于 CI 中。

这两个目的需要不同的工具和不同的严谨度。我们使用 **Criterion** 来回答第一个问题，并优先使用指令计数工具（**iai**）来回答第二个问题。单个基准测试可能同时服务于这两个目的，但各自所需的方法学是不同的，这一区别贯穿本文档其余部分。

---

## 方法

项目对待基准测试的方式由以下几条原则塑造。

**基准测试就是文档。** 一份基准测试记录了我们当时认为的热点路径、我们判断为现实的输入、以及在那个时间点上产生的开销。未来的贡献者通过阅读基准测试来理解时间消耗在哪里，而不仅仅是验证变更未引入回退。

**优先衡量真实的工作单元。** 对一个已填充结构上有意义的公共方法进行计时的基准测试，比孤立测试一个私有辅助函数更有用。前者能在重构中存活下来；后者每次调用方变化时都会失效。

**对你优化的内容进行基准测试，而不是对方便测试的内容。** 仅仅因为代码方便驱动就添加一个基准测试，并不能证明其维护成本的合理性。新的基准测试应针对热点路径或正在主动优化的路径，而不是任意函数。

**绝对数值因机器而异；相对数值则相对稳定。** 墙钟时间（wall-clock）数据在不同硬件之间不可移植，即使是比率也会随缓存大小、微架构和频率行为而变化。当你需要有意义的差值时，请在同一台机器上背靠背地进行比较。CI 变更检测在固定的自托管机器上运行；来自开发者笔记本的本地数据不应被引用为权威数据。

**不要在没有测量的情况下进行优化。** 先做性能剖析或基准测试。代码库足够庞大，依靠直觉判断热点路径并不可靠。

**没有基准测试就不要宣称胜利。** PR 描述或发布说明中的性能声明应引用一份基准测试或性能剖析结果。没有数据的"更快"对评审者而言不可操作，也无法在下一次重构中存活。

---

## 我们对什么进行基准测试，以及何时进行

基准测试在三种场景下被添加，每种场景的范围和维护期望都不同。

### 1. 热点路径微基准（每个 crate）

这些基准测试位于每个 crate 的 `benches/` 文件夹中，针对被判定为热点路径的单个函数或公共方法。例如：

- `crates/execution/benches/matching_core.rs`：`OrderMatchingCore` 的 add / delete / lookup / iterate API。
- `crates/common/benches/matching.rs`：消息总线主题匹配。
- `crates/common/benches/cache_orders.rs`：订单缓存查询和接入。

何时添加：

- 一项新的优化或重构需要一个基线，以便未来的变更可以与之对比衡量。
- 某段代码路径对性能敏感，但缺乏覆盖。
- 评审者要求提供变更对性能影响的证据。

何时跳过：

- 函数是没有分配或分支的直线代码。
- 函数位于冷的管理路径上（启动、配置校验、诊断）。
- 已有基准测试通过更高层级的调用覆盖了相关工作。

### 2. 端到端 / 场景基准

这些基准测试演练更大的工作单元：通过数据引擎接入一次 tick 突发、回放一次市场会话、通过实盘节点（live-node）调度执行。维护起来更重，但相比于单函数微基准，是更接近用户可观察性能的代理。示例位于 `crates/data/benches/`、`crates/live/benches/`，以及位于 `tests/performance_tests/` 的 Python 性能套件中。请注意，`crates/live/benches/` 仍然是有范围限定的（例如，仅 dispatch 部分，而非完整的 select 循环）；更深入的 runner-加-engine 工作负载是位于 `crates/live/tests/stress.rs` 的被忽略的压力测试。

### 3. CI 变更检测基准

部分 crate 通过 [`performance` 工作流](.github/workflows/performance.yml) 在推送到 `nightly` 分支时在 CI 中运行基准测试。被包含的 crate 列在工作区 `Makefile` 的 `CI_BENCH_CRATES` 变量中（目前为 `nautilus-core`、`nautilus-model`、`nautilus-common` 和 `nautilus-live`）。要让一项新基准测试加入 nightly CI 执行，请在其 crate 的 `Cargo.toml` 中注册该测试，并确保该 crate 位于 `CI_BENCH_CRATES` 中。

目前 CI 不会因 Rust 基准测试的差值而让 PR 失败：性能工作流仅在推送到 `nightly` 时运行，不会在 PR 开启时运行。对于实质性改变热点路径的 PR，调查疑似性能回退或确认所声称的性能改进的贡献者，应在本地对 `develop` 运行一次 Criterion 比较；nightly 运行结果是事后查阅的。

Python 性能套件（`tests/performance_tests/`）在同一个 nightly 工作流中通过 [CodSpeed](https://codspeed.io/) 运行。Nightly 仪表盘会同时显示性能回退和性能改进；两者只要超过噪声阈值就都值得调查。

### Python 性能测试 vs Rust 基准测试

当工作发生在 Rust 中，且你需要绝对数值或指令计数变化信号时，添加 Rust 基准测试（位于 `crates/<crate>/benches/` 下的 Criterion 或 iai）。当工作跨越 Cython/PyO3 边界，或者衡量在纯 Rust 基准测试中不会体现出来的终端用户 Python API 开销时，添加 Python 性能测试（`tests/performance_tests/...`，由 CodSpeed 采集）。两套套件是互补的：Rust 套件追踪引擎性能，Python 套件追踪用户实际调用的 API 表面。

---

## 工具一览

| 框架                                                            | 衡量内容                                  | 用途                                                  |
|---------------------------------------------------------------|-------------------------------------------|------------------------------------------------------|
| [**Criterion**](https://docs.rs/criterion/latest/criterion/)  | 墙钟时间，附带置信区间                       | 任何 ≥ 100 ns 的操作；绝对测量；比较。              |
| [**iai**](https://docs.rs/iai/latest/iai/)                    | 退役 CPU 指令数（通过 Cachegrind）          | 亚 100 ns 的函数；CI 变更检测。                     |
| [**flamegraph**](https://github.com/flamegraph-rs/flamegraph) | 采样得到的调用栈剖析                         | 调查慢速基准测试内部的时间消耗位置。                 |

Criterion 产出墙钟时间数据。它们反映了用户实际体验到的性能，但会随 CPU 频率、热状态、调度器决策、ASLR 和缓存状态而波动。在引用这些数据之前，先降低噪声（参见下文 [降低噪声](#降低噪声)）。

iai 在 valgrind 的 Cachegrind 下统计机器指令数。对于固定的二进制、工具链、输入和环境，该计数是确定性的，因此计数上的小幅变化是任一方向上可靠的变更信号。该计数与墙钟时间并不直接可比，且在不同二进制（工具链升级、代码生成变化）上测得的计数会以不可移植的方式发生位移。请使用 iai 在同一台机器和工具链上检测变化，而不是用它来评估工作负载规模。

关于配置、示例和模板，请参阅 [开发者指南](docs/developer_guide/benchmarking.md)。

---

## 记录结果

我们在三个地方记录基准测试结果，具体取决于场景。

**内联 Criterion HTML 报告。** 每次 `cargo bench` 运行都会写入 `target/criterion/<group>/<id>/report/index.html`。Criterion 已保存的基线（位于同一目录）在两次运行于同一台机器上背靠背完成时，可提供 PR 对比基线的比较。

**发布说明。** 当一次变更产生可衡量的性能改进时，请在"Internal Improvements"下添加一条简短条目，注明被优化的组件。不要把完整的基准测试表格粘贴到发布说明中；一行足矣。更大的头条数据应放在 PR 描述中。

**PR 描述。** 跨越多次变更的实质性优化或重组工作，应在 PR 描述中包含一份"头条数据（headline numbers）"表格，并在旁边注明硬件和工具链（参见下方示例）。PR 描述是这些数据的持久家园；发布说明只放一行简短文字。

我们目前不维护一份签入的历史基准数据库。长期记录存放在 CI 工作流上传的位置（Python 套件存放于 CodSpeed；Rust 的 Criterion HTML 存放在 runner 上）。

---

## 降低噪声

对于需要被报告或对比的 Criterion 运行，请在测量前降低噪声：

- **使用正确的 profile 构建。** 两个 profile 都继承自 `release` 并保留完整的调试符号：
  - `bench`：`cargo bench` 的默认 profile。不开启 LTO，迭代速度快，适合本地迭代和临时比较。
  - `bench-lto`：添加 `lto = "fat"` 和 `codegen-units = 1`，以匹配生产环境发布的二进制。任何将被报告或公开发布的数据（每个适配器的 `BENCHMARKS.md`、PR 描述中的头条数据表格、发布说明中的数字）都应使用这个 profile：`cargo bench --profile bench-lto`。
- **使机器进入静默状态。** 关闭其他工作负载。在 Linux 上，将 CPU governor 设置为 `performance`：

  ```bash
  sudo cpupower frequency-set -g performance
  ```

- **禁用 ASLR 以提高可重复性**（Linux）：

  ```bash
  setarch -R cargo bench --profile bench-lto -p <crate> --bench <name>
  ```

- **在 BIOS 中禁用超线程和动态频率调节**，用于更深入的分析。临时测量不需要。
- **多次运行基准测试** 并按用例取最佳或中位数。Criterion 的置信区间已能提供帮助，但多次完整运行可以捕捉到会话级的漂移。
- **记录机器信息。** 在发布数据时，注明 CPU 型号、内核 / 操作系统、Rust 工具链，以及使用了哪个构建 profile。缺少这些上下文的数据无法操作。

随发布数据附带的示例头部信息：

```text
Hardware: AMD Ryzen Threadripper 9980X (64C), Linux 6.17.0
Toolchain: rustc 1.95.0
Profile: bench-lto (release + lto = "fat" + codegen-units = 1, debug = full)
```

对于 iai，上述内容均不适用：Cachegrind 的虚拟 CPU 模型意味着指令计数不依赖于机器静默状态或频率调节。直接运行即可，无需上述噪声缓解措施。

---

## 总结

- 两个问题、两种工具：Criterion 用于绝对时间，iai 用于变更检测。
- 对你优化的内容进行基准测试，而不是对方便测试的内容。
- 在引用数据之前降低噪声；引用时记录机器信息。
- 通过将 crate 添加到 `cargo-ci-benches` recipe，可让其纳入 nightly CI 执行。
- 将已有的基准测试视为我们认为是热点的文档。在没有解释的情况下让其回退是代码评审上需要关注的问题。

关于实现细节（编写基准测试、本地运行、火焰图、模板），请参阅 [`docs/developer_guide/benchmarking.md`](docs/developer_guide/benchmarking.md)。
