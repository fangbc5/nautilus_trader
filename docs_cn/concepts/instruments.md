# Instruments

> 本文档为 [English 原文](../../docs/concepts/instruments.md) 的中文翻译版本。如有歧义请以英文原版为准。

instrument 代表任何可交易资产或合约的规格。所有 instrument 类型都实现为 Rust struct，
并实现 `Instrument` trait。在 Python 中通过 `nautilus_trader.model.instruments`
暴露为 Cython 扩展类型，配套有 PyO3 表示，并在边界上转换为 Cython 类型。
纯 Rust 系统直接使用 Rust 类型。平台支持多种资产类别和 instrument 类别：

- `Equity`：在现金市场交易的上市股票或 ETF。
- `CurrencyPair`：以 BASE/QUOTE 格式在现金市场交易的现货外汇或加密货币对。
- `Commodity`：在现金市场交易的现货商品（如黄金或原油）。
- `IndexInstrument`：由成分股计算的现货指数；作为参考价格使用，不可直接交易。
- `FuturesContract`：可交割的期货合约，具有明确的标的、到期日和乘数。
- `FuturesSpread`：交易所定义的多腿期货策略（如日历价差或跨品种价差），作为单个 instrument 报价。
- `CryptoFuture`：有固定到期日、加密标的和结算货币的可交割加密期货合约。
- `CryptoPerpetual`：加密永续期货合约（永续掉期），无到期日；可为反向或 quanto 结算。
- `PerpetualContract`：资产类别无关的永续掉期，可对任意标的（外汇、股票、商品、指数、加密）使用。
- `OptionContract`：交易所交易的期权（看跌或看涨），有标的、行权价和到期日。
- `OptionSpread`：交易所定义的多腿期权策略（如垂直价差、日历价差、跨式），作为单个 instrument 报价。
- `CryptoOption`：加密标的、加密计价/结算的期权；支持反向或 quanto 形式。
- `BinaryOption`：基于二元结果结算为 0 或 1 的固定赔付期权。
- `Cfd`：场外差价合约，追踪标的，按现金结算。
- `BettingInstrument`：体育/博彩市场的下注选项（如球队或赛马），可在博彩场所交易。
- `SyntheticInstrument`：合成标的，价格通过公式从成分 instrument 派生。

## 符号体系

所有 instrument 都应拥有唯一的 `InstrumentId`，由原生符号和 venue ID 通过点号连接组成。
例如，在 Binance Futures 加密货币交易所，以太坊永续期货合约的 instrument ID 是 `ETHUSDT-PERP.BINANCE`。

所有原生符号*应当*在一个 venue 内唯一（虽然并不总是如此，例如 Binance 的现货和期货市场共享原生符号），
而 `{symbol.venue}` 组合在一个 Nautilus 系统内*必须*唯一。

:::warning
为了逻辑上正确运行，正确的 instrument 必须与对应的市场数据集（如 tick 或订单簿数据）匹配。
错误指定 instrument 可能截断数据或产生意外结果。
:::

## 回测

可以通过 `TestInstrumentProvider` 实例化通用测试 instrument：

```python
from nautilus_trader.test_kit.providers import TestInstrumentProvider

audusd = TestInstrumentProvider.default_fx_ccy("AUD/USD")
```

```python
from nautilus_trader.adapters.binance.spot.providers import BinanceSpotInstrumentProvider
from nautilus_trader.model import InstrumentId

provider = BinanceSpotInstrumentProvider(client=binance_http_client)
await provider.load_all_async()

btcusdt = InstrumentId.from_str("BTCUSDT.BINANCE")
instrument = provider.find(btcusdt)
```

或直接构造特定 instrument 类型：

```python
from nautilus_trader.model.instruments import OptionContract

instrument = OptionContract(...)  # 传入所有必要参数
```

```rust
use nautilus_model::instruments::CurrencyPair;
use nautilus_model::identifiers::{InstrumentId, Symbol};
use nautilus_model::types::{Currency, Price, Quantity};

let instrument = CurrencyPair::new(
    InstrumentId::from("EUR/USD.SIM"),
    Symbol::from("EUR/USD"),
    Currency::from("EUR"),
    Currency::from("USD"),
    5,                          // price_precision
    0,                          // size_precision
    Price::from("0.00001"),     // price_increment
    Quantity::from("1"),        // size_increment
    // ... 其余参数
);
```

完整 instrument [API 参考](/docs/python-api-latest/model/instruments.html)。

## 实盘交易

实盘集成适配器拥有 `InstrumentProvider` 实现，会自动缓存该 venue 的最新 instrument 定义。
向需要 `InstrumentId` 的数据和执行方法传入相应的 ID 即可引用特定 instrument。

## 查找 instrument

由于同样的 actor/策略类既可用于回测也可用于实盘，你可以以完全相同的方式通过中央缓存获取 instrument：

