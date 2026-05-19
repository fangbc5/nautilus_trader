# Reports

> 本文档为 [English 原文](../../docs/concepts/reports.md) 的中文翻译版本。如有歧义请以英文原版为准。

本指南介绍 `ReportProvider` 类提供的组合分析与报告能力，以及这些报告如何用于盈亏会计和回测后分析。

## 概览

NautilusTrader 中的 `ReportProvider` 类从交易数据生成结构化分析报告，
把原始订单、成交、持仓和账户状态转化为 pandas DataFrame，便于分析与可视化。
这些报告帮助你评估策略表现、分析执行质量、验证盈亏会计。

报告可以通过两种方式生成：

- **Trader 辅助方法**（推荐）：便捷的方法如 `trader.generate_orders_report()`。
- **直接使用 ReportProvider**：对数据选择和过滤需要更精细控制时使用。

报告在回测和实盘交易环境下提供一致的分析能力，使绩效评估和策略对比可靠可信。

## 可用的报告

`ReportProvider` 类提供若干静态方法以从交易数据生成报告。
每个报告返回一个带有特定列和索引的 pandas DataFrame，便于分析。

### 订单报告

生成所有订单的完整视图：

```python
# 使用 Trader 辅助方法（推荐）
orders_report = trader.generate_orders_report()

# 或直接使用 ReportProvider
from nautilus_trader.analysis import ReportProvider

orders = cache.orders()
orders_report = ReportProvider.generate_orders_report(orders)
```

**返回 `pd.DataFrame`。主要列包括：**

| 列                 | 描述                                                    |
|--------------------|---------------------------------------------------------|
| `client_order_id`  | 索引 —— 唯一的订单标识符。                              |
| `instrument_id`    | 交易标的。                                              |
| `strategy_id`      | 创建该订单的策略。                                      |
| `trader_id`        | 交易者标识符。                                          |
| `account_id`       | 账户标识符（若已分配）。                                |
| `venue_order_id`   | 场所分配的订单 ID（若被接受）。                         |
| `side`             | BUY 或 SELL。                                           |
| `type`             | MARKET、LIMIT 等。                                      |
| `status`           | 当前订单状态。                                          |
| `quantity`         | 原始订单数量（字符串）。                                |
| `filled_qty`       | 已成交数量（字符串）。                                  |
| `price`            | 限价（与订单类型相关）。                                |
| `avg_px`           | 平均成交价（若有成交）。                                |
| `time_in_force`    | 有效期指令。                                            |
| `ts_init`          | 订单初始化时间戳（Unix 纳秒）。                         |
| `ts_last`          | 最后更新时间戳（Unix 纳秒）。                           |

额外列因订单类型不同而异（例如止损单的 `trigger_price`、GTD 订单的 `expire_time`）。
完整字段列表请参见 `Order.to_dict()`。

### 订单成交报告

提供成交订单的汇总（每个订单一行）：

```python
# 使用 Trader 辅助方法（推荐）
fills_report = trader.generate_order_fills_report()

# 或直接使用 ReportProvider
orders = cache.orders()
fills_report = ReportProvider.generate_order_fills_report(orders)
```

该报告仅包含 `filled_qty > 0` 的订单，列与订单报告相同，但仅限于已执行的订单。
注意，此报告中 `ts_init` 与 `ts_last` 被转换为 datetime 对象以便分析。

### 成交报告

详细列出单个成交事件（每次成交一行）：

```python
# 使用 Trader 辅助方法（推荐）
fills_report = trader.generate_fills_report()

# 或直接使用 ReportProvider
orders = cache.orders()
fills_report = ReportProvider.generate_fills_report(orders)
```

**返回 `pd.DataFrame`。主要列包括：**

| 列                 | 描述                                     |
|--------------------|------------------------------------------|
| `client_order_id`  | 索引 —— 订单标识符。                     |
| `trade_id`         | 唯一的成交标识符。                       |
| `venue_order_id`   | 场所分配的订单 ID。                      |
| `instrument_id`    | 交易标的。                               |
| `strategy_id`      | 创建该订单的策略。                       |
| `account_id`       | 账户标识符。                             |
| `position_id`      | 关联的持仓 ID（如适用）。                |
| `order_side`       | BUY 或 SELL。                            |
| `order_type`       | 订单类型（MARKET、LIMIT 等）。           |
| `last_px`          | 成交价（字符串）。                       |
| `last_qty`         | 成交数量（字符串）。                     |
| `currency`         | 成交货币。                               |
| `liquidity_side`   | MAKER 或 TAKER。                         |
| `commission`       | 手续费金额与货币。                       |
| `ts_event`         | 成交时间戳（datetime）。                 |
| `ts_init`          | 初始化时间戳（datetime）。               |

完整字段列表请参见 `OrderFilled.to_dict()`。

### 持仓报告

包含快照的持仓分析：

