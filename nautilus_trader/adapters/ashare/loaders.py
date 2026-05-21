#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Data Loader
# -------------------------------------------------------------------------------------------------
"""
Loads A-Share market data and converts to NautilusTrader Bar objects.

Supports Tushare Pro and AKShare as data sources, with Parquet local caching.
"""

import os
import logging

import pandas as pd

from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarSpecification
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import BarAggregation
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.instruments import Equity
from nautilus_trader.persistence.wranglers import BarDataWrangler

from nautilus_trader.adapters.ashare.config import AShareDataConfig
from nautilus_trader.adapters.ashare.instruments import create_stock_instrument

logger = logging.getLogger(__name__)


class AShareDataLoader:
    """
    A 股数据加载器，将 Tushare/AKShare 数据转换为 NautilusTrader Bar 对象。

    核心流程:
    1. 尝试从 Parquet 缓存加载
    2. 缓存未命中则从 API 拉取
    3. 转换为 NautilusTrader Bar 对象列表
    """

    def __init__(self, config: AShareDataConfig) -> None:
        self._config = config
        self._pro = None  # Tushare pro API

    def _cache_path(self, symbol: str, start: str, end: str, adj: str) -> str:
        """生成缓存文件路径。"""
        return os.path.join(
            self._config.cache_dir,
            f"daily_{symbol}_{start}_{end}_{adj}.parquet",
        )

    def _load_cache(self, symbol: str, start: str, end: str, adj: str) -> pd.DataFrame:
        """从 Parquet 缓存加载数据。"""
        if not self._config.cache_enabled:
            return pd.DataFrame()
        path = self._cache_path(symbol, start, end, adj)
        if os.path.exists(path):
            try:
                df = pd.read_parquet(path)
                logger.info(f"从缓存加载 {symbol}: {len(df)} 条")
                return df
            except Exception as e:
                logger.warning(f"缓存读取失败: {e}")
        return pd.DataFrame()

    def _save_cache(self, df: pd.DataFrame, symbol: str, start: str, end: str, adj: str) -> None:
        """保存数据到 Parquet 缓存。"""
        if not self._config.cache_enabled or df.empty:
            return
        os.makedirs(self._config.cache_dir, exist_ok=True)
        path = self._cache_path(symbol, start, end, adj)
        try:
            df.to_parquet(path, index=False, engine="pyarrow")
            logger.debug(f"已缓存到 {path}")
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")

    def _init_tushare(self):
        """初始化 Tushare Pro API。"""
        if self._pro is not None:
            return True
        try:
            import tushare as ts
            token = self._config.tushare_token
            if not token:
                return False
            ts.set_token(token)
            self._pro = ts.pro_api()
            return True
        except Exception as e:
            logger.warning(f"Tushare 初始化失败: {e}")
            return False

    def _fetch_tushare(self, symbol: str, start: str, end: str, adj: str) -> pd.DataFrame:
        """通过 Tushare 获取日线数据。"""
        if not self._init_tushare():
            return pd.DataFrame()
        try:
            ts_code = f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
            df = self._pro.daily(ts_code=ts_code, start_date=start, end_date=end)
            if df is None or df.empty:
                return pd.DataFrame()

            # 前复权处理
            if adj == "qfq":
                adj_factor = self._pro.adj_factor(ts_code=ts_code, start_date=start, end_date=end)
                if not adj_factor.empty:
                    df = df.merge(adj_factor[["trade_date", "adj_factor"]], on="trade_date", how="left")
                    factor = df["adj_factor"].iloc[0]
                    for col in ["open", "high", "low", "close"]:
                        df[col] = df[col] * df["adj_factor"] / factor

            df = df.sort_values("trade_date")
            return df
        except Exception as e:
            logger.warning(f"Tushare 数据获取失败 {symbol}: {e}")
            return pd.DataFrame()

    def _fetch_akshare(self, symbol: str, start: str, end: str, adj: str) -> pd.DataFrame:
        """通过 AKShare 获取日线数据。"""
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust=adj if adj else "",
            )
            if df is None or df.empty:
                return pd.DataFrame()

            # 统一列名
            df = df.rename(columns={
                "日期": "trade_date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
                "涨跌幅": "pct_change",
                "换手率": "turnover_rate",
            })
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
            return df
        except Exception as e:
            logger.warning(f"AKShare 数据获取失败 {symbol}: {e}")
            return pd.DataFrame()

    def _to_bar_dataframe(self, raw: pd.DataFrame) -> pd.DataFrame:
        """
        将原始数据转换为 BarDataWrangler 所需的格式。
        需要: timestamp 索引 + ['open', 'high', 'low', 'close', 'volume'] 列。
        """
        df = raw.copy()

        # 处理日期列：支持 trade_date 列 或 date 索引
        if "trade_date" in df.columns:
            df["timestamp"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
            df = df.set_index("timestamp")
        elif df.index.name == "date" or isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            df.index.name = "timestamp"
        else:
            raise ValueError(f"无法识别日期列，可用列: {list(df.columns)}, index: {df.index.name}")

        # 确保 volume 列存在
        if "volume" not in df.columns and "vol" in df.columns:
            df["volume"] = df["vol"]
        elif "volume" not in df.columns:
            df["volume"] = 0.0

        # 只保留需要的列
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                raise ValueError(f"缺少必要列 '{col}'，可用列: {list(df.columns)}")

        return df[["open", "high", "low", "close", "volume"]]

    def load_daily_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        instrument: Equity | None = None,
    ) -> list[Bar]:
        """
        加载日线数据并转换为 NautilusTrader Bar 对象列表。

        Parameters
        ----------
        symbol : str
            股票代码，如 "600519"
        start_date : str
            开始日期，如 "20230101"
        end_date : str
            结束日期，如 "20241231"
        instrument : Equity, optional
            已有的 instrument 对象，不传则自动创建

        Returns
        -------
        list[Bar]
            NautilusTrader Bar 对象列表
        """
        adj = self._config.adj_type or "none"

        # 1) 尝试缓存
        raw = self._load_cache(symbol, start_date, end_date, adj)

        # 2) 缓存未命中，从 API 拉取
        if raw.empty:
            if self._config.source == "tushare":
                raw = self._fetch_tushare(symbol, start_date, end_date, adj)
            if raw.empty:
                raw = self._fetch_akshare(symbol, start_date, end_date, adj)
            if not raw.empty:
                self._save_cache(raw, symbol, start_date, end_date, adj)

        if raw.empty:
            logger.error(f"无法获取 {symbol} 数据")
            return []

        # 3) 创建 instrument
        if instrument is None:
            instrument = create_stock_instrument(symbol)

        # 4) 构建 BarType（日线 LAST 价格）
        bar_type = BarType(
            instrument.id,
            BarSpecification(1, BarAggregation.DAY, PriceType.LAST),
        )

        # 5) 使用 BarDataWrangler 转换
        bar_df = self._to_bar_dataframe(raw)
        wrangler = BarDataWrangler(bar_type, instrument)
        bars: list[Bar] = wrangler.process(bar_df)

        logger.info(f"加载 {symbol}: {len(bars)} 根日线 Bar")
        return bars