# Portfolio（组合）

> 本文档为 [English 原文](../../docs/concepts/portfolio.md) 的中文翻译版本。如有歧义请以英文原版为准。

Portfolio 是交易节点或回测中跨所有活跃策略管理和跟踪所有持仓的中央枢纽。它从多个标的中汇总持仓数据，提供持仓、风险敞口与整体表现的统一视图。

## 货币转换

Portfolio 支持 PnL 与敞口计算的自动货币转换，便于以你偏好的货币查看结果。这在以下场景特别有用：跨多个不同结算货币的标的交易，或管理多个不同基础货币的账户。

### 支持的转换

货币转换可用于以下 Portfolio 查询：

- `realized_pnl()` / `realized_pnls()` - 将已实现盈亏（PnL）转换为目标货币。
- `unrealized_pnl()` / `unrealized_pnls()` - 将未实现盈亏转换为目标货币。
- `total_pnl()` / `total_pnls()` - 将总盈亏转换为目标货币。
- `net_exposure()` / `net_exposures()` - 将净敞口转换为目标货币。

所有方法都接受可选的 `target_currency` 参数，用于指定期望的输出货币。

### 单账户行为

查询单个账户而未指定 `target_currency` 时，Portfolio 会自动将值转换为该账户的基础货币：

```python
# 以账户的基础货币（例如 USD）返回敞口
exposure = portfolio.net_exposures(venue=BINANCE, account_id=account_id)
```

### 多账户行为

同时查询多个账户时，行为取决于你查询所有标的（`net_exposures()`）还是单个标的（`net_exposure()`）：

**对于 `net_exposures()`（所有标的）：**

- **相同基础货币**：自动转换为公共基础货币。
- **不同基础货币**：返回包含多种货币的 dict，每种货币已转换为其账户的基础货币。提供 `target_currency` 可得到单一货币的结果。

**对于 `net_exposure()`（跨账户的单个标的）：**

- **不同基础货币**：除非你提供 `target_currency`，否则返回 `None`。

```python
# 场景 1：多账户，全部以 USD 为基础货币
exposures = portfolio.net_exposures(venue=BINANCE)
# 返回 {USD: Money(...)}

# 场景 2：多账户，基础货币不同（USD 和 EUR）
exposures = portfolio.net_exposures(venue=BINANCE)
# 返回 {USD: Money(...), EUR: Money(...)}

# 强制跨账户统一为单一货币
exposures = portfolio.net_exposures(venue=BINANCE, target_currency=USD)
# 返回 {USD: Money(...)}
```

### 转换失败

当提供了 `target_currency` 且货币转换失败时，行为取决于方法类型：

- **单值方法**（`realized_pnl`、`unrealized_pnl`、`total_pnl`、`net_exposure`）：
  返回 `None` 并记录错误日志，以避免错误的数值。
- **返回 dict 的方法**（`realized_pnls`、`unrealized_pnls`、`total_pnls`、`net_exposures`）：
  忽略转换失败的标的，但返回转换成功的结果。

:::warning
跨货币聚合使用 `target_currency` 时，必须有可用的汇率数据。
:::

### 转换价格类型

将敞口转换为目标货币时，Portfolio 会根据持仓构成使用不同价格类型：

- **全部多头**：使用 `BID` 价格（对多头敞口偏保守）。
- **全部空头**：使用 `ASK` 价格（对空头敞口偏保守）。
- **混合持仓**：使用 `MID` 价格（同时存在多空时中性）。

这样可以确保转换反映现实的市场状况：你会以 bid 价格平掉多头、以 ask 价格回补空头。对于混合持仓，mid 价格提供中性估值。

如果在 Portfolio 配置中启用了 `use_mark_xrates`，混合持仓与一般转换将以 `MARK` 价格替代 `MID` 价格。

## 权益与按市值计价

Portfolio 暴露三个拉取式查询用于持续的组合估值。每个返回按相关账户基础货币或原生结算货币归类的逐币种结果。

| 方法                                       | 返回                                                                  |
|--------------------------------------------|-----------------------------------------------------------------------|
| `mark_values(venue, account_id)`           | 开放持仓的有符号 MTM 合计。                                           |
| `equity(venue, account_id)`                | 结合余额与持仓估值的总权益。                                          |
| `missing_price_instruments(venue)`         | 当前被标记为无法估价的标的。                                          |

多头贡献正向名义价值，空头贡献负向名义价值。无持仓的方向会被跳过。

### 权益公式

权益将账户余额与开放持仓估值组合，根据账户类型使用不同的第二项：

- **现金账户与博彩账户**：`balances_total + Σ mark_value(open positions)`。
- **保证金账户**：`balances_total + Σ unrealized_pnl(open positions)`。

现金与博彩路径在内部使用 `mark_values()`。保证金路径使用与 `unrealized_pnls()` 相同的缓存未实现盈亏管线。

### 价格回退

估值会按以下顺序向 `Cache` 询价，命中即停止：

1. mark 价格（当 `PortfolioConfig` 中 `use_mark_prices=true` 且缓存中有 mark 价时）。
2. 与方向相匹配的 quote：多头取 `BID`，空头取 `ASK`。
3. 最近成交价。
4. 最近缓存 bar 的收盘价（当 `bar_updates=true` 时填充）。

如果以上四项都无法得到价格，该持仓会进入缺失价格追踪器并在求和时被跳过。

### 基础货币转换

当 `convert_to_account_base_currency=true`（默认值）且账户设置了 `base_currency` 时，结算货币的值会通过 `Cache.get_xrate()` 提供的 `MID` 汇率转换为基础货币。若 `use_mark_xrates=true`，则先使用 `Cache.get_mark_xrate()` 返回的缓存 mark 汇率，若不可用则回退到 `MID`。输出字典则只包含一个匹配基础货币的键。

