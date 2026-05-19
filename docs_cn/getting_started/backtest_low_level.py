# %% [markdown]
# # 回测（低阶 API）
#
# 本文件为英文版本（../../docs/getting_started/backtest_low_level.py）的中文注释版本。
#
# 使用 `BacktestEngine` 直接访问各个组件：加载行情数据、装配策略与执行算法，
# 并在对每个步骤都拥有完全控制权的前提下运行回测。本教程在一个模拟的 Binance Spot
# 交易所上，使用历史成交 Tick 数据回测一个搭配 TWAP 执行算法的 EMA 交叉策略。
#
# [在 GitHub 上查看源码](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/getting_started/backtest_low_level.py)。

# %% [markdown]
# ## 前置条件
# - Python 3.12+
# - 已安装最新版本的 [NautilusTrader](https://pypi.org/project/nautilus_trader/)（`pip install nautilus_trader`）

# %%
from decimal import Decimal

from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.examples.algorithms.twap import TWAPExecAlgorithm
from nautilus_trader.examples.strategies.ema_cross_twap import EMACrossTWAP
from nautilus_trader.examples.strategies.ema_cross_twap import EMACrossTWAPConfig
from nautilus_trader.model import BarType
from nautilus_trader.model import Money
from nautilus_trader.model import TraderId
from nautilus_trader.model import Venue
from nautilus_trader.model.currencies import ETH
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestDataProvider
from nautilus_trader.test_kit.providers import TestInstrumentProvider

# %% [markdown]
# ## 加载数据
#
# 加载内置的测试数据（Binance 上的 ETHUSDT 成交数据），初始化与数据匹配的
# 标的（instrument），并将原始 CSV 处理成 Nautilus 的 `TradeTick` 对象。

# %%
# 加载存根（stub）测试数据
provider = TestDataProvider()
trades_df = provider.read_csv_ticks("binance/ethusdt-trades.csv")

# 初始化与数据匹配的标的
ETHUSDT_BINANCE = TestInstrumentProvider.ethusdt_binance()

# 处理成 Nautilus 对象
wrangler = TradeTickDataWrangler(instrument=ETHUSDT_BINANCE)
ticks = wrangler.process(trades_df)

# %% [markdown]
# 数据处理流水线的细节请参阅 [Data](../concepts/data.md) 概念指南。

# %% [markdown]
# ## 初始化引擎
#
# 通过传入 `BacktestEngineConfig` 来配置引擎。这里我们设置了一个自定义的
# `trader_id` 以示例此模式。

# %%
# 配置回测引擎
config = BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001"))

# 构建回测引擎
engine = BacktestEngine(config=config)

# %% [markdown]
# ## 添加交易场所
#
# 搭建一个与行情数据匹配的模拟交易场所。这里我们配置了一个使用现金账户
# 的 Binance Spot 交易所。

# %%
# 添加一个交易场所（可以添加多个）
BINANCE = Venue("BINANCE")
engine.add_venue(
    venue=BINANCE,
    oms_type=OmsType.NETTING,
    account_type=AccountType.CASH,  # Spot CASH account (not for perpetuals or futures)
    base_currency=None,  # Multi-currency account
    starting_balances=[Money(1_000_000.0, USDT), Money(10.0, ETH)],
)

# %% [markdown]
# ## 添加数据
#
# 将标的与成交 Tick 数据添加到引擎中。

# %%
# 添加标的（可以添加多个）
engine.add_instrument(ETHUSDT_BINANCE)

# 添加数据
engine.add_data(ticks)

# %% [markdown]
# :::note
# 你可以添加多种数据类型（包括自定义类型），并跨多个交易场所进行回测。
# :::
#

# %% [markdown]
# ## 添加策略
#
# 配置并添加一个带 TWAP 执行参数的 EMA 交叉策略。

# %%
# 配置你的策略
strategy_config = EMACrossTWAPConfig(
    instrument_id=ETHUSDT_BINANCE.id,
    bar_type=BarType.from_str("ETHUSDT.BINANCE-250-TICK-LAST-INTERNAL"),
    trade_size=Decimal("0.10"),
    fast_ema_period=10,
    slow_ema_period=20,
    twap_horizon_secs=10.0,
    twap_interval_secs=2.5,
)

# 实例化并添加策略
strategy = EMACrossTWAP(config=strategy_config)
engine.add_strategy(strategy=strategy)

# %% [markdown]
# 该策略配置中引用了 TWAP 参数，但执行算法本身是一个独立的组件。
#
# ## 添加执行算法
#
# 向引擎添加一个 TWAP 执行算法。

# %%
# 实例化并添加执行算法
exec_algorithm = TWAPExecAlgorithm()  # Using defaults
engine.add_exec_algorithm(exec_algorithm)

# %% [markdown]
# ## 运行回测
#
# 调用 `.run()` 处理所有可用的数据。引擎按时间戳顺序回放事件，并采用
# 确定性的执行语义。

# %%
# 运行引擎（从数据起点到数据末尾）
engine.run()

# %% [markdown]
# ## 运行后分析
#
# 引擎会将数据与执行相关的对象保留在内存中，用于生成报告。它还会在日志中
# 输出一份包含默认统计指标的 tearsheet；如需自定义统计指标，请参阅
# [Portfolio statistics](../concepts/portfolio.md#portfolio-statistics) 指南。

# %%
engine.trader.generate_account_report(BINANCE)

# %%
engine.trader.generate_order_fills_report()

# %%
engine.trader.generate_positions_report()

# %% [markdown]
# ## 重复运行
#
# 要重复使用不同配置运行回测，可以重置引擎。重置后标的与数据仍然保留，
# 因此你只需要添加新的组件即可。

# %%
# 进行重复回测时，重置引擎
engine.reset()

# 标的与数据保留，只需添加新的组件并再次运行

# %% [markdown]
# 根据需要移除并添加各个组件（actor、策略、执行算法）。
#
# 实现这一点的所有可用方法说明请参阅 [Trader](../api_reference/trading.md) API 参考。
#

# %%
# 完成后，如果脚本还会继续运行，最好释放该对象
engine.dispose()
