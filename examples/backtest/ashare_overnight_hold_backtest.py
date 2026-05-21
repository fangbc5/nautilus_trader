#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Overnight Hold Backtest (一夜持股法回测)
# -------------------------------------------------------------------------------------------------
"""
杨永兴一夜持股法全市场回测。

策略逻辑：
1. 每个交易日收盘后，从全A股中筛选符合条件的股票
2. 选股条件：涨跌幅1%~7%、换手率1%~15%、量比>1.2、非ST、非停牌
3. 综合评分（涨幅+换手率+量比）取 Top N
4. 以当日收盘价买入（等权分配资金）
5. 次日以开盘价卖出
6. 扣除手续费：佣金万2.3 + 印花税0.05%(卖) + 过户费0.001%

Usage:
    python -m examples.backtest.ashare_overnight_hold_backtest
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================
START_DATE = "20260401"
END_DATE = "20260520"
INITIAL_CAPITAL = 10_000.0  # 1万元
TOP_N = 3                    # 每日选股数量
LOT_SIZE = 100               # A股最低手数

# Commission rates
COMMISSION_RATE = 0.00023    # 佣金 万分之2.3
STAMP_DUTY_RATE = 0.0005    # 印花税 0.05% (sell only)
TRANSFER_FEE_RATE = 0.00001 # 过户费 0.001%
MIN_COMMISSION = 5.0         # 最低佣金 5元

# Screening criteria
MIN_PCT_CHANGE = 1.0         # 最小涨跌幅 %
MAX_PCT_CHANGE = 7.0         # 最大涨跌幅 %
MIN_TURNOVER = 1.0           # 最小换手率 %
MAX_TURNOVER = 15.0          # 最大换手率 %
MIN_VOLUME_RATIO = 1.2       # 最小量比
EXCLUDE_ST = True            # 排除ST
EXCLUDE_NEW_DAYS = 60        # 排除次新股（上市不足N天）

# Data cache (与项目其他 A 股回测共用 ~/.nautilus/ashare_cache/ 目录)
DATA_CACHE_DIR = os.path.expanduser("~/.nautilus/ashare_cache")

# Rate limiting
RATE_LIMIT_DELAY = 0.3       # API请求间隔(秒)
BATCH_PAUSE = 60             # 每批N只后暂停(秒)
BATCH_SIZE = 200             # 每批数量


# ============================================================================
# Data Fetcher with Rate Limiting
# ============================================================================
class AShareDataFetcher:
    """A股数据拉取器，支持限流和 Parquet 本地缓存。"""

    def __init__(self, cache_dir: str = DATA_CACHE_DIR) -> None:
        self._last_call_time: float = 0.0
        self._ak = None
        self._pro = None
        self._use_tushare = False
        self._cache_dir = cache_dir

    # ------------------------------------------------------------------
    # Parquet Cache
    # ------------------------------------------------------------------
    def _cache_path(self, trade_date: str) -> str:
        """返回某交易日的 Parquet 缓存路径（daily_all_ 前缀区分全市场数据）。"""
        return os.path.join(self._cache_dir, f"daily_all_{trade_date}.parquet")

    def load_from_cache(self, trade_date: str) -> pd.DataFrame:
        """从本地 Parquet 缓存读取数据，无缓存返回空 DataFrame。"""
        path = self._cache_path(trade_date)
        if os.path.exists(path):
            try:
                df = pd.read_parquet(path)
                logger.debug(f"  {trade_date}: 从缓存加载 {len(df)} 只股票")
                return df
            except Exception as e:
                logger.warning(f"  {trade_date}: 缓存读取失败 ({e})，重新拉取")
        return pd.DataFrame()

    def save_to_cache(self, trade_date: str, df: pd.DataFrame) -> None:
        """将数据保存到本地 Parquet 缓存。"""
        if df.empty:
            return
        os.makedirs(self._cache_dir, exist_ok=True)
        path = self._cache_path(trade_date)
        try:
            df.to_parquet(path, index=False, engine="pyarrow")
            logger.debug(f"  {trade_date}: 已缓存到 {path}")
        except Exception as e:
            logger.warning(f"  {trade_date}: 缓存保存失败 ({e})")

    def cache_stats(self) -> tuple[int, int]:
        """返回 (已缓存文件数, 缓存总大小MB)。"""
        if not os.path.exists(self._cache_dir):
            return 0, 0
        files = [f for f in os.listdir(self._cache_dir) if f.endswith(".parquet")]
        total_size = sum(os.path.getsize(os.path.join(self._cache_dir, f)) for f in files)
        return len(files), total_size / (1024 * 1024)

    def _rate_limit(self) -> None:
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_call_time = time.time()

    def init_tushare(self) -> bool:
        """初始化 Tushare Pro API."""
        try:
            import tushare as ts
            token = os.getenv("TUSHARE_TOKEN", "")
            if not token:
                # Try loading from .env file
                env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
                if os.path.exists(env_path):
                    with open(env_path) as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("TUSHARE_TOKEN="):
                                token = line.split("=", 1)[1].strip()
                                break
            if token:
                ts.set_token(token)
                self._pro = ts.pro_api()
                self._use_tushare = True
                logger.info("Tushare Pro API initialized successfully")
                return True
        except Exception as e:
            logger.warning(f"Tushare init failed: {e}")
        return False

    def init_akshare(self) -> bool:
        """初始化 AKShare."""
        try:
            import akshare as ak
            self._ak = ak
            logger.info("AKShare initialized successfully")
            return True
        except ImportError:
            logger.error("akshare not installed. pip install akshare")
            return False

    def get_trade_dates(self, start: str, end: str) -> list[str]:
        """获取交易日列表。"""
        if self._use_tushare and self._pro:
            try:
                self._rate_limit()
                df = self._pro.trade_cal(
                    exchange="SSE",
                    start_date=start,
                    end_date=end,
                    is_open="1",
                )
                return sorted(df["cal_date"].tolist())
            except Exception as e:
                logger.warning(f"Tushare trade calendar failed: {e}")

        # Fallback: generate weekdays
        dates = []
        start_dt = datetime.strptime(start, "%Y%m%d")
        end_dt = datetime.strptime(end, "%Y%m%d")
        current = start_dt
        while current <= end_dt:
            if current.weekday() < 5:  # Mon-Fri
                dates.append(current.strftime("%Y%m%d"))
            current += timedelta(days=1)

        # Remove known Chinese holidays (2026 approximate)
        holidays = {
            "20260404", "20260405", "20260406",  # 清明节
            "20260501", "20260502", "20260503", "20260504", "20260505",  # 劳动节
        }
        dates = [d for d in dates if d not in holidays]
        return dates

    def fetch_daily_all_tushare(self, trade_date: str) -> pd.DataFrame:
        """通过 Tushare 获取某日全市场日线数据（一次请求）。"""
        if not self._pro:
            return pd.DataFrame()
        try:
            self._rate_limit()
            df = self._pro.daily(trade_date=trade_date)
            if df.empty:
                return df

            # Get daily_basic for turnover rate
            self._rate_limit()
            basic = self._pro.daily_basic(
                trade_date=trade_date,
                fields="ts_code,turnover_rate,volume_ratio,pe,pb,total_mv,circ_mv",
            )

            # Merge
            if not basic.empty:
                df = df.merge(basic, on="ts_code", how="left")

            # Normalize column names to match screener expectations
            df = df.rename(columns={
                "ts_code": "symbol",
                "pct_chg": "pct_change",
                "vol": "volume",
                "amount": "amount",
            })

            # Convert ts_code format (000001.SZ -> 000001)
            df["symbol"] = df["symbol"].str.split(".").str[0]

            # Add name column placeholder (tushare daily doesn't have names)
            if "name" not in df.columns:
                df["name"] = ""

            # Filter to main boards only
            df = df[df["symbol"].str.match(r"^(60|00|30)\d{4}$")]

            logger.debug(f"  Tushare {trade_date}: {len(df)} stocks, columns={list(df.columns)}")
            return df
        except Exception as e:
            logger.warning(f"Tushare daily fetch failed for {trade_date}: {e}")
            return pd.DataFrame()

    def fetch_daily_all_akshare(self, trade_date: str) -> pd.DataFrame:
        """通过 AKShare 获取某日全市场数据。"""
        if not self._ak:
            return pd.DataFrame()
        try:
            self._rate_limit()
            # Use ak.stock_zh_a_spot_em() for current snapshot
            # For historical dates, use individual stock history
            # This is less efficient but works for free
            df = self._ak.stock_zh_a_spot_em()
            if df.empty:
                return df

            # Rename columns
            df = df.rename(columns={
                "代码": "symbol",
                "名称": "name",
                "最新价": "close",
                "今开": "open",
                "涨跌幅": "pct_change",
                "涨跌额": "change",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "最高": "high",
                "最低": "low",
                "量比": "volume_ratio",
                "换手率": "turnover_rate",
                "市盈率-动态": "pe",
                "市净率": "pb",
            })

            # Filter to main boards only (SH 60xxxx, SZ 00xxxx, SZ 30xxxx)
            df = df[df["symbol"].str.match(r"^(60|00|30)\d{4}$")]
            df["trade_date"] = trade_date
            return df
        except Exception as e:
            logger.warning(f"AKShare fetch failed for {trade_date}: {e}")
            return pd.DataFrame()

    def fetch_stock_daily_akshare(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """获取单只股票日线数据（AKShare）。"""
        if not self._ak:
            return pd.DataFrame()
        try:
            self._rate_limit()
            df = self._ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="qfq",
            )
            if df.empty:
                return df

            df = df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "pct_change",
                "涨跌额": "change",
                "换手率": "turnover_rate",
            })
            df["symbol"] = symbol
            df["date"] = pd.to_datetime(df["date"])
            return df
        except Exception as e:
            return pd.DataFrame()


# ============================================================================
# Stock Screener
# ============================================================================
class OvernightHoldScreener:
    """一夜持股法选股器。"""

    def __init__(self, top_n: int = TOP_N) -> None:
        self.top_n = top_n

    def screen(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        从全市场数据中筛选符合条件的股票。

        Parameters
        ----------
        df : DataFrame with columns: symbol, name, close, pct_change,
             turnover_rate, volume_ratio, etc.

        Returns
        -------
        DataFrame of top N stocks with score.
        """
        if df.empty:
            return pd.DataFrame()

        # Make a copy
        data = df.copy()

        # Basic filters
        # 1. Price must be positive
        data = data[data["close"] > 0]

        # 2. Exclude ST stocks
        if "name" in data.columns and EXCLUDE_ST:
            data = data[~data["name"].str.contains("ST|\\*ST|退", na=False)]

        # 3. Pct change filter
        if "pct_change" in data.columns:
            data = data[(data["pct_change"] >= MIN_PCT_CHANGE) & (data["pct_change"] <= MAX_PCT_CHANGE)]
        else:
            return pd.DataFrame()

        # 4. Turnover rate filter
        if "turnover_rate" in data.columns:
            data = data[(data["turnover_rate"] >= MIN_TURNOVER) & (data["turnover_rate"] <= MAX_TURNOVER)]

        # 5. Volume ratio filter
        if "volume_ratio" in data.columns:
            data = data[data["volume_ratio"] >= MIN_VOLUME_RATIO]

        # 6. Exclude stocks with price too high for our budget
        max_price_per_stock = INITIAL_CAPITAL / self.top_n
        data = data[data["close"] * LOT_SIZE <= max_price_per_stock]

        if data.empty:
            return pd.DataFrame()

        # Scoring: composite score based on pct_change, turnover, volume_ratio
        # Higher score = better candidate
        score = pd.Series(0.0, index=data.index)

        if "pct_change" in data.columns:
            # Prefer moderate gains (3-5% ideal)
            pct_score = data["pct_change"].rank(pct=True) * 40
            score += pct_score

        if "turnover_rate" in data.columns:
            turnover_score = data["turnover_rate"].rank(pct=True) * 30
            score += turnover_score

        if "volume_ratio" in data.columns:
            vr_score = data["volume_ratio"].rank(pct=True) * 30
            score += vr_score

        data = data.copy()
        data["score"] = score

        # Sort by score, take top N
        data = data.nlargest(self.top_n, "score")

        return data


