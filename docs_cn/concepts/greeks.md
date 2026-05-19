# Greeks

> 本文档为 [English 原文](../../docs/concepts/greeks.md) 的中文翻译版本。如有歧义请以英文原版为准。

Nautilus 提供两条处理期权 Greeks（期权价格对市场变量变动的敏感度）的路径：

1. **场所提供的 Greeks（Rust/PyO3）**：通过 `OptionGreeks` 数据类型和期权链聚合系统，
   从 Deribit、Bybit、OKX 等场所实时流式传输的 Greeks。
2. **本地 Greeks 计算器（Cython/Python）**：`GreeksCalculator` 类，
   基于缓存中的市场数据计算 Black-Scholes Greeks，支持组合聚合、冲击场景和 beta 加权。

两条路径可以独立工作，也可以一起使用。场所提供的 Greeks 通过数据订阅系统抵达，无需本地计算。
本地计算器覆盖不流式传输 Greeks 的场所、回测以及自定义调整（冲击、beta 加权、百分比 Greeks）。

## 场所提供的 Greeks（Rust/PyO3）

### OptionGreeks

`OptionGreeks` 类型代表场所为单一期权合约提供的敏感度。它是一种 Rust 原生类型，通过 PyO3 暴露给 Python。

| 字段                | 类型             | 描述                                                |
|--------------------|------------------|-----------------------------------------------------|
| `instrument_id`    | `InstrumentId`   | 这些 Greeks 适用的期权合约。                        |
| `delta`            | `float`          | 单位标的资产变动对应的期权价格变动率。              |
| `gamma`            | `float`          | 单位标的资产变动对应的 delta 变动率。               |
| `vega`             | `float`          | 对隐含波动率 1% 变动的敏感度。                      |
| `theta`            | `float`          | 每日时间衰减（dV/dt / 365.25）。                    |
| `rho`              | `float`          | 对利率变动的敏感度。                                |
| `mark_iv`          | `float` 或 None  | Mark 隐含波动率。                                   |
| `bid_iv`           | `float` 或 None  | Bid 隐含波动率。                                    |
| `ask_iv`           | `float` 或 None  | Ask 隐含波动率。                                    |
| `underlying_price` | `float` 或 None  | 计算时的标的资产价格。                              |
| `open_interest`    | `float` 或 None  | 该合约的未平仓量。                                  |
| `ts_event`         | `int`            | 事件的 UNIX 时间戳（纳秒）。                        |
| `ts_init`          | `int`            | 初始化时的 UNIX 时间戳（纳秒）。                    |

在 actor 或策略中订阅：

```python
self.subscribe_option_greeks(instrument_id, client_id=ClientId("DERIBIT"))
```

处理更新：

```python
def on_option_greeks(self, greeks: OptionGreeks) -> None:
    self.log.info(f"delta={greeks.delta:.4f} gamma={greeks.gamma:.6f}")
```

完整订阅 API（含期权链聚合、行权价范围过滤、快照模式）请参见 [Options](options.md) 指南。

### 底层 Rust 类型

核心 Rust 实现位于 `crates/model/src/data/greeks.rs`：

- `OptionGreekValues`：包含 `delta`、`gamma`、`vega`、`theta`、`rho` 字段的普通 struct。
  实现 `Add` 和 `Mul<f64>` 以支持聚合。
- `OptionGreeks`（位于 `crates/model/src/data/option_chain.rs`）：在 `OptionGreekValues`
  基础上额外携带 `instrument_id`、隐含波动率字段和时间戳。
  实现 `Deref<Target = OptionGreekValues>`，因此可以直接访问 Greeks 字段。
- `HasGreeks` trait：提供返回 `OptionGreekValues` 的 `greeks()` 方法。
  由 `OptionGreekValues` 和 `OptionGreeks` 共同实现。

### Black-Scholes 函数（Rust/PyO3）

从 `crates/model/src/data/greeks.rs` 向 Python 暴露的底层定价函数：

```python
from nautilus_trader.core.nautilus_pyo3 import (
    black_scholes_greeks,
    imply_vol,
    imply_vol_and_greeks,
    refine_vol_and_greeks,
)

# 在已知波动率的情况下计算 Greeks
result = black_scholes_greeks(s=100.0, r=0.05, b=0.0, vol=0.20, is_call=True, k=100.0, t=0.25)
# result.delta、result.gamma、result.vega、result.theta、result.price、result.vol

# 由市场价格反推波动率，然后计算 Greeks
result = imply_vol_and_greeks(s=100.0, r=0.05, b=0.0, is_call=True, k=100.0, t=0.25, price=5.0)

# 从初始波动率估计精炼波动率（收敛更快）
result = refine_vol_and_greeks(s=100.0, r=0.05, b=0.0, is_call=True, k=100.0, t=0.25,
                                target_price=5.0, initial_vol=0.18)
```

这些函数返回的 `BlackScholesGreeksResult` 包含：`price`、`vol`、`delta`、`gamma`、`vega`、`theta` 与 `itm_prob`。