```python
# 使用 Trader 辅助方法（推荐）
# NETTING OMS 自动包含快照
positions_report = trader.generate_positions_report()

# 或直接使用 ReportProvider
positions = cache.positions()
snapshots = cache.position_snapshots()  # 用于 NETTING OMS
positions_report = ReportProvider.generate_positions_report(
    positions=positions,
    snapshots=snapshots
)
```

**返回 `pd.DataFrame`。主要列包括：**

| 列                 | 描述                                     |
|--------------------|------------------------------------------|
| `position_id`      | 索引 —— 唯一的持仓标识符。               |
| `instrument_id`    | 交易标的。                               |
| `strategy_id`      | 管理该持仓的策略。                       |
| `trader_id`        | 交易者标识符。                           |
| `account_id`       | 账户标识符。                             |
| `opening_order_id` | 开仓订单 ID。                            |
| `closing_order_id` | 平仓订单 ID。                            |
| `entry`            | 入场方向（BUY 或 SELL）。                |
| `side`             | 持仓方向（LONG、SHORT 或 FLAT）。        |
| `quantity`         | 当前持仓数量。                           |
| `peak_qty`         | 达到的最大数量。                         |
| `avg_px_open`      | 平均入场价。                             |
| `avg_px_close`     | 平均出场价（若已平仓）。                 |
| `commissions`      | 已付手续费列表。                         |
| `realized_pnl`     | 已实现盈亏。                             |
| `realized_return`  | 收益率百分比。                           |
| `ts_init`          | 持仓初始化时间戳。                       |
| `ts_opened`        | 开仓时间戳（datetime）。                 |
| `ts_last`          | 最后更新时间戳。                         |
| `ts_closed`        | 平仓时间戳（datetime 或 NA）。           |
| `duration_ns`      | 持仓持续纳秒数。                         |
| `is_snapshot`      | 是否为历史快照。                         |

### 账户报告

跟踪账户余额和保证金随时间的变化：

```python
# 使用 Trader 辅助方法（推荐）
# 需要 venue 参数
from nautilus_trader.model.identifiers import Venue
venue = Venue("BINANCE")
account_report = trader.generate_account_report(venue)

# 或直接使用 ReportProvider
account = cache.account(account_id)
account_report = ReportProvider.generate_account_report(account)
```

**返回 `pd.DataFrame`。列包括：**

| 列              | 描述                                       |
|-----------------|--------------------------------------------|
| `ts_event`      | 索引 —— 账户状态变化的时间戳。             |
| `account_id`    | 账户标识符。                               |
| `account_type`  | 账户类型（如 SPOT、MARGIN）。              |
| `base_currency` | 账户基础货币。                             |
| `total`         | 总余额（字符串）。                         |
| `free`          | 可用余额（字符串）。                       |
| `locked`        | 在订单中锁定的余额（字符串）。             |
| `currency`      | 余额货币。                                 |
| `reported`      | 余额是否由场所报告。                       |
| `margins`       | 保证金信息（列表，如适用）。               |
| `info`          | 场所特定的额外信息。                       |

每一行代表一项余额条目；多币种账户每次账户状态事件会产生多行。

## 盈亏会计注意事项

精确的盈亏会计需要仔细考虑几个因素：

### 基于持仓的盈亏

- **已实现盈亏**：在持仓部分或完全平仓时计算。
- **未实现盈亏**：使用当前价格按市价估值。
- **手续费影响**：仅在结算货币下计入。

:::warning
盈亏计算取决于 OMS 类型。在 `NETTING` OMS 下，持仓快照在持仓重新开仓时保留历史盈亏。
报告中务必包含快照以获得准确的总盈亏。在 `HEDGING` OMS 下，由于每个持仓有唯一 ID 且永不重新开仓，
不使用快照。
:::

### 多币种会计

处理多币种时：

- 每个持仓在其结算货币下追踪盈亏。
- 组合聚合需要货币换算。
- 手续费货币可能与结算货币不同。

```python
# 跨持仓访问盈亏
for position in positions:
    realized = position.realized_pnl  # 以结算货币计
    unrealized = position.unrealized_pnl(last_price)

    # 处理多币种聚合（示意）
    # 注意：货币换算需要用户提供汇率
    if position.settlement_currency != base_currency:
        # 从你的数据源应用换算汇率
        # rate = get_exchange_rate(position.settlement_currency, base_currency)
        # realized_converted = realized.as_double() * rate
        pass
```

### 快照注意事项

对 `NETTING` OMS：

```python
from nautilus_trader.model.objects import Money

# 包含快照以获取完整盈亏（按货币）
pnl_by_currency = {}

# 累加当前持仓的盈亏
for position in cache.positions(instrument_id=instrument_id):
    if position.realized_pnl:
        currency = position.realized_pnl.currency
        if currency not in pnl_by_currency:
            pnl_by_currency[currency] = 0.0
        pnl_by_currency[currency] += position.realized_pnl.as_double()

# 累加历史快照的盈亏
for snapshot in cache.position_snapshots(instrument_id=instrument_id):
    if snapshot.realized_pnl:
        currency = snapshot.realized_pnl.currency
        if currency not in pnl_by_currency:
            pnl_by_currency[currency] = 0.0
        pnl_by_currency[currency] += snapshot.realized_pnl.as_double()

# 为每个货币创建 Money 对象
total_pnls = [Money(amount, currency) for currency, amount in pnl_by_currency.items()]
```

