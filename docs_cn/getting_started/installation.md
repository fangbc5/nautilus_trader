# 安装

> 本文档为 [English 原文](../../docs/getting_started/installation.md) 的中文翻译版本。如有歧义请以英文原版为准。

NautilusTrader 在以下 64 位平台上官方支持 Python 3.12-3.14：

| 操作系统               | 支持版本           | CPU 架构          |
|------------------------|--------------------|-------------------|
| Linux (Ubuntu)         | 22.04 及更高版本   | x86_64            |
| Linux (Ubuntu)         | 22.04 及更高版本   | ARM64             |
| macOS                  | 15.0 及更高版本    | ARM64             |
| Windows Server         | 2022 及更高版本    | x86_64            |

:::note
NautilusTrader 也可能在其他平台上正常工作，但只有上表中列出的平台是开发者经常使用并在 CI 中测试的。
:::

持续的 CI 覆盖来自我们使用的 GitHub Actions runner：

- `Linux (Ubuntu)` 构建当前固定使用 `ubuntu-22.04`，以保持与 glibc 2.35 的兼容性，即使 `ubuntu-latest` 已经更新到更高版本。
- `macOS (ARM64)` 构建运行在 `macos-latest` 上，因此支持范围会随该 runner 镜像的更新而变化。
- `Windows (x86_64)` 构建当前固定使用 `windows-2022`，以保持工具链稳定。

在 Linux 上，请先用 `ldd --version` 确认你的 glibc 版本，确保版本号为 2.35 或更高，再继续后续步骤。