**约定**：

- Vega 按 0.01 缩放（对应 1 个百分点的波动率变动）。
- Theta 按 1/365.25 缩放（每日衰减）。
- 美式期权在计算 Greeks 时按欧式定价。

## 本地 Greeks 计算器（Cython/Python）

### GreeksCalculator

`nautilus_trader/model/greeks.pyx` 中的 `GreeksCalculator` 类根据缓存的市场数据计算 Black-Scholes Greeks。
它可在任何 actor 或策略中访问。

```python
from nautilus_trader.model.greeks import GreeksCalculator

# 通常在 on_start() 中创建
calculator = GreeksCalculator(cache=self.cache, clock=self.clock)
```

#### 单标的 Greeks

按数量为 1 计算单个标的（期权或标的资产）的 Greeks：

```python
greeks = calculator.instrument_greeks(
    instrument_id=option_id,
    flat_interest_rate=0.0425,  # 当缓存中没有收益率曲线时使用
)
# 返回 GreeksData 或 None
```

计算器的步骤：

1. 在缓存中查找该 instrument 及其标的资产。
2. 获取当前价格（优先 MID，其次回退到 LAST）。
3. 从缓存中查找收益率曲线（回退到 `flat_interest_rate`）。
4. 使用 `imply_vol_and_greeks` 从市场价格反推波动率。
5. 返回包含全部计算值的 `GreeksData` 对象。

对于非期权标的（期货、股票），计算器返回 `delta=1`（或 beta 加权的 delta）且无 gamma/vega/theta 的 `GreeksData`。

**冲击场景**：对现货、波动率或时间应用假设变动：

```python
greeks = calculator.instrument_greeks(
    instrument_id=option_id,
    spot_shock=10.0,            # 标的资产 +10 个点
    vol_shock=0.02,             # 波动率绝对增加 2%
    time_to_expiry_shock=1/365, # 向前滚动一天
)
```

**波动率更新**：从缓存中的初始值精炼隐含波动率以加快收敛：

```python
greeks = calculator.instrument_greeks(
    instrument_id=option_id,
    update_vol=True,        # 使用缓存的 vol 作为起点
    cache_greeks=True,      # 存储结果以供下次迭代
)
```

**Beta 加权 Greeks**：以某个指数为基准表达 delta 和 gamma：

```python
greeks = calculator.instrument_greeks(
    instrument_id=option_id,
    index_instrument_id=InstrumentId.from_str("SPX.CBOE"),
    beta_weights={underlying_id: 1.15},
    percent_greeks=True,
)
```

**时间加权 vega**：将不同到期日的 vega 归一化：

```python
greeks = calculator.instrument_greeks(
    instrument_id=option_id,
    vega_time_weight_base=30,  # 归一化为 30 天 vega
)
```

#### 组合 Greeks

按筛选条件聚合所有匹配未平仓持仓的 Greeks：

```python
portfolio = calculator.portfolio_greeks(
    underlyings=["AAPL", "MSFT"],
    venue=Venue("CBOE"),
    strategy_id=StrategyId("DELTA_HEDGE-001"),
    flat_interest_rate=0.0425,
    index_instrument_id=InstrumentId.from_str("SPX.CBOE"),
    beta_weights=beta_dict,
    percent_greeks=True,
)
# 返回 PortfolioGreeks：pnl、price、delta、gamma、vega、theta
```

筛选器：

- `underlyings`：标的符号前缀列表（如 `["AAPL"]` 匹配 AAPL 股票及所有 AAPL 期权）。
- `venue`：限制为单个 venue。
- `instrument_id`：限制为单个 instrument。
- `strategy_id`：限制为单个策略。
- `side`：按持仓方向过滤（LONG、SHORT）。
- `greeks_filter`：接受每个持仓的 `PortfolioGreeks` 的可调用对象；返回 `True` 表示包含。

### GreeksData

`GreeksData` 是一个 Python 自定义数据类（`@customdataclass`），承载单个 instrument 的 Greeks 计算的全部上下文。
它继承自 `Data`，支持 Arrow 序列化、缓存存储和 catalog 持久化。

| 字段                | 类型            | 描述                                                |
|---------------------|-----------------|-----------------------------------------------------|
| `instrument_id`     | `InstrumentId`  | 标的。                                              |
| `is_call`           | `bool`          | True 表示看涨，False 表示看跌。                     |
| `strike`            | `float`         | 行权价。                                            |
| `expiry`            | `int`           | 到期日（YYYYMMDD 整数形式）。                       |
| `expiry_in_days`    | `int`           | 距到期的天数。                                      |
| `expiry_in_years`   | `float`         | 距到期的年数（天数 / 365.25）。                     |
| `multiplier`        | `float`         | 合约乘数。                                          |
| `quantity`          | `float`         | 持仓数量（`instrument_greeks` 总是 1）。            |
| `underlying_price`  | `float`         | 计算时使用的标的资产价格。                          |
| `interest_rate`     | `float`         | 使用的利率。                                        |
| `cost_of_carry`     | `float`         | 持有成本（r - 股息收益率；期货为 0）。              |
| `vol`               | `float`         | 隐含波动率。                                        |
| `pnl`               | `float`         | 相对持仓入场价的盈亏（若提供持仓）。                |
| `price`             | `float`         | 模型价格。                                          |
| `delta`             | `float`         | Delta。                                             |
| `gamma`             | `float`         | Gamma。                                             |
| `vega`              | `float`         | Vega（dV / 1% vol 变动）。                          |
| `theta`             | `float`         | Theta（每日衰减）。                                 |
| `itm_prob`          | `float`         | 实值概率。                                          |