当 `convert_to_account_base_currency=false`，或账户未设置 `base_currency` 时，结果按每个持仓的原生结算货币归类，不进行汇率转换。

如果某次必要的转换缺少汇率数据，对应持仓将被视为无法估价，通过缺失价格追踪器进行标记，而不是默默以 1.0 的汇率估值。

### 缺失价格追踪

追踪器是按交易场所组织的标的 ID 集合，记录上一次 `mark_values()` 或 `equity()` 调用中无法估价的标的。它有两种可观察行为：

- 每个标的从"可估价"切换为"无法估价"时只触发一次警告日志，后续调用不会重复触发。下一次切换回"可估价"会清除条目，未来再次失去价格时再次发出警告。
- 当某个交易场所没有任何开放持仓时，会清除其追踪器条目，避免过时的标的继续被标记。

调用 `missing_price_instruments(venue)` 可以查看当前集合。

:::tip
如果 `equity()` 低于你的预期，先检查 `missing_price_instruments(venue)`，再去核对计算。某个标的的 quote、trade 与 bar 数据源全部为空，是最常见的隐性缺口原因。
:::

### 交易场所与账户范围

`mark_values` 与 `equity` 接受可选的 `account_id`，将聚合限定到单个账户。`account_id=None` 时，结果聚合该交易场所上的所有账户。

缺失价格追踪器以交易场所为粒度。`missing_price_instruments` 只接受交易场所参数；带 `account_id` 过滤的 `mark_values(venue, account_id)` 调用不会清除该交易场所条目，因此同交易场所上其他账户标记的标的将保留。

## 组合统计

平台提供了一系列[内置组合统计](https://github.com/nautechsystems/nautilus_trader/tree/develop/crates/analysis/src/statistics)，用于分析交易组合在回测与实盘交易中的表现。

统计大致分为以下几类：

- 基于盈亏（PnL）的统计（按币种）
- 基于回报的统计
- 基于持仓的统计
- 基于订单的统计

你可以在任意时刻调用某个 trader 的 `PortfolioAnalyzer` 来计算统计，包括*在*回测或实盘交易过程中。

## 自定义统计

可以通过继承 `PortfolioStatistic` 基类并实现任意 `calculate_` 方法来定义自定义组合统计。

例如，下面是内置 `WinRate` 统计的实现：

```python
import pandas as pd
from typing import Any
from nautilus_trader.analysis.statistic import PortfolioStatistic


class WinRate(PortfolioStatistic):
    """
    Calculates the win rate from a realized PnLs series.
    """

    def calculate_from_realized_pnls(self, realized_pnls: pd.Series) -> Any | None:
        # Preconditions
        if realized_pnls is None or realized_pnls.empty:
            return 0.0

        # Calculate statistic
        winners = [x for x in realized_pnls if x > 0.0]
        losers = [x for x in realized_pnls if x <= 0.0]

        return len(winners) / float(max(1, (len(winners) + len(losers))))
```

之后可将这些统计注册到 trader 的 `PortfolioAnalyzer`：

```python
stat = WinRate()

# Register with the portfolio analyzer
engine.portfolio.analyzer.register_statistic(stat)
```

可用方法详见 [`PortfolioAnalyzer` API 参考](/docs/python-api-latest/analysis.html#nautilus_trader.analysis.analyzer.PortfolioAnalyzer)。

:::tip
你的统计应当处理退化输入，如 `None`、空序列或数据不足的情况。对未知/不可计算的值返回 `None`，对语义上合理的默认值（例如无交易时的胜率）则返回 `0.0`。
:::

## 回报：持仓 vs 组合

分析器跟踪两个不同的回报序列：

- **持仓回报**（`analyzer.position_returns()`）按持仓度量已实现回报，基于平均开仓价的方向感知价格回报。它反映的是标的在开仓到平仓之间的价格变化，与账户规模或杠杆无关。
- **组合回报**（`analyzer.portfolio_returns()`）按账户总余额的每日百分比变化度量。在 100,000 美元账户上盈利 900 美元时，当日大约报 0.9%。

当分析器拥有跨越至少两个不同自然日的账户状态历史时，会自动计算组合回报，并把它作为统计、tearsheet 与月度回报热力图的主序列。同一天的多个快照算作一天，因此仅有日内交易并不会产生组合回报。当组合回报不可用时，会回退到持仓回报。

便捷访问器 `analyzer.returns()` 会解析这个优先级：有组合回报时使用组合回报，否则使用持仓回报。

### 多币种账户

组合回报需要单一货币的余额历史。当账户携带多币种余额时，分析器无法生成单一回报序列，会静默回退到持仓回报。统计与 tearsheet 图表使用 `returns()` 解析出的序列。

如果你需要为多币种账户得到组合层级的回报，请在外部将余额换算为同一货币后再计算百分比变化。

### 按交易场所计算

在回测引擎中，分析器按交易场所运行（`engine.pyx`）。每个交易场所的账户产生其自身的组合回报序列。Tearsheet 会聚合所有缓存账户，为多交易场所回测生成合并的回报序列。

## 回测分析

回测运行完成后，引擎将已实现盈亏、回报、持仓和订单数据传递给每个注册的统计。任何输出会显示在 tear sheet 的 `Portfolio Performance` 标题下，按以下方式分组：

- 已实现盈亏统计（按币种）
- 回报统计（针对整个组合）
- 由持仓与订单数据派生的通用统计（针对整个组合）

## 相关指南

- [Positions](positions.md) - 组合中的持仓跟踪。
- [Reports](reports.md) - 生成组合分析报告。
- [Visualization](visualization.md) - 组合性能可视化。
