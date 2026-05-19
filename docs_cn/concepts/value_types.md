# Value Types（值类型）

> 本文档为 [English 原文](../../docs/concepts/value_types.md) 的中文翻译版本。如有歧义请以英文原版为准。

NautilusTrader 为核心交易概念提供了专门的值类型：`Price`、`Quantity` 和 `Money`。这些类型在内部使用定点算术，确保跨平台与跨环境的高性能、确定性计算。

## 概述

| 类型       | 用途                                | 是否有符号 | 是否含币种 |
|------------|-------------------------------------|------------|------------|
| `Quantity` | 交易数量、订单数量、持仓数量。      | 否         | -          |
| `Price`    | 市场价格、报价、价格层级。          | 是         | -          |
| `Money`    | 金额、盈亏、账户余额。              | 是         | 是         |

## 不可变性

所有值类型都是**不可变的**。一旦构造完成，其值便不能更改。运算操作不会修改原始对象。

```python
from nautilus_trader.model.objects import Quantity

qty1 = Quantity(100, precision=0)
qty2 = Quantity(50, precision=0)

# 这会创建一个新的 Quantity；qty1 和 qty2 保持不变
result = qty1 + qty2

print(qty1)    # 100
print(qty2)    # 50
print(result)  # 150
```

这种设计带来若干好处：

- **线程安全**：不可变值可以在线程间安全共享，无需同步。
- **可预测性**：值不会意外改变，便于调试。
- **可哈希性**：不可变类型可以用作字典键或集合元素。

## 算术运算

值类型支持标准算术运算符（`+`、`-`、`*`、`/`、`%`、`//`）以及一元运算符（`-`、`+`、`abs`）。返回类型取决于运算符与操作数类型。

### 同类型二元运算

同类型值的加减返回该类型，保留领域含义（价格加价格仍是价格）：

| 运算                  | 结果       |
|-----------------------|------------|
| `Quantity + Quantity` | `Quantity` |
| `Quantity - Quantity` | `Quantity` |
| `Price + Price`       | `Price`    |
| `Price - Price`       | `Price`    |
| `Money + Money`       | `Money`    |
| `Money - Money`       | `Money`    |

```python
from nautilus_trader.model.objects import Price

price1 = Price(100.50, precision=2)
price2 = Price(0.25, precision=2)

result = price1 + price2  # 返回 Price(100.75, precision=2)
print(type(result))       # <class 'Price'>
```

两个同类型值之间的乘法、除法、整除与取模返回 `Decimal`：

| 运算                  | 结果      |
|-----------------------|-----------|
| `Price * Price`       | `Decimal` |
| `Price / Price`       | `Decimal` |
| `Price // Price`      | `Decimal` |
| `Price % Price`       | `Decimal` |

同样的模式适用于 `Quantity` 与 `Money`。

这些运算之所以不返回原始类型，是因为结果具有不同的量纲含义。价格乘以价格得到的是"价格的平方"，而不是价格；数量除以数量得到的是一个无量纲的比率，而不是数量。返回 `Decimal` 可以让单位变化变得显式，避免将结果误解为具有原始单位的值。

### 一元运算

一元运算符在结果对该类型仍然有效时保留值类型：

| 运算         | `Price`   | `Quantity` | `Money`   |
|--------------|-----------|------------|-----------|
| `-x` (取负)  | `Price`   | `Decimal`  | `Money`   |
| `+x` (取正)  | `Price`   | `Quantity` | `Money`   |
| `abs(x)`     | `Price`   | `Quantity` | `Money`   |
| `int(x)`     | `int`     | `int`      | `int`     |
| `float(x)`   | `float`   | `float`    | `float`   |
| `round(x)`   | `Decimal` | `Decimal`  | `Decimal` |

`Quantity.__neg__` 返回 `Decimal` 而不是 `Quantity`，因为 `Quantity` 是无符号的，无法表示负值。

```python
from nautilus_trader.model.objects import Price, Quantity, Money
from nautilus_trader.model.currencies import USD

price = Price(100.50, precision=2)
print(-price)            # -100.50
print(type(-price))      # <class 'Price'>

money = Money(-50.00, USD)
print(abs(money))        # 50.00 USD
print(type(abs(money)))  # <class 'Money'>

qty = Quantity(10, precision=0)
print(+qty)              # 10
print(type(+qty))        # <class 'Quantity'>
```

### 混合类型运算

