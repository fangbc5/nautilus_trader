# %% [markdown]
# # 回测（高阶 API）
#
# 本文件为英文版本（../../docs/getting_started/backtest_high_level.py）的中文注释版本。
#
# 使用 `BacktestNode` 进行基于配置驱动、并搭配 Parquet 数据目录的回测。
# 这是面向生产环境工作流的推荐路径，因为你在这里构建的策略、
# actor 和执行算法可以直接迁移到使用 `TradingNode` 的实盘交易。
#
# 本教程加载外汇报价 Tick 数据，将其写入数据目录（catalog），并在一个
# 模拟的 FX ECN 交易场所上回测 EMA 交叉策略。
#
# [在 GitHub 上查看源码](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/getting_started/backtest_high_level.py)。

# %% [markdown]
# ## 前置条件
# - Python 3.12+
# - 已安装最新版本的 [NautilusTrader](https://pypi.org/project/nautilus_trader/)（`pip install nautilus_trader`）

# %%
import os
import shutil
from decimal import Decimal
from pathlib import Path

import pandas as pd

from nautilus_trader.backtest.node import BacktestDataConfig
from nautilus_trader.backtest.node import BacktestEngineConfig
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.backtest.node import BacktestRunConfig
from nautilus_trader.backtest.node import BacktestVenueConfig
from nautilus_trader.config import ImportableStrategyConfig
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model import QuoteTick
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.persistence.wranglers import QuoteTickDataWrangler
from nautilus_trader.test_kit.providers import CSVTickDataLoader
from nautilus_trader.test_kit.providers import TestInstrumentProvider

# %% [markdown]
# ## 下载示例数据
#
# 本示例使用来自 [histdata.com](https://www.histdata.com/download-free-forex-historical-data/?/ascii/tick-data-quotes/) 的外汇 Tick 数据。
# 选择一个外汇货币对以及一个或多个月份进行下载。
#
# 下载得到的文件示例：
#
# - `DAT_ASCII_EURUSD_T_202410.csv`（EUR/USD 2024 年 10 月）
# - `DAT_ASCII_EURUSD_T_202411.csv`（EUR/USD 2024 年 11 月）
#
# 将 CSV 文件解压到 `~/Downloads/Data/HISTDATA/`（或设置环境变量
# `NAUTILUS_DATA_DIR` 指向包含 `HISTDATA` 子目录的父目录）。

# %%
DATA_DIR = Path(os.environ.get("NAUTILUS_DATA_DIR", "~/Downloads/Data")).expanduser() / "HISTDATA"

# %%
path = DATA_DIR
raw_files = [
    f for f in path.iterdir() if f.is_file() and (f.suffix == ".csv" or f.name.endswith(".csv.gz"))
]
assert raw_files, f"Unable to find any CSV files in directory {path}"
raw_files

# %% [markdown]
# ## 将数据加载到数据目录中
#
# Histdata 的 CSV 文件包含 `timestamp, bid_price, ask_price` 等字段。先将原始数据
# 加载到 DataFrame 中，然后使用 `QuoteTickDataWrangler` 处理成 Nautilus
# 的 `QuoteTick` 对象。

# %%
# 将第一个 CSV 文件加载到 pandas DataFrame
df = CSVTickDataLoader.load(
    file_path=raw_files[0],
    index_col=0,
    header=None,
    names=["timestamp", "bid_price", "ask_price", "volume"],
    usecols=["timestamp", "bid_price", "ask_price"],
    parse_dates=["timestamp"],
    date_format="%Y%m%d %H%M%S%f",
)

df = df.sort_index()
df.head(2)

# %%
# 使用 wrangler 处理报价数据
EURUSD = TestInstrumentProvider.default_fx_ccy("EUR/USD")
wrangler = QuoteTickDataWrangler(EURUSD)

ticks = wrangler.process(df)

# 预览：查看前 2 个 Tick
ticks[0:2]

# %% [markdown]
# 更多细节请参阅 [Loading data](../concepts/data) 指南。
#
# 使用一个存储目录实例化 `ParquetDataCatalog`（这里我们使用当前目录），
# 并将标的（instrument）和 Tick 数据写入数据目录。
#

# %%
CATALOG_PATH = Path.cwd() / "catalog"

