# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener - Data Providers
# -------------------------------------------------------------------------------------------------
"""
Data providers for the stock screener.

Currently supports A-Share market via Tushare.
"""

from __future__ import annotations

import os

import pandas as pd


class AShareScreenerDataProvider:
    """
    A-Share stock data provider for screening.

    Fetches fundamental and technical data from Tushare API.

    Usage
    -----
    >>> provider = AShareScreenerDataProvider(tushare_token="your_token")
    >>> data = provider.get_screening_data(date="20240101")
    >>> # data is a DataFrame with columns: pe, pb, roe, revenue_growth, volume_ratio, ...
    """

    def __init__(self, tushare_token: str | None = None) -> None:
        self._token = tushare_token or os.getenv("TUSHARE_TOKEN", "")
        if not self._token:
            raise ValueError(
                "Tushare token required. Set TUSHARE_TOKEN env var or pass tushare_token parameter."
            )

    def _get_pro(self):
        """Get Tushare pro API client."""
        import tushare as ts
        ts.set_token(self._token)
        return ts.pro_api()

    def get_basic_info(self, date: str) -> pd.DataFrame:
        """
        Get basic stock info for all A-shares.

        Parameters
        ----------
        date : str
            Trade date in YYYYMMDD format.

        Returns
        -------
        pd.DataFrame
            Columns: ts_code, symbol, name, area, industry, market, list_date

        """
        pro = self._get_pro()
        df = pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,area,industry,market,list_date",
        )
        return df

    def get_daily_basic(self, date: str) -> pd.DataFrame:
        """
        Get daily fundamental data.

        Parameters
        ----------
        date : str
            Trade date in YYYYMMDD format.

        Returns
        -------
        pd.DataFrame
            Columns: ts_code, pe, pb, dv_ratio, total_mv, circ_mv

        """
        pro = self._get_pro()
        df = pro.daily_basic(
            trade_date=date,
            fields="ts_code,trade_date,pe,pb,dv_ratio,total_mv,circ_mv,turnover_rate",
        )
        return df

    def get_financial_indicator(self, date: str) -> pd.DataFrame:
        """
        Get financial indicators (quarterly).

        Returns columns including roe, revenue growth, etc.
        """
        pro = self._get_pro()
        # Get recent financial data
        df = pro.fina_indicator(
            period=date[:6],
            fields="ts_code,ann_date,roe,revenue_growth,tr_yoy,update_flag",
        )
        if df.empty:
            return df
        # Keep only latest announcement per stock
        df = df.sort_values("ann_date").groupby("ts_code").last().reset_index()
        return df[["ts_code", "roe", "revenue_growth"]]

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
            Combined data with columns: pe, pb, roe, revenue_growth, total_mv, turnover_rate, name, industry
            Index is 6-digit stock symbol.

        """
        print(f"  [Screener] Fetching basic info...")
        basic = self.get_basic_info(date)

        print(f"  [Screener] Fetching daily fundamentals for {date}...")
        daily = self.get_daily_basic(date)

        if daily.empty:
            print(f"  [Screener] WARNING: No daily data for {date}. Market may be closed.")
            return pd.DataFrame()

        print(f"  [Screener] Fetching financial indicators...")
        try:
            fina = self.get_financial_indicator(date)
        except Exception:
            fina = pd.DataFrame(columns=["ts_code", "roe", "revenue_growth"])

        # Merge all data
        merged = daily.merge(basic[["ts_code", "symbol", "name", "industry", "list_date"]], on="ts_code", how="left")

        if not fina.empty:
            merged = merged.merge(fina, on="ts_code", how="left")

        # Filter: exclude ST stocks
        merged = merged[~merged["name"].str.contains("ST", na=False)]

        # Filter: exclude stocks listed less than 60 days
        if "list_date" in merged.columns:
            list_cutoff = int(date) - 20000  # rough: 60 days
            merged = merged[merged["list_date"].fillna("0").astype(str).str[:8].astype(int, errors="ignore") < list_cutoff]

        # Filter: exclude PE < 0 or PE > 200 (loss-making or extreme)
        merged = merged[(merged["pe"] > 0) & (merged["pe"] < 200)]

        # Set index to symbol
        merged = merged.set_index("symbol")

        print(f"  [Screener] {len(merged)} stocks after filtering")
        return merged


class DemoDataProvider:
    """
    Demo data provider with synthetic data for testing.

    No API token required. Generates realistic-looking A-share data.
    """

    def get_screening_data(self, date: str = "20240101") -> pd.DataFrame:
        """Generate demo screening data for ~50 well-known A-share stocks."""
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