```python
from nautilus_trader.model import InstrumentId

instrument_id = InstrumentId.from_str("ETHUSDT-PERP.BINANCE")
instrument = self.cache.instrument(instrument_id)
```

```rust
use nautilus_model::identifiers::InstrumentId;

let instrument_id = InstrumentId::from("ETHUSDT-PERP.BINANCE");
let instrument = cache.instrument(&instrument_id);
```

也可以订阅特定 instrument 的任何变更：

```python
self.subscribe_instrument(instrument_id)
```

或订阅整个 venue 的全部 instrument 变更：

```python
from nautilus_trader.model import Venue

binance = Venue("BINANCE")
self.subscribe_instruments(binance)
```

当 `DataEngine` 接收到 instrument 更新时，对象会被传给 `on_instrument()` 处理器。
重写此方法以在接收到 instrument 更新时执行相应操作：

```python
from nautilus_trader.model.instruments import Instrument

def on_instrument(self, instrument: Instrument) -> None:
    # 对 instrument 更新执行某些操作
    pass
```

## 精度

精度定义给定 instrument 上价格和数量允许的小数位数。每个 instrument 都指定 `price_precision` 与
`size_precision`，决定该市场上有效的小数分辨率。

NautilusTrader 在设计上严格强制精度。本节解释这一做法的理由与机制。

### 为什么强制精度

**逼真的市场模拟**。真实交易所只接受特定精度的价格和数量。
一个加密现货市场可能支持 2 位小数（如 `50000.01`），而另一个支持 8 位（如 `0.00012345`）。
如果在回测中允许任意精度，可能会以生产中不存在的价格档位成交，从而产生误导性的绩效指标。

**场所兼容性**。大多数交易所对收到的订单校验价格和数量精度，
拒绝超出 instrument 规格的订单。在平台层强制精度可以提早捕获这一类常见问题。
注意场所可能还会强制 tick 倍数或 step-size 约束，超出 `RiskEngine` 当前的校验范围，
因此仅满足精度并不能保证场所接受订单。

**确定性计算**。带显式精度的定点算术可消除浮点漂移，确保跨平台和跨环境的计算可复现。
处理相同数据的两个系统将始终产生相同结果。

**数据完整性**。回测撮合引擎校验所有传入的市场数据（quote、trade、bar）是否匹配 instrument 声明的精度。
这能尽早捕获 instrument 定义与数据源之间的不一致，避免成交价和成交量被静默地损坏。

### 精度如何工作

每个 instrument 定义两个精度值：

| 字段              | 约束                                  | 示例              |
|-------------------|---------------------------------------|------------------|
| `price_precision` | 订单价、触发价、成交价。              | `2` -> `50000.01` |
| `size_precision`  | 订单数量、成交数量。                  | `5` -> `1.00001`  |

这些精度与最小增量配对：

| 字段              | 用途                                       |
|-------------------|--------------------------------------------|
| `price_increment` | 最小有效价格变动（tick size）。            |
| `size_increment`  | 最小有效数量变动。                         |

增量自身的精度必须严格匹配 instrument 声明的精度。
例如 `price_precision=2` 且 `price_increment=Price(0.01, 2)` 是合法的，
但若两者不匹配会在创建 instrument 时报错。

### 精度的强制位置

精度在平台多个层面被校验：

1. **Instrument 创建**：`price_increment` 与 `size_increment` 的精度必须分别匹配
   `price_precision` 与 `size_precision`。
2. **风控引擎**：在订单到达场所之前，`RiskEngine` 检查订单的价格和数量精度是否超过 instrument 的限制。
   未通过的订单会被拒绝。
3. **撮合引擎**：回测期间，撮合引擎校验所有传入的市场数据是否匹配 instrument 的精度。
   不匹配会立即抛出 `RuntimeError`。

:::warning
`RiskEngine` 不会自动取整。如果你在仅支持 2 位小数的 instrument 上创建了 5 位小数精度的 `Price`，
订单将被拒绝。请使用 `instrument.make_price()` 和 `instrument.make_qty()` 显式取整。
:::

### 使用 instrument 的精度

使用 instrument 的工厂方法创建具有正确精度的值：

```python
instrument = self.cache.instrument(instrument_id)

price = instrument.make_price(0.90500)
quantity = instrument.make_qty(150)
```

这些方法把输入舍入到 instrument 声明的精度，确保结果能通过精度检查。
其他校验规则仍然适用（如最小/最大数量限制），且当取整后的值为零时 `make_qty()` 会抛错。

:::tip
创建订单参数时，总是使用 `instrument.make_price()` 与 `instrument.make_qty()`。
这能避免精度不匹配错误，并确保你的值具有该 instrument 所需的正确小数位数。
:::

如果你在回测中遇到精度不匹配错误，请检查：

