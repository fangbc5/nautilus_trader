# Positions

> 本文档为 [English 原文](../../docs/concepts/positions.md) 的中文翻译版本。如有歧义请以英文原版为准。

本指南解释 NautilusTrader 中的持仓如何工作，包括生命周期、从订单成交聚合得到、盈亏计算，
以及对净额 OMS 配置而言重要的持仓快照（position snapshotting）概念。

## 概览

持仓代表对市场中某 instrument 的开放敞口。持仓对追踪交易绩效与风险至关重要，
它聚合该 instrument 的所有成交，并持续计算未实现盈亏、平均入场价、总敞口等指标。

系统在订单成交时自动创建持仓，并从开仓到平仓全程跟踪。
平台通过其 OMS（订单管理系统）配置同时支持净额（netting）与对冲（hedging）两种持仓管理风格。

## 持仓生命周期

### 创建

系统在首次成交时开仓：

- **NETTING OMS**：在某 instrument 的首次成交时开仓（每个 instrument 一个持仓）。
- **HEDGING OMS**：在新 `position_id` 的首次成交时开仓（每个 instrument 可有多个持仓）。

持仓追踪：

- 开仓订单和成交详情。
- 入场方向（`LONG` 或 `SHORT`）。
- 初始数量与平均价格。
- 初始化与开仓时间戳。

:::tip
可在 actor/策略内通过 `self.cache.position(position_id)` 或
`self.cache.positions(instrument_id=instrument_id)` 访问持仓。
:::

### 更新

随着新的成交发生，持仓会：

- 聚合买入与卖出成交的数量。
- 重新计算平均入场价与平均出场价。
- 更新峰值数量（达到的最大敞口）。
- 追踪所有相关的订单 ID 与成交 ID。
- 按货币累计手续费。

### 平仓

当净数量变为零（`FLAT`）时持仓关闭。平仓时：

