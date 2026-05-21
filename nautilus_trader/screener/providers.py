#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener - Data Providers
# -------------------------------------------------------------------------------------------------
"""
Data providers for the stock screener.

Provides a unified interface for backtest and live modes:
- CachedScreenerProvider: Backtest mode, reads from pre-loaded Parquet cache
- LiveScreenerProvider: Live mode, calls Tushare/AKShare API in real-time
- DemoDataProvider: Testing with synthetic data
"""

from __future__ import annotations

import os
from abc import ABC
from abc import abstractmethod

import pandas as pd


class ScreenerDataProvider(ABC):
    """
    Abstract base class for screener data providers.

    Implementations must provide screening data (PE, PB, ROE, etc.)
    for a given date. The same interface is used in backtest and live mode.
    """

    @abstractmethod
    def get_screening_data(self, date: str) -> pd.DataFrame:
        """
        Get comprehensive screening data for all A-shares on a given date.

        Parameters
        ----------
        date : str
            Trade date in YYYYMMDD format.

        Returns
        -------
        pd.DataFrame
            Columns: pe, pb, roe, revenue_growth, total_mv, turnover_rate, name, industry
            Index is 6-digit stock symbol.
        """

    @abstractmethod
    def get_available_dates(self) -> list[str]:
        """Get list of available trade dates (YYYYMMDD format)."""


class CachedScreenerProvider(ScreenerDataProvider):
    """
    Backtest-mode provider: reads from pre-loaded Parquet cache files.

    Usage
    -----
    >>> provider = CachedScreenerProvider(cache_dir="~/.nautilus/ashare_cache")
    >>> data = provider.get_screening_data("20240101")
    """

    def __init__(self, cache_dir: str | None = None) -> None:
        self._cache_dir = cache_dir or os.path.expanduser("~/.nautilus/ashare_cache")
        self._date_cache: list[str] | None = None

    def get_screening_data(self, date: str) -> pd.DataFrame:
        path = os.path.join(self._cache_dir, f"screening_{date}.parquet")
        if os.path.exists(path):
            return pd.read_parquet(path)

        # Fallback: try live provider
        try:
            provider = LiveScreenerProvider()
            data = provider.get_screening_data(date)
            if not data.empty:
                os.makedirs(self._cache_dir, exist_ok=True)
                data.to_parquet(path)
            return data
        except Exception:
            return pd.DataFrame()

    def get_available_dates(self) -> list[str]:
        if self._date_cache is not None:
            return self._date_cache
        import glob
        files = glob.glob(os.path.join(self._cache_dir, "screening_*.parquet"))
        dates = sorted(f.split("_")[-1].replace(".parquet", "") for f in files)
        self._date_cache = dates
        return dates

    def preCache(self, dates: list[str], provider: ScreenerDataProvider) -> None:
        """Pre-cache screening data for backtest dates."""
        os.makedirs(self._cache_dir, exist_ok=True)
        for date in dates:
            path = os.path.join(self._cache_dir, f"screening_{date}.parquet")
            if os.path.exists(path):
                continue
            print(f"  Pre-caching screening data for {date}...")
            data = provider.get_screening_data(date)
            if not data.empty:
                data.to_parquet(path)
        self._date_cache = None


