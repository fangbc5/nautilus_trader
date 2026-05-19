# Accounting

> 本文档为 [English 原文](../../docs/concepts/accounting.md) 的中文翻译版本。如有歧义请以英文原版为准。

会计子系统追踪平台所交互的每个账户的余额、保证金和盈亏。本指南涵盖数据模型、策略使用的查询 API，
以及适配器作者必须遵循的约定，以保证各场所之间的一致性。

它同样适用于回测和实盘交易。回测专用配置（起始余额、按场所选择保证金模型）请参见 [Backtesting](backtesting.md)。

## 账户类型

将场所附加到引擎用于实盘交易或回测时，通过 `account_type` 选择三种会计模式之一：

| 账户类型     | 典型用例                                         | 引擎锁定的内容                                                          |
| ------------ | ------------------------------------------------ | ----------------------------------------------------------------------- |
| Cash         | 现货交易（例如 BTC/USDT、股票）                  | 待成交订单将开仓的每个持仓的名义价值。                                  |
| Margin       | 衍生品或任何允许杠杆的产品                       | 每笔订单的初始保证金加上已开仓持仓的维持保证金。                        |
| Betting      | 体育博彩、博彩公司                               | 场所要求的下注金额；无杠杆。                                            |

### 现金账户

现金账户对交易进行全额结算；没有杠杆，因此也没有保证金的概念。锁定余额反映为待成交订单预留的名义金额。

### 保证金账户

保证金账户支持需要抵押品的标的，例如期货或带杠杆的加密永续。它们追踪账户余额、为未平仓订单和持仓预留保证金，
并按每个 instrument 应用可配置的杠杆。保证金按两种范围追踪；详见下文 [Margin scopes](#margin-scopes)。

**关键术语**：

- **杠杆（Leverage）**：相对账户权益放大敞口。杠杆越高，潜在收益和风险都越大。
- **初始保证金（Initial margin）**：提交订单时预留的抵押品。
- **维持保证金（Maintenance margin）**：维持已开仓持仓所需的最小抵押品。
- **锁定余额（Locked balance）**：作为抵押品预留的资金，不能用于新订单。

:::note
仅减仓（reduce-only）订单不会增加现金账户的 `balance_locked`，也不会增加保证金账户的初始保证金，
因为它们只能减少敞口。
:::

### 博彩账户

博彩账户专为下注后赢取或损失固定赔付的场所（预测市场、体育博彩）设计。引擎仅锁定场所要求的下注金额；
不适用杠杆和保证金。

## 余额模型

`AccountBalance` 在同一种货币下保存三个值：

- `total`：场所报告的总余额数字（视场所不同，可能是钱包余额、净清算价值或保证金余额）。
- `locked`：为未平仓订单和持仓预留的金额。
- `free`：可用于新订单的金额（`total - locked`）。

不变式 `total == locked + free` 必须在货币精度下始终成立。

Python 的 `AccountBalance(total, locked, free)` 构造函数要求一开始就传入三个字段。
Rust 的适配器代码还提供两个额外的派生构造函数，集中强制这一不变式；
当场所只报告三个值中的两个时，请优先使用它们而非 `AccountBalance::new`：

| Rust 辅助函数                           | 使用时机                                                                       |
| --------------------------------------- | ------------------------------------------------------------------------------ |
| `AccountBalance::from_total_and_locked` | 场所报告 total 与 locked；`free` 由其派生并截断到 `[0, total]`。              |
| `AccountBalance::from_total_and_free`   | 场所报告 total 与 free；`locked` 由其派生并截断。                              |
| `AccountBalance::new`                   | 三个值都已知且一致（测试、透传场景）。                                         |

当 `total >= 0` 时，辅助函数会将派生字段截断到 `[0, total]`，这样场所舍入产生的瞬态溢出
不会使账户进入损坏状态。

## 保证金范围

`MarginBalance` 有四个字段：`initial`、`maintenance`、`currency`，以及一个 `Optional[InstrumentId]`，
用于选择两种范围之一。

### 按 instrument 范围

`MarginBalance.instrument_id` 设置为具体 instrument。用于：

- 逐仓保证金（per-position collateral），例如 OKX 统一账户的某些模式或 Bybit 的逐仓模式。
- 回测或计算得到的保证金，由 `AccountsManager` 基于每个 instrument 的未平仓订单和持仓在本地推导。

### 账户级范围

`MarginBalance.instrument_id` 为 `None`。该条目以其 `currency`（抵押品货币）为键。用于：

- 按抵押品报告单一汇总值的全仓保证金场所。例子：Binance USDT-M（USDT）和 COIN-M（每个基础币一个）、
  OKX、BitMEX、Hyperliquid（USDC）、Bybit UNIFIED（每个币一个）、Deribit（每种货币一个）、Kraken Futures。

两种范围在同一个 `MarginAccount` 上并存于各自的内部存储。
`AccountState` 事件可以携带任意范围或两种范围的条目，
`MarginAccount.apply()` 会根据 `instrument_id` 是否设置，把每个条目路由到对应的存储中。

:::note
`MarginAccount.apply()` 用传入事件**整体替换**两个存储。它不会与先前状态合并。
发送部分快照的适配器必须在每次更新时包含所有有效的保证金条目，否则这些条目会一直被丢弃，直到下一个完整快照到来。
余额列表同样会被替换。
:::

## 策略查询 API

使用与场所报告形态匹配的查询。如果场所报告按 instrument 的保证金，按 `InstrumentId` 查询；
如果它报告账户级保证金，按 `Currency` 查询。

| 你想要的值的范围                         | 使用方法                                                  |
| ---------------------------------------- | -------------------------------------------------------- |
| 按 instrument 的保证金（逐仓）           | `margin(id)` / `margin_init(id)` / `margin_maint(id)`    |
| 单一抵押品的账户级保证金                 | `margin_for_currency(ccy)` / `margin_init_for_currency(ccy)` / `margin_maint_for_currency(ccy)` |
| 两种范围对某币的合计                     | `total_margin_init(ccy)` / `total_margin_maint(ccy)`     |

按条目查询在条目不存在时返回 `None`；总计查询总是返回 `Money`（若没有匹配则为该币零额）。

:::note
下面的名字是 `MarginAccount` 上的 Python/Cython API。使用 `nautilus-model` crate 的 Rust 策略
调用 `account_margin(&currency)`、`account_initial_margin(&currency)`、
`account_maintenance_margin(&currency)`、`total_initial_margin(currency)`、
`total_maintenance_margin(currency)`：以 `Option<InstrumentId>` 进行同样的范围拆分，方法名不同。
:::

### 按 instrument 查询（`MarginAccount`）

- `margin(instrument_id) -> MarginBalance | None`
- `margin_init(instrument_id) -> Money | None`
- `margin_maint(instrument_id) -> Money | None`
- `margins() -> dict[InstrumentId, MarginBalance]`（所有按 instrument 的条目）
- `margins_init() -> dict[InstrumentId, Money]`
- `margins_maint() -> dict[InstrumentId, Money]`

这些方法仅查看按 instrument 的存储。在全仓保证金场所返回空 dict 或 `None`。请使用下方的账户级查询。

### 账户级查询（`MarginAccount`）

- `margin_for_currency(currency) -> MarginBalance | None`
- `margin_init_for_currency(currency) -> Money | None`
- `margin_maint_for_currency(currency) -> Money | None`
- `account_margins() -> dict[Currency, MarginBalance]`（所有账户级条目）
- `account_margins_init() -> dict[Currency, Money]`
- `account_margins_maint() -> dict[Currency, Money]`

### 合计（`MarginAccount`）

这些方法对给定货币的按 instrument 与账户级条目求和：

- `total_margin_init(currency) -> Money`
- `total_margin_maint(currency) -> Money`

当策略在同时可能出现两种范围的场所交易时（例如逐仓持仓与全仓抵押品并存）有用。

### 清除账户级条目

- `clear_account_margin(currency)` 移除给定抵押品货币的账户级条目，并触发余额重新计算。
  对应按 instrument 条目的方法是 `clear_margin(instrument_id)`。

这些是系统方法；适配器代码通过 `MarginAccount.apply()` 隐式调用。策略一般不需要直接使用。

### 组合级查询

保证金查询：

- `portfolio.margins_init(venue=..., account_id=...) -> dict[InstrumentId, Money]`
- `portfolio.margins_maint(venue=..., account_id=...) -> dict[InstrumentId, Money]`

它们对应 `MarginAccount.margins_init` / `margins_maint`，仅返回按 instrument 的条目。
对全仓保证金场所的账户级数据，请通过 `portfolio.account(venue).margin_init_for_currency(ccy)` 直接查询账户。

盈亏、敞口、按市价估值（mark-to-market）和权益查询都接受 `venue` 与可选的 `account_id` 以限定多账户场所：

- `portfolio.unrealized_pnls(venue=..., account_id=...) -> dict[Currency, Money]`
- `portfolio.realized_pnls(venue=..., account_id=...) -> dict[Currency, Money]`
- `portfolio.total_pnls(venue=..., account_id=...) -> dict[Currency, Money]`
- `portfolio.net_exposures(venue=..., account_id=...) -> dict[Currency, Money]`
- `portfolio.mark_values(venue=..., account_id=...) -> dict[Currency, Money]`
- `portfolio.equity(venue=..., account_id=...) -> dict[Currency, Money]`
- `portfolio.missing_price_instruments(venue) -> list[InstrumentId]`

权益公式、价格回退链、基础货币转换行为以及"仅警告一次"的缺价跟踪器，请参见
[Portfolio 指南](portfolio.md#equity-and-mark-to-market)。

### 实例

Hyperliquid（单一抵押品 USDC 全仓）：

```python
usdc_margin = margin_account.margin_init_for_currency(USDC)
usdc_total  = margin_account.total_margin_init(USDC)
```

Bybit UNIFIED（按币全仓）：

```python
for ccy, margin_balance in margin_account.account_margins().items():
    print(ccy, margin_balance.initial, margin_balance.maintenance)
```

dYdX v4（USDC 全仓，按计价货币聚合）：

```python
usdc_margin = margin_account.margin_init_for_currency(USDC)
```

## 保证金模型

NautilusTrader 提供灵活的保证金计算模型，用于计算路径（回测，以及为对账而使用
`calculate_account_state=True` 的实盘策略）。场所报告的保证金会直接流入 `_account_margins` 或 `_margins`，
不经过模型。

### 概览

不同场所对杠杆的处理方式不同：

- **传统经纪商**（Interactive Brokers、TD Ameritrade）：无论杠杆多少，保证金比例固定。
- **加密货币交易所**（Binance 等）：杠杆可能降低保证金要求。

两种内置模型都使用 instrument 的 `margin_init` 和 `margin_maint` 字段，按名义价值的百分比计算保证金。
它们的区别仅在于杠杆是否减少预留量。对于真正按合约固定保证金的场所（CME / ICE），
请设置 `instrument.margin_init` 和 `margin_maint` 使百分比恢复到期望的美元金额，
或者实现一个 [自定义模型](#自定义模型)。

### 可用模型

#### `StandardMarginModel`

使用固定百分比，不对杠杆进行除法，符合传统经纪商行为。

```python
# 固定百分比 —— 忽略杠杆
margin = notional * instrument.margin_init
```

- 初始保证金：`notional_value * instrument.margin_init`
- 维持保证金：`notional_value * instrument.margin_maint`

**适用场景**：传统经纪商（Interactive Brokers）、保证金要求固定的外汇经纪商。

#### `LeveragedMarginModel`

按杠杆对保证金要求进行除法。

```python
# 杠杆降低保证金要求
adjusted_notional = notional / leverage
margin = adjusted_notional * instrument.margin_init
```

- 初始保证金：`(notional_value / leverage) * instrument.margin_init`
- 维持保证金：`(notional_value / leverage) * instrument.margin_maint`

**适用场景**：随杠杆降低保证金的加密货币交易所，杠杆影响保证金要求的场所。

### 默认行为

`MarginAccount` 默认使用 `LeveragedMarginModel`。可通过编程方式覆盖：

```python
from nautilus_trader.backtest.models import LeveragedMarginModel
from nautilus_trader.backtest.models import StandardMarginModel
from nautilus_trader.test_kit.stubs.execution import TestExecStubs

account = TestExecStubs.margin_account()

# 传统经纪商行为
account.set_margin_model(StandardMarginModel())

# 或使用杠杆模型（默认）
account.set_margin_model(LeveragedMarginModel())
```

### 实例：EUR/USD

- **Instrument**：EUR/USD
- **数量**：100,000 EUR
- **价格**：1.10000
- **名义**：$110,000
- **杠杆**：50x
- **`instrument.margin_init`**：3%

| 模型      | 计算                   | 结果   | 百分比     |
| --------- | ---------------------- | ------ | ---------- |
| Standard  | $110,000 × 0.03        | $3,300 | 3.00%      |
| Leveraged | ($110,000 ÷ 50) × 0.03 | $66    | 0.06%      |

在 $10,000 账户上：standard 模型会阻止交易；leveraged 模型允许交易。

### 自定义模型

继承 `MarginModel` 并通过 `MarginModelConfig` 接收配置：

```python
from decimal import Decimal

from nautilus_trader.backtest.config import MarginModelConfig
from nautilus_trader.backtest.models import MarginModel
from nautilus_trader.model.objects import Money


class RiskAdjustedMarginModel(MarginModel):
    def __init__(self, config: MarginModelConfig) -> None:
        self.risk_multiplier = Decimal(str(config.config.get("risk_multiplier", 1.0)))
        self.use_leverage = config.config.get("use_leverage", False)

    def calculate_margin_init(self, instrument, quantity, price, leverage, use_quote_for_inverse=False):
        notional = instrument.notional_value(quantity, price, use_quote_for_inverse)

        if self.use_leverage:
            adjusted = notional.as_decimal() / leverage
        else:
            adjusted = notional.as_decimal()

        margin = adjusted * instrument.margin_init * self.risk_multiplier
        return Money(margin, instrument.quote_currency)

    def calculate_margin_maint(self, instrument, side, quantity, price, leverage, use_quote_for_inverse=False):
        return self.calculate_margin_init(instrument, quantity, price, leverage, use_quote_for_inverse)
```

通过 `BacktestVenueConfig` 与 `MarginModelConfig` 在回测全局配置保证金模型，请参见
[Backtesting](backtesting.md#margin-models) 的保证金模型章节。

## 适配器约定

实盘适配器把场所响应翻译为 `AccountBalance` 和 `MarginBalance` 实例。适配器作者必须遵循以下约定：

### 构造 `AccountBalance`

优先使用派生辅助函数，使截断与 `total == locked + free` 不变式在中心层被强制。
仅在三个值都已经是权威值（例如测试中的透传路径）时，才适合手工计算三个字段并传给 `AccountBalance::new`。

### 构造 `MarginBalance`

选择与场所报告形态匹配的范围：

| 场所报告的内容                                 | 范围           | 发送方式                                                  |
| --------------------------------------------- | -------------- | -------------------------------------------------------- |
| 按 instrument（逐仓持仓）                      | 按 instrument  | `MarginBalance::new(initial, maint, Some(id))`           |
| 单一抵押品的单一汇总值（全仓）                 | 账户级         | `MarginBalance::new(initial, maint, None)`               |
| 多个汇总值，每个抵押品一个                     | 账户级         | 每个货币一个 `MarginBalance`，`instrument_id=None`        |

### 当前实盘适配器约定

| 适配器               | 范围                         | 抵押品货币                                              |
| -------------------- | ---------------------------- | -------------------------------------------------------- |
| Binance Futures      | 账户级                       | USDT-M：USDT（多资产模式下也可为 BNB 等）；COIN-M：每个基础币一个（BTC、ETH 等） |
| Bybit                | 账户级                       | 每个币一个（USDT、BTC、USDC 等）；累加持仓 IM + 订单 IM  |
| Deribit              | 账户级                       | 每种货币一个（BTC、ETH、USDC 等）                        |
| Hyperliquid          | 账户级                       | USDC                                                     |
| OKX                  | 账户级                       | USD（统一账户汇总）                                      |
| BitMEX               | 账户级                       | 按抵押品货币（XBT、USDT 等）                             |
| Kraken Futures       | 账户级                       | USD                                                      |
| dYdX v4              | 账户级                       | 按持仓计算，按计价货币聚合（USDC）                       |
| Interactive Brokers  | 账户级                       | 按账户货币                                               |

:::note
不再使用合成的 `ACCOUNT.{VENUE}` 或 `ACCOUNT-{COIN}.{VENUE}` `InstrumentId` 占位符。
账户级条目携带 `instrument_id=None`，并以 `currency` 为键。
:::

## 迁移说明

### 1.226.0

`MarginBalance.instrument_id` 改为 `Optional[InstrumentId]`，
`MarginAccount` 将其内部存储拆分为按 instrument 与账户级两种存储。
如果你的策略之前使用 `portfolio.margins_init(account_id=...)` 通过合成 ID 发现全仓余额，
请迁移到：

```python
account = portfolio.account(venue)

# 该账户所有账户级保证金
account_margins = account.account_margins_init()

# 特定抵押品货币
usdc_margin = account.margin_init_for_currency(USDC)

# 某货币的按 instrument 与账户级之和
total = account.total_margin_init(USDC)
```

按 instrument 的查询 API（`margin_init(instrument_id)`、`margins_init()`）保持不变，
现在具有严格的按 instrument 语义。

## 相关指南

- [Backtesting](backtesting.md)：起始余额、`MarginModelConfig` 与回测专用账户设置。
- [Portfolio](portfolio.md)：组合级盈亏、敞口与货币换算。
- [Positions](positions.md)：持仓生命周期、聚合与盈亏。
- [Adapters](adapters.md)：适配器作者的要求与最佳实践。
