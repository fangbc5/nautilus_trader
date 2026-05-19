# Synthetics（合成标的）

> 本文档为 [English 原文](../../docs/concepts/synthetics.md) 的中文翻译版本。如有歧义请以英文原版为准。

合成标的（Synthetic instruments）是本地定义的标的，其价格由其他标的派生。它们可以组合来自一个或多个交易场所的成分，并将结果以合成场所代码 `SYNTH` 暴露为标准的 Nautilus 标的。

合成标的常用于：

- 让 `Actor` 与 `Strategy` 组件订阅 quote 或 trade 数据。
- 基于派生价格触发模拟订单。
- 由合成的 quotes 或 trades 构建 K 线（bar）。

合成标的不能直接交易。它们仅在平台内部存在，作为分析工具使用。未来 Nautilus 可能会基于合成标的行为支持对其成分标的进行交易。

## 公式语言

每个合成标的定义一个派生公式。Nautilus 用其内置的数值表达式引擎对该公式求值，并将最终的数值结果转换为合成标的的 `Price`。

### 支持的语法

公式可以直接引用成分 `InstrumentId` 的值，包括包含 `/` 与 `-` 的 ID。

| 构造               | 示例                                           | 说明                                                                 |
|--------------------|------------------------------------------------|----------------------------------------------------------------------|
| 成分引用           | `BTCUSDT.BINANCE`                              | 使用 `InstrumentId` 的原始文本。                                     |
| 成分引用           | `AUD/USD.SIM`                                  | 包含 `/` 的 ID 有效。                                                |
| 成分引用           | `ETH-USDT-SWAP.OKX`                            | 包含 `-` 的 ID 有效。                                                |
| 数值字面量         | `1`、`0.5`、`1.2e-3`                           | 按 `f64` 语义求值。                                                  |
| 布尔字面量         | `true`、`false`                                | 用于条件与逻辑表达式。                                               |
| 括号               | `(a + b) / 2`                                  | 使用括号覆盖运算优先级。                                             |
| 一元运算符         | `-x`、`!flag`                                  | 一元 `-` 取数值的相反数；一元 `!` 取布尔的相反值。                   |
| 二元运算符         | `+ - * / % ^`、`== !=`、`< <= > >=`、`&& \|\|` | 算术为数值类型，逻辑运算符为布尔类型。                                |
| 局部赋值           | `spread = a - b; spread / 2`                   | 语句从左到右执行。公式必须以一个值结尾。                              |
| 注释               | `// line`、`/* block */`                       | 注释会被忽略。                                                       |

:::note
新公式应使用原始 `InstrumentId` 值。出于向后兼容，使用 `_` 替换成分 ID 中 `-` 的公式仍被接受。
:::

### 运算符优先级

表达式引擎按以下顺序对运算符求值，从最高优先级到最低优先级：

| 级别   | 运算符                | 说明                                                          |
|--------|-----------------------|---------------------------------------------------------------|
| 最高   | `^`                   | 幂运算。右结合。                                              |
|        | 一元 `-`、一元 `!`    | `-2 ^ 2` 求值为 `-(2 ^ 2)`。                                  |
|        | `*`、`/`、`%`         | 乘法、除法与取模。                                            |
|        | `+`、`-`              | 加法与减法。                                                  |
|        | `<`、`<=`、`>`、`>=`  | 数值比较。                                                    |
|        | `==`、`!=`            | 相等与不等。两边必须为相同类型。                              |
| 最低   | `&&`、`\|\|`          | 布尔运算符。                                                  |

赋值不是表达式运算符。用 `;` 分隔语句，并让最后一条语句作为合成标的产生的值。

### 内置函数

| 函数      | 签名                                   | 说明                                                  |
|-----------|----------------------------------------|-------------------------------------------------------|
| `abs`     | `abs(x)`                               | 绝对值。                                              |
| `ceil`    | `ceil(x)`                              | 向上取整。                                            |
| `floor`   | `floor(x)`                             | 向下取整。                                            |
| `round`   | `round(x)`                             | 按 Rust `f64` 规则四舍五入至最近整数。                |
| `min`     | `min(x1, x2, ...)`                     | 接受一个或多个数值参数。                              |
| `max`     | `max(x1, x2, ...)`                     | 接受一个或多个数值参数。                              |
| `if`      | `if(condition, when_true, when_false)` | 条件必须是布尔。两个分支类型一致。仅会对所选分支求值。 |

### 类型规则

- 成分输入是数值类型。
- 算术运算符要求数值操作数，并返回数值结果。
- `<`、`<=`、`>`、`>=` 要求数值操作数，返回布尔结果。
- `==` 与 `!=` 接受同类型的任意值（同为数值或同为布尔），返回布尔结果。
- `&&`、`||` 与一元 `!` 要求布尔操作数。
- `&&` 与 `||` 短路计算；右侧仅在必要时求值。
- 局部变量必须先赋值后使用。
- 局部变量名必须以字母或 `_` 开头，之后可包含字母、数字或 `_`。
- 公式最终结果必须是数值。以赋值结尾或得到布尔结果的公式对合成标的而言无效。

### 限制

表达式引擎强制以下编译期上限。超过限制的公式在构造时会给出明确错误。