1. instrument 定义是否匹配你的数据源精度。
2. 数据在加载时是否被无意取整或截断。
3. 自定义数据加载器是否保留了原始精度元数据。

## 限制

某些数值限制对 instrument 是可选的，可能为 `None`，这些与交易所相关，可能包括：

- `max_quantity`（单笔订单最大数量）。
- `min_quantity`（单笔订单最小数量）。
- `max_notional`（单笔订单最大名义值）。
- `min_notional`（单笔订单最小名义值）。
- `max_price`（最大有效报价或订单价）。
- `min_price`（最小有效报价或订单价）。

:::note
大多数限制由 Nautilus 的 `RiskEngine` 检查，否则超出公布的限制*可能*导致交易所拒单。
:::

## 保证金与费用

保证金计算由 `MarginAccount` 类处理。本节解释保证金如何工作并介绍你需要了解的关键概念。

### 何时适用保证金

每个交易所（如 CME 或 Binance）以特定账户类型运作，决定是否适用保证金计算。
在设置交易所 venue 时，你需要指定其中一种账户类型：

- `AccountType.MARGIN`：使用保证金计算的账户，下面会解释。
- `AccountType.CASH`：不涉及保证金计算的简单账户。
- `AccountType.BETTING`：为博彩设计的账户，同样不涉及保证金计算。

### 术语

在理解保证金交易之前，让我们先了解一些关键术语：

**名义价值**：以计价货币表示的合约总价值，代表你持仓的全部市场价值。例如 CME 的 EUR/USD 期货（代号 6E）：

- 每份合约代表 125,000 EUR（EUR 为基础货币，USD 为计价货币）。
- 如果当前市场价为 1.1000，名义价值等于 125,000 EUR × 1.1000（EUR/USD 价格）= 137,500 USD。

**杠杆**（`leverage`）：相对账户保证金能控制的市场敞口比率。
例如 10× 杠杆下，可用账户里的 1,000 USD 控制价值 10,000 USD 的持仓。

**初始保证金**（`margin_init`）：开仓所需的保证金比例。代表开新仓时账户里必须可用的最低资金。
这只是预先检查；并不实际锁定资金。

**维持保证金**（`margin_maint`）：维持持仓所需的保证金比例。该金额会被锁定以维持持仓。
通常低于初始保证金。可在策略中通过以下方式查看锁定的总金额（已开仓维持保证金之和）：

```python
self.portfolio.balances_locked(venue)
```

**Maker/Taker 费用**：交易所根据订单与市场的交互方式收取的费用：

- Maker 费用（`maker_fee`）：当你"做出"流动性、订单留在订单簿上时收取的费用（通常较低）。
  例如低于当前价的限价买单会增加流动性，成交时收取 *maker* 费。
- Taker 费用（`taker_fee`）：当你"吃掉"流动性、订单立即执行时收取的费用（通常较高）。
  例如市价买单或高于当前价的限价买单会移除流动性，收取 *taker* 费。

**费率符号约定**：Nautilus 在所有适配器和回测引擎中对费率使用一致的符号约定：

- **正费率** = 手续费（收取费用，减少账户余额）。
- **负费率** = 返佣（赚取费用，增加账户余额）。

例如 maker 费率 `-0.00025` 表示你因提供流动性而获得 0.025% 返佣，
而 taker 费率 `0.00075` 表示你因吃单而支付 0.075% 手续费。

:::note
不同交易所在其 API 中使用不同的符号约定。Nautilus 适配器会将其规范化为上述约定。
如果你为回测手动指定费率，请遵循该约定。
:::

:::tip
并非所有交易所或 instrument 都实现 maker/taker 费用。如果不存在，将 `Instrument`
（如 `FuturesContract`、`Equity`、`CurrencyPair`、`Commodity`、`Cfd`、`BinaryOption`、`BettingInstrument`）
的 `maker_fee` 与 `taker_fee` 都设为 0。
:::

### 保证金计算公式

`MarginAccount` 类使用以下公式计算保证金：

```python
# 初始保证金计算
margin_init = (notional_value / leverage * margin_init) + (notional_value / leverage * taker_fee)

# 维持保证金计算
margin_maint = (notional_value / leverage * margin_maint) + (notional_value / leverage * taker_fee)
```

**要点**：

- 两个公式结构相同，但使用各自的保证金比例（`margin_init` 与 `margin_maint`）。
- 每个公式由两部分组成：
  - **主保证金计算**：基于名义价值、杠杆和保证金比例。
  - **费用调整**：考虑 maker/taker 费用。

### 实现细节

如果你想深入了解技术实现：