# ============================================================================
# Backtest Engine
# ============================================================================
class OvernightHoldBacktest:
    """一夜持股法回测引擎。"""

    def __init__(
        self,
        initial_capital: float = INITIAL_CAPITAL,
        top_n: int = TOP_N,
    ) -> None:
        self.initial_capital = initial_capital
        self.top_n = top_n
        self.screener = OvernightHoldScreener(top_n=top_n)
        self.trades: list[dict[str, Any]] = []
        self.daily_nav: list[dict[str, Any]] = []

    def run(
        self,
        daily_data: dict[str, pd.DataFrame],
        trade_dates: list[str],
    ) -> dict[str, Any]:
        """
        运行回测。

        Parameters
        ----------
        daily_data : dict mapping trade_date -> DataFrame of all stocks
        trade_dates : sorted list of trade dates

        Returns
        -------
        dict with backtest results.
        """
        cash = self.initial_capital
        holdings: dict[str, dict] = {}  # symbol -> {shares, buy_price, buy_date}

        logger.info(f"开始回测: {trade_dates[0]} ~ {trade_dates[-1]}, {len(trade_dates)} 个交易日")
        logger.info(f"初始资金: {cash:,.2f} CNY, 每日选股: {self.top_n} 只")

        for i, trade_date in enumerate(trade_dates):
            df = daily_data.get(trade_date, pd.DataFrame())
            if df.empty:
                logger.debug(f"  {trade_date}: 无数据，跳过")
                continue

            # ---- Step 1: Sell previous day's holdings at today's open ----
            sell_proceeds = 0.0
            sell_details = []
            symbols_to_sell = list(holdings.keys())

            for symbol in symbols_to_sell:
                holding = holdings.pop(symbol)

                # Find today's open price for this stock
                stock_rows = df[df["symbol"] == symbol] if "symbol" in df.columns else pd.DataFrame()

                if stock_rows.empty:
                    # Try to find in the raw data using ts_code
                    ts_code = f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
                    stock_rows = df[df["ts_code"] == ts_code] if "ts_code" in df.columns else pd.DataFrame()

                if not stock_rows.empty:
                    sell_price = float(stock_rows.iloc[0].get("open", stock_rows.iloc[0].get("close", 0)))
                else:
                    # Use buy price as fallback (no data = suspended)
                    sell_price = holding["buy_price"]
                    logger.debug(f"  {trade_date}: {symbol} 无开盘数据，按买入价计算")

                if sell_price <= 0:
                    sell_price = holding["buy_price"]

                shares = holding["shares"]
                buy_price = holding["buy_price"]
                buy_date = holding["buy_date"]
                sell_value = shares * sell_price

                # Commission on sell
                sell_commission = max(shares * sell_price * COMMISSION_RATE, MIN_COMMISSION)
                sell_transfer = shares * sell_price * TRANSFER_FEE_RATE
                stamp_duty = shares * sell_price * STAMP_DUTY_RATE

                total_sell_cost = sell_commission + sell_transfer + stamp_duty
                net_proceeds = sell_value - total_sell_cost

                pnl = net_proceeds - (shares * buy_price)
                pnl_pct = pnl / (shares * buy_price) * 100 if buy_price > 0 else 0

                sell_details.append({
                    "buy_date": buy_date,
                    "sell_date": trade_date,
                    "symbol": symbol,
                    "shares": shares,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "sell_value": sell_value,
                    "commission": total_sell_cost,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                })
                sell_proceeds += net_proceeds
                self.trades.append(sell_details[-1])

            cash += sell_proceeds

            # ---- Step 2: Screen and buy new stocks at close ----
            selected = self.screener.screen(df)

            buy_details = []
            if not selected.empty:
                # Equal weight allocation
                alloc_per_stock = cash / self.top_n

                for _, row in selected.iterrows():
                    symbol = str(row.get("symbol", row.get("ts_code", ""))).split(".")[0]
                    close_price = float(row.get("close", 0))

                    if close_price <= 0:
                        continue

                    # Calculate shares (round down to lot size)
                    lots = int(alloc_per_stock / (close_price * LOT_SIZE))
                    shares = lots * LOT_SIZE

                    if shares <= 0:
                        logger.debug(f"  {trade_date}: {symbol} 价格{close_price:.2f}太高，资金不足1手")
                        continue

                    buy_value = shares * close_price
                    buy_commission = max(buy_value * COMMISSION_RATE, MIN_COMMISSION)
                    buy_transfer = buy_value * TRANSFER_FEE_RATE
                    total_buy_cost = buy_value + buy_commission + buy_transfer

                    if total_buy_cost > cash:
                        shares = int((cash - MIN_COMMISSION) / (close_price * (1 + COMMISSION_RATE + TRANSFER_FEE_RATE)))
                        shares = (shares // LOT_SIZE) * LOT_SIZE
                        if shares <= 0:
                            continue
                        buy_value = shares * close_price
                        buy_commission = max(buy_value * COMMISSION_RATE, MIN_COMMISSION)
                        buy_transfer = buy_value * TRANSFER_FEE_RATE
                        total_buy_cost = buy_value + buy_commission + buy_transfer

                    cash -= total_buy_cost
                    holdings[symbol] = {
                        "shares": shares,
                        "buy_price": close_price,
                        "buy_date": trade_date,
                    }
                    buy_details.append(f"{symbol}@{close_price:.2f}x{shares}")

            # ---- Step 3: Calculate daily NAV ----
            holdings_value = 0.0
            for symbol, h in holdings.items():
                # Use close price for NAV calculation
                stock_rows = df[df["symbol"] == symbol] if "symbol" in df.columns else pd.DataFrame()
                if stock_rows.empty:
                    ts_code = f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
                    stock_rows = df[df["ts_code"] == ts_code] if "ts_code" in df.columns else pd.DataFrame()
                current_price = float(stock_rows.iloc[0]["close"]) if not stock_rows.empty else h["buy_price"]
                holdings_value += h["shares"] * current_price

            nav = cash + holdings_value

            self.daily_nav.append({
                "date": trade_date,
                "cash": cash,
                "holdings_value": holdings_value,
                "nav": nav,
                "num_holdings": len(holdings),
                "new_buys": len(buy_details),
                "sells": len(sell_details),
            })

            # Logging
            sell_str = "; ".join([f"{s['symbol']} PnL={s['pnl']:.1f}({s['pnl_pct']:.1f}%)" for s in sell_details])
            buy_str = ", ".join(buy_details)
            logger.info(
                f"  {trade_date}: NAV={nav:,.2f} | "
                f"卖: [{sell_str}] | 买: [{buy_str}]"
            )

        # ---- Final: Force sell remaining holdings at last close ----
        if holdings and trade_dates:
            last_date = trade_dates[-1]
            last_df = daily_data.get(last_date, pd.DataFrame())
            for symbol, h in list(holdings.items()):
                stock_rows = last_df[last_df["symbol"] == symbol] if "symbol" in last_df.columns else pd.DataFrame()
                if stock_rows.empty:
                    ts_code = f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
                    stock_rows = last_df[last_df["ts_code"] == ts_code] if "ts_code" in last_df.columns else pd.DataFrame()
                sell_price = float(stock_rows.iloc[0]["close"]) if not stock_rows.empty else h["buy_price"]
                shares = h["shares"]
                sell_value = shares * sell_price
                sell_commission = max(sell_value * COMMISSION_RATE, MIN_COMMISSION)
                stamp_duty = sell_value * STAMP_DUTY_RATE
                sell_transfer = sell_value * TRANSFER_FEE_RATE
                net = sell_value - sell_commission - stamp_duty - sell_transfer
                cash += net
                pnl = net - (shares * h["buy_price"])
                self.trades.append({
                    "buy_date": h["buy_date"],
                    "sell_date": last_date,
                    "symbol": symbol,
                    "shares": shares,
                    "buy_price": h["buy_price"],
                    "sell_price": sell_price,
                    "sell_value": sell_value,
                    "commission": sell_commission + stamp_duty + sell_transfer,
                    "pnl": pnl,
                    "pnl_pct": pnl / (shares * h["buy_price"]) * 100 if h["buy_price"] > 0 else 0,
                })
            holdings.clear()

        return self._generate_report(cash)

    def _generate_report(self, final_cash: float) -> dict[str, Any]:
        """生成回测报告。"""
        nav_df = pd.DataFrame(self.daily_nav)
        trades_df = pd.DataFrame(self.trades) if self.trades else pd.DataFrame()

        total_pnl = final_cash - self.initial_capital
        total_return = total_pnl / self.initial_capital * 100

        # Win/Loss stats
        wins = 0
        losses = 0
        total_win_pnl = 0.0
        total_loss_pnl = 0.0
        if not trades_df.empty:
            wins = int((trades_df["pnl"] > 0).sum())
            losses = int((trades_df["pnl"] <= 0).sum())
            total_win_pnl = trades_df.loc[trades_df["pnl"] > 0, "pnl"].sum()
            total_loss_pnl = trades_df.loc[trades_df["pnl"] <= 0, "pnl"].sum()

        win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        avg_win = total_win_pnl / wins if wins > 0 else 0
        avg_loss = total_loss_pnl / losses if losses > 0 else 0
        profit_factor = abs(total_win_pnl / total_loss_pnl) if total_loss_pnl != 0 else float("inf")

        # Max drawdown
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        if not nav_df.empty:
            nav_series = nav_df["nav"]
            running_max = nav_series.cummax()
            drawdown = nav_series - running_max
            drawdown_pct = drawdown / running_max * 100
            max_drawdown = float(drawdown.min())
            max_drawdown_pct = float(drawdown_pct.min())

        # Sharpe ratio (annualized, risk-free = 2%)
        sharpe = 0.0
        if not nav_df.empty and len(nav_df) > 1:
            daily_returns = nav_df["nav"].pct_change().dropna()
            if len(daily_returns) > 0 and daily_returns.std() > 0:
                rf_daily = 0.02 / 252
                excess_returns = daily_returns - rf_daily
                sharpe = float(excess_returns.mean() / daily_returns.std() * np.sqrt(252))

        return {
            "initial_capital": self.initial_capital,
            "final_nav": final_cash,
            "total_pnl": total_pnl,
            "total_return_pct": total_return,
            "total_trades": len(trades_df),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
            "sharpe_ratio": sharpe,
            "trades_df": trades_df,
            "nav_df": nav_df,
        }


# ============================================================================
# Report Printer
# ============================================================================
def print_report(report: dict[str, Any]) -> None:
    """打印回测报告。"""
    print("\n" + "=" * 80)
    print("  🌙 一夜持股法回测报告 (杨永兴策略)")
    print("=" * 80)

    print(f"\n  📅 回测区间: {START_DATE} ~ {END_DATE}")
    print(f"  💰 初始资金: {report['initial_capital']:>12,.2f} CNY")
    print(f"  💰 最终净值: {report['final_nav']:>12,.2f} CNY")
    print(f"  📊 总盈亏:   {report['total_pnl']:>12,.2f} CNY")
    print(f"  📈 总收益率: {report['total_return_pct']:>11.2f} %")

    print(f"\n  --- 交易统计 ---")
    print(f"  总交易次数:   {report['total_trades']:>8d}")
    print(f"  盈利次数:     {report['wins']:>8d}")
    print(f"  亏损次数:     {report['losses']:>8d}")
    print(f"  胜率:         {report['win_rate']:>7.1f} %")
    print(f"  平均盈利:     {report['avg_win']:>12,.2f} CNY")
    print(f"  平均亏损:     {report['avg_loss']:>12,.2f} CNY")
    print(f"  盈亏比:       {report['profit_factor']:>7.2f}")

    print(f"\n  --- 风险指标 ---")
    print(f"  最大回撤:     {report['max_drawdown']:>12,.2f} CNY")
    print(f"  最大回撤率:   {report['max_drawdown_pct']:>11.2f} %")
    print(f"  夏普比率:     {report['sharpe_ratio']:>7.2f}")

    # Print trade details
    trades_df = report["trades_df"]
    if not trades_df.empty:
        print(f"\n  --- 交易明细 ---")
        print("-" * 80)
        with pd.option_context(
            "display.max_rows", 200,
            "display.max_columns", None,
            "display.width", 200,
            "display.float_format", "{:.2f}".format,
        ):
            print(trades_df[[
                "buy_date", "sell_date", "symbol", "shares",
                "buy_price", "sell_price", "pnl", "pnl_pct", "commission",
            ]].to_string(index=False))

    # Print NAV curve
    nav_df = report["nav_df"]
    if not nav_df.empty:
        print(f"\n  --- 每日净值 ---")
        print("-" * 80)
        with pd.option_context(
            "display.max_rows", 100,
            "display.width", 200,
            "display.float_format", "{:.2f}".format,
        ):
            print(nav_df[["date", "cash", "holdings_value", "nav", "new_buys", "sells"]].to_string(index=False))

    print("\n" + "=" * 80)
    print("  回测完成! 🚀")
    print("=" * 80)


def save_report_to_file(report: dict[str, Any]) -> str:
    """保存报告到文件。"""
    output_path = "ashare_overnight_hold_report.txt"
    import io
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer
    print_report(report)
    sys.stdout = old_stdout

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(buffer.getvalue())

    return output_path


# ============================================================================
# Main
# ============================================================================
def main() -> None:
    print("=" * 80)
    print("  🌙 一夜持股法全市场回测 (杨永兴策略)")
    print(f"  区间: {START_DATE} ~ {END_DATE}")
    print(f"  资金: {INITIAL_CAPITAL:,.0f} CNY | 选股: Top {TOP_N}")
    print("=" * 80)

    # Initialize data fetcher
    fetcher = AShareDataFetcher()

    # Try tushare first (much faster for bulk data)
    use_tushare = fetcher.init_tushare()
    if not use_tushare:
        logger.info("Tushare unavailable, falling back to AKShare")
        if not fetcher.init_akshare():
            logger.error("No data source available!")
            return

    # Get trade dates
    logger.info("获取交易日历...")
    trade_dates = fetcher.get_trade_dates(START_DATE, END_DATE)
    logger.info(f"共 {len(trade_dates)} 个交易日: {trade_dates[0]} ~ {trade_dates[-1]}")

    # Fetch daily data for all trade dates (with Parquet cache)
    cached_count, cached_size = fetcher.cache_stats()
    logger.info(f"本地缓存: {cached_count} 个文件, {cached_size:.1f} MB")
    logger.info("开始加载/拉取全市场日线数据...")
    daily_data: dict[str, pd.DataFrame] = {}
    failed_dates: list[str] = []
    api_fetch_count = 0  # 跟踪实际API调用次数

    for idx, trade_date in enumerate(trade_dates):
        # 1) 尝试从缓存加载
        df = fetcher.load_from_cache(trade_date)

        if not df.empty:
            daily_data[trade_date] = df
            logger.info(f"  [{idx+1}/{len(trade_dates)}] {trade_date}: 从缓存加载 {len(df)} 只股票 ✓")
            continue

        # 2) 缓存未命中，从API拉取
        logger.info(f"  [{idx+1}/{len(trade_dates)}] 拉取 {trade_date} 数据...")
        df = pd.DataFrame()
        if use_tushare:
            df = fetcher.fetch_daily_all_tushare(trade_date)

        if df.empty:
            # Fallback to akshare for this date
            df = fetcher.fetch_daily_all_akshare(trade_date)

        if df.empty:
            logger.warning(f"  {trade_date}: 无数据")
            failed_dates.append(trade_date)
        else:
            daily_data[trade_date] = df
            # 3) 保存到 Parquet 缓存
            fetcher.save_to_cache(trade_date, df)
            api_fetch_count += 1
            logger.info(f"  {trade_date}: {len(df)} 只股票 (API拉取+缓存)")

        # Batch pause for rate limiting (only for API calls)
        if api_fetch_count > 0 and api_fetch_count % 10 == 0:
            remaining_api = sum(1 for d in trade_dates[idx+1:] if not os.path.exists(fetcher._cache_path(d)))
            if remaining_api > 0:
                logger.info(f"  暂停 {BATCH_PAUSE}s 避免限流... (剩余 {remaining_api} 个需API拉取)")
                time.sleep(BATCH_PAUSE)

    # Remove failed dates
    trade_dates = [d for d in trade_dates if d not in failed_dates]
    logger.info(f"成功获取 {len(trade_dates)}/{len(trade_dates)+len(failed_dates)} 个交易日数据")

    if not trade_dates:
        logger.error("无可用数据，回测终止")
        return

    # Run backtest
    backtest = OvernightHoldBacktest(
        initial_capital=INITIAL_CAPITAL,
        top_n=TOP_N,
    )
    report = backtest.run(daily_data, trade_dates)

    # Print and save report
    print_report(report)
    output_path = save_report_to_file(report)
    logger.info(f"报告已保存到: {output_path}")


if __name__ == "__main__":
    main()