| 限制               | 数值 | 描述                                              |
|--------------------|------|---------------------------------------------------|
| 栈深度             | 32   | 求值栈上中间值的最大数量。                        |
| 局部变量           | 16   | 不同局部变量名的最大数量。                        |

这些限制对任何实际定价公式都很充足。对 8 个成分的加权求和，峰值栈深度为 3，无局部变量。

### 示例

```python
# 简单价差
formula = "BTCUSDT.BINANCE - ETHUSDT.BINANCE"

# 两个外汇对的平均
formula = "(AUD/USD.SIM + NZD/USD.SIM) / 2"

# 复用中间值
formula = "spread = BTCUSDT.BINANCE - ETHUSDT.BINANCE; spread / 2"

# 条件输出
formula = "if(BTCUSDT.BINANCE > ETHUSDT.BINANCE, BTCUSDT.BINANCE, ETHUSDT.BINANCE)"
```

## 创建合成标的

在定义新的合成标的之前，确保所有成分标的已存在于缓存中。

下面的示例通过 Actor 或策略创建一个合成标的，表示 Binance 上 Bitcoin 与 Ethereum 现货价格之间的简单价差。它假定 `BTCUSDT.BINANCE` 与 `ETHUSDT.BINANCE` 已存在于缓存中。

```python
from nautilus_trader.model.instruments import SyntheticInstrument

btcusdt_binance_id = InstrumentId.from_str("BTCUSDT.BINANCE")
ethusdt_binance_id = InstrumentId.from_str("ETHUSDT.BINANCE")

synthetic = SyntheticInstrument(
    symbol=Symbol("BTC-ETH:BINANCE"),
    price_precision=8,
    components=[
        btcusdt_binance_id,
        ethusdt_binance_id,
    ],
    formula=f"{btcusdt_binance_id} - {ethusdt_binance_id}",
    ts_event=self.clock.timestamp_ns(),
    ts_init=self.clock.timestamp_ns(),
)

self._synthetic_id = synthetic.id
self.add_synthetic(synthetic)
self.subscribe_quote_ticks(self._synthetic_id)
```

:::note
上例中合成标的的 `instrument_id` 为 `{symbol}.SYNTH`，生成结果为 `BTC-ETH:BINANCE.SYNTH`。
:::

## 更新公式

你可以随时更新合成标的的公式。

```python
synthetic = self.cache.synthetic(self._synthetic_id)

new_formula = "(BTCUSDT.BINANCE + ETHUSDT.BINANCE) / 2"
synthetic.change_formula(new_formula)

self.update_synthetic(synthetic)
```

## 触发用 instrument ID

你可以由合成价格触发模拟订单。下例中，合成标的在合成价格达到触发条件后释放一个模拟订单。

```python
order = self.strategy.order_factory.limit(
    instrument_id=ETHUSDT_BINANCE.id,
    order_side=OrderSide.BUY,
    quantity=Quantity.from_str("1.5"),
    price=Price.from_str("30000.00000000"),
    emulation_trigger=TriggerType.DEFAULT,
    trigger_instrument_id=self._synthetic_id,
)

self.strategy.submit_order(order)
```

## 性能

公式在构造时一次性编译，并在每一次成分价格 tick 到达时求值。表达式引擎采用编译一次/多次求值的架构，并使用零分配的 f64 栈，因此求值给 tick 处理路径增加的开销可以忽略。

测量环境：Apple M4 Pro，rustc 1.94.1，release profile（opt-level 3）：

### 求值（热路径）

| 公式模式                                  | 耗时    |
|-------------------------------------------|---------|
| `(A + B) / 2.0`                           | 12 ns   |
| `A * 0.4 + B * 0.3 + C * 0.2 + D * 0.1`   | 18 ns   |
| `if(A > B, A - B, B - A)`                 | 12 ns   |
| `spread = A - B; mid = ...; mid + ...`    | 19 ns   |
| `max(min(A, B * 20), abs(A - B))`         | 15 ns   |

### 求值伸缩（加权求和）

| 成分数 | 耗时    |
|--------|---------|
| 2      | 14 ns   |
| 4      | 18 ns   |
| 8      | 28 ns   |

### 编译（冷路径）

| 公式模式            | 耗时     |
|---------------------|----------|
| 简单平均            | 675 ns   |
| 4 输入加权          | 1.4 us   |
| 条件                | 1.0 us   |
| 含局部变量          | 1.3 us   |
| 含连字符 ID         | 755 ns   |

## 错误处理

Nautilus 在每个边界上都校验合成标的。公式编译会拒绝未知符号、类型错误与容量溢出。求值会在公式接触之前拒绝错误的输入数量与非有限价格（NaN、Infinity）。

详见
[`SyntheticInstrument` API 参考](/docs/python-api-latest/model/instruments.html#nautilus_trader.model.instruments.synthetic.SyntheticInstrument)
了解输入要求与异常。

## 相关指南

- [Instruments](instruments.md) - 标的定义与各交易场所专属的标的类型。
- [Data](data.md) - 引用标的的行情数据类型。
- [Orders](orders.md) - 订单可使用合成标的 ID 作为模拟触发器。
