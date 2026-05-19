# %% [markdown]
# # 快速上手
#
# 本文件为英文版本（../../docs/getting_started/quickstart.py）的中文注释版本。
#
# 在五分钟内运行你的第一个回测。
#
# [在 GitHub 上查看源码](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/getting_started/quickstart.py)。

# %% [markdown]
# ## 前置条件
#
# - Python 3.12+
# - `pip install nautilus_trader`

# %% [markdown]
# ## 编写一个策略
#
# 一个策略继承自 `Strategy` 基类，并通过重写事件处理器来响应行情数据。
# 本示例交易一个 EMA 交叉信号：当短期指数移动平均线向上穿越长期指数移动平均线时买入，
# 反向穿越时卖出。

# %%
from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class EMACrossConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_ema_period: int = 10
    slow_ema_period: int = 20


class EMACross(Strategy):
    def __init__(self, config: EMACrossConfig):
        super().__init__(config)
        self.fast_ema = ExponentialMovingAverage(config.fast_ema_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_ema_period)

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return

        if self.fast_ema.value >= self.slow_ema.value:
            if self.portfolio.is_flat(self.config.instrument_id):
                self.buy()
            elif self.portfolio.is_net_short(self.config.instrument_id):
                self.close_all_positions(self.config.instrument_id)
                self.buy()
        elif self.fast_ema.value < self.slow_ema.value:
            if self.portfolio.is_flat(self.config.instrument_id):
                self.sell()
            elif self.portfolio.is_net_long(self.config.instrument_id):
                self.close_all_positions(self.config.instrument_id)
                self.sell()

    def buy(self):
        instrument = self.cache.instrument(self.config.instrument_id)
        order = self.order_factory.market(
            self.config.instrument_id,
            OrderSide.BUY,
            instrument.make_qty(self.config.trade_size),
        )
        self.submit_order(order)

    def sell(self):
        instrument = self.cache.instrument(self.config.instrument_id)
        order = self.order_factory.market(
            self.config.instrument_id,
            OrderSide.SELL,
            instrument.make_qty(self.config.trade_size),
        )
        self.submit_order(order)

    def on_stop(self):
        self.close_all_positions(self.config.instrument_id)


# %% [markdown]
# `on_start` 注册两个 EMA 指标，引擎会在每根新 bar 到来时自动更新它们。
# `on_bar` 等待指标完成热身（warm up），然后根据交叉信号建仓或反手。

# %% [markdown]
# ## 生成合成数据
#
# 为了让快速上手示例自包含，我们用随机游走生成 10,000 根合成的 EUR/USD 1 分钟 K 线（bar）。
# 在实际使用中，你会从数据供应商或 Parquet 数据目录加载真实的行情数据。

# %%
import numpy as np
import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider

# 在 SIM 交易场所上创建一个 EUR/USD 标的
EURUSD = TestInstrumentProvider.default_fx_ccy("EUR/USD")

# 生成合成的 1 分钟 K 线（在 1.10 附近的随机游走）
rng = np.random.default_rng(42)
n = 10_000
price = 1.10 + np.cumsum(rng.normal(0, 0.0002, n))
spread = np.abs(rng.normal(0, 0.0003, n))
bars_df = pd.DataFrame(
    {
        "open": price,
        "high": price + spread,
        "low": price - spread,
        "close": price + rng.normal(0, 0.00005, n),
    },
    index=pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC"),
)
bars_df["high"] = bars_df[["open", "high", "close"]].max(axis=1)
bars_df["low"] = bars_df[["open", "low", "close"]].min(axis=1)

bar_type = BarType.from_str("EUR/USD.SIM-1-MINUTE-LAST-EXTERNAL")
bars = BarDataWrangler(bar_type, EURUSD).process(bars_df)

# %% [markdown]
# `BarDataWrangler` 将一个带 OHLCV 列的 pandas DataFrame 转换为 Nautilus 的 `Bar` 对象。
# bar 类型字符串编码了标的、聚合周期、价格来源以及数据来源等信息。

# %% [markdown]
# ## 配置并运行引擎
#
# 创建一个 `BacktestEngine`，添加一个使用保证金账户的模拟外汇交易场所，
# 装配标的、数据和策略，然后运行。引擎会按时间戳顺序处理所有 bar，
# 并采用确定性的执行语义。

# %%
engine = BacktestEngine(
    config=BacktestEngineConfig(
        logging=LoggingConfig(log_level="ERROR"),
    ),
)

# 添加一个模拟的外汇交易场所
SIM = Venue("SIM")
engine.add_venue(
    venue=SIM,
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    starting_balances=[Money(1_000_000, USD)],
    base_currency=USD,
    default_leverage=Decimal(1),
)

# 添加标的、数据和策略
engine.add_instrument(EURUSD)
engine.add_data(bars)

strategy = EMACross(
    EMACrossConfig(
        instrument_id=EURUSD.id,
        bar_type=bar_type,
        trade_size=Decimal(100000),
    ),
)
engine.add_strategy(strategy)

# 运行回测
engine.run()

# %% [markdown]
# 引擎按时间戳顺序处理全部 10,000 根 bar。每根 bar 都会更新已注册的指标，
# 随后触发 `on_bar`。模拟交易所按当前价格成交市价单。

# %% [markdown]
# ## 查看结果
#
# 引擎会基于已完成的回测生成报告：账户报告（account report）展示余额随时间的变化，
# 持仓报告（positions report）列出每一次完整的进出场交易及其已实现盈亏（realized PnL），
# 订单成交报告（order fills report）则展示每一笔执行。

# %%
engine.trader.generate_account_report(SIM)

# %%
engine.trader.generate_positions_report()

# %%
engine.trader.generate_order_fills_report()

# %% [markdown]
# ## 下一步
#
# - [回测（低阶 API）](backtest_low_level)：直接使用 `BacktestEngine`，
#   配合真实行情数据与执行算法。
# - [回测（高阶 API）](backtest_high_level)：基于配置驱动，使用 `BacktestNode`
#   与 Parquet 数据目录进行回测。
# - [教程](../tutorials/)：覆盖做市、均值回归、订单簿失衡等策略模式的完整演示。

# %%
engine.dispose()