- 记录平仓订单 ID。
- 计算从开仓到平仓的持续时间。
- 计算最终已实现盈亏。
- 在 `NETTING` OMS 下，当持仓之后再次开仓时，引擎会对已关闭状态拍快照以保留历史盈亏
  （参见 [持仓快照](#持仓快照)）。

## 订单成交聚合

持仓通过聚合订单成交来维持对市场敞口的准确视图。聚合过程同时处理交易活动的两侧：

### 买入成交

当 BUY 订单成交时：

- 增加多头敞口或减少空头敞口。
- 为开仓部分更新平均入场价。
- 为平仓部分更新平均出场价。
- 计算任何已平仓部分的已实现盈亏。

### 卖出成交

当 SELL 订单成交时：

- 增加空头敞口或减少多头敞口。
- 为开仓部分更新平均入场价。
- 为平仓部分更新平均出场价。
- 计算任何已平仓部分的已实现盈亏。

### 净持仓计算

持仓维护一个 `signed_qty` 字段，表示净敞口：

- 正值表示 `LONG` 持仓。
- 负值表示 `SHORT` 持仓。
- 零表示 `FLAT`（已平仓）持仓。

```python
# 示例：持仓聚合
# 初始 BUY 100 单位，价格 $50
signed_qty = +100  # LONG 持仓

# 后续 SELL 150 单位，价格 $55
signed_qty = -50   # 现在是 SHORT 持仓

# 最后 BUY 50 单位，价格 $52
signed_qty = 0     # 持仓 FLAT（已平仓）
```

## 持仓调整

持仓调整跟踪在正常订单成交之外发生的数量或盈亏变化，
确保持仓数量准确反映真实的净资产持仓。系统为这些场景生成 `PositionAdjusted` 事件。

### 基础货币手续费

交易现货货币对（如 BTC/USDT）或外汇现货时，以基础货币支付的手续费会直接影响实际收到或交付的净数量：

- **开仓成交**：手续费从交易数量中扣除。买入 1.0 BTC 并支付 0.001 BTC 手续费，
  净多头持仓为 0.999 BTC。
- **平仓成交**：手续费会作用于 `signed_qty`，因为它影响实际库存。
  以 0.000999 BTC 手续费平仓 0.999 BTC 多头持仓后，你会处于 0.000999 BTC 空头，
  而非 FLAT，因为你总共付出了 0.999999 BTC。
- **翻转**：手续费会影响翻转两侧的最终持仓规模。

:::note
基础货币手续费仅适用于手续费货币等于 `instrument.base_currency` 的现货货币对和外汇现货 instrument。
对其他 instrument，手续费独立跟踪，不影响持仓数量。
:::

### 资金费率支付

资金调整追踪永续期货的周期性支付，不影响持仓数量。
这些条目以 `quantity_change = None` 记录，并可能包含盈亏影响。

### 调整跟踪

所有调整都保留在持仓事件历史中：

- `position.adjustments` 返回所有 `PositionAdjusted` 事件的列表。
- 每个调整包含类型（`COMMISSION` 或 `FUNDING`）、数量变化和时间戳。
- 持仓关闭后再开仓时调整历史会清空。当事件被清除时，与被移除成交相关的手续费调整会重新生成，
  而非手续费调整（例如资金费率）会被保留。

## OMS 类型与持仓管理

NautilusTrader 支持两种主要 OMS 类型，它们从根本上影响持仓如何被跟踪与管理。
还有 `OmsType.UNSPECIFIED` 选项，默认采用组件的上下文。完整细节参见
[Execution 指南](execution.md#order-management-system-oms)。

### `NETTING`

在 `NETTING` 模式下，某 instrument 的所有成交会聚合到单个持仓：

- 每个 instrument ID 一个持仓。
- 所有成交贡献到同一个持仓。
- 当净数量变化时，持仓在 `LONG` 与 `SHORT` 之间翻转。
- 历史快照保留已关闭持仓状态。

### `HEDGING`

在 `HEDGING` 模式下，同一 instrument 可以存在多个持仓：

- 可同时存在多个 `LONG` 与 `SHORT` 持仓。
- 每个持仓有唯一的持仓 ID。
- 持仓独立跟踪。
- 不会自动跨持仓净额。
- 关闭的持仓仍保留在缓存历史中但不会重新开仓；新的成交会创建新持仓。

:::warning
使用 `HEDGING` 模式时，请注意保证金需求增加，因为每个持仓独立占用保证金。
部分场所可能不支持真正的对冲模式，会自动对持仓做净额处理。
:::

### 策略 OMS 与场所 OMS

平台允许策略和场所使用不同的 OMS 配置：

| 策略 OMS     | 场所 OMS  | 行为                                                        |
|--------------|-----------|-------------------------------------------------------------|
| `NETTING`    | `NETTING` | 策略和场所层均按 instrument 单一持仓。                      |
| `HEDGING`    | `HEDGING` | 两层均支持多持仓。                                          |
| `NETTING`    | `HEDGING` | 场所追踪多个，Nautilus 维护单一持仓。                       |
| `HEDGING`    | `NETTING` | 场所追踪单一，Nautilus 维护虚拟持仓。                       |

:::tip
对大多数交易场景，让策略和场所的 OMS 类型保持一致可简化持仓管理。
覆盖配置主要用于自营交易团队或对接遗留系统。场所相关 OMS 配置参见 [Live 指南](live.md)。
:::

## 持仓快照

持仓快照（position snapshotting）是 `NETTING` OMS 配置的重要特性，
它保留已关闭持仓的状态以便准确跟踪盈亏与生成报告。

### 为什么快照很重要

在 `NETTING` 系统中，当持仓关闭（变为 `FLAT`）后通过新交易重新开仓时，持仓对象会被重置以追踪新敞口。
若没有快照，之前持仓周期的历史已实现盈亏将丢失。

### 工作原理

当 `NETTING` 持仓关闭后又收到对同一 instrument 的新成交时，执行引擎会在重置之前对已关闭的持仓状态拍快照，保留：

- 最终数量与价格。
- 已实现盈亏。
- 所有成交事件。
- 累计手续费。

该快照按持仓 ID 索引存储在缓存中。持仓随后为新周期重置，而之前的快照仍可访问。
Portfolio 跨所有快照聚合盈亏，得到准确总额。

:::note
此历史快照机制不同于可选的持仓状态快照（`snapshot_positions`），
后者定期记录未平仓持仓状态用于遥测。`snapshot_positions` 与
`snapshot_positions_interval_secs` 设置请参见 [Live 指南](live.md)。
:::

### 示例场景

```python
# NETTING OMS 示例
# 周期 1：开 LONG 持仓
BUY 100 单位 价格 $50   # 开仓
SELL 100 单位 价格 $55  # 平仓，PnL = $500
# 拍快照保留 $500 已实现盈亏

# 周期 2：开 SHORT 持仓
SELL 50 单位 价格 $54   # 再开仓（SHORT）
BUY 50 单位 价格 $52    # 平仓，PnL = $100
# 拍快照保留 $100 已实现盈亏

# 总已实现盈亏 = $500 + $100 = $600（来自快照）
```

若没有快照，仅最近一个周期的盈亏可用，导致报告与分析错误。

## 盈亏计算

NautilusTrader 提供考虑 instrument 规格和市场约定的盈亏计算。

### 已实现盈亏

在持仓部分或完全平仓时计算：

```python
# 标准 instrument
realized_pnl = (exit_price - entry_price) * closed_quantity * multiplier

# 反向 instrument（按方向区分）
# LONG: realized_pnl = closed_quantity * multiplier * (1/entry_price - 1/exit_price)
# SHORT: realized_pnl = closed_quantity * multiplier * (1/exit_price - 1/entry_price)
```

引擎根据持仓方向自动选择正确公式。

### 未实现盈亏

针对未平仓持仓，使用当前市场价格计算。`price` 参数可接受任意参考价（bid、ask、mid、last 或 mark）：

```python
position.unrealized_pnl(last_price)  # 使用最新成交价
position.unrealized_pnl(bid_price)   # LONG 持仓的保守估计
position.unrealized_pnl(ask_price)   # SHORT 持仓的保守估计
```

对 `FLAT` 持仓，无论传入什么价格都返回 `Money(0, settlement_currency)`。

### 总盈亏

合并已实现与未实现部分：

```python
total_pnl = position.total_pnl(current_price)
# 返回 realized_pnl + unrealized_pnl
```

### 货币注意事项

- 盈亏以 instrument 的结算货币计算。
- 对外汇，通常是计价货币。
- 对反向合约，盈亏可能以基础货币计算。
- Portfolio 按 instrument 在结算货币下聚合已实现盈亏。
- 多币种合计需要在 Position 类之外做换算。

## 手续费与成本

持仓追踪所有交易成本：

- 按货币累计手续费。
- 每次成交的手续费加入累计总额。
- 支持多种手续费货币。
- 已实现盈亏仅在以结算货币计价时才纳入手续费。
- 其他货币的手续费独立追踪，可能需要换算。

```python
commissions = position.commissions()
# 返回 list[Money]，按货币聚合的手续费总额

notional = position.notional_value(current_price)
# 返回计价货币（标准）或基础货币（反向）的 Money
```

**限制**：

- 如果反向 instrument 未设置 `base_currency` 则会 panic。
- 不处理 quanto 合约（返回的是计价货币，而非结算货币）。
- 对 quanto instrument，请改用 `instrument.calculate_notional_value()`。

## 持仓属性与状态

### 标识符

- `id`：唯一持仓标识符。
- `instrument_id`：交易的 instrument。
- `account_id`：持仓所在账户。
- `trader_id`：持有该持仓的 trader。
- `strategy_id`：管理该持仓的策略。
- `opening_order_id`：开仓的客户订单 ID。
- `closing_order_id`：平仓的客户订单 ID。

### 持仓状态

- `side`：当前持仓方向（`LONG`、`SHORT` 或 `FLAT`）。
- `entry`：当前未平仓持仓的方向（`LONG` 为 `Buy`，`SHORT` 为 `Sell`）。在持仓翻转方向时更新。
- `quantity`：当前持仓绝对数量。
- `signed_qty`：有符号持仓数量（`LONG` 为正，`SHORT` 为负）。
- `peak_qty`：持仓生命周期中达到的最大数量。
- `is_open`：持仓是否当前打开。
- `is_closed`：持仓是否已关闭（`FLAT`）。
- `is_long`：持仓方向是否为 `LONG`。
- `is_short`：持仓方向是否为 `SHORT`。

### 价格与估值

- `avg_px_open`：平均入场价。
- `avg_px_close`：平仓时的平均出场价。
- `realized_pnl`：已实现盈亏。
- `realized_return`：已实现收益率（小数形式，如 5% 为 0.05）。
- `quote_currency`：instrument 的计价货币。
- `base_currency`：基础货币（如适用）。
- `settlement_currency`：盈亏结算货币。

### Instrument 规格

- `multiplier`：合约乘数。
- `price_precision`：价格小数精度。
- `size_precision`：数量小数精度。
- `is_inverse`：是否为反向 instrument。

### 时间戳

- `ts_init`：持仓初始化时刻。
- `ts_opened`：持仓开仓时刻。
- `ts_last`：最近更新时间戳。
- `ts_closed`：持仓关闭时刻。
- `duration_ns`：从开仓到平仓的持续纳秒数。

### 关联数据

- `symbol`：instrument 的代号。
- `venue`：交易场所。
- `client_order_ids`：与持仓关联的所有客户订单 ID。
- `venue_order_ids`：与持仓关联的所有场所订单 ID。
- `trade_ids`：来自场所的所有成交 ID。
- `events`:应用到持仓的所有订单成交事件。
- `event_count`：已应用的成交事件总数。
- `last_event`：最近的成交事件。
- `last_trade_id`：最近的成交 ID。

:::info
完整的类型信息和详细属性文档参见 Position [API 参考](/docs/python-api-latest/model/position.html#nautilus_trader.model.position.Position)。
:::

## 事件与跟踪

持仓维护完整的事件历史：

- 所有订单成交事件按时间顺序存储。
- 关联的客户订单 ID 被跟踪。
- 来自场所的成交 ID 被保留。
- 事件计数指示已应用的成交总数。

这些历史数据支持：

- 详细的持仓分析。
- 交易对账。
- 业绩归因。
- 审计跟踪。

:::tip
使用 `position.events` 访问完整成交历史以便对账。
`position.trade_ids` 属性有助于匹配经纪商对账单。对账最佳实践参见 [Execution 指南](execution.md)。
:::

## 数值精度

持仓计算在盈亏和均价计算上使用 64 位浮点（`f64`）算术。
虽然定点类型（`Price`、`Quantity`、`Money`）在配置的小数位数下保持精确，
但内部计算为性能和防溢出转为 `f64`。

### 设计理由

平台在持仓计算中使用 `f64` 以兼顾性能与精度：

- 浮点运算明显快于任意精度算术。
- 即使是 128 位整数，原始整数乘法也可能溢出。
- 每次计算都从精确的定点值开始，避免累积误差。
- IEEE-754 双精度提供约 15 位十进制精度。

### 已验证的精度特性

测试确认 `f64` 算术对典型交易场景保持精度：

- 标准金额：标准货币下 ≥ 0.01 的金额无精度损失。
- 高精度 instrument：9 位小数的加密货币价格在 1e-6 容差内保持。
- 连续成交：100 次成交无漂移（手续费精度达 1e-10）。
- 极端价格：处理 0.00001 到 99,999.99999 范围且无溢出。
- 往返交易：同价开仓与平仓产生精确盈亏（仅手续费）。

实现细节参见 `crates/model/src/position.rs` 中的 `test_position_pnl_precision_*` 测试。

:::note
若需为合规或审计跟踪使用精确十进制算术，请考虑使用外部库的 `Decimal` 类型。
低于 `f64` epsilon（约 1e-15）的极小金额可能舍入为零。
这不会影响以典型货币精度（通常 2-9 位小数）进行的现实交易场景。
:::

## 与其他组件的集成

持仓与多个关键组件交互：

- **Portfolio**：跨 instrument 与策略聚合持仓。
- **ExecutionEngine**：根据成交创建并更新持仓。
- **Cache**：存储持仓状态与快照。
- **RiskEngine**：监控持仓限制与敞口。

:::note
不会为价差 instrument 创建持仓。虽然连带订单仍可对价差触发，但它们在不与持仓关联的情况下工作。
引擎对价差 instrument 与常规持仓分别处理。
:::

## 小结

持仓是跟踪交易活动与绩效的核心。理解持仓如何聚合成交、计算盈亏，
以及如何处理不同 OMS 配置，对构建交易策略至关重要。
持仓快照在 `NETTING` 模式下提供准确的历史跟踪，事件历史则支持详细的分析与对账。

## 相关指南

- [Events](events.md) - 成交如何产生持仓事件。
- [Orders](orders.md) - 创建和修改持仓的订单。
- [Execution](execution.md) - 更新持仓的成交处理。
- [Portfolio](portfolio.md) - 组合级持仓聚合。
