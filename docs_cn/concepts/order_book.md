# Order Book（订单簿）

> 本文档为 [English 原文](../../docs/concepts/order_book.md) 的中文翻译版本。如有歧义请以英文原版为准。

NautilusTrader 提供了由 Rust 实现的高性能订单簿，能够维护从 L1 到 L3 数据的完整订单簿状态。`OrderBook` 是跟踪公开市场深度的主要组件，而 `OwnOrderBook` 则单独跟踪你自己的订单，从而提供减去自身订单后的真实可用流动性视图。

:::note
本指南介绍 Rust API。这些类型也通过 PyO3 绑定（`nautilus_pyo3.OrderBook`、`nautilus_pyo3.OwnOrderBook`）从 Python 暴露。由 `cache.order_book()` 返回的 v1 旧版 Cython `OrderBook`（`nautilus_trader.model.book.OrderBook`）接口类似但并不完全相同。差异请参考 API 参考文档。
:::

## 订单簿类型

`OrderBook` 实例在回测和实盘交易中按标的维护：

- `L3_MBO`：**Market by order** 数据。跟踪每个价格层级的每个订单，以订单 ID 为键。
- `L2_MBP`：**Market by price** 数据。按价格层级聚合订单（每个价格一个条目）。
- `L1_MBP`：**最优盘口**数据，也称为最佳买卖（BBO）。只捕获最优价格。

:::note
`QuoteTick`、`TradeTick` 和 Bar 等最优盘口数据也可以维护 `L1_MBP` 订单簿。
:::

## 订阅订单簿数据

策略和 Actor 通过以下方法订阅订单簿更新。订阅与处理器位于 Python 策略/Actor 层：

```python
# L3/L2 增量 delta
self.subscribe_order_book_deltas(instrument_id)

# 聚合深度快照（最多 10 个层级）
self.subscribe_order_book_depth(instrument_id)

# 按定时间隔的完整订单簿快照
self.subscribe_order_book_at_interval(instrument_id, interval_ms=1000)
```

每种订阅类型将数据分发到对应的处理器：

```python
def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
    ...

def on_order_book_depth(self, depth: OrderBookDepth10) -> None:
    ...

def on_order_book(self, order_book: OrderBook) -> None:
    ...
```

## 访问订单簿

`OrderBook` 提供最优盘口访问器：

```rust
let best_bid: Option<Price> = book.best_bid_price();
let best_ask: Option<Price> = book.best_ask_price();
let spread: Option<f64> = book.spread();
let midpoint: Option<f64> = book.midpoint();
```

## 分析方法

`OrderBook` 支持市场深度分析和执行模拟：

```rust
// 给定数量的平均成交价
let avg_px = book.get_avg_px_for_quantity(quantity, OrderSide::Buy);

// 目标敞口（名义价值）的平均价格与数量
let (price, qty, exposure) =
    book.get_avg_px_qty_for_exposure(target_exposure, OrderSide::Buy);

// 优于或等于某价格的累计可用数量
let qty = book.get_quantity_for_price(price, OrderSide::Buy);

// 仅在指定价格层级的数量
let qty = book.get_quantity_at_level(price, OrderSide::Buy, 2);

// 在订单簿上模拟成交
let fills: Vec<(Price, Quantity)> = book.simulate_fills(&order);

// 所有交叉层级（与订单数量无关）
let levels = book.get_all_crossed_levels(OrderSide::Buy, price, 2);
```

## 完整性校验

`book_check_integrity` 函数校验订单簿状态与其类型一致：

- **L1_MBP**：每侧不超过一个层级。
- **L2_MBP**：每个价格层级不超过一个订单。
- **L3_MBO**：无结构约束（任意价格层级可有任意数量订单）。
- **所有类型**：最优买价不得高于最优卖价（交叉订单簿）。锁定市场（bid == ask）视为有效。

这些检查会在应用 delta 时内部运行。传入 delta 的 instrument ID 也会与订单簿的 instrument ID 校验，不匹配时返回 `BookIntegrityError::InstrumentMismatch`。

## 美化输出

`OrderBook` 与 `OwnOrderBook` 都提供 `pprint` 方法，将订单簿渲染为可读的表格：

```rust
book.pprint(5, None);
book.pprint(5, Some(Decimal::new(1, 2))); // group_size = 0.01
```

`group_size` 参数将价格层级聚合为更粗的分组，适用于 tick size 很细的标的。输出是一个格式化表格，左侧为买单，中间为价格，右侧为卖单。

## 自有订单簿（Own order book）

`OwnOrderBook` 将你自己的工作中订单与公开订单簿分开跟踪。做市与其他报价策略使用它来估算各价格层级在减去自身订单后的可用流动性。

当启用 `manage_own_order_books` 时，执行引擎会维护自有订单簿。缓存会随着订单事件改变状态而更新现有的自有订单簿。符合条件的订单需具备价格且不使用 `IOC` 或 `FOK` 有效期（Time in Force）。终止事件仍可能清理已有的自有订单簿条目，即便该订单原本不符合跟踪资格。

### 订单生命周期

