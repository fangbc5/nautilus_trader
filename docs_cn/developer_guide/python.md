# Python

> 本文档为 [English 原文](../../docs/developer_guide/python.md) 的中文翻译版本。如有歧义请以英文原版为准。

[Python](https://www.python.org/) 编程语言用于实现 NautilusTrader 中大多数面向用户的代码。
Python 拥有丰富的库和框架生态，非常适合策略开发、数据分析和系统集成。

## 代码风格

### PEP-8

代码库总体上遵循 PEP-8 风格指南。
一个值得注意的偏离是：除集合类型外，并不总是依赖 Python 的真值性（truthiness）来检查参数是否为 `None`。

根据 [Google Python 风格指南](https://google.github.io/styleguide/pyguide.html)，当某个参数可能是预期之外的对象时，不建议用真值性来判断它是否为 `None`——这种判断可能产生意料之外的真值结果（可能导致逻辑错误类型的 bug）。

*"始终使用 `if foo is None:`（或 `is not None`）来检查 `None` 值。例如，当测试一个默认值为 `None` 的变量或参数是否被设置为其他值时——这个其他值在布尔上下文中可能正好是 false！"*

:::note
对于空集合的检查，使用真值性（例如 `if not my_list:`）而不是显式比较 `None` 或空值。
:::

我们欢迎对于代码库中无明显原因偏离 PEP-8 的所有反馈。

### 类型提示

所有函数与方法签名*必须*包含类型注解：

```python
def __init__(self, config: EMACrossConfig) -> None:
def on_bar(self, bar: Bar) -> None:
def on_save(self) -> dict[str, bytes]:
def on_load(self, state: dict[str, bytes]) -> None:
```

**联合语法**：对可选类型使用 PEP 604 联合语法：

```python
# Preferred
def get_instrument(self, id: InstrumentId) -> Instrument | None:

# Avoid
def get_instrument(self, id: InstrumentId) -> Optional[Instrument]:
```

**泛型类型**：对可复用组件使用 `TypeVar`：

```python
T = TypeVar("T")
class ThrottledEnqueuer(Generic[T]):
```

### Docstring

代码库通篇使用 [NumPy docstring 规范](https://numpydoc.readthedocs.io/en/latest/format.html)。
该规范必须始终遵守，文档构建才能正确进行。

**Python** docstring 应使用**祈使语气**——例如 *"Return a cached client."*。

该约定与 Python 生态的主流风格保持一致，使生成的文档对终端用户更自然。

#### 私有方法

不要为私有方法（以 `_` 前缀命名）添加 docstring：

- Docstring 会生成对外暴露的 API 文档。
- 在私有方法上写 docstring 会错误地暗示它们属于公开 API。
- 私有方法属于实现细节，并非面向终端用户。

可以例外书写 docstring 的情况：

- 包含非平凡逻辑、多步骤或重要边界情况的复杂方法。
- 由于复杂度需要详细记录参数或返回值的方法。

当私有方法需要额外上下文（如复杂的前置条件或副作用）时，更推荐在相关逻辑附近添加简短的行内注释（`#`），而不是 docstring。

### 属性 vs 方法（PyO3 绑定）

在通过 PyO3 将 Rust 类型暴露给 Python 时，应根据调用方语义而非值是否会变化来选择使用 `#[getter]`（属性）或普通方法：

- **属性（`#[getter]`）：** 廉价、无副作用、类属性的当前状态视图。标量字段、谓词和轻量级派生值都属于此类，即使它们在对象生命周期内会变化。
  示例：`status`、`side`、`quantity`、`price`、`is_open`、`has_inputs`、`realized_pnl`、`venue_order_id`。
- **方法（无 `#[getter]`）：** 动作、修改、非平凡工作、分配/复制、I/O，或任何接受参数的操作。
  示例：`apply(fill)`、`unrealized_pnl(price)`、`calculate_pnl(...)`。
- **灰色地带（优先用方法）：** 每次调用都会克隆或分配一个集合的 getter。使用方法形式向调用方提示其代价。
  示例：`events()`、`adjustments()`、`client_order_ids()`、`trade_ids()`。

### 测试命名

使用能解释场景的描述性名称：

```python
def test_currency_with_negative_precision_raises_overflow_error(self):
def test_sma_with_no_inputs_returns_zero_count(self):
def test_sma_with_single_input_returns_expected_value(self):
```

### Ruff

代码库使用 [ruff](https://astral.sh/ruff) 进行 lint 检查。Ruff 规则定义在顶层 `pyproject.toml` 中，忽略项通常会附带注释说明原因。

## Cython（遗留）

:::note
本节涵盖 `.pyx` 与 `.pxd` 文件的 Cython 约定。
:::

对于 `.pyx` 和 `.pxd` 文件，所有返回 `void` 或原生 C 类型（如 `bint`、`int`、`double`）的函数和方法都必须在签名中包含 `except *` 关键字。否则，Python 异常会被静默忽略。

更多信息请参阅 [Cython 文档](https://cython.readthedocs.io/en/latest/index.html)。