`GreeksData` 可通过 `to_portfolio_greeks()` 方法缩放到组合级，该方法把所有值乘以合约 `multiplier`。
`*` 运算符可应用持仓数量：

```python
position_greeks = signed_qty * instrument_greeks  # 返回 PortfolioGreeks
```

### PortfolioGreeks

`PortfolioGreeks` 是 `portfolio_greeks()` 的聚合结果。支持加法（`+`，用于组合持仓）和标量乘法（`*`，用于缩放）：

| 字段    | 类型    | 描述              |
|---------|---------|-------------------|
| `pnl`   | `float` | 聚合盈亏。        |
| `price` | `float` | 聚合模型价值。    |
| `delta` | `float` | 组合 delta。      |
| `gamma` | `float` | 组合 gamma。      |
| `vega`  | `float` | 组合 vega。       |
| `theta` | `float` | 组合 theta。      |

### YieldCurveData

`YieldCurveData` 存储利率或股息收益率曲线。`GreeksCalculator` 通过货币代码（用于利率）
或标的 instrument ID（用于股息收益率）从缓存中查找曲线。

```python
from nautilus_trader.model.greeks_data import YieldCurveData
import numpy as np

curve = YieldCurveData(
    ts_event=0,
    ts_init=0,
    curve_name="USD",
    tenors=np.array([0.25, 0.5, 1.0, 2.0]),
    interest_rates=np.array([0.04, 0.042, 0.045, 0.048]),
)

# 可调用：为给定 tenor 插值
rate = curve(0.75)  # 二次插值
```

## 在两条路径之间做选择

| 条件                         | 场所提供（`OptionGreeks`）             | 本地计算器（`GreeksCalculator`）        |
|------------------------------|----------------------------------------|------------------------------------------|
| 计算位置                     | 由场所完成                             | 本地 Black-Scholes                       |
| 延迟                         | 随市场数据到达                         | 按需计算                                 |
| 支持场所                     | Deribit、Bybit、OKX                    | 任何具有期权 instrument 的场所           |
| 冲击场景                     | 不支持                                 | 现货、波动率、时间冲击                   |
| 组合聚合                     | 手动（迭代 `OptionChainSlice`）        | 通过 `portfolio_greeks()` 内建支持       |
| Beta 加权                    | 不支持                                 | 内建                                     |
| 回测支持                     | 通过录制的 `OptionGreeks` 数据         | 任意时间点的缓存价格                     |
| 可用的 Greeks                | delta、gamma、vega、theta、rho、IV、OI | delta、gamma、vega、theta、itm_prob、vol |
| 数据类型                     | `OptionGreeks`（Rust/PyO3）            | `GreeksData`（Python `@customdataclass`）|

## Greek 定义

供参考，Nautilus 计算的 Greeks：

| Greek      | 符号   | 定义                                                                          |
|------------|--------|-------------------------------------------------------------------------------|
| Delta      | `d`    | 期权价格对标的资产价格的一阶导数（dV/dS）。                                   |
| Gamma      | `g`    | 期权价格对标的资产价格的二阶导数（d2V/dS2）。                                 |
| Vega       | `v`    | 对隐含波动率 1 个百分点变动的敏感度（dV/dVol）。                              |
| Theta      | `t`    | 每日时间衰减：每日历日对应的期权价格变动（dV/dt / 365.25）。                  |
| Rho        | `r`    | 对无风险利率变动的敏感度（dV/dr）。                                           |
| ITM prob   | -      | 期权到期为实值的概率：P(ϕS_T > ϕK)，看涨时 ϕ = 1，看跌时 ϕ = -1。              |

## 示例

仓库中包含完整可运行的示例：

- `examples/live/bybit/bybit_option_greeks.py`：订阅 Bybit 场所提供的 Greeks。
- `examples/live/deribit/deribit_option_greeks.py`：订阅 Deribit 场所提供的 Greeks。
- `examples/live/okx/okx_option_greeks.py`：订阅 OKX 场所提供的 Greeks。

## 相关指南

- [Options](options.md) - 期权 instrument、期权链订阅与行权价过滤。
- [Data](data.md) - 内置数据类型、自定义数据与订阅模型。
- [Actors](actors.md) - 订阅与处理函数参考。
- [Strategies](strategies.md) - 策略实现与处理方法。
