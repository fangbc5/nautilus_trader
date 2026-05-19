# 商标与命名政策

> 本文档为 [English 原文](../TRADEMARK.md) 的中文翻译版本。如有歧义请以英文原版为准。
>
> ⚠️ 本翻译仅供参考，所有法律效力以英文原文为准。

本政策规范第三方项目、fork、适配器、wrapper、教程、课程及任何其他衍生或兼容作品对 NautilusTrader™ 名称、相关标记和徽标的使用。

NautilusTrader 是 Nautech Systems Pty Ltd（ABN 88 609 589 237）的注册商标。Nautech Systems 拥有并维护这些标记和本政策。完整的商标政策发布于 [nautilustrader.io/legal/trademark-policy](https://nautilustrader.io/legal/trademark-policy/)。
如有疑问或担忧，请联系 <legal@nautechsystems.io>。

## 这些标记

以下名称由 Nautech Systems 保留以供官方项目使用：

- **NautilusTrader**（组合形式）
- **Nautilus Trader**（分开形式）
- **nautilus_trader**（包名）
- **nautilus-trader**（连字符形式）
- NautilusTrader 徽标和任何相关的视觉品牌元素

这些标记标识由 Nautech Systems 制作和维护的软件。任何第三方项目不得在项目名称、包名或公共 registry 标识中将这些标记用作前缀或前导组成部分。

## 通用原则

1. **这些标记的存在是为了保护用户避免对什么是官方、什么不是官方产生混淆。本政策力求务实和公平，而不是为了限制而限制。**

2. 引用 NautilusTrader 的第三方项目必须清晰、诚实地表明它们与该项目的关系。

3. 使用或分发 NautilusTrader 代码的第三方项目，必须遵守 [LGPL v3.0 许可证](./LICENSE)（在适用之处）。本商标政策与软件许可证相互独立，并构成额外约束。

4. 遵守本政策并不构成背书、关联或官方身份。只有在 [nautechsystems](https://github.com/nautechsystems) GitHub 组织内维护并由项目维护者指定的项目才具有官方身份。

## 可接受的指代性使用

第三方项目可以引用 NautilusTrader 名称来描述兼容性或用途。以下用法是可接受的：

- "for NautilusTrader"
- "compatible with NautilusTrader"
- "an adapter for NautilusTrader"
- "works with NautilusTrader"

**这些短语描述与项目的关系。它们在文档、描述和 README 中是可接受的，但不得用于项目名或包名中。**

## 这些规则适用于哪里

本政策适用于仓库名、PyPI 发行版名称、crates.io crate 名称、npm 包名称以及任何其他公共包 registry。它也适用于域名、GitHub 组织名和用户名，以及社交媒体账号。

## 第三方项目的命名规则

第三方项目不得将 `nautilustrader`、`nautilus_trader` 或 `nautilus-trader` 用作项目或包名的前缀或前导组成部分。当用于交易、经纪、行情数据、回测或相关金融软件，且可能与 NautilusTrader 产生混淆时，独立的单词 `nautilus` 也受到限制。在同一领域内，包 registry 上的 `nautilus-*` 命名空间保留给官方发布的 NautilusTrader 包。

实际而言，源代码仓库通常比已发布的包更不容易引起混淆。确实要发布到包 registry 的项目，在命名上应格外小心。希望被纳入官方适配器的贡献者，应遵循 [ROADMAP](./ROADMAP.md#community-contributed-integrations) 中描述的 RFC 流程。

**`nt` 简写形式。** 项目指定 `nt` 作为获批准的简写形式，供第三方项目用于表示与 NautilusTrader 的兼容性。

**命名示例：**

| 合规                    | 不合规                   |
|-------------------------|--------------------------|
| `mt5-nt-community`      | `nautilus-mt5`           |
| `sinopac-nt-community`  | `nautilus-sinopac`       |
| `mt5-connect`           | `nautilustrader-stocks`  |

推荐使用 `-community` 后缀以明确表示这是一个独立项目，但并非必须。

## 必需的免责声明

所有分发与 NautilusTrader 集成代码的第三方软件项目（适配器、wrapper、fork、包、库）必须在其 README 或主文档中包含明确的免责声明。该免责声明必须说明该项目：

1. 与 Nautech Systems Pty Ltd 或 NautilusTrader 项目无关联；
2. 未被 Nautech Systems Pty Ltd 或 NautilusTrader 项目背书；
3. 未被 Nautech Systems Pty Ltd 或 NautilusTrader 项目支持。

**参考文本：**

> This is an independent community project. It is not affiliated with, endorsed
> by, or supported by Nautech Systems Pty Ltd or the official NautilusTrader
> project.

项目可以调整措辞以匹配其文档风格，但上述三个要素必须都存在，且法律实体名称（Nautech Systems Pty Ltd）必须出现。

## Fork

为个人使用、企业内部非公开使用，或为通过 pull request 向官方仓库回馈而创建的 fork，可豁免于本政策中的命名、免责声明和品牌要求。遵循 [CONTRIBUTING.md](./CONTRIBUTING.md) 中描述的工作流的标准开发 fork 无需做出任何更改。

## 徽标

NautilusTrader 徽标和相关视觉品牌元素归 Nautech Systems 所有。第三方项目不得以暗示官方身份或背书的方式使用官方徽标或其衍生物。使用徽标需要事先获得 Nautech Systems 的书面许可。

## 社区渠道

为商业产品或服务访问、推广或使用官方 NautilusTrader 社区渠道（包括论坛、聊天服务器或邮件列表）需要事先获得 Nautech Systems 的书面批准。参与社区渠道并不意味着获得背书或建立关联。

## 合作伙伴及关联实体的使用

合作伙伴可以根据与 Nautech Systems 单独签署的书面合作或联合品牌协议条款使用这些标记。关联实体只能根据与 Nautech Systems 单独签署的书面许可或授权使用这些标记。

## 执行

Nautech Systems 保留通过适当方式执行其标记的权利，包括但不限于：要求更改名称、要求移除引起混淆的品牌元素、从官方渠道下架，以及在必要时寻求正式的商标救济。

执行通常会先发出直接通知，并给予改正机会，然后再考虑更强的措施。对某一具体使用行为不执行的决定，并不构成放弃在未来对该使用或任何其他使用进行执行的权利。

## 更新

本政策可能会不定期更新。权威版本发布于 [nautilustrader.io/legal/trademark-policy](https://nautilustrader.io/legal/trademark-policy/)。两个版本在内容上保持一致。

最后更新：2026-04-13
