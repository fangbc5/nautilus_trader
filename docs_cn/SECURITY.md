# 安全政策

> 本文档为 [English 原文](../SECURITY.md) 的中文翻译版本。如有歧义请以英文原版为准。

安全是 NautilusTrader 项目的优先事项，我们重视那些帮助识别和解决漏洞的人员所做的工作。如果你发现了一个安全问题，请遵循下方指南。

完整的安全政策请参阅 <https://nautilustrader.io/security/>。

## 范围

本政策涵盖：

- NautilusTrader 开源软件以及官方仓库。
- Nautech Systems 网站（nautilustrader.io）。

第三方服务、交易所和数据提供商不在覆盖范围内。

## 漏洞报告

**首选方式：** [GitHub 安全公告（Security Advisories）](https://github.com/nautechsystems/nautilus_trader/security/advisories/new)

这允许在公开披露之前进行私密披露和协调。你将在安全公告和发布说明中获得致谢。

**备选方式：** 电子邮件 <security@nautechsystems.io>

对于通过电子邮件提交的敏感报告，你可以请求我们的 PGP 公钥用于加密通信。

请包含：漏洞描述、复现步骤、受影响版本，以及（如有）建议的修复方案。

## 响应时间线

我们承诺：

- **初次响应**：在报告提交后 48 小时内。
- **状态更新**：在 7 天内提供初步评估。
- **修复时间线**：关键漏洞在 30 天内修补；其他问题在 90 天内修补。
- **协调披露**：我们将与你协商一个公开披露日期。

## 负责任的披露

我们鼓励对你可能发现的任何安全漏洞进行负责任的披露。报告时，我们请你：

- 在修复方案可用之前，不要公开披露该漏洞。
- 仅在演示漏洞所必需的范围内利用该问题。
- 不要访问未经授权的数据或破坏系统。
- 遵守所有适用法律。

我们将在安全公告和发布说明中致谢你的贡献，除非你希望保持匿名。

## 受支持的版本

我们仅支持 NautilusTrader 的最新版本。如果你使用的是较旧版本，漏洞可能已在较新版本中被修复。

## 漏洞赏金计划

目前，我们没有正式的漏洞赏金计划。我们感谢任何帮助我们提升平台安全性的努力，并将尽力恰当地认可和致谢你的贡献。

## 安全基础设施

NautilusTrader 在开发与发布生命周期中采用了多层安全措施：

### 源代码与评审控制

- **CODEOWNERS**：关键基础设施文件、依赖清单和锁文件在合并前需要核心团队评审。
- **分支与标签规则集**：受保护分支要求签名提交并通过 CI 检查。匹配 `v*` 的发布标签在创建后不可变更。
- **源限制**：Rust 包仅来源于 crates.io。禁止使用 Git 依赖和未知 registry。

### 依赖接入控制

- **版本锁定与锁文件**：Rust 依赖在 `Cargo.lock` 中通过加密校验和锁定。Python 依赖在 `uv.lock` 和 `python/uv.lock` 中通过完整性哈希锁定。禁止使用通配符版本要求。
- **依赖与工具冷却期**：Python 依赖解析通过 `pyproject.toml` 中的 `exclude-newer` 排除过去 3 天内发布的包。开发工具在 `tools.toml`、`Cargo.toml` 和相关清单中锁定到明确版本，版本提升会在安全审计中评审。Rust crate 更新通过我们的 cargo-vet 审计流程和策略进行评审。冷却期为社区争取了时间，以检测和隔离被入侵的发布版本。
- **仅 wheel 的 Python 安装**：`[tool.uv]` 中的 `no-build-package` 列表枚举了在 `uv.lock` 中锁定的每个第三方包，并禁止 `uv` 从源码构建任何此类包。在正常操作下 uv 优先选择 wheel，因此该设置是无操作的；它仅在某个列出的上游不再为目标平台发布 wheel 时生效，此时 `uv lock` 会失败而非静默地从 sdist 构建。本地工作区包刻意不在其中，因为它必须由工作区自身的构建后端构建。`check-no-build-packages` pre-commit 钩子会在每次涉及锁文件或清单的提交中验证该列表与 `uv.lock` 保持同步。
- **工具链锁定**：uv 包管理器版本通过 `pyproject.toml` 中的 `required-version` 锁定，并在 CI、Docker 和本地开发中强制执行。发布和审计工具的 Python CLI 在 `tools.toml` 中锁定。
- **许可证合规**：自动化检查确保与 LGPL-3.0-or-later 的兼容性。

### 合并前与定时扫描

- **Pre-commit 安全**：Gitleaks 凭证筛查、私钥检测、Zizmor GitHub Actions 审计，以及 Unicode 控制字符检测，会在变更落地之前运行。
- **依赖审计**：自动化安全扫描通过 cargo-audit、cargo-deny、cargo-vet 和 OSV Scanner（Rust）、pip-audit（Python）和 Zizmor（GitHub Actions）运行。
- **供应链溯源**：cargo-vet 通过导入来自 Bytecode Alliance、Google、Mozilla 和 Embark Studios 等组织的可信审计数据，验证 Rust 依赖的溯源。
- **代码扫描**：CodeQL 静态分析在向 `master` 提交的 PR、向 `nightly` 的推送以及手动触发时覆盖 Python 和 Rust 代码。当 token 权限允许时，定时安全审计还会上传 Zizmor 的 SARIF 结果用于 GitHub Actions 工作流问题。

### 构建与发布控制

- **构建完整性**：Python 发布产物的 SLSA 构建溯源证明、GitHub 发布的校验和清单、不可变的 GitHub 发布证明、被锁定到 commit SHA 的不可变 GitHub Actions、容器摘要锁定、通过 Sigstore cosign 进行的 Docker 镜像签名、容器镜像的 SPDX SBOM 生成与 Sigstore 证明，以及通过明确允许列表阻断网络出站的加固 CI runner。
- **发布顺序**：稳定版本会先创建一个草稿 GitHub release 并附上 wheel 和 sdist 产物，然后再发布到包索引（`packages.nautechsystems.io`、PyPI、crates.io）。CI 验证各 registry，附加最终的校验和与溯源产物，然后发布 GitHub release 并验证其发布证明。这使 GitHub release 和校验和清单成为下游 registry 验证的锚点，同时保持与 GitHub release 不可变性的兼容性。
- **部署环境**：发布与包发布作业使用带作用域的 GitHub 部署环境（`release`、`r2-develop` 和 `r2-nightly`），使发布凭证和 OIDC 可信发布者身份与测试、lint 和仅构建作业相隔离。
- **发布认证**：PyPI 和 crates.io 的上传使用绑定到 `release` GitHub 环境的 Trusted Publishing（OIDC），消除了长生命周期的 API token。每次发布都会铸造一个仅作用于特定仓库、工作流和环境的短期 token。
- **GHCR 认证**：推送到 GitHub Container Registry 的容器镜像使用短生命周期的 `GITHUB_TOKEN`，其作用域限定于该工作流运行，而非长生命周期的个人访问 token。
- **发布后验证**：CI 根据 GitHub release 清单和预期的 PyPI 发布者身份验证 PyPI 的 wheel 和 sdist，验证 crates.io 条目是否由本仓库通过 trusted-publish 发布，记录每个 crate 是否匹配本次发布的 commit 或已由更早发布过，验证最终的 GitHub release 证明，并在发布后根据预期的 GitHub Actions 工作流身份验证容器镜像签名和 SBOM 证明。

### 运行时密码学

- **密码学**：所有 TLS 和密码学操作均使用 [aws-lc-rs](https://github.com/aws/aws-lc-rs)，即 AWS-LC 的 Rust 绑定。该库运行于非 FIPS 模式，因为 FIPS 140-3 模块（`aws-lc-fips-sys`）需要 Go 工具链作为构建依赖。底层的密码学原语（AES-GCM、SHA-2、ECDSA、ChaCha20-Poly1305）在两种模式下完全一致；FIPS 模块增加了联邦认证所要求的运行时自检和模块边界强制。

完整的供应链安全政策请参阅 <https://nautilustrader.io/security/supply-chain/>。

详细的 CI/CD 安全实践请参阅 [.github/OVERVIEW.md](.github/OVERVIEW.md#security)。

## 已知漏洞管理

当某个传递依赖中存在已知公告但暂无可用修复时，我们会在审计配置中记录风险评估、上下文和缓解措施。已接受的风险按严重程度、范围（直接 vs 传递、运行时 vs 开发时）分类，并对上游解决方案进行监控。

当依赖中识别出新漏洞时：

- 夜间安全审计会自动标记该公告。
- 核心团队在 NautilusTrader 的上下文中评估严重程度和暴露面。
- 直接依赖中的关键漏洞在 30 天内修补或缓解。
- 通过发布说明，并在适当情况下通过安全公告通知用户。

从源码构建 NautilusTrader 或使用额外依赖对其进行扩展的用户，应负责审计自己的依赖树。本政策中描述的控制措施适用于 NautilusTrader 的官方发布版本和官方仓库。

## 已解决的公告

我们通过依赖升级解决过的第三方安全公告。每次升级的检测滞后由上文描述的 `exclude-newer` 冷却期决定；当某个 CVE 需要立即响应时，该冷却期可以被绕过。

- **1.227.0**：
  - [GHSA-mf9v-mfxr-j63j](https://github.com/urllib3/urllib3/security/advisories/GHSA-mf9v-mfxr-j63j)：
    `urllib3` 通过部分解压缩后调用 `HTTPResponse.drain_conn()`、以及 Brotli 解压缩后第二次调用 `read(amt=N)`/`stream(amt=N)` 而绕过解压缩炸弹防护。已将 `urllib3` 升级至 v2.7.0。
  - [GHSA-qccp-gfcp-xxvc](https://github.com/urllib3/urllib3/security/advisories/GHSA-qccp-gfcp-xxvc)：
    通过 `ProxyManager.connection_from_url` 创建的 `urllib3` 连接池在跨主机重定向时未剥离 `Retry.remove_headers_on_redirect` 中列出的请求头。已将 `urllib3` 升级至 v2.7.0。

## 验证发布产物

Python 发布产物和 Docker 镜像通过 Sigstore 支持的工作流进行签名或证明。Cargo crate 通过 crates.io 的 Trusted Publishing 发布。发布验证器会记录每个 crate 版本是否由当前发布 commit 发布，或是来自本仓库更早的 trusted-published commit。你可以在安装前独立验证产物。

### Python wheel 和 sdist

GitHub release 包含生成的校验和表格、聚合的 `SHA256SUMS` 文件、每个产物对应的 `.sha256` 文件，以及面向 Python wheel 和 sdist 的机器可读 `dist-manifest.json`。在安装之前，请使用其中一个校验和源对已下载的产物进行核对。

GitHub release 还为每个 Python 产物附带 `.sigstore` 的 Sigstore bundle 和 `.intoto.jsonl` 的 DSSE 信封文件。GitHub CLI 默认从 GitHub API 获取证明；使用 `--bundle <artifact>.sigstore` 可改为对已下载的 Sigstore bundle 进行验证。

从 PyPI 或 GitHub release 下载后，使用 GitHub CLI 验证每个产物。`--cert-identity-regex` 和 `--cert-oidc-issuer` 标志将验证绑定到 `build.yml` 发布工作流，而不仅仅是仓库：

```sh
ISSUER=https://token.actions.githubusercontent.com
IDENTITY='^https://github\.com/nautechsystems/nautilus_trader/\.github/workflows/build\.yml@refs/heads/(master|nightly)$'

# `gh attestation verify` takes one subject per call, so loop over wheels
for whl in nautilus_trader-*.whl; do
  gh attestation verify "$whl" \
    --repo nautechsystems/nautilus_trader \
    --cert-identity-regex "$IDENTITY" \
    --cert-oidc-issuer "$ISSUER"
done

gh attestation verify nautilus_trader-*.tar.gz \
  --repo nautechsystems/nautilus_trader \
  --cert-identity-regex "$IDENTITY" \
  --cert-oidc-issuer "$ISSUER"
```

### Docker 镜像

请先将可变标签解析为不可变的摘要，使每次检查、随后的 `docker pull` 和 `docker run` 都作用于同一个镜像：

```sh
# Use crane (or `docker buildx imagetools inspect <ref> --format '{{.Manifest.Digest}}'`)
DIGEST=$(crane digest ghcr.io/nautechsystems/nautilus_trader:latest)
IMAGE=ghcr.io/nautechsystems/nautilus_trader@${DIGEST}
ISSUER=https://token.actions.githubusercontent.com
IDENTITY='^https://github\.com/nautechsystems/nautilus_trader/\.github/workflows/docker\.yml@refs/heads/(master|nightly)$'
```

验证 cosign 签名，证明该镜像由 NautilusTrader 的 CI 工作流构建：

```sh
cosign verify "$IMAGE" \
  --certificate-identity-regexp "$IDENTITY" \
  --certificate-oidc-issuer "$ISSUER"
```

验证 SPDX SBOM 证明绑定到同一个镜像摘要：

```sh
cosign verify-attestation --type https://spdx.dev/Document/v2.3 "$IMAGE" \
  --certificate-identity-regexp "$IDENTITY" \
  --certificate-oidc-issuer "$ISSUER"
```

GitHub CLI 也可以验证 SBOM 证明，但不会检查 cosign 镜像签名，因此请在上面的 `cosign verify` 之外额外使用它：

```sh
gh attestation verify "oci://${IMAGE}" \
  --repo nautechsystems/nautilus_trader \
  --predicate-type https://spdx.dev/Document/v2.3 \
  --cert-identity-regex "$IDENTITY" \
  --cert-oidc-issuer "$ISSUER"
```
