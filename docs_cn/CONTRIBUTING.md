# 为 NautilusTrader 做贡献

> 本文档为 [English 原文](../CONTRIBUTING.md) 的中文翻译版本。如有歧义请以英文原版为准。

我们高度重视来自交易社区的参与，所有贡献都将得到衷心感谢，因为它们帮助我们不断改进 NautilusTrader！

> [!NOTE]
>
> **集成（Integrations）：**
> 新增集成是该项目的一项重大工作，因此在开启任何 PR 之前需要进行额外的讨论和审批。
> 关于具体流程请参阅 [ROADMAP：社区贡献的集成](ROADMAP.md#community-contributed-integrations)，关于适配器层级、社区列名和支持边界请参阅 [ADAPTERS.md](ADAPTERS.md)。

## 步骤

要进行贡献，请遵循以下步骤：

1. 在 GitHub 上开启一个 issue，讨论你提出的变更或增强。

2. 在所有人达成一致后，fork `develop` 分支，并通过定期合并任何上游变更确保你的 fork 保持最新。

3. 按照 [环境配置指南](docs/developer_guide/environment_setup.md) 配置你的开发环境，该指南涵盖 Rust、Python 和 uv。完成这些前置条件后，安装已锁定版本的开发工具（包括 [prek](https://github.com/j178/prek)，它会在每次提交前运行 pre-commit 检查、格式化工具和 lint 检查工具）：
    ```bash
    cargo install cargo-binstall --locked  # one-off prerequisite
    make install-tools
    prek install
    ```
   `make install-tools` 会安装来自 `Cargo.toml`、`tools.toml` 和 `pyproject.toml` 中所有锁定版本的工具。关于每个锁定工具的作用，请参阅 [安装开发工具](docs/developer_guide/environment_setup.md#2-install-development-tools)。

4. 向 `develop` 分支开启一个 pull request（PR），附上摘要说明并引用任何相关的 GitHub issue。

5. CI 系统会对你的代码运行完整的测试套件，包括所有单元测试和集成测试，因此请在 PR 中包含相应的测试。

6. 阅读并理解贡献者许可协议（CLA），可在 https://github.com/nautechsystems/nautilus_trader/blob/develop/CLA.md 查阅。

7. 你还需要签署该 CLA，签署流程通过 [CLA Assistant](https://cla-assistant.io/) 自动完成。

8. 我们将尽快评审你的代码，如果在合并前需要任何变更，会及时提供反馈。

## 提示

- 遵循 [开发者指南](https://nautilustrader.io/docs/developer_guide/index.html) 中既定的编码实践。
- 对于文档变更，请遵循 `docs/developer_guide/docs.md` 中的样式指南（H2 及以下级别的标题使用句首大写）。
- 保持 PR 小而聚焦，以便更易评审。
- 在你的 PR 评论中引用相关的 GitHub issue。