- [nautilus_trader/accounting/accounts/margin.pyx](https://github.com/nautechsystems/nautilus_trader/blob/develop/nautilus_trader/accounting/accounts/margin.pyx)
- 关键方法：`calculate_margin_init(self, ...)` 与 `calculate_margin_maint(self, ...)`

## 手续费

交易手续费指交易所或经纪商为执行交易收取的费用。
虽然 maker/taker 费用在加密货币市场常见，但 CME 等传统交易所通常使用其他费用结构，如按合约的固定佣金。
NautilusTrader 支持多种手续费模型，以适应不同市场的多样化费用结构。

### 内置费用模型

框架提供两种内置费用模型实现：

1. `MakerTakerFeeModel`：实现加密货币交易所常见的 maker/taker 费用结构，按交易价值的百分比计算。
2. `FixedFeeModel`：每笔交易收取固定佣金，与规模无关。

### 创建自定义费用模型

虽然内置模型覆盖了常见场景，你可能会遇到需要特定佣金结构的情况。
NautilusTrader 灵活的架构允许你通过继承 `FeeModel` 实现自定义费用模型。

例如，如果你在按合约收取佣金的交易所（如 CME）交易期货，可以实现自定义费用模型。
创建自定义费用模型时，我们继承 `FeeModel` 基类，出于性能原因该类用 Cython 实现。
这种 Cython 实现也反映在参数命名约定上，类型信息通过下划线融入参数名（如 `Order_order` 或 `Quantity_fill_qty`）。

对 Python 开发者来说这些参数名看起来不寻常，但它们是 Cython 类型系统的结果，有助于保持与框架核心组件的一致性。
下面是如何创建按合约收费的费用模型：

```python
class PerContractFeeModel(FeeModel):
    def __init__(self, commission: Money):
        super().__init__()
        self.commission = commission

    def get_commission(self, Order_order, Quantity_fill_qty, Price_fill_px, Instrument_instrument):
        total_commission = Money(self.commission * Quantity_fill_qty, self.commission.currency)
        return total_commission
```

这个自定义实现通过将"固定每合约费"乘以"交易合约数"计算总佣金。
`get_commission(...)` 方法接收订单、成交数量、成交价和 instrument 的信息，允许基于这些参数灵活计算佣金。

我们的新类 `PerContractFeeModel` 继承自用 Cython 实现的 `FeeModel`，因此请注意方法签名中的 Cython 风格参数名：

- `Order_order`：订单对象，前缀 `Order_`。
- `Quantity_fill_qty`：成交数量，前缀 `Quantity_`。
- `Price_fill_px`：成交价，前缀 `Price_`。
- `Instrument_instrument`：instrument 对象，前缀 `Instrument_`。

这些参数名遵循 NautilusTrader 的 Cython 命名约定，前缀表明期望的类型。
与典型 Python 命名约定相比可能显得冗长，但它确保了类型安全以及与框架 Cython 代码库的一致性。

### 实际使用费用模型

要在交易系统中使用任意费用模型（无论内置还是自定义），在设置 venue 时指定即可。
下面是使用自定义按合约费用模型的示例：

```python
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.objects import Money, Currency

engine.add_venue(
    venue=venue,
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=USD,
    fee_model=PerContractFeeModel(Money(2.50, USD)),  # 每合约 2.50 USD
    starting_balances=[Money(1_000_000, USD)],  # 初始余额 1,000,000 USD
)
```

:::tip
实现自定义费用模型时，请确保其准确反映目标交易所的费用结构。
即使佣金计算的微小差异，也会在回测时显著影响策略的绩效指标。
:::

### 附加信息

由交易所提供（通常来自 JSON 序列化数据）的原始 instrument 定义还以通用 Python dict 形式包含进来。
这是为了保留并非统一 Nautilus API 的一部分的所有信息，用户在运行时通过 `.info` 属性访问。

## 合成 instrument

平台支持创建自定义的合成 instrument，可生成合成的 quote 和 trade。它们有助于：

- 让 `Actor` 和 `Strategy` 组件订阅 quote 或 trade 数据。
- 触发模拟订单。
- 从合成 quote 或 trade 构建 K 线。

合成 instrument 不能直接交易，因为它们仅作为构造存在于平台本地。它们作为分析工具，根据成分 instrument 提供有用指标。

未来我们计划支持合成 instrument 的订单管理，从而基于合成 instrument 的行为交易其成分 instrument。

:::info
合成 instrument 的 venue 始终为 `'SYNTH'`。
:::

合成 instrument 通过一个公式从两个或更多成分 instrument 派生其价格。
对订阅和模拟触发而言，它表现得像普通 instrument，但仅存在于 NautilusTrader 内部。

参见 [Synthetics](synthetics.md) 指南了解：

- 公式语言参考。
- 支持的运算符与函数。
- 创建和更新示例。
- 由合成价格触发的模拟订单。
- 校验规则与错误处理。

## 相关指南

- [Data](data.md) - instrument 的市场数据类型。
- [Orders](orders.md) - 订单引用 instrument。
