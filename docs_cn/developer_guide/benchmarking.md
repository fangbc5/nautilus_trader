# 基准测试

> 本文档为 [English 原文](../../docs/developer_guide/benchmarking.md) 的中文翻译版本。如有歧义请以英文原版为准。

本文档是编写和运行 NautilusTrader 基准测试的实战参考。
其内容涵盖工具细节、目录布局、示例代码、本地执行以及火焰图剖析。

关于政策（我们对什么做基准测试、何时做、严谨程度如何、如何接入 CI），
请参见仓库根目录下的 [`/BENCHMARKING.md`](../../BENCHMARKING.md)。

---

## 工具概览

NautilusTrader 使用两种互补的 Rust 基准测试框架：

| 框架                                                          | 测量内容                                  | 何时优先使用                                              |
|---------------------------------------------------------------|-------------------------------------------|-----------------------------------------------------------|
| [**Criterion**](https://docs.rs/criterion/latest/criterion/)  | 含置信区间的挂钟时间                      | 任何 ≥ 100 ns 的代码；绝对测量；对比分析。                |
| [**iai**](https://docs.rs/iai/latest/iai/)                    | 已退役的 CPU 指令数（通过 Cachegrind）    | 小于 100 ns 的函数；CI 中的回归检测。                     |

大多数热点路径会同时受益于两者。Criterion 给出用户可见的数字；iai 给出无噪声的回归信号。

:::note
iai 是确定性的（不受系统噪声影响），但结果与机器相关。请将其用于 CI 内的回归检测，而非跨机器对比。
:::

---

## 目录布局

每个 crate 将其基准测试保存在本地的 `benches/` 文件夹中：

```text
crates/<crate_name>/
└── benches/
    ├── foo_criterion.rs
    └── foo_iai.rs
```

在 crate 的 `Cargo.toml` 中显式注册每个基准测试，以便 `cargo bench` 能发现它：

```toml
[[bench]]
name = "foo_criterion"
path = "benches/foo_criterion.rs"
harness = false

[[bench]]
name = "foo_iai"
path = "benches/foo_iai.rs"
harness = false
```

要将该 crate 纳入夜间 CI 的性能工作流，请把它加入工作区 `Makefile` 中的 `cargo-ci-benches` 配方。

---

## 编写 Criterion 基准测试

1. **在计时循环之外完成准备工作。** 所有不会在迭代之间变化的工作都应放在外围代码或 `iter_batched_ref` 的 setup 闭包中，而不应放进传给 `iter` 的函数体里。
2. **用 `black_box` 包裹输入**，防止优化器将其折叠优化掉。
3. **对会发生修改的基准测试使用 `iter_batched_ref`。** 它会将输入的 `Drop` 排除在计时区间之外，否则对持有大型结构的基准测试，析构会主导测量结果。
4. **为按大小参数化的组添加 `Throughput::Elements(n)`**，使 Criterion 报告每元素吞吐量。
5. **注释意图。** 说明该基准测试度量的是什么（热路径、最坏情况、缓存冷启动），让未来的读者理解一旦其退化意味着什么。

```rust
use std::hint::black_box;

use criterion::{BatchSize, BenchmarkId, Criterion, Throughput, criterion_group, criterion_main};

const SIZES: &[usize] = &[10, 100, 1_000];

fn bench_my_op(c: &mut Criterion) {
    let mut group = c.benchmark_group("module/my_op");

    for &n in SIZES {
        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |b, &n| {
            b.iter_batched_ref(
                || populate(n),
                |state| state.run(black_box(n)),
                BatchSize::SmallInput,
            );
        });
    }

    group.finish();
}

criterion_group!(benches, bench_my_op);
criterion_main!(benches);
```

---

## 编写 iai 基准测试

`iai` 要求函数不接受任何参数。请让它们保持小巧，使指令计数具有实际意义，也避免函数外的变更渗入测量。

```rust
use std::hint::black_box;

fn bench_add() -> i64 {
    let a = black_box(123);
    let b = black_box(456);
    a + b
}

iai::main!(bench_add);
```

每次运行之间变化的准备工作（分配、随机数、系统调用）会以误导性的方式抬高指令计数。iai 最适合纯净、无分配的函数。

---

## 在本地运行基准测试

| 目标                                | 命令                                                                  |
|-------------------------------------|-----------------------------------------------------------------------|
| 单个 crate 内的全部基准测试         | `cargo bench -p nautilus-execution`                                   |
| 单个基准测试模块                    | `cargo bench -p nautilus-execution --bench matching_core`             |
| 按名称模式运行特定基准测试          | `cargo bench -p nautilus-execution --bench matching_core -- iterate`  |
| 快速冒烟运行（采样数较少）          | `cargo bench ... -- --quick`                                          |
| 所有受 CI 跟踪的基准测试            | `make cargo-ci-benches`                                               |

Criterion 会把 HTML 报告写入 `target/criterion/`。打开 `target/criterion/report/index.html`。报告中包含每个基准测试的小提琴图、置信区间，以及与上一次保存的基线之间的对比。

---

## 生成火焰图

`cargo-flamegraph` 会为某个基准测试生成采样调用栈剖析。当某项基准测试出现回归但难以确定是哪个内部调用导致时，它非常有用。

1. 每台机器安装一次：

   ```bash
   cargo install flamegraph
   ```

2. 使用 `bench` profile 运行特定的基准测试：

   ```bash
   cargo flamegraph --bench matching -p nautilus-common --profile bench
   ```

3. 在浏览器中打开 `flamegraph.svg`，深入查看热路径。

### Linux

需要可用的 `perf`。在 Debian/Ubuntu 上：

```bash
sudo apt install linux-tools-common linux-tools-$(uname -r)
```

如果 `perf_event_paranoid` 阻止了运行：

```bash
sudo sh -c 'echo 1 > /proc/sys/kernel/perf_event_paranoid'
```

值设为 `1` 通常已足够。事后将其恢复为 `2`（默认值），或通过 `/etc/sysctl.conf` 持久化。

### macOS

`DTrace` 需要 root 权限，因此 `cargo flamegraph` 必须以 `sudo` 运行。

:::warning
使用 `sudo` 运行会在 `target/` 中产生属主为 root 的文件，从而导致后续 `cargo` 命令出现权限错误。你可能需要手动删除这些文件，或运行 `sudo cargo clean`。
:::

```bash
sudo cargo flamegraph --bench matching -p nautilus-common --profile bench
```

`bench` profile 保留了完整的调试符号，因此火焰图能渲染出可读的函数名，又不会让生产二进制文件膨胀（生产构建仍然使用 `panic = "abort"`，由 `[profile.release]` 构建）。

> **注意** 基准测试的二进制文件采用在工作区 `Cargo.toml` 中定义的自定义 `[profile.bench]` 编译。该 profile 继承自 `release`，并设置 `debug = "full"`，从而*在保留完整优化的同时*保留调试符号，使 `cargo flamegraph` 或 `perf` 之类工具能产生可读的调用栈。

---

## 模板

可直接复制的起步文件位于 [`docs/dev_templates/`](../dev_templates/)：

- **Criterion**：[`criterion_template.rs`](../dev_templates/criterion_template.rs)
- **iai**：[`iai_template.rs`](../dev_templates/iai_template.rs)

将模板复制到目标 crate 的 `benches/` 目录，调整 imports 和组名，在 `Cargo.toml` 中注册，即可开始度量。