## 回测后分析

回测完成后，可通过多种报告和组合分析器获得分析结果。

### 访问回测结果

```python
# 回测运行后
engine.run(start=start_time, end=end_time)

# 通过 Trader 辅助方法生成报告
orders_report = engine.trader.generate_orders_report()
positions_report = engine.trader.generate_positions_report()
fills_report = engine.trader.generate_fills_report()

# 或直接访问数据进行自定义分析
orders = engine.cache.orders()
positions = engine.cache.positions()
snapshots = engine.cache.position_snapshots()
```

### 组合统计

组合分析器提供性能指标：

```python
# 访问组合分析器
portfolio = engine.portfolio

# 获取不同类别的统计
stats_pnls = portfolio.analyzer.get_performance_stats_pnls()
stats_returns = portfolio.analyzer.get_performance_stats_returns()
stats_general = portfolio.analyzer.get_performance_stats_general()
```

:::info
关于可用统计的详细信息以及如何创建自定义指标，请参见 [Portfolio 指南](portfolio.md#portfolio-statistics)。
Portfolio 指南包括：

- 内置统计类别（基于盈亏、收益、持仓、订单）。
- 通过 `PortfolioStatistic` 创建自定义统计。
- 注册和使用自定义指标。
:::

### 可视化

NautilusTrader 通过 Plotly 提供交互式 tearsheet 和图表：

```python
from nautilus_trader.analysis import create_tearsheet

# 回测运行后
engine.run()

# 生成交互式 HTML tearsheet
create_tearsheet(engine, output_path="tearsheet.html")
```

这会创建一个包含以下内容的交互式 HTML 报告：

- 权益曲线
- 回撤分析
- 月度收益热力图
- 性能统计表
- 收益分布

如需更精细的控制，可分别生成各个图表：

```python
from nautilus_trader.analysis import create_equity_curve

returns = engine.portfolio.analyzer.returns()
fig = create_equity_curve(returns, title="My Strategy Equity")
fig.show()  # 在浏览器中显示
fig.write_image("equity.png")  # 导出为 PNG（需要 kaleido）
```

安装可视化依赖：

```bash
uv pip install "nautilus_trader[visualization]"
```

## 报告生成模式

### 实盘交易

实盘交易中，定期生成报告：

```python
import pandas as pd

class ReportingActor(Actor):
    def on_start(self):
        # 安排定期报告
        self.clock.set_timer(
            name="generate_reports",
            interval=pd.Timedelta(minutes=30),
            callback=self.generate_reports
        )

    def generate_reports(self, event):
        # 生成并记录报告
        positions_report = self.trader.generate_positions_report()

        # 保存或发送报告
        positions_report.to_csv(f"positions_{event.ts_event}.csv")
```

### 绩效分析

回测分析：

```python
import pandas as pd

# 运行回测
engine.run(start=start_time, end=end_time)

# 收集结果
positions_closed = engine.cache.positions_closed()
stats_pnls = engine.portfolio.analyzer.get_performance_stats_pnls()
stats_returns = engine.portfolio.analyzer.get_performance_stats_returns()
stats_general = engine.portfolio.analyzer.get_performance_stats_general()

# 创建汇总字典
results = {
    "total_positions": len(positions_closed),
    "pnl_total": stats_pnls.get("PnL (total)"),
    "sharpe_ratio": stats_returns.get("Sharpe Ratio (252 days)"),
    "profit_factor": stats_general.get("Profit Factor"),
    "win_rate": stats_general.get("Win Rate"),
}

# 显示结果
results_df = pd.DataFrame([results])
print(results_df.T)  # 转置以纵向显示
```

:::info
报告由内存中的数据结构生成。对于大规模分析或长时间运行的系统，建议把报告持久化到数据库以便高效查询。
持久化选项参见 [Cache 指南](cache.md)。
:::

## 与其他组件的集成

`ReportProvider` 与多个系统组件协作：

- **Cache**：所有交易数据（订单、持仓、账户）的来源。
- **Portfolio**：使用报告进行绩效分析和指标计算。
- **BacktestEngine**：使用报告进行回测后分析与可视化。
- **持仓快照**：在 `NETTING` OMS 下准确报告盈亏所必需。

## 小结

`ReportProvider` 从订单、成交、持仓和账户状态生成结构化 DataFrame 报告，便于分析与可视化。
对于 `NETTING` OMS 的总盈亏精度，请在生成报告时包含持仓快照。

## 相关指南

- [Visualization](visualization.md) - 从回测结果生成交互式 tearsheet 与图表。
- [Portfolio](portfolio.md) - 组合统计与绩效指标。
- [Backtesting](backtesting.md) - 运行生成报告的回测。
- [Cache](cache.md) - 存储报告数据的缓存系统。