与其他数值类型进行运算时，结果类型遵循 Python 的 [数值塔（numeric tower）](https://docs.python.org/3/library/numbers.html) 约定。一般原则是运算结果会扩展到更通用的类型：`float` 运算返回 `float`，`int` 与 `Decimal` 运算则返回 `Decimal` 以保留精度。

这适用于全部六种二元运算符（`+`、`-`、`*`、`/`、`//`、`%`），且双向都成立（`value op scalar` 与 `scalar op value`）：

| 左操作数     | 右操作数      | 结果类型    |
|--------------|---------------|-------------|
| 值类型       | `int`         | `Decimal`   |
| 值类型       | `float`       | `float`     |
| 值类型       | `Decimal`     | `Decimal`   |
| `int`        | 值类型        | `Decimal`   |
| `float`      | 值类型        | `float`     |
| `Decimal`    | 值类型        | `Decimal`   |

```python
from decimal import Decimal
from nautilus_trader.model.objects import Quantity

qty = Quantity(100, precision=0)

# Quantity + int -> Decimal
result1 = qty + 50
print(type(result1))  # <class 'decimal.Decimal'>

# Quantity + float -> float
result2 = qty + 50.5
print(type(result2))  # <class 'float'>

# Quantity + Decimal -> Decimal
result3 = qty + Decimal("50")
print(type(result3))  # <class 'decimal.Decimal'>
```

## 精度处理

每个值类型都存储一个 precision 字段，指示小数位数。precision 在构造时确定且不可变。不存在"未指定"精度的情况。

### 定点表示

值类型在内部按全局固定精度缩放为整数存储（例如高精度模式下为 10^16），而不是浮点数。`precision` 字段记录构造时使用的小数位数，控制显示格式与序列化，但底层原始值始终使用全局缩放系数。

```python
from nautilus_trader.model.objects import Price

p1 = Price(1.23, precision=2)   # 显示为 "1.23"
p2 = Price(1.230, precision=3)  # 显示为 "1.230"

p1 == p2  # True：底层值相同
str(p1)   # "1.23"
str(p2)   # "1.230"
```

**精度控制显示，而非身份。** 两个小数值相同但精度不同的价格是相等的。`precision` 字段决定字符串格式与显示的小数位数，但相等性基于底层数值。

**行情数据序列化使用精度元数据。** 当行情数据类型（quotes、trades、订单簿 delta）以 Parquet 或 Arrow 格式写入时，精度会存储在文件元数据中，以便正确解码值。单个文件中的所有行情数据值必须具有相同精度。

:::note
如果某个交易场所修改了某个标的的 tick size（从而改变其精度），那么变更前后写入的数据文件会有不同的精度元数据，不应合并到同一个文件中。
:::

关于标的级别的精度如何约束有效价格与数量，请参见 Instruments 指南的 [Precision](instruments.md#precision) 章节。

### 算术精度

对不同精度的值进行算术运算时，结果使用各操作数中最大的精度。

```python
from nautilus_trader.model.objects import Price

price1 = Price(100.5, precision=1)    # 1 位小数
price2 = Price(0.125, precision=3)    # 3 位小数

result = price1 + price2
print(result)            # 100.625
print(result.precision)  # 3 （1 和 3 的最大值）
```

## 特定类型约束

### Quantity

`Quantity` 表示非负数量。尝试创建负数量或从较小的数量中减去较大的数量会触发错误：

```python
from nautilus_trader.model.objects import Quantity

# 这会抛出 ValueError：Quantity cannot be negative
qty = Quantity(-100, precision=0)

# 这同样会抛出 ValueError
qty1 = Quantity(50, precision=0)
qty2 = Quantity(100, precision=0)
result = qty1 - qty2  # 结果为 -50，无效
```

### Money

`Money` 值包含一个币种。`Money` 值之间的加减要求币种一致：

```python
from nautilus_trader.model.objects import Money
from nautilus_trader.model.currencies import USD, EUR

usd_amount = Money(100.00, USD)
eur_amount = Money(50.00, EUR)

# 可以——同一币种
result = usd_amount + Money(25.00, USD)

# 这会抛出 ValueError——币种不匹配
result = usd_amount + eur_amount
```

## 常见用法

### 累加值

由于值类型不可变，需要通过重新赋值来累加：

```python
from nautilus_trader.model.objects import Money
from nautilus_trader.model.currencies import USD

total = Money(0.00, USD)
amounts = [Money(100.00, USD), Money(50.00, USD), Money(25.00, USD)]

for amount in amounts:
    total = total + amount  # 重新赋值为新的 Money 实例

print(total)  # 175.00 USD
```

### 转换为其他类型

值类型提供转换方法：

```python
from nautilus_trader.model.objects import Price

price = Price(123.456, precision=3)

# 转为 Decimal（保留精度）
decimal_value = price.as_decimal()

# 转为 float
float_value = price.as_double()

# 转为字符串
string_value = str(price)  # "123.456"
```

### 从字符串创建

从字符串表示解析值类型：

```python
from nautilus_trader.model.objects import Quantity, Price, Money

qty = Quantity.from_str("100.5")
price = Price.from_str("99.95")
money = Money.from_str("1000.00 USD")
```