# 如果目录已存在则清空，然后重新创建
if CATALOG_PATH.exists():
    shutil.rmtree(CATALOG_PATH)
CATALOG_PATH.mkdir(parents=True)

# 创建一个 catalog 实例
catalog = ParquetDataCatalog(CATALOG_PATH)

# 将标的写入 catalog
catalog.write_data([EURUSD])

# 将 Tick 数据写入 catalog
catalog.write_data(ticks)

# %% [markdown]
# ## 查询数据目录
#
# 数据目录提供了 `.instruments()`、`.quote_ticks()` 等方法，用于查询已存储的数据
# 并确定可用的时间范围。

# %%
# 获取 catalog 中所有标的的列表
catalog.instruments()

# %%
# 查看 catalog 中的第 1 个标的
instrument = catalog.instruments()[0]
instrument

# %%
# 从 catalog 中查询报价 Tick，以确定数据范围
all_ticks = catalog.quote_ticks(instrument_ids=[EURUSD.id.value])
print(f"Total ticks in catalog: {len(all_ticks)}")

if all_ticks:
    # 从数据中获取时间戳
    first_tick_time = pd.Timestamp(all_ticks[0].ts_init, unit="ns", tz="UTC")
    last_tick_time = pd.Timestamp(all_ticks[-1].ts_init, unit="ns", tz="UTC")
    print(f"Data range: {first_tick_time} to {last_tick_time}")

    # 将回测时间范围设置为数据的前 2 周（以 ISO 字符串形式传入 BacktestDataConfig）
    start_time = first_tick_time.isoformat()
    end_time = (first_tick_time + pd.Timedelta(days=14)).isoformat()
    print(f"Backtest range: {start_time} to {end_time}")

    # 预览所选数据
    start_ns = all_ticks[0].ts_init
    end_ns = dt_to_unix_nanos(first_tick_time + pd.Timedelta(days=14))
    selected_quote_ticks = catalog.quote_ticks(
        instrument_ids=[EURUSD.id.value],
        start=start_ns,
        end=end_ns,
    )
    print(f"Selected ticks for backtest: {len(selected_quote_ticks)}")
    selected_quote_ticks[:2]
else:
    raise ValueError("No ticks found in catalog")

# %% [markdown]
# ## 添加交易场所

# %%
venue_configs = [
    BacktestVenueConfig(
        name="SIM",
        oms_type="HEDGING",
        account_type="MARGIN",
        base_currency="USD",
        starting_balances=["1_000_000 USD"],
    ),
]

# %% [markdown]
# ## 添加数据

# %%
str(CATALOG_PATH)

# %%
data_configs = [
    BacktestDataConfig(
        catalog_path=str(CATALOG_PATH),
        data_cls=QuoteTick,
        instrument_id=instrument.id,
        start_time=start_time,
        end_time=end_time,
    ),
]

# %% [markdown]
# ## 添加策略

# %%
strategies = [
    ImportableStrategyConfig(
        strategy_path="nautilus_trader.examples.strategies.ema_cross:EMACross",
        config_path="nautilus_trader.examples.strategies.ema_cross:EMACrossConfig",
        config={
            "instrument_id": instrument.id,
            "bar_type": "EUR/USD.SIM-15-MINUTE-BID-INTERNAL",
            "fast_ema_period": 10,
            "slow_ema_period": 20,
            "trade_size": Decimal(1_000_000),
        },
    ),
]

# %% [markdown]
# ## 配置回测
#
# `BacktestRunConfig` 将交易场所、数据和策略的配置集中到一个对象中。
# 它是 Partialable 的，因此可以分阶段构建。这在进行参数扫描或网格搜索时
# 可以显著减少样板代码。

# %%
config = BacktestRunConfig(
    engine=BacktestEngineConfig(strategies=strategies),
    data=data_configs,
    venues=venue_configs,
)

# %% [markdown]
# ## 运行回测
#
# `BacktestNode` 按时间戳顺序处理所有数据，并采用确定性的执行语义。
# 这里使用的架构模式（策略、actor、执行算法）可以直接迁移到使用
# `TradingNode` 的实盘交易。

# %%
node = BacktestNode(configs=[config])

results = node.run()
results
