# <img src="https://github.com/nautechsystems/nautilus_trader/raw/develop/assets/nautilus-trader-logo.png" width="500">

[![codecov](https://codecov.io/gh/nautechsystems/nautilus_trader/branch/master/graph/badge.svg?token=DXO9QQI40H)](https://codecov.io/gh/nautechsystems/nautilus_trader)
[![codspeed](https://img.shields.io/endpoint?url=https://codspeed.io/badge.json)](https://codspeed.io/nautechsystems/nautilus_trader)
![pythons](https://img.shields.io/pypi/pyversions/nautilus_trader)
![pypi-version](https://img.shields.io/pypi/v/nautilus_trader)
![pypi-format](https://img.shields.io/pypi/format/nautilus_trader?color=blue)
[![Downloads](https://pepy.tech/badge/nautilus-trader)](https://pepy.tech/project/nautilus-trader)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?logo=discord&logoColor=white)](https://discord.gg/NautilusTrader)

> 本文档为 [English README.md](../README.md) 的中文翻译版本。如有歧义请以英文原版为准。

| 分支      | 版本                                                                                                                                                                                                                       | 构建状态                                                                                                                                                                                          |
| :-------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `master`  | [![version](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnautechsystems%2Fnautilus_trader%2Fmaster%2Fversion.json)](https://packages.nautechsystems.io/simple/nautilus-trader/index.html)  | [![build](https://github.com/nautechsystems/nautilus_trader/actions/workflows/build.yml/badge.svg?branch=nightly)](https://github.com/nautechsystems/nautilus_trader/actions/workflows/build.yml) |
| `nightly` | [![version](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnautechsystems%2Fnautilus_trader%2Fnightly%2Fversion.json)](https://packages.nautechsystems.io/simple/nautilus-trader/index.html) | [![build](https://github.com/nautechsystems/nautilus_trader/actions/workflows/build.yml/badge.svg?branch=nightly)](https://github.com/nautechsystems/nautilus_trader/actions/workflows/build.yml) |
| `develop` | [![version](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnautechsystems%2Fnautilus_trader%2Fdevelop%2Fversion.json)](https://packages.nautechsystems.io/simple/nautilus-trader/index.html) | [![build](https://github.com/nautechsystems/nautilus_trader/actions/workflows/build.yml/badge.svg?branch=develop)](https://github.com/nautechsystems/nautilus_trader/actions/workflows/build.yml) |

| 平台               | Rust   | Python    |
| :----------------- | :----- | :-------- |
| `Linux (x86_64)`   | 1.95.0 | 3.12-3.14 |
| `Linux (ARM64)`    | 1.95.0 | 3.12-3.14 |
| `macOS (ARM64)`    | 1.95.0 | 3.12-3.14 |
| `Windows (x86_64)` | 1.95.0 | 3.12-3.14 |

- **文档**: <https://nautilustrader.io/docs/>
- **官网**: <https://nautilustrader.io>
- **技术支持**: [support@nautilustrader.io](mailto:support@nautilustrader.io)

## 简介

NautilusTrader 是一个开源的、生产级、Rust 原生的多资产、多交易所交易系统引擎。

整个系统在单一事件驱动架构中覆盖研究、确定性模拟和实盘执行，Python 作为控制面（control plane）负责策略逻辑、配置和编排。

这种分离同时带来了编译型交易引擎的性能与安全性，以及 Python 在系统组合与策略开发上的灵活性。
对于任务关键型工作负载，交易系统也可以完全用 Rust 编写。

研究系统与实盘系统使用相同的执行语义和确定性时间模型。策略从研究环境部署到生产环境无需修改代码，
这一**研究到实盘的语义一致性**（research-to-live parity）显著降低了通常会带来部署风险的偏差。

NautilusTrader 与资产类别无关。任何拥有 REST API 或 WebSocket 数据源的交易场所都可以通过模块化适配器接入。
目前的集成涵盖加密货币交易所（CEX 和 DEX）、传统市场（外汇、股票、期货、期权）和博彩交易所。

![nautilus-trader](https://github.com/nautechsystems/nautilus_trader/raw/develop/assets/nautilus-trader.png "nautilus-trader")

## 特性

- **高性能**：Rust 核心配合基于 [tokio](https://crates.io/crates/tokio) 的异步网络。
- **可靠**：Rust 提供类型与线程安全保证，可选 Redis 作为状态持久化后端。
- **可移植**：支持 Linux、macOS 与 Windows，可通过 Docker 部署。
- **灵活**：模块化适配器可接入任何 REST API 或 WebSocket 数据源。
- **高级**：支持 `IOC`、`FOK`、`GTC`、`GTD`、`DAY`、`AT_THE_OPEN`、`AT_THE_CLOSE` 等订单有效期类型，丰富的订单类型与条件触发；支持 `post-only`、`reduce-only`、冰山单等执行指令；支持 `OCO`、`OUO`、`OTO` 等连带订单。
- **可定制**：用户可自定义组件，也可基于 [缓存](https://nautilustrader.io/docs/latest/concepts/cache) 和 [消息总线](https://nautilustrader.io/docs/latest/concepts/message_bus) 从零搭建完整系统。
- **回测**：纳秒级精度，支持在多个交易场所、多个标的、多策略上同时使用历史报价 Tick、成交 Tick、K 线、订单簿和自定义数据进行回测。
- **实盘**：研究与实盘部署使用完全相同的策略实现。
- **多场所**：同时在多个交易场所运行做市和跨场所策略。
- **AI 训练**：引擎速度足以用于训练 AI 交易智能体（RL/ES）。

![nautilus](https://github.com/nautechsystems/nautilus_trader/raw/develop/assets/nautilus-art.png "nautilus")

> *nautilus —— 源自古希腊语，意为 "sailor"（水手），naus 意为 "ship"（船）。*
>
> *鹦鹉螺壳由模块化的腔室构成，其增长因子近似一条对数螺旋线。
> 这一理念可以延伸至设计与建筑的美学。*

## 为什么选择 NautilusTrader？

交易策略研究通常采用 Python 进行向量化分析，而生产交易系统则单独使用编译语言的事件驱动架构来实现。

NautilusTrader 消除了这一割裂。

Rust 原生核心为研究与实盘执行提供了确定性的事件驱动运行时，Python 担任控制面。
两种环境共享同一架构、同一执行语义、同一时间模型，因此策略无需重新实现即可从研究环境迁移到生产环境。

Python 绑定通过 [PyO3](https://pyo3.rs) 提供，目前正在从 Cython 逐步迁移过来。安装时无需 Rust 工具链。

本项目郑重作出 [Soundness Pledge（健全性承诺）](https://raphlinus.github.io/rust/2020/01/18/soundness-pledge.html)：

> "本项目的目标是不存在健全性缺陷。
> 开发者将尽最大努力规避此类问题，并欢迎社区协助分析与修复。"

> [!NOTE]
>
> **MSRV**：NautilusTrader 大量依赖 Rust 语言与编译器的改进。
> 因此，最低支持的 Rust 版本（MSRV）通常与 Rust 的最新稳定版本保持一致。

## 集成

NautilusTrader 采用模块化设计，通过*适配器*（adapters）工作。适配器将各交易场所与数据提供商的原始 API 转换为统一接口和标准化领域模型，从而实现对接。

目前支持的集成如下；详情请参见 [docs/integrations/](https://nautilustrader.io/docs/latest/integrations/)：

| 名称                                                                         | ID                    | 类型                | 状态                                                  | 文档                                       |
| :--------------------------------------------------------------------------- | :-------------------- | :------------------ | :---------------------------------------------------- | :----------------------------------------- |
| [AX Exchange](https://architect.exchange)                                    | `AX`                  | 永续合约交易所      | ![status](https://img.shields.io/badge/stable-green)  | [指南](docs/integrations/architect_ax.md)  |
| [Betfair](https://betfair.com)                                               | `BETFAIR`             | 体育博彩交易所      | ![status](https://img.shields.io/badge/stable-green)  | [指南](docs/integrations/betfair.md)       |
| [Binance](https://binance.com)                                               | `BINANCE`             | 加密货币交易所（CEX）| ![status](https://img.shields.io/badge/stable-green) | [指南](docs/integrations/binance.md)       |
| [Coinbase](https://coinbase.com)                                             | `COINBASE`            | 加密货币交易所（CEX）| ![status](https://img.shields.io/badge/beta-yellow)  | [指南](docs/integrations/coinbase.md)      |
| [BitMEX](https://www.bitmex.com)                                             | `BITMEX`              | 加密货币交易所（CEX）| ![status](https://img.shields.io/badge/stable-green) | [指南](docs/integrations/bitmex.md)        |
| [Bybit](https://www.bybit.com)                                               | `BYBIT`               | 加密货币交易所（CEX）| ![status](https://img.shields.io/badge/stable-green) | [指南](docs/integrations/bybit.md)         |
| [Databento](https://databento.com)                                           | `DATABENTO`           | 数据提供商          | ![status](https://img.shields.io/badge/stable-green)  | [指南](docs/integrations/databento.md)     |
| [Deribit](https://www.deribit.com)                                           | `DERIBIT`             | 加密货币交易所（CEX）| ![status](https://img.shields.io/badge/stable-green) | [指南](docs/integrations/deribit.md)       |
| [dYdX](https://dydx.exchange/)                                               | `DYDX`                | 加密货币交易所（DEX）| ![status](https://img.shields.io/badge/stable-green) | [指南](docs/integrations/dydx.md)          |
| [Hyperliquid](https://hyperliquid.xyz)                                       | `HYPERLIQUID`         | 加密货币交易所（DEX）| ![status](https://img.shields.io/badge/stable-green) | [指南](docs/integrations/hyperliquid.md)   |
| [Interactive Brokers](https://www.interactivebrokers.com)                    | `INTERACTIVE_BROKERS` | 经纪商（多场所）    | ![status](https://img.shields.io/badge/stable-green)  | [指南](docs/integrations/ib.md)            |
| [Kraken](https://kraken.com)                                                 | `KRAKEN`              | 加密货币交易所（CEX）| ![status](https://img.shields.io/badge/stable-green) | [指南](docs/integrations/kraken.md)        |
| [OKX](https://okx.com)                                                       | `OKX`                 | 加密货币交易所（CEX）| ![status](https://img.shields.io/badge/stable-green) | [指南](docs/integrations/okx.md)           |
| [Polymarket](https://polymarket.com)                                         | `POLYMARKET`          | 预测市场（DEX）     | ![status](https://img.shields.io/badge/stable-green)  | [指南](docs/integrations/polymarket.md)    |
| [Tardis](https://tardis.dev)                                                 | `TARDIS`              | 加密货币数据提供商  | ![status](https://img.shields.io/badge/stable-green)  | [指南](docs/integrations/tardis.md)        |

- **ID**：集成适配器客户端的默认客户端 ID。
- **类型**：集成的类型（通常对应交易场所的类别）。

### 状态说明

- `planned`：计划中，待开发。
- `building`：开发中，尚不可用。
- `beta`：已达最小可用状态，处于 Beta 测试阶段。
- `stable`：功能集与 API 已趋稳定，已在开发者与用户层面经过合理程度的测试（仍可能存在少量 bug）。

详情请参见 [Integrations](https://nautilustrader.io/docs/latest/integrations/) 文档。

## 路线图

[路线图](/ROADMAP.md) 阐述了 NautilusTrader 的战略方向。
当前重点包括完善 Rust 原生核心、改进文档、提升代码人体工学。

本开源项目专注于面向个人和小团队量化交易者的单节点回测与实盘交易。
UI 仪表盘、分布式编排、内置 AI/ML 工具等不在项目范围内，以便聚焦核心引擎与生态的可持续发展。

新集成提案应先以 RFC issue 形式提出，与团队讨论合适性后再提交 PR。
具体指引请参见 [社区贡献的集成](/ROADMAP.md#community-contributed-integrations)。

## 版本与发布

> [!WARNING]
>
> **NautilusTrader 仍处于积极开发阶段**。部分功能可能尚不完善；尽管 API 趋于稳定，
> 版本之间仍可能出现破坏性变更。我们会**尽力**在发布说明中记录这些变更。

我们的目标是按**双周发布**节奏更新，但实验性或大型功能可能造成延迟。

### 分支

我们力求各分支均保持构建可通过的稳定状态。

- `master`：对应最新发布版本的源代码；推荐用于生产环境。
- `nightly`：`develop` 分支的每日快照，便于早期测试；每天 **UTC 14:00** 合并，必要时也会合并。
- `develop`：贡献者和功能开发使用的活跃开发分支。

> [!NOTE]
>
> 我们的[路线图](/ROADMAP.md)目标是在 **2.x 版本**实现稳定 API（很可能在 Rust 迁移完成之后）。
> 达成这一里程碑后，我们计划为任何 API 变更实施正式的弃用流程。
> 在此之前，这种做法可让我们保持快速迭代。

## 精度模式

NautilusTrader 为其核心值类型（`Price`、`Quantity`、`Money`）支持两种精度模式，区别在于内部位宽和最大小数精度。

- **高精度模式**：128 位整数，最多 16 位小数精度，数值范围更大。
- **标准精度模式**：64 位整数，最多 9 位小数精度，数值范围较小。

> [!NOTE]
>
> Linux 和 macOS 上的官方 Python wheel 默认使用高精度（128 位）模式。
> Windows 上仅提供标准精度（64 位）Python wheel，因为 MSVC 的 C/C++ 前端不支持 `__int128`，
> 导致 Cython/FFI 层无法处理 128 位整数。
>
> 对于纯 Rust crate，所有平台（包括 Windows）都可启用高精度模式，因为 Rust 通过软件模拟处理
> `i128`/`u128`。默认采用标准精度，需显式启用 `high-precision` 特性开关方可切换。

详情请参见 [安装指南](https://nautilustrader.io/docs/latest/getting_started/installation)。

**Rust 特性开关**：要在 Rust 中启用高精度模式，需在 Cargo.toml 中添加 `high-precision` 特性：

```toml
[dependencies]
nautilus_model = { version = "*", features = ["high-precision"] }
```

## 安装

我们建议使用最新受支持的 Python 版本，并在虚拟环境中安装 [nautilus_trader](https://pypi.org/project/nautilus_trader/)，以隔离依赖。

**支持两种安装方式**：

1. 从 PyPI 或 Nautech Systems 包索引获取预构建二进制 wheel。
2. 从源码构建。

> [!TIP]
>
> 我们强烈推荐使用 [uv](https://docs.astral.sh/uv) 包管理器配合"原生"CPython。
>
> Conda 等其他 Python 发行版*可能*可用，但未正式支持。

### 从 PyPI 安装

使用 Python 的 pip 包管理器从 PyPI 安装最新二进制 wheel（或源码包）：

```bash
pip install -U nautilus_trader
```

为特定集成安装可选依赖（"extras"，例如 `betfair`、`docker`、`dydx`、`ib`、`polymarket`、`visualization`）：

```bash
pip install -U "nautilus_trader[docker,ib]"
```

完整 extras 列表请参见 [安装指南](https://nautilustrader.io/docs/latest/getting_started/installation#extras)。

### 从 Nautech Systems 包索引安装

Nautech Systems 包索引（`packages.nautechsystems.io`）遵循 [PEP-503](https://peps.python.org/pep-0503/) 规范，
同时托管 `nautilus_trader` 的稳定版与开发版二进制 wheel。
用户可以由此安装最新稳定发布版，也可以安装预发布版本进行测试。

#### 稳定版 wheel

稳定版 wheel 对应 `nautilus_trader` 在 PyPI 上的官方发布，采用标准版本号。

安装最新稳定发布版：

```bash
pip install -U nautilus_trader --index-url=https://packages.nautechsystems.io/simple
```

> [!TIP]
>
> 如果希望 pip 在找不到包时自动回退到 PyPI，可改用 `--extra-index-url` 而非 `--index-url`。

#### 开发版 wheel

开发版 wheel 从 `nightly` 和 `develop` 两个分支发布，便于用户提前测试新特性与修复。

这一流程也有助于节省计算资源，方便用户直接获取 CI 流水线中测试过的二进制文件，
同时遵循 [PEP-440](https://peps.python.org/pep-0440/) 版本规范：

- `develop` 版 wheel 使用 `dev{date}+{build_number}` 格式（例如 `1.208.0.dev20241212+7001`）。
- `nightly` 版 wheel 使用 `a{date}`（alpha）格式（例如 `1.208.0a20241212`）。

| 平台               | Nightly | Develop |
| :----------------- | :------ | :------ |
| `Linux (x86_64)`   | ✓       | ✓       |
| `Linux (ARM64)`    | ✓       | -       |
| `macOS (ARM64)`    | ✓       | -       |
| `Windows (x86_64)` | ✓       | -       |

**注**：`develop` 分支的开发版 wheel 仅发布 Linux x86_64 版本。
Windows、macOS 和 Linux ARM64 的构建在 nightly 计划下执行，以保持 CI 反馈的速度。

> [!WARNING]
>
> 我们不建议在生产环境中使用开发版 wheel，例如管理真实资金的实盘交易。

#### 安装命令

默认情况下，pip 会安装最新稳定版。加上 `--pre` 标志可使 pip 同时考虑预发布版本（含开发版 wheel）。

安装最新可用的预发布版（含开发版 wheel）：

```bash
pip install -U nautilus_trader --pre --index-url=https://packages.nautechsystems.io/simple
```

安装特定开发版 wheel（例如 2025 年 10 月 26 日的 `1.221.0a20251026`）：

```bash
pip install nautilus_trader==1.221.0a20251026 --index-url=https://packages.nautechsystems.io/simple
```

#### 可用版本

可在[包索引页面](https://packages.nautechsystems.io/simple/nautilus-trader/index.html)查看所有可用的 `nautilus_trader` 版本。

也可以通过脚本获取并列出可用版本：

```bash
curl -s https://packages.nautechsystems.io/simple/nautilus-trader/index.html | sed -n 's/.*<a href="\([^"]*\)".*/\1/p' | awk -F'#' '{print $1}' | sort
```

> [!NOTE]
>
> Linux 上请使用 `ldd --version` 确认 glibc 版本，安装二进制 wheel 前需确保版本不低于 **2.35**。

#### 分支更新策略

- `develop` 分支 wheel（`.dev`）：每次合并提交都会持续构建并发布。
- `nightly` 分支 wheel（`a`）：在 **UTC 14:00** 自动合并 `develop` 分支后（如有变更），每日构建并发布。

#### 保留策略

- `develop` 分支 wheel（`.dev`）：仅保留最近一次构建。
- `nightly` 分支 wheel（`a`）：仅保留最近 30 次构建。

#### 验证构建来源

项目发布的所有构建产物均附带 CI/CD 流水线生成的密码学证明：

- Python wheel 和源码分发包（PyPI、GitHub Releases、Nautech Systems 包索引）：[SLSA](https://slsa.dev/) 构建来源证明。
- Docker 镜像（`ghcr.io/nautechsystems/nautilus_trader`、`ghcr.io/nautechsystems/jupyterlab`）：基于无密钥的 [cosign](https://github.com/sigstore/cosign) 签名以及 SPDX SBOM 证明。

两类证明均通过 [Sigstore](https://www.sigstore.dev/) 颁发，并绑定到特定的提交 SHA，
因此校验后可确认构件确实由官方 NautilusTrader GitHub Actions 工作流生成，且自此未被篡改。

具体校验步骤请参见 `SECURITY.md` 中的 [Verifying releases](SECURITY.md#verifying-releases) 章节。

> [!NOTE]
>
> 校验 Python 构件需要 [GitHub CLI](https://cli.github.com/)（`gh`），校验 Docker 镜像需要 [cosign](https://github.com/sigstore/cosign)。
> `develop` 和 `nightly` 分支的开发版 wheel 同样附带证明。

### 从源码安装

如果先按 `pyproject.toml` 中的要求安装构建依赖，就可以使用 pip 从源码安装。

1. 安装 [rustup](https://rustup.rs/)（Rust 工具链安装器）：
   - Linux 与 macOS：

       ```bash
       curl https://sh.rustup.rs -sSf | sh
       ```

   - Windows：
       - 下载并安装 [`rustup-init.exe`](https://win.rustup.rs/x86_64)
       - 通过 [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 安装"使用 C++ 的桌面开发"
   - 验证（所有系统）：
       在终端中运行 `rustc --version`

2. 在当前 shell 中启用 `cargo`：
   - Linux 与 macOS：

       ```bash
       source $HOME/.cargo/env
       ```

   - Windows：
     - 启动新的 PowerShell

3. 安装 [clang](https://clang.llvm.org/)（LLVM 的 C 语言前端）：
   - Linux（同时安装 [lld](https://lld.llvm.org/)，作为 Rust 链接器以加速构建）：

       ```bash
       sudo apt-get install clang lld
       ```

   - macOS：

       ```bash
       xcode-select --install
       ```

   - Windows：
       1. 在 [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 中添加 Clang：
          - 开始 | Visual Studio Installer | 修改 | 勾选 "适用于 Windows 的 C++ Clang 工具（最新版）" | 修改
       2. 在当前 shell 中启用 `clang`：

          ```powershell
          [System.Environment]::SetEnvironmentVariable('path', "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\Llvm\x64\bin\;" + $env:Path,"User")
          ```

   - 验证（所有系统）：
       在终端中运行 `clang --version`

4. 安装 uv（详情参见 [uv 安装指南](https://docs.astral.sh/uv/getting-started/installation)）：

    - Linux 与 macOS：

        ```bash
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```

    - Windows（PowerShell）：

        ```powershell
        irm https://astral.sh/uv/install.ps1 | iex
        ```

5. 使用 `git` 克隆源码并在项目根目录下安装：

    ```bash
    git clone --branch develop --depth 1 https://github.com/nautechsystems/nautilus_trader
    cd nautilus_trader
    uv sync --all-extras
    ```

> [!NOTE]
>
> `--depth 1` 仅拉取最新一次提交，可加快克隆速度、减少体积。

6. 设置 PyO3 编译所需的环境变量（仅 Linux 和 macOS）。在 `uv sync` 后于仓库根目录执行：

    ```bash
    # 为 PyO3 设置 Python 可执行文件路径
    export PYO3_PYTHON="$PWD/.venv/bin/python"

    # 仅 Linux：为 uv 管理的 Python 运行时设置库路径
    PYTHON_LIB_DIR="$("$PYO3_PYTHON" -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR"))')"
    export LD_LIBRARY_PATH="$PYTHON_LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

    # 使用 uv 安装的 Python 运行 Rust 测试时所需
    export PYTHONHOME="$("$PYO3_PYTHON" -c 'import sys; print(sys.base_prefix)')"
    ```

> [!NOTE]
>
> `LD_LIBRARY_PATH` 仅 Linux 需要，macOS 不需要。
>
> 当使用 uv 安装的 Python 运行 `make cargo-test` 时，需要设置 `PYTHONHOME`。
> 否则依赖 PyO3 的测试可能无法定位 Python 运行时。

其他选项与更多细节请参见 [安装指南](https://nautilustrader.io/docs/latest/getting_started/installation)。

## Redis

在 NautilusTrader 中使用 [Redis](https://redis.io) 是**可选**的，仅在你将其配置为
[缓存](https://nautilustrader.io/docs/latest/concepts/cache) 数据库或
[消息总线](https://nautilustrader.io/docs/latest/concepts/message_bus) 的后端时才需要。
详情参见[安装指南](https://nautilustrader.io/docs/latest/getting_started/installation#redis)的 **Redis** 部分。

## Makefile

仓库提供了 `Makefile` 来自动化大多数开发场景下的安装与构建任务。常用 target 包括：

- `make install`：以 `release` 模式安装，包含所有依赖组和 extras。
- `make install-debug`：与 `make install` 相同，但使用 `debug` 模式。
- `make install-just-deps`：仅安装 `main`、`dev` 和 `test` 依赖（不安装包本身）。
- `make build`：以 `release` 模式运行构建脚本（默认）。
- `make build-debug`：以 `debug` 模式运行构建脚本。
- `make build-wheel`：在 `release` 模式下使用 uv 构建 wheel。
- `make build-wheel-debug`：在 `debug` 模式下使用 uv 构建 wheel。
- `make cargo-test`：使用 `cargo-nextest` 运行所有 Rust crate 的测试。
- `make clean`：删除所有构建产物，例如 `.so` 或 `.dll` 文件。
- `make distclean`：**警告** 删除仓库中所有未被 git 跟踪的文件，包括尚未 `git add` 的源文件。
- `make docs`：使用 Sphinx 构建 HTML 文档。
- `make pre-commit`：对所有文件运行 pre-commit 检查。
- `make ruff`：使用 `pyproject.toml` 中的配置对所有文件运行 ruff（含自动修复）。
- `make pytest`：使用 `pytest` 运行所有测试。
- `make test-performance`：使用 [codspeed](https://codspeed.io) 运行性能测试。

> [!TIP]
>
> 运行 `make help` 可查看所有可用 make target 的说明。

> [!TIP]
>
> 关于基础设施集成测试的运行方法，请参见 [crates/infrastructure/TESTS.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/crates/infrastructure/TESTS.md)。

## 示例

指标和策略可以用 Python、Cython 或 Rust 开发。对性能或延迟敏感的应用我们推荐 Rust。下面是一些示例：

- 用 Python 编写的[指标](/nautilus_trader/examples/indicators/ema_python.py)示例。
- 用 Cython 实现的[指标](/nautilus_trader/indicators/)。
- 用 Python 编写的[策略](/nautilus_trader/examples/strategies/)示例。
- 直接使用 `BacktestEngine` 的[回测](/examples/backtest/)示例。

## Docker

Docker 容器以下列变体标签构建：

- `nautilus_trader:latest`：安装最新发布版。
- `nautilus_trader:nightly`：安装 `nightly` 分支头部代码。
- `jupyterlab:latest`：安装最新发布版，并附带 `jupyterlab` 及示例回测 notebook 和配套数据。
- `jupyterlab:nightly`：安装 `nightly` 分支头部代码，并附带 `jupyterlab` 及示例回测 notebook 和配套数据。

拉取容器镜像：

```bash
docker pull ghcr.io/nautechsystems/<image_variant_tag> --platform linux/amd64
```

通过下列命令启动回测示例容器：

```bash
docker pull ghcr.io/nautechsystems/jupyterlab:nightly --platform linux/amd64
docker run -p 8888:8888 ghcr.io/nautechsystems/jupyterlab:nightly
```

然后在浏览器中打开：

```bash
http://127.0.0.1:8888/lab
```

> [!WARNING]
>
> 示例使用 `log_level="ERROR"`，因为 Nautilus 日志输出会超过 Jupyter 的 stdout 速率限制，
> 在更低日志级别下会导致 notebook 挂起。

## 开发

我们致力于为这个 Rust、Python、Cython 混合代码库提供尽可能愉悦的开发者体验。
有用信息请参见 [开发者指南](https://nautilustrader.io/docs/latest/developer_guide/)。

> [!TIP]
>
> 修改 Rust 或 Cython 代码后运行 `make build-debug` 重新编译，可获得最高效的开发流程。

### 使用 Rust 测试

[cargo-nextest](https://nexte.st) 是 NautilusTrader 标准的 Rust 测试运行器。
它的核心优势是将每个测试隔离在独立进程中，避免相互干扰，从而提升测试可靠性。

安装 cargo-nextest：

```bash
cargo install cargo-nextest
```

> [!TIP]
>
> 使用 `make cargo-test` 运行 Rust 测试，该命令使用 **cargo-nextest** 并启用了高效配置。

## 贡献

感谢你考虑为 NautilusTrader 做出贡献！我们欢迎任何形式的协助以改进项目。
若你有改进想法或 bug 修复，建议先在 GitHub 上提交 [issue](https://github.com/nautechsystems/nautilus_trader/issues)
与团队讨论。这有助于确保你的贡献与项目目标一致，并避免重复劳动。

开始之前，请阅读项目路线图中的[开源范围](/ROADMAP.md#open-source-scope)以了解哪些工作在范围内、哪些不在。

准备开始时，请遵循 [CONTRIBUTING.md](https://github.com/nautechsystems/nautilus_trader/blob/develop/CONTRIBUTING.md) 中的指南，
包括签署贡献者许可协议（Contributor License Agreement，CLA），以便你的贡献可以并入项目。

> [!NOTE]
>
> Pull request 应以 `develop` 分支（默认分支）为目标。新特性与改进会在此分支集成，然后再发布。

再次感谢你对 NautilusTrader 的关注！我们期待审阅你的贡献，与你一起改进这个项目。

## 社区

欢迎加入我们的 [Discord](https://discord.gg/NautilusTrader) 用户与贡献者社区，
与大家交流并及时获取 NautilusTrader 的最新公告与功能。无论你是希望参与贡献的开发者，
还是想更深入了解平台的用户，我们的 Discord 服务器都欢迎你。

> [!WARNING]
>
> NautilusTrader 不发行、不推广、不背书任何加密货币代币。任何相反的声明或宣传均为未授权且不实的内容。
>
> NautilusTrader 的所有官方公告和通讯将仅通过 <https://nautilustrader.io>、我们的
> [GitHub](https://github.com/nautechsystems)、[Discord 服务器](https://discord.gg/NautilusTrader)
> 或经过验证的 X（Twitter）账号 [@NautilusTrader](https://x.com/NautilusTrader) 发布。
>
> 如发现可疑活动，请向相应平台举报，并通过 <info@nautechsystems.io> 联系我们。

## 安全

如需报告漏洞，请参见我们的[安全策略](SECURITY.md)。
完整的安全策略（含供应链安全）请参见 <https://nautilustrader.io/security/>。

## 许可证

NautilusTrader 源代码托管在 GitHub，采用 [GNU Lesser General Public License v3.0](https://www.gnu.org/licenses/lgpl-3.0.en.html) 许可。
项目欢迎贡献，但需先完成标准的 [贡献者许可协议（CLA）](https://github.com/nautechsystems/nautilus_trader/blob/develop/CLA.md)。

---

NautilusTrader™ 由 Nautech Systems 开发与维护，Nautech Systems 是一家专注于高性能交易系统开发的技术公司。
详情请访问 <https://nautilustrader.io>。

使用本软件即表示你接受 [免责声明](https://nautilustrader.io/legal/disclaimer/)。

© 2015-2026 Nautech Systems Pty Ltd. 保留所有权利。

![nautechsystems](https://github.com/nautechsystems/nautilus_trader/raw/develop/assets/ns-logo.png "nautechsystems")
<img src="https://github.com/nautechsystems/nautilus_trader/raw/develop/assets/ferris.png" width="128">