class LiveScreenerProvider(ScreenerDataProvider):
    """
    Live-mode provider: calls Tushare API in real-time.

    Usage
    -----
    >>> provider = LiveScreenerProvider(tushare_token="your_token")
    >>> data = provider.get_screening_data("20240101")
    """

    def __init__(self, tushare_token: str | None = None) -> None:
        self._token = tushare_token or os.getenv("TUSHARE_TOKEN", "")
        if not self._token:
            env_path = os.path.join(os.getcwd(), ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("TUSHARE_TOKEN="):
                            self._token = line.split("=", 1)[1].strip()
                            break

    def _get_pro(self):
        """Get Tushare pro API client."""
        import tushare as ts
        if not self._token:
            raise ValueError("Tushare token required. Set TUSHARE_TOKEN env var or pass tushare_token.")
        ts.set_token(self._token)
        return ts.pro_api()

    def get_screening_data(self, date: str) -> pd.DataFrame:
        """Get comprehensive screening data for all A-shares on a given date."""
        print(f"  [Screener] Fetching screening data for {date}...")
        try:
            pro = self._get_pro()
        except (ImportError, ValueError) as e:
            print(f"  [Screener] WARNING: {e}")
            return pd.DataFrame()

        basic = pro.stock_basic(
            exchange="", list_status="L",
            fields="ts_code,symbol,name,area,industry,market,list_date",
        )
        daily = pro.daily_basic(
            trade_date=date,
            fields="ts_code,trade_date,pe,pb,dv_ratio,total_mv,circ_mv,turnover_rate",
        )
        if daily is None or daily.empty:
            print(f"  [Screener] WARNING: No daily data for {date}. Market may be closed.")
            return pd.DataFrame()

        try:
            fina = pro.fina_indicator(
                period=date[:6],
                fields="ts_code,ann_date,roe,revenue_growth,tr_yoy,update_flag",
            )
            if fina is not None and not fina.empty:
                fina = fina.sort_values("ann_date").groupby("ts_code").last().reset_index()
                fina = fina[["ts_code", "roe", "revenue_growth"]]
            else:
                fina = pd.DataFrame(columns=["ts_code", "roe", "revenue_growth"])
        except Exception:
            fina = pd.DataFrame(columns=["ts_code", "roe", "revenue_growth"])

        merged = daily.merge(basic[["ts_code", "symbol", "name", "industry", "list_date"]], on="ts_code", how="left")
        if not fina.empty:
            merged = merged.merge(fina, on="ts_code", how="left")

        merged = merged[~merged["name"].str.contains("ST", na=False)]
        if "list_date" in merged.columns:
            list_cutoff = int(date) - 20000
            merged = merged[
                merged["list_date"].fillna("0").astype(str).str[:8].apply(
                    lambda x: int(x) if x.isdigit() else 0
                ) < list_cutoff
            ]
        merged = merged[(merged["pe"] > 0) & (merged["pe"] < 200)]
        merged = merged.set_index("symbol")

        print(f"  [Screener] {len(merged)} stocks after filtering")
        return merged

    def get_available_dates(self) -> list[str]:
        """Get recent trading dates from Tushare calendar."""
        try:
            pro = self._get_pro()
            df = pro.trade_cal(exchange="SSE", is_open="1", limit=30)
            if df is not None and not df.empty:
                return sorted(df["cal_date"].tolist(), reverse=True)
        except Exception:
            pass
        return []


class DemoDataProvider(ScreenerDataProvider):
    """Demo data provider with synthetic data for testing."""

    def get_screening_data(self, date: str = "20240101") -> pd.DataFrame:
        stocks = {
            "600519": {"name": "贵州茅台", "industry": "白酒", "pe": 35.2, "pb": 12.1, "roe": 33.5, "revenue_growth": 18.2, "total_mv": 21000, "turnover_rate": 0.3},
            "000858": {"name": "五粮液", "industry": "白酒", "pe": 25.8, "pb": 7.8, "roe": 28.3, "revenue_growth": 15.6, "total_mv": 6800, "turnover_rate": 0.5},
            "600036": {"name": "招商银行", "industry": "银行", "pe": 6.2, "pb": 1.1, "roe": 17.8, "revenue_growth": 8.5, "total_mv": 9500, "turnover_rate": 0.4},
            "601318": {"name": "中国平安", "industry": "保险", "pe": 9.5, "pb": 1.5, "roe": 16.2, "revenue_growth": 5.3, "total_mv": 8200, "turnover_rate": 0.6},
            "000333": {"name": "美的集团", "industry": "家电", "pe": 14.3, "pb": 4.2, "roe": 25.6, "revenue_growth": 12.8, "total_mv": 4500, "turnover_rate": 0.8},
            "600900": {"name": "长江电力", "industry": "电力", "pe": 22.1, "pb": 4.5, "roe": 16.8, "revenue_growth": 10.2, "total_mv": 5200, "turnover_rate": 0.3},
            "601899": {"name": "紫金矿业", "industry": "有色金属", "pe": 18.5, "pb": 3.8, "roe": 22.1, "revenue_growth": 25.3, "total_mv": 3800, "turnover_rate": 1.2},
            "000001": {"name": "平安银行", "industry": "银行", "pe": 5.1, "pb": 0.6, "roe": 11.5, "revenue_growth": 3.2, "total_mv": 2200, "turnover_rate": 0.9},
            "600276": {"name": "恒瑞医药", "industry": "医药", "pe": 52.3, "pb": 8.9, "roe": 14.2, "revenue_growth": 8.5, "total_mv": 3100, "turnover_rate": 0.7},
            "002415": {"name": "海康威视", "industry": "安防", "pe": 28.5, "pb": 5.6, "roe": 19.8, "revenue_growth": 7.5, "total_mv": 3200, "turnover_rate": 0.6},
            "600809": {"name": "山西汾酒", "industry": "白酒", "pe": 42.1, "pb": 15.2, "roe": 38.5, "revenue_growth": 22.1, "total_mv": 3500, "turnover_rate": 0.5},
            "002352": {"name": "顺丰控股", "industry": "物流", "pe": 32.5, "pb": 3.2, "roe": 10.5, "revenue_growth": 6.8, "total_mv": 2100, "turnover_rate": 0.8},
            "600031": {"name": "三一重工", "industry": "机械", "pe": 15.8, "pb": 2.8, "roe": 18.3, "revenue_growth": -5.2, "total_mv": 1500, "turnover_rate": 1.5},
            "601012": {"name": "隆基绿能", "industry": "光伏", "pe": 18.2, "pb": 2.5, "roe": 15.6, "revenue_growth": -8.3, "total_mv": 1800, "turnover_rate": 2.1},
            "000568": {"name": "泸州老窖", "industry": "白酒", "pe": 30.5, "pb": 10.5, "roe": 35.2, "revenue_growth": 20.5, "total_mv": 3200, "turnover_rate": 0.4},
            "601888": {"name": "中国中免", "industry": "旅游零售", "pe": 38.2, "pb": 6.8, "roe": 18.5, "revenue_growth": -2.1, "total_mv": 2800, "turnover_rate": 0.9},
            "002475": {"name": "立讯精密", "industry": "电子", "pe": 25.8, "pb": 5.2, "roe": 20.1, "revenue_growth": 15.3, "total_mv": 3200, "turnover_rate": 1.1},
            "600030": {"name": "中信证券", "industry": "券商", "pe": 16.5, "pb": 1.5, "roe": 9.8, "revenue_growth": 12.5, "total_mv": 2800, "turnover_rate": 1.8},
            "002714": {"name": "牧原股份", "industry": "畜牧", "pe": 12.3, "pb": 2.8, "roe": 15.2, "revenue_growth": -15.6, "total_mv": 2500, "turnover_rate": 1.3},
            "600309": {"name": "万华化学", "industry": "化工", "pe": 14.2, "pb": 3.5, "roe": 22.5, "revenue_growth": 8.9, "total_mv": 2600, "turnover_rate": 0.7},
            "601166": {"name": "兴业银行", "industry": "银行", "pe": 5.0, "pb": 0.5, "roe": 10.8, "revenue_growth": 2.5, "total_mv": 3800, "turnover_rate": 0.5},
            "000725": {"name": "京东方A", "industry": "面板", "pe": 45.2, "pb": 1.2, "roe": 5.2, "revenue_growth": 12.3, "total_mv": 1800, "turnover_rate": 2.5},
            "002594": {"name": "比亚迪", "industry": "新能源车", "pe": 28.5, "pb": 5.8, "roe": 16.5, "revenue_growth": 42.5, "total_mv": 6500, "turnover_rate": 1.5},
            "300750": {"name": "宁德时代", "industry": "锂电池", "pe": 22.8, "pb": 5.5, "roe": 18.2, "revenue_growth": 35.2, "total_mv": 9500, "turnover_rate": 1.2},
            "688981": {"name": "中芯国际", "industry": "芯片", "pe": 65.2, "pb": 2.8, "roe": 5.8, "revenue_growth": 15.2, "total_mv": 4500, "turnover_rate": 1.8},
            "601633": {"name": "长城汽车", "industry": "汽车", "pe": 22.5, "pb": 3.2, "roe": 12.5, "revenue_growth": 18.5, "total_mv": 2200, "turnover_rate": 1.6},
            "002049": {"name": "紫光国微", "industry": "芯片", "pe": 55.2, "pb": 8.5, "roe": 15.8, "revenue_growth": 22.5, "total_mv": 1200, "turnover_rate": 2.2},
            "600585": {"name": "海螺水泥", "industry": "建材", "pe": 8.5, "pb": 1.2, "roe": 12.5, "revenue_growth": -8.5, "total_mv": 1500, "turnover_rate": 0.6},
            "000651": {"name": "格力电器", "industry": "家电", "pe": 8.2, "pb": 2.5, "roe": 25.8, "revenue_growth": 5.2, "total_mv": 2100, "turnover_rate": 0.8},
            "601857": {"name": "中国石油", "industry": "石油", "pe": 10.2, "pb": 1.0, "roe": 10.5, "revenue_growth": 8.2, "total_mv": 15000, "turnover_rate": 0.2},
        }
        df = pd.DataFrame.from_dict(stocks, orient="index")
        df.index.name = "symbol"
        return df

    def get_available_dates(self) -> list[str]:
        return ["20240101", "20240201", "20240301", "20240401", "20240501"]