# 编码规范

> 本文档为 [English 原文](../../docs/developer_guide/coding_standards.md) 的中文翻译版本。如有歧义请以英文原版为准。

## 代码风格

当前代码库本身就是格式约定的参考。
此外，下面列出了一些补充规范。

### 通用格式规则

下列规则适用于**所有**源文件（Rust、Python、Cython、shell 等）：

- 只使用**空格**，绝不使用硬制表符（hard tab）。
- 行长一般应保持在 **100 个字符**以内；必要时合理换行。
- 优先使用美式英语拼写（`color`、`serialize`、`behavior`）。

### Shell 脚本可移植性

本仓库中的 shell 脚本使用 **bash**（而非 POSIX sh），并且必须在 **Linux** 和 **macOS** 上具备可移植性。面向用户的脚本（例如 `scripts/cli/install.sh`）还必须能在 **Windows** 上通过 Git Bash 或 WSL 运行。

**Shebang**：始终使用 `#!/usr/bin/env bash` 以保证可移植性。

**常见陷阱**：GNU 与 BSD 工具在 Linux 和 macOS 上存在差异：

| 命令                 | Linux (GNU)       | macOS (BSD)       | 可移植解决方案                              |
|----------------------|-------------------|-------------------|---------------------------------------------|
| `sed -i`             | `sed -i 's/…'`    | `sed -i '' 's/…'` | 使用备份扩展名：`sed -i.bak 's/…'`          |
| `stat`（文件大小）   | `stat -c%s file`  | `stat -f%z file`  | 通过 `stat --version` 探测                   |
| `sha256sum`          | `sha256sum file`  | N/A               | 使用 `shasum -a 256` 或动态探测              |
| `readlink -f`        | 可用              | N/A               | 避免使用，或改用 `realpath`                  |
| `grep -P`（PCRE）    | 可用              | N/A               | 改用 `-E`（扩展正则）                        |
| `date`（纳秒）       | `date +%N`        | N/A               | 改用 `$RANDOM` 来打破缓存                    |

**Bash 版本**：macOS 自带 bash 3.2；面向用户的脚本应避免 bash 4+ 的特性：

| 特性                              | Bash 版本    | 替代方案                          |
|-----------------------------------|--------------|-----------------------------------|
| 关联数组（`declare -A`）          | 4.0+         | 使用文件或普通数组                |
| `readarray` / `mapfile`           | 4.0+         | 使用 `while read` 循环            |
| `${var,,}` / `${var^^}`（大小写） | 4.0+         | 使用 `tr '[:upper:]' '[:lower:]'` |

**CI 脚本**（`scripts/ci/*`）运行在 Linux runner 上，因此可以使用 bash 4+ 和 GNU 工具。

### 注释约定

1. 通常在每个注释块或 docstring 上方留**一个空行**，使其与代码视觉上分离。
2. 使用 *sentence case*（句首大写）—— 首字母大写，其余保持小写，除非是专有名词或缩写。
3. 句号后不要使用双空格。
4. **单行注释**不应以句号结尾，*除非*该行以 URL 或行内 Markdown 链接结尾——这种情况下保留链接所需的标点。
5. **多行注释**应以逗号分隔句子（而非每行一个句号）。最后一行*应当*以句号结尾。
6. 注释要简洁；只解释那些不明显的内容——*少即是多*。
7. 文本中避免使用 emoji 符号。

### Doc 注释语气

**Rust** doc 注释应使用**陈述语气**——例如 *"Returns a cached client."*。

该约定与 Rust 生态的主流风格保持一致，使生成的文档对终端用户更自然。

### 术语与措辞

1. **错误消息**：避免在错误消息中使用 ", got"。根据上下文使用更具描述性的替代词，如 ", was"、", received" 或 ", found"。
   - ❌ `"Expected string, got {type(value)}"`
   - ✅ `"Expected string, was {type(value)}"`

2. **拼写**：使用 "hardcoded"（单词形式），而非 "hard-coded" 或 "hard coded"——这是更现代、更被广泛接受的拼法。

3. **错误变量命名**：对捕获的错误/异常使用单字母 `e`：
   - Rust：`Err(e)` 而非 `Err(err)` 或 `Err(error)`；闭包中使用 `|e|` 而非 `|err|`。
   - Python：`except SomeError as e:` 而非 `as err:` 或 `as error:`。

### 命名约定

1. **内部字段**：私有/内部字段可使用缩写（例如 `_price_prec`、`_size_prec`），以让热路径代码保持精炼。

2. **面向用户的 API**：公共属性、函数参数、返回类型以及指标名称/标签应使用完整、描述性的名称（例如 `price_precision`、`size_precision`）。这可以防止缩写术语泄漏到仪表盘或告警中。

3. **错误消息与日志**：使用完整词以确保清晰（例如使用 "price precision" 而非 "price prec"）。用户绝不应看到缩写术语。

### 格式

1. 对于较长的代码行，以及当传递的参数超过几个时，应换行并对齐到下一个逻辑缩进位置（而不是尝试以开括号为基准做悬挂的"花式"对齐）。这种做法节省右侧空间，使重要代码更居中可见，并且在函数/方法名变更时不易失效。

2. 闭合括号应单独成行，并对齐到逻辑缩进。

3. 多个换行的参数应以尾随逗号结尾：

```python
long_method_with_many_params(
    some_arg1,
    some_arg2,
    some_arg3,  # <-- trailing comma
)
```

## 提交消息

以下是关于提交消息风格的一些指引：

1. 主题（标题）行限制在 60 个字符以内。首字母大写，且不要以句号结尾。

2. 使用"祈使语气"，即消息应描述提交一旦应用后会做什么。

3. 可选：在正文中说明变更。与主题之间留一个空行。每行宽度保持在 100 字符以内。可选择是否在每条 bullet 末尾加句号。

4. 可选：提供 `#` 引用相关的 issue 或工单。

5. 可选：提供任何具有参考价值的超链接。

### Gitlint（可选）

Gitlint 可用于自动强制执行提交消息规范。它会检查提交消息是否符合上述指引（字符数限制、格式等）。此为**可选启用**，不在 CI 中强制执行。

**收益**：鼓励简洁而富有表达力的提交消息，有助于清晰说明变更内容。

**安装**：在本地运行 gitlint 前需先安装：

```bash
uv pip install gitlint
```

将 gitlint 启用为自动 commit-msg 钩子：

```bash
prek install --hook-type commit-msg
```

**手动用法**：检查上一次提交消息：

```bash
gitlint
```

配置位于仓库根目录的 `.gitlint`：

- **60 字符标题限制**：确保在 GitHub 上清晰渲染，鼓励在保持描述性的同时做到简短。
- **79 字符正文宽度**：与 Python 的 PEP 8 约定和 git 工具的传统限制保持一致。

:::note
未来可能会在 CI 中强制执行 Gitlint，因此尽早采用这些实践会让过渡更顺畅。
:::