`OwnOrderBook` 跟踪订单的整个生命周期。订单在提交或通过对账（reconciliation）实现时加入，随状态更新而更新，关闭时移除。更新涵盖订单模型支持的 accepted、pending update、pending cancel、partially filled、filled、canceled、expired、rejected 与 denied 等状态。

每个 `OwnBookOrder` 携带：

- `client_order_id`：用于将自有订单簿与缓存状态对账的客户端订单 ID。
- `venue_order_id`：交易场所分配的订单 ID（已分配时）。
- `side`、`price` 与 `size`：订单方向及剩余的自有订单簿价格层级。
- `order_type` 与 `time_in_force`：用于过滤与诊断的订单类型元数据。
- `status`：当前订单状态，例如 `SUBMITTED`、`ACCEPTED` 或 `PENDING_CANCEL`。
- `ts_last`：应用到该自有订单簿条目的最新订单事件的时间戳。
- `ts_accepted`：交易场所接受订单的时间戳。
- `ts_submitted`：订单提交的时间戳。
- `ts_init`：订单初始化的时间戳。

这些字段使过滤视图可以根据状态与接受时间包括或排除自有订单（参见 [Status and time filtering](#status-and-time-filtering)）。

### 审计

`audit_open_orders` 方法将自有订单簿与一组有效的 client order ID 进行对账。任何不在该集合中的自有订单簿条目都会被移除，并作为审计错误记录。`Cache::audit_own_order_books` 从开放与在途订单中构建该集合，避免在交易场所正常延迟期间移除已提交订单。实盘系统可以通过自有订单簿审计间隔定期运行该审计。

### 查询

```rust
// 检查特定订单是否被跟踪
let in_book = own_book.is_order_in_book(&client_order_id);

// 按方向获取所有被跟踪的订单 ID
let bid_ids = own_book.bid_client_order_ids();
let ask_ids = own_book.ask_client_order_ids();

// 按价格层级聚合的数量
let bid_qty = own_book.bid_quantity(None, None, None, None, None);
let ask_qty = own_book.ask_quantity(None, None, None, None, None);

// 美化输出
own_book.pprint(5, None);
```

### 过滤视图

从公开订单簿中减去你自己的订单，得到净可用流动性：

```rust
// price -> quantity 的过滤映射（已减去自有订单）
let net_bids = book.bids_filtered_as_map(Some(10), Some(&own_book), None, None, None);
let net_asks = book.asks_filtered_as_map(Some(10), Some(&own_book), None, None, None);

// 提供完整分析方法的过滤 OrderBook
let filtered = book.filtered_view(Some(&own_book), Some(10), None, None, None);
let avg_px = filtered.get_avg_px_for_quantity(quantity, OrderSide::Buy);
```

`filtered_view` 方法返回一个减去自有数量后的新 `OrderBook`，可在净订单簿上使用完整的分析方法（`spread`、`midpoint`、`get_avg_px_for_quantity` 等）。

### 状态与时间过滤

过滤视图支持对自有订单进行可选的状态与时间过滤：

```rust
let status = Some(AHashSet::from([OrderStatus::Accepted]));

// 仅减去 ACCEPTED 订单（忽略 SUBMITTED、PENDING_CANCEL 等）
let filtered = book.filtered_view(Some(&own_book), None, status, None, None);
```

`accepted_buffer_ns` 参数提供一个宽限期：设置后，只有 `ts_accepted + buffer <= now` 的订单才会被纳入。这可以排除可能尚未出现在公开订单簿数据源中的最近接受订单。该缓冲适用于 `ts_accepted` 字段，与订单状态无关。可以与状态过滤组合，同时排除非 accepted 订单。

```rust
// 只减去至少 500ms 前接受的订单
let filtered = book.filtered_view(
    Some(&own_book),
    None,
    None,
    Some(500_000_000),
    Some(clock.timestamp_ns()),
);
```

## 二元市场

对于二元/预测市场（例如 Polymarket），标的有两个互补的方向（YES 与 NO），其价格之和为 1.0。NO 侧 0.40 的买单在经济学上等同于 YES 侧 0.60 的卖单。

`OwnOrderBook::combined_with_opposite` 方法处理该转换，将两侧的自有订单合并到一个视图中：

```rust
let yes_own = own_yes_book
    .cloned()
    .unwrap_or_else(|| OwnOrderBook::new(yes_instrument_id));

let no_own = own_no_book
    .cloned()
    .unwrap_or_else(|| OwnOrderBook::new(no_instrument_id));

// 通过对偶价格变换（1 - price）合并 NO 侧订单
let combined = yes_own.combined_with_opposite(&no_own).unwrap();

// 使用合并后的自有订单簿过滤公开的 YES 订单簿
let filtered = book.filtered_view(Some(&combined), None, None, None, None);
```

变换过程如下：

- 价格为 P 的 NO 卖单变为合并订单簿中价格为 1 - P 的买单。
- 价格为 P 的 NO 买单变为合并订单簿中价格为 1 - P 的卖单。

这能够完整展现你自有流动性在市场两侧的分布。