我们建议使用受支持的最新 Python 版本，并在虚拟环境中安装 [nautilus_trader](https://pypi.org/project/nautilus_trader/) 以隔离依赖。

**目前有两种受支持的安装方式**：

1. 从 PyPI *或* Nautech Systems package index 安装预构建的二进制 wheel。
2. 从源码构建。

:::tip
我们强烈建议使用 [uv](https://docs.astral.sh/uv) 包管理器配合 "原生" CPython 进行安装。

Conda 及其他 Python 发行版 *可能* 可用，但并非官方支持。
:::

## 从 PyPI 安装

要从 PyPI 安装最新的 [nautilus_trader](https://pypi.org/project/nautilus_trader/) 二进制 wheel（或 sdist 包）：

```bash
uv pip install nautilus_trader
```

## 可选额外组件（Extras）

可以将可选依赖以 "extras" 方式安装，用于特定集成：

- `betfair`：Betfair 适配器（集成）所需依赖。
- `docker`：使用 IB gateway（配合 Interactive Brokers 适配器）时所需的 Docker 依赖。
- `ib`：Interactive Brokers 适配器（集成）所需依赖。
- `polymarket`：Polymarket 适配器（集成）所需依赖。
- `visualization`：基于 Plotly 的交互式回测报告（tearsheet）与图表。

带特定 extras 安装：

```bash
uv pip install "nautilus_trader[docker,ib]"
```

## 从 Nautech Systems package index 安装

Nautech Systems 的 package index（`packages.nautechsystems.io`）符合 [PEP-503](https://peps.python.org/pep-0503/) 规范，同时托管 `nautilus_trader` 的稳定版与开发版二进制 wheel。
这样用户既可以安装最新的稳定版本，也可以安装预发布版本以进行测试。

### 稳定版 wheel

稳定版 wheel 对应 `nautilus_trader` 在 PyPI 上的官方发布版本，使用标准版本号。

安装最新稳定版本：

```bash
uv pip install nautilus_trader --index-url=https://packages.nautechsystems.io/simple
```

:::tip
如果希望 uv 在找不到包时自动回退到 PyPI，请用 `--extra-index-url` 替代 `--index-url`：

:::

### 开发版 wheel

开发版 wheel 同时从 `nightly` 与 `develop` 分支发布，允许用户在稳定版本发布之前抢先测试新特性与修复。

这个流程还能节省算力资源，方便用户直接获取在 CI 流水线中测试过的二进制文件，同时遵循 [PEP-440](https://peps.python.org/pep-0440/) 版本号规范：

- `develop` 版 wheel 使用版本号格式 `dev{date}+{build_number}`（例如 `1.208.0.dev20241212+7001`）。
- `nightly` 版 wheel 使用版本号格式 `a{date}`（alpha，例如 `1.208.0a20241212`）。

| 平台               | Nightly | Develop |
| :----------------- | :------ | :------ |
| `Linux (x86_64)`   | ✓       | ✓       |
| `Linux (ARM64)`    | ✓       | -       |
| `macOS (ARM64)`    | ✓       | -       |
| `Windows (x86_64)` | ✓       | -       |

**注意**：来自 `develop` 分支的开发版 wheel 仅针对 Linux x86_64 发布。
Windows、macOS 与 Linux ARM64 的构建放在 nightly 调度中执行，以保持 CI 的反馈速度。

:::warning
我们不建议在生产环境（例如控制真实资金的实盘交易）中使用开发版 wheel。
:::

### 安装命令

默认情况下，uv 会安装最新的稳定版本。添加 `--pre` 标志会让 uv 同时考虑预发布版本（包括开发版 wheel）。

安装最新可用的预发布版本（包括开发版 wheel）：

```bash
uv pip install nautilus_trader --pre --index-url=https://packages.nautechsystems.io/simple
```

安装某个指定的开发版 wheel（例如 2025 年 9 月 12 日的 `1.221.0a20250912`）：

```bash
uv pip install nautilus_trader==1.221.0a20250912 --index-url=https://packages.nautechsystems.io/simple
```

### 可用版本列表

你可以在 [package index](https://packages.nautechsystems.io/simple/nautilus-trader/index.html) 上查看 `nautilus_trader` 的所有可用版本。

以编程方式请求并列出可用版本：

```bash
curl -s https://packages.nautechsystems.io/simple/nautilus-trader/index.html | grep -oP '(?<=<a href=")[^"]+(?=")' | awk -F'#' '{print $1}' | sort
```

### 分支更新策略

- `develop` 分支 wheel（`.dev`）：每次合并提交后持续构建并发布。
- `nightly` 分支 wheel（`a`）：每天 **UTC 14:00** 自动合并 `develop` 分支后构建并发布（仅在有改动时）。

### 保留策略

- `develop` 分支 wheel（`.dev`）：仅保留最近一次的 wheel 构建。
- `nightly` 分支 wheel（`a`）：仅保留最近 30 次 wheel 构建。

### 验证构建来源（build provenance）

项目发布的所有构建产物均带有由 CI/CD 流水线生成的加密证明：

- Python wheel 与源码分发包（PyPI、GitHub Releases、Nautech Systems package index）：[SLSA](https://slsa.dev/) 构建溯源证明。
- Docker 镜像（`ghcr.io/nautechsystems/nautilus_trader`、`ghcr.io/nautechsystems/jupyterlab`）：keyless 模式下的 [cosign](https://github.com/sigstore/cosign) 签名以及 SPDX SBOM 证明。

两者均通过 [Sigstore](https://www.sigstore.dev/) 颁发，并绑定到具体的 commit SHA，因此验证后可以确认该产物确实由官方的 NautilusTrader GitHub Actions 工作流生产，并且自构建以来未被篡改。

逐步验证命令请参阅 `SECURITY.md` 中的 [Verifying releases](https://github.com/nautechsystems/nautilus_trader/blob/develop/SECURITY.md#verifying-releases)。

:::note
验证 Python 构建产物需要 [GitHub CLI](https://cli.github.com/)（`gh`），验证 Docker 镜像需要 [cosign](https://github.com/sigstore/cosign)。
来自 `develop` 与 `nightly` 分支的开发版 wheel 同样带有证明。
:::

## 从源码构建

只要先按 `pyproject.toml` 中的要求安装好构建依赖，就可以使用 pip 从源码安装。

### 1. 安装 rustup

安装 [rustup](https://rustup.rs/)（Rust 工具链安装器）：

```bash tab="Linux/macOS"
curl https://sh.rustup.rs -sSf | sh
```

```powershell tab="Windows"
# Download and install rustup-init.exe from https://win.rustup.rs/x86_64
# Also install "Desktop development with C++" via Build Tools for Visual Studio 2022
```

验证：`rustc --version`

### 2. 启用 cargo

在当前 shell 中启用 `cargo`：

```bash tab="Linux/macOS"
source $HOME/.cargo/env
```

```powershell tab="Windows"
# Start a new PowerShell session
```

### 3. 安装 clang

安装 [clang](https://clang.llvm.org/)（LLVM 的 C 语言前端）。在 Linux 上这一步同时会安装 [lld](https://lld.llvm.org/)，并将其配置为 Rust 的链接器，以加快构建速度：

```bash tab="Linux"
sudo apt-get install clang lld
```

```powershell tab="Windows"
# 1. Add Clang via Visual Studio Installer:
#    Modify > C++ Clang tools for Windows (latest) > Modify
# 2. Add to PATH:
[System.Environment]::SetEnvironmentVariable('path', "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\Llvm\x64\bin\;" + $env:Path,"User")
```

验证：`clang --version`

### 4. 安装 uv

安装 [uv](https://docs.astral.sh/uv/getting-started/installation)：

```bash tab="Linux/macOS"
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell tab="Windows"
irm https://astral.sh/uv/install.ps1 | iex
```

### 5. 克隆并安装

使用 `git` 克隆源码仓库，然后在项目根目录执行安装：

```bash
git clone --branch develop --depth 1 https://github.com/nautechsystems/nautilus_trader
cd nautilus_trader
uv sync --all-extras
```

:::note
`--depth 1` 仅拉取最新一次提交，可获得更快、更轻量的克隆。
:::

### 6. 安装 Cap'n Proto（用于开发）

如果你打算启用 `capnp` Rust 特性、重新生成序列化 schema，或参与序列化相关代码开发，请安装 [Cap'n Proto](https://capnproto.org/)。在 Linux 或 macOS 上可使用仓库提供的脚本安装 `tools.toml` 中固定的版本：

```bash
./scripts/install-capnp.sh
```

验证：`capnp --version`

:::note
Cap'n Proto 是开发依赖。安装预构建 wheel 时并不需要它。
:::

### 7. 设置环境变量

为 PyO3 编译设置环境变量（仅适用于 Linux 与 macOS）。在执行完 `uv sync` 后，从仓库根目录运行以下命令：

```bash
# Set the Python executable path for PyO3
export PYO3_PYTHON="$PWD/.venv/bin/python"

# Linux only: Set the library path for the uv-managed Python runtime
PYTHON_LIB_DIR="$("$PYO3_PYTHON" -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR"))')"
export LD_LIBRARY_PATH="$PYTHON_LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

# Required for Rust tests when using uv-installed Python
export PYTHONHOME="$("$PYO3_PYTHON" -c 'import sys; print(sys.base_prefix)')"
```

:::note
`LD_LIBRARY_PATH` 的导出仅在 Linux 上需要，macOS 不需要。

使用通过 `uv` 安装的 Python 运行 `make cargo-test` 时需要设置 `PYTHONHOME`。
如果未设置，依赖 PyO3 的测试可能找不到 Python 运行时，因此会失败。
:::

## 从 GitHub release 安装

要从 GitHub 安装二进制 wheel，请先前往 [最新发布版本](https://github.com/nautechsystems/nautilus_trader/releases/latest)。
为你的操作系统与 Python 版本下载对应的 `.whl` 文件，然后执行：

```bash
uv pip install <file-name>.whl
```

## 版本号与发布

NautilusTrader 仍在持续开发中。一些特性可能尚未完善；虽然 API 正在逐步稳定，但版本之间仍可能出现破坏性变更。
我们会尽量在 release notes 中记录这些变更，但仅尽 **力而为**。

我们的目标是按 **每两周一次** 的节奏发布版本，不过较大或带实验性质的特性可能造成延期。

只有在你愿意持续跟进这些变更的前提下，才适合使用 NautilusTrader。

## Redis

在 NautilusTrader 中使用 [Redis](https://redis.io) 是 **可选** 的，仅当你需要把它作为缓存数据库或 [消息总线](../concepts/message_bus.md) 的后端时才需要。

:::info
受支持的 Redis 最低版本为 6.2（[streams](https://redis.io/docs/latest/develop/data-types/streams/) 功能要求该版本）。
:::

如需快速搭建，我们建议使用 [Redis 的 Docker 容器](https://hub.docker.com/_/redis/)。你可以在 `.docker` 目录中找到一个示例配置，或者运行以下命令直接启动容器：

```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

这条命令会：

- 如果本地没有 Redis 镜像，则从 Docker Hub 拉取最新版本。
- 以后台模式（`-d`）运行容器。
- 将容器命名为 `redis`，便于后续引用。
- 将 Redis 暴露在默认端口 6379，使本机上的 NautilusTrader 可以访问。

管理 Redis 容器：

- 使用 `docker start redis` 启动
- 使用 `docker stop redis` 停止

:::tip
我们推荐使用 [Redis Insight](https://redis.io/insight/) 作为 GUI，以便高效地可视化和调试 Redis 数据。
:::

## 精度模式（Precision mode）

NautilusTrader 为其核心值类型（`Price`、`Quantity`、`Money`）支持两种精度模式，二者在内部位宽和最大小数精度方面有所不同。

- **高精度（high-precision）**：使用 128 位整数，最多支持 16 位小数精度，数值范围更大。
- **标准精度（standard-precision）**：使用 64 位整数，最多支持 9 位小数精度，数值范围较小。

:::note
在 Linux 与 macOS 上，官方 Python wheel 默认采用高精度模式（128 位）。
在 Windows 上仅提供标准精度（64 位）的 Python wheel，因为 MSVC 的 C/C++ 前端不支持 `__int128`，Cython/FFI 层无法处理 128 位整数。

对于纯 Rust crate，高精度模式可以在所有平台上工作（包括 Windows），因为 Rust 通过软件模拟实现了 `i128`/`u128`。默认情况下使用标准精度，除非你显式启用 `high-precision` 特性开关（feature flag）。
:::

性能权衡是：在典型回测中，标准精度大约快 ~3-5%，但小数精度较低、可表示的数值范围也较小。

:::note
对比两种模式的性能基准测试仍在准备中。
:::

### 构建配置

精度模式由以下方式决定：

- 在编译期间设置 `HIGH_PRECISION` 环境变量，**或者**
- 显式启用 `high-precision` 这一 Rust 特性开关。

```bash tab="High-precision (128-bit)"
export HIGH_PRECISION=true
make install-debug
```

```bash tab="Standard-precision (64-bit)"
export HIGH_PRECISION=false
make install-debug
```

### Rust 特性开关

要在 Rust 中启用高精度模式（128 位），请在 `Cargo.toml` 中添加 `high-precision` 特性：

```toml
[dependencies]
nautilus_core = { version = "*", features = ["high-precision"] }
```

:::info
更多细节请参阅 [Value Types](../concepts/overview.md#value-types) 规范。
:::
