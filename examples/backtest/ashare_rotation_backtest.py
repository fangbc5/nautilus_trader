#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Backtest: Multi-Factor Weekly Rotation Strategy (多因子周频轮动策略)
# -------------------------------------------------------------------------------------------------
"""
Stable strategy: Weekly rebalancing with diversified holdings.

Key principles:
    - Diversified: 15 stocks equally weighted
    - Low frequency: Weekly rebalancing (every Friday)
    - Multi-factor: Momentum + Value + Quality + Technical
    - Trend following: Only invest when market is trending up
    - No look-ahead: Signal on Friday, execute at Monday open

Usage:
    python -m examples.backtest.ashare_rotation_backtest
"""

import os
import glob
from datetime import datetime

import pandas as pd
import numpy as np

# ============================================================================
# Configuration
# ============================================================================

CACHE_DIR = os.path.expanduser("~/.nautilus/ashare_cache")
INITIAL_CAPITAL = 200_000.0

# Portfolio
NUM_HOLDINGS = 15
REBALANCE_DAY = 4          # 0=Mon, 4=Friday
POSITION_WEIGHT = 1.0 / NUM_HOLDINGS

# Factor weights
W_MOMENTUM = 0.40
W_VALUE = 0.20
W_QUALITY = 0.20
W_TECHNICAL = 0.20

# Market filter
MARKET_BREADTH_THRESHOLD = 0.45
BREADTH_LOOKBACK = 5

# Stock filters
MIN_CLOSE = 3.0
MAX_CLOSE = 100.0
MIN_VOLUME = 100_000
MIN_HISTORY = 60

# Transaction costs
COMMISSION_RATE = 0.001
SLIPPAGE = 0.001

# Holding rules
STOP_LOSS_PCT = 8.0
TRAILING_STOP_PCT = 5.0
TRAILING_ACTIVATE_PCT = 5.0


# ============================================================================
# Data Loading
# ============================================================================

def load_data(cache_dir: str) -> dict[str, pd.DataFrame]:
    pattern = os.path.join(cache_dir, "daily_all_*.parquet")
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"  ERROR: 未找到数据文件于 {cache_dir}")
        return {}
    daily_data = {}
    for f in files:
        date_str = os.path.basename(f).replace("daily_all_", "").replace(".parquet", "")
        try:
            daily_data[date_str] = pd.read_parquet(f)
        except Exception as e:
            print(f"  警告: 读取失败: {e}")
    return daily_data


# ============================================================================
# Vectorized Factor Engine
# ============================================================================

def build_stock_time_series(daily_data: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """Build per-stock sorted arrays for fast factor computation."""
    print("  构建股票时间序列...")
    dates_all = sorted(daily_data.keys())
    date_to_idx = {d: i for i, d in enumerate(dates_all)}

    # Aggregate all data
    stock_ts: dict[str, dict[str, dict]] = {}
    for date in dates_all:
        df = daily_data[date]
        for _, row in df.iterrows():
            sym = str(row["symbol"])
            if sym not in stock_ts:
                stock_ts[sym] = {}
            stock_ts[sym][date] = {
                "open": float(row["open"]) if pd.notna(row["open"]) else np.nan,
                "high": float(row["high"]) if pd.notna(row["high"]) else np.nan,
                "low": float(row["low"]) if pd.notna(row["low"]) else np.nan,
                "close": float(row["close"]) if pd.notna(row["close"]) else np.nan,
                "volume": float(row["volume"]) if pd.notna(row["volume"]) else 0,
                "pct_change": float(row["pct_change"]) if pd.notna(row["pct_change"]) else 0,
                "total_mv": float(row["total_mv"]) if pd.notna(row.get("total_mv", np.nan)) else np.nan,
                "pe": float(row["pe"]) if pd.notna(row.get("pe", np.nan)) else np.nan,
                "pb": float(row["pb"]) if pd.notna(row.get("pb", np.nan)) else np.nan,
                "turnover_rate": float(row["turnover_rate"]) if pd.notna(row.get("turnover_rate", np.nan)) else np.nan,
                "volume_ratio": float(row["volume_ratio"]) if pd.notna(row.get("volume_ratio", np.nan)) else np.nan,
            }

    # Convert to numpy arrays
    print("  向量化...")
    stock_arrays = {}
    for sym, ts in stock_ts.items():
        if len(ts) < MIN_HISTORY:
            continue
        sorted_dates = sorted(ts.keys())
        n = len(sorted_dates)
        d = np.array(sorted_dates)
        d_idx = {dd: i for i, dd in enumerate(sorted_dates)}

        closes = np.array([ts[dd]["close"] for dd in sorted_dates])
        opens = np.array([ts[dd]["open"] for dd in sorted_dates])
        highs = np.array([ts[dd]["high"] for dd in sorted_dates])
        lows = np.array([ts[dd]["low"] for dd in sorted_dates])
        volumes = np.array([ts[dd]["volume"] for dd in sorted_dates])
        pcts = np.array([ts[dd]["pct_change"] for dd in sorted_dates])
        total_mvs = np.array([ts[dd]["total_mv"] for dd in sorted_dates])
        pes = np.array([ts[dd]["pe"] for dd in sorted_dates])
        pbs = np.array([ts[dd]["pb"] for dd in sorted_dates])
        turnover_rates = np.array([ts[dd]["turnover_rate"] for dd in sorted_dates])
        volume_ratios = np.array([ts[dd]["volume_ratio"] for dd in sorted_dates])

        # Moving averages (vectorized cumsum)
        ma20 = np.full(n, np.nan)
        ma60 = np.full(n, np.nan)
        for period, arr in [(20, ma20), (60, ma60)]:
            if n >= period:
                cs = np.cumsum(closes)
                cs[period:] = cs[period:] - cs[:-period]
                arr[period - 1:] = cs[period - 1:] / period

        # Momentum
        mom_20d = np.full(n, np.nan)
        mom_60d = np.full(n, np.nan)
        if n >= 20:
            mom_20d[20:] = (closes[20:] / closes[:-20] - 1) * 100
        if n >= 60:
            mom_60d[60:] = (closes[60:] / closes[:-60] - 1) * 100

        stock_arrays[sym] = {
            "dates": d, "date_to_idx": d_idx, "n": n,
            "closes": closes, "opens": opens, "highs": highs, "lows": lows,
            "volumes": volumes, "pcts": pcts,
            "total_mvs": total_mvs, "pes": pes, "pbs": pbs,
            "turnover_rates": turnover_rates, "volume_ratios": volume_ratios,
            "ma20": ma20, "ma60": ma60,
            "mom_20d": mom_20d, "mom_60d": mom_60d,
        }

    print(f"  有效股票: {len(stock_arrays)} 只")
    return stock_arrays, date_to_idx, dates_all


def score_stocks_on_date(stock_arrays: dict, date: str) -> pd.DataFrame:
    """Score all stocks for a given date using vectorized operations."""
    candidates = []

    for sym, arr in stock_arrays.items():
        i = arr["date_to_idx"].get(date, -1)
        if i < MIN_HISTORY:
            continue

        close = arr["closes"][i]
        if np.isnan(close) or close < MIN_CLOSE or close > MAX_CLOSE:
            continue
        if arr["volumes"][i] < MIN_VOLUME:
            continue
        if np.isnan(arr["ma20"][i]) or np.isnan(arr["ma60"][i]):
            continue

        ma20_val = arr["ma20"][i]
        ma60_val = arr["ma60"][i]
        above_ma20 = close > ma20_val
        above_ma60 = close > ma60_val

        # Only consider stocks above MA20 (trend filter)
        if not above_ma20:
            continue

        mom_20 = arr["mom_20d"][i]
        mom_60 = arr["mom_60d"][i]
        if np.isnan(mom_20):
            continue

        candidates.append({
            "symbol": sym,
            "close": close,
            "volume": arr["volumes"][i],
            "total_mv": arr["total_mvs"][i],
            "pe": arr["pes"][i],
            "pb": arr["pbs"][i],
            "turnover_rate": arr["turnover_rates"][i],
            "volume_ratio": arr["volume_ratios"][i],
            "mom_20d": mom_20,
            "mom_60d": mom_60 if not np.isnan(mom_60) else mom_20,
            "above_ma20": above_ma20,
            "above_ma60": above_ma60,
        })

    if not candidates:
        return pd.DataFrame()

    df = pd.DataFrame(candidates)

    # Score: Momentum (rank-based, cross-sectional)
    df["mom_score"] = (
        df["mom_20d"].rank(pct=True) * 0.6 +
        df["mom_60d"].rank(pct=True) * 0.4
    ) * 100

    # Score: Value (low PE + low PB → higher score)
    df["value_score"] = 50.0
    valid_pe = df["pe"].notna() & (df["pe"] > 0) & (df["pe"] < 100)
    valid_pb = df["pb"].notna() & (df["pb"] > 0) & (df["pb"] < 50)
    if valid_pe.any():
        df.loc[valid_pe, "value_score"] += (100 - df.loc[valid_pe, "pe"].rank(pct=True) * 100) * 0.25
    if valid_pb.any():
        df.loc[valid_pb, "value_score"] += (100 - df.loc[valid_pb, "pb"].rank(pct=True) * 100) * 0.25

    # Score: Quality (moderate turnover)
    df["quality_score"] = 50.0
    valid_tr = df["turnover_rate"].notna()
    if valid_tr.any():
        tr = df.loc[valid_tr, "turnover_rate"]
        median_tr = tr.median()
        std_tr = tr.std() + 0.01
        df.loc[valid_tr, "quality_score"] = np.clip(100 - np.abs(tr - median_tr) / std_tr * 15, 10, 100)

    # Score: Technical
    df["tech_score"] = (
        df["above_ma20"].astype(float) * 30 +
        df["above_ma60"].astype(float) * 30 +
        (df["volume_ratio"].fillna(1.0) > 1.0).astype(float) * 20 +
        np.clip(df["volume_ratio"].fillna(1.0), 0, 3) / 3 * 20
    )

    # Composite
    df["composite_score"] = (
        df["mom_score"] * W_MOMENTUM +
        df["value_score"] * W_VALUE +
        df["quality_score"] * W_QUALITY +
        df["tech_score"] * W_TECHNICAL
    )

    df = df.sort_values("composite_score", ascending=False)
    return df


# ============================================================================
# Backtest Engine
# ============================================================================

def run_backtest(daily_data: dict[str, pd.DataFrame]) -> dict:
    """Run the multi-factor rotation backtest."""
    all_dates = sorted(daily_data.keys())
    print(f"  总交易日: {len(all_dates)} ({all_dates[0]} ~ {all_dates[-1]})")

    # Build stock arrays
    stock_arrays, date_to_idx, _ = build_stock_time_series(daily_data)

    # Determine rebalance dates (every Friday)
    rebalance_dates = set()
    for d in all_dates:
        dt = datetime.strptime(d, "%Y%m%d")
        if dt.weekday() == REBALANCE_DAY:
            rebalance_dates.add(d)

    print(f"  调仓日 (周五): {len(rebalance_dates)} 个")

    # Build date-indexed price lookups
    print("  构建价格索引...")
    price_lookup = {}
    for date in all_dates:
        df = daily_data[date]
        price_lookup[date] = {}
        for _, row in df.iterrows():
            sym = str(row["symbol"])
            price_lookup[date][sym] = {
                "open": float(row["open"]) if pd.notna(row["open"]) else np.nan,
                "high": float(row["high"]) if pd.notna(row["high"]) else np.nan,
                "low": float(row["low"]) if pd.notna(row["low"]) else np.nan,
                "close": float(row["close"]) if pd.notna(row["close"]) else np.nan,
                "pct_change": float(row["pct_change"]) if pd.notna(row["pct_change"]) else 0,
            }

    # Track portfolio
    portfolio = {}
    cash = INITIAL_CAPITAL
    nav_history = []
    trades = []
    rebalance_log = []

    for date_idx, date in enumerate(all_dates):
        today_prices = price_lookup.get(date, {})

        # Check stop losses first
        for sym in list(portfolio.keys()):
            pos = portfolio[sym]
            if sym not in today_prices:
                continue

            tp = today_prices[sym]
            entry_price = pos["entry_price"]
            current_price = tp["close"]

            if np.isnan(current_price):
                continue

            # Update high water mark
            if not np.isnan(tp["high"]):
                pos["high_since"] = max(pos["high_since"], tp["high"])

            # Fixed stop loss
            if current_price <= entry_price * (1 - STOP_LOSS_PCT / 100):
                sell_value = pos["shares"] * current_price * (1 - COMMISSION_RATE - SLIPPAGE)
                pnl_pct = (current_price - entry_price) / entry_price * 100
                cash += sell_value
                trades.append({
                    "symbol": sym, "action": "SELL", "date": date,
                    "price": current_price, "shares": pos["shares"],
                    "pnl_pct": pnl_pct, "reason": "STOP_LOSS",
                    "entry_date": pos["entry_date"], "entry_price": entry_price,
                })
                del portfolio[sym]
                continue

            # Trailing stop (only after sufficient profit)
            if pos["high_since"] > entry_price * (1 + TRAILING_ACTIVATE_PCT / 100):
                trail_price = pos["high_since"] * (1 - TRAILING_STOP_PCT / 100)
                if current_price <= trail_price:
                    sell_value = pos["shares"] * current_price * (1 - COMMISSION_RATE - SLIPPAGE)
                    pnl_pct = (current_price - entry_price) / entry_price * 100
                    cash += sell_value
                    trades.append({
                        "symbol": sym, "action": "SELL", "date": date,
                        "price": current_price, "shares": pos["shares"],
                        "pnl_pct": pnl_pct, "reason": "TRAILING_STOP",
                        "entry_date": pos["entry_date"], "entry_price": entry_price,
                    })
                    del portfolio[sym]

        # Rebalance on Fridays
        if date in rebalance_dates:
            # Compute market breadth
            advancing = sum(1 for p in today_prices.values() if p["pct_change"] > 0)
            total_active = sum(1 for p in today_prices.values() if not np.isnan(p["close"]) and p["close"] > 0)
            market_breadth = advancing / total_active if total_active > 0 else 0

            # Multi-day average breadth
            recent_breadth = market_breadth
            lookback = min(BREADTH_LOOKBACK, date_idx)
            for lb in range(1, lookback + 1):
                prev_date = all_dates[date_idx - lb]
                prev_prices = price_lookup.get(prev_date, {})
                adv = sum(1 for p in prev_prices.values() if p["pct_change"] > 0)
                tot = sum(1 for p in prev_prices.values() if not np.isnan(p["close"]) and p["close"] > 0)
                recent_breadth += adv / tot if tot > 0 else 0
            recent_breadth /= (lookback + 1)

            should_invest = recent_breadth >= MARKET_BREADTH_THRESHOLD

            if should_invest:
                # Score and rank stocks
                candidates = score_stocks_on_date(stock_arrays, date)

                if not candidates.empty:
                    target_symbols = set(candidates.head(NUM_HOLDINGS)["symbol"].values)
                    current_symbols = set(portfolio.keys())

                    # Compute current NAV for allocation
                    pv = sum(
                        pos["shares"] * today_prices[sym]["close"]
                        for sym, pos in portfolio.items()
                        if sym in today_prices and not np.isnan(today_prices[sym]["close"])
                    )
                    current_nav = cash + pv

                    # Sell positions not in target
                    for sym in list(current_symbols - target_symbols):
                        pos = portfolio[sym]
                        if sym in today_prices and not np.isnan(today_prices[sym]["close"]):
                            sell_price = today_prices[sym]["close"]
                            sell_value = pos["shares"] * sell_price * (1 - COMMISSION_RATE - SLIPPAGE)
                            pnl_pct = (sell_price - pos["entry_price"]) / pos["entry_price"] * 100
                            cash += sell_value
                            trades.append({
                                "symbol": sym, "action": "SELL", "date": date,
                                "price": sell_price, "shares": pos["shares"],
                                "pnl_pct": pnl_pct, "reason": "REBALANCE",
                                "entry_date": pos["entry_date"], "entry_price": pos["entry_price"],
                            })
                            del portfolio[sym]

                    # Buy new positions at NEXT day's open (no look-ahead)
                    next_idx = date_idx + 1
                    if next_idx < len(all_dates):
                        next_date = all_dates[next_idx]
                        next_prices = price_lookup.get(next_date, {})

                        # Recompute NAV after sells
                        pv = sum(
                            pos["shares"] * today_prices.get(sym, {}).get("close", pos["entry_price"])
                            for sym, pos in portfolio.items()
                        )
                        current_nav = cash + pv

                        for sym in target_symbols - set(portfolio.keys()):
                            if sym not in next_prices:
                                continue
                            buy_price = next_prices[sym]["open"]
                            if np.isnan(buy_price) or buy_price <= 0:
                                continue

                            alloc = current_nav * POSITION_WEIGHT
                            cost_per_share = buy_price * (1 + COMMISSION_RATE + SLIPPAGE)
                            shares = int(alloc / cost_per_share) // 100 * 100
                            if shares <= 0:
                                continue

                            cost = shares * cost_per_share
                            if cost > cash:
                                shares = int(cash / cost_per_share) // 100 * 100
                                if shares <= 0:
                                    continue
                                cost = shares * cost_per_share

                            cash -= cost
                            portfolio[sym] = {
                                "shares": shares,
                                "entry_price": buy_price,
                                "entry_date": next_date,
                                "high_since": buy_price,
                            }
                            trades.append({
                                "symbol": sym, "action": "BUY", "date": next_date,
                                "price": buy_price, "shares": shares,
                                "pnl_pct": 0, "reason": "REBALANCE",
                                "entry_date": next_date, "entry_price": buy_price,
                            })

                    rebalance_log.append({
                        "date": date, "breadth": market_breadth,
                        "recent_breadth": recent_breadth,
                        "num_candidates": len(candidates),
                        "num_holdings": len(portfolio), "action": "INVEST",
                    })
                else:
                    rebalance_log.append({
                        "date": date, "breadth": market_breadth,
                        "recent_breadth": recent_breadth,
                        "num_candidates": 0, "num_holdings": len(portfolio),
                        "action": "NO_CANDIDATES",
                    })
            else:
                # Market bearish - sell all
                for sym in list(portfolio.keys()):
                    pos = portfolio[sym]
                    if sym in today_prices and not np.isnan(today_prices[sym]["close"]):
                        sell_price = today_prices[sym]["close"]
                        sell_value = pos["shares"] * sell_price * (1 - COMMISSION_RATE - SLIPPAGE)
                        pnl_pct = (sell_price - pos["entry_price"]) / pos["entry_price"] * 100
                        cash += sell_value
                        trades.append({
                            "symbol": sym, "action": "SELL", "date": date,
                            "price": sell_price, "shares": pos["shares"],
                            "pnl_pct": pnl_pct, "reason": "MARKET_EXIT",
                            "entry_date": pos["entry_date"], "entry_price": pos["entry_price"],
                        })
                        del portfolio[sym]

                rebalance_log.append({
                    "date": date, "breadth": market_breadth,
                    "recent_breadth": recent_breadth,
                    "num_candidates": 0, "num_holdings": 0, "action": "CASH_OUT",
                })

        # Record daily NAV
        pv = 0
        for sym, pos in portfolio.items():
            if sym in today_prices and not np.isnan(today_prices[sym]["close"]):
                pv += pos["shares"] * today_prices[sym]["close"]
            else:
                pv += pos["shares"] * pos.get("entry_price", 0)

        nav = cash + pv
        nav_history.append({
            "date": date, "nav": nav, "cash": cash,
            "portfolio_value": pv, "num_holdings": len(portfolio),
        })

    return {
        "nav_history": nav_history,
        "trades": trades,
        "rebalance_log": rebalance_log,
    }


# ============================================================================
# Analysis
# ============================================================================

def analyze_results(results: dict) -> tuple:
    nav_df = pd.DataFrame(results["nav_history"])
    trades_df = pd.DataFrame(results["trades"]) if results["trades"] else pd.DataFrame()
    rebalance_df = pd.DataFrame(results["rebalance_log"]) if results["rebalance_log"] else pd.DataFrame()

    nav_df["date_dt"] = pd.to_datetime(nav_df["date"], format="%Y%m%d")
    nav_df = nav_df.set_index("date_dt").sort_index()

    initial_nav = nav_df["nav"].iloc[0]
    final_nav = nav_df["nav"].iloc[-1]
    total_return = (final_nav / initial_nav - 1) * 100

    nav_df["daily_return"] = nav_df["nav"].pct_change()
    ann_return = (1 + nav_df["daily_return"].mean()) ** 252 - 1
    ann_vol = nav_df["daily_return"].std() * np.sqrt(252)
    sharpe = (ann_return - 0.02) / ann_vol if ann_vol > 0 else 0

    nav_df["cummax"] = nav_df["nav"].cummax()
    nav_df["drawdown"] = (nav_df["nav"] - nav_df["cummax"]) / nav_df["cummax"] * 100
    max_dd = nav_df["drawdown"].min()
    calmar = ann_return / abs(max_dd / 100) if max_dd != 0 else 0

    print("\n" + "=" * 70)
    print("  多因子周频轮动策略 — 回测结果")
    print("=" * 70)
    print(f"\n  初始资金:      {initial_nav:>12,.2f} CNY")
    print(f"  最终资金:      {final_nav:>12,.2f} CNY")
    print(f"  总收益率:      {total_return:>11.2f} %")
    print(f"  年化收益率:    {ann_return*100:>11.2f} %")
    print(f"  年化波动率:    {ann_vol*100:>11.2f} %")
    print(f"  夏普比率:      {sharpe:>11.2f}")
    print(f"  最大回撤:      {max_dd:>11.2f} %")
    print(f"  卡玛比率:      {calmar:>11.2f}")

    # Yearly
    print(f"\n  {'='*66}")
    print(f"  按年度分析")
    print(f"  {'='*66}")
    print(f"  {'年份':>6s} | {'收益率':>8s} | {'最大回撤':>8s} | {'夏普':>6s} | {'交易数':>6s} | {'胜率':>6s}")
    print(f"  {'-'*6}-+-{'-'*8}-+-{'-'*8}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}")

    nav_df["year"] = nav_df.index.year
    for year in sorted(nav_df["year"].unique()):
        yd = nav_df[nav_df["year"] == year]
        yr = (yd["nav"].iloc[-1] / yd["nav"].iloc[0] - 1) * 100
        ydd = yd["drawdown"].min()
        ydr = yd["daily_return"].dropna()
        if len(ydr) > 1:
            ys = ((1 + ydr.mean()) ** 252 - 1 - 0.02) / (ydr.std() * np.sqrt(252))
        else:
            ys = 0

        if not trades_df.empty:
            yt = trades_df[(trades_df["action"] == "SELL") & (trades_df["date"].str.startswith(str(year)))]
            nt = len(yt)
            wr = (yt["pnl_pct"] > 0).sum() / nt * 100 if nt > 0 else 0
        else:
            nt, wr = 0, 0

        marker = " ★" if yr > 0 else " ✗"
        print(f"  {year:>6d} | {yr:>+7.1f}% | {ydd:>+7.1f}% | {ys:>5.2f} | {nt:>6d} | {wr:>5.1f}%{marker}")

    # Quarterly
    print(f"\n  {'='*56}")
    print(f"  按季度分析")
    print(f"  {'='*56}")
    print(f"  {'季度':>8s} | {'收益率':>8s} | {'最大回撤':>8s} | {'持仓天':>6s}")
    print(f"  {'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*6}")

    nav_df["quarter"] = nav_df.index.to_period("Q")
    for q in sorted(nav_df["quarter"].unique()):
        qd = nav_df[nav_df["quarter"] == q]
        qr = (qd["nav"].iloc[-1] / qd["nav"].iloc[0] - 1) * 100
        qdd = qd["drawdown"].min()
        hd = (qd["num_holdings"] > 0).sum()
        marker = " ★" if qr > 0 else ""
        print(f"  {str(q):>8s} | {qr:>+7.1f}% | {qdd:>+7.1f}% | {hd:>6d}{marker}")

    # Monthly heatmap
    print(f"\n  {'='*60}")
    print(f"  月度收益率")
    print(f"  {'='*60}")
    nav_df["month"] = nav_df.index.to_period("M")
    monthly = []
    for m in sorted(nav_df["month"].unique()):
        md = nav_df[nav_df["month"] == m]
        mr = (md["nav"].iloc[-1] / md["nav"].iloc[0] - 1) * 100
        monthly.append({"month": str(m), "return": mr})
    mdf = pd.DataFrame(monthly)
    for i in range(0, len(mdf), 6):
        row = mdf.iloc[i:i+6]
        line = "  "
        for _, r in row.iterrows():
            sign = "+" if r["return"] > 0 else ""
            line += f"{r['month']}:{sign}{r['return']:.1f}%  "
        print(line)

    pos_months = (mdf["return"] > 0).sum()
    print(f"\n  正收益月份: {pos_months}/{len(mdf)} ({pos_months/len(mdf)*100:.0f}%)")

    # Trade stats
    if not trades_df.empty:
        sells = trades_df[trades_df["action"] == "SELL"]
        buys = trades_df[trades_df["action"] == "BUY"]
        print(f"\n  {'='*56}")
        print(f"  交易统计")
        print(f"  {'='*56}")
        print(f"  买入: {len(buys)} | 卖出: {len(sells)}")

        if not sells.empty:
            wins = sells[sells["pnl_pct"] > 0]
            losses = sells[sells["pnl_pct"] <= 0]
            print(f"  胜率: {len(wins)/len(sells)*100:.1f}%")
            if len(wins) > 0:
                print(f"  平均盈利: {wins['pnl_pct'].mean():+.2f}%")
            if len(losses) > 0:
                print(f"  平均亏损: {losses['pnl_pct'].mean():+.2f}%")
            if len(wins) > 0 and len(losses) > 0:
                print(f"  盈亏比: {wins['pnl_pct'].sum()/abs(losses['pnl_pct'].sum()):.2f}")

            print(f"\n  --- 退出原因 ---")
            for reason, grp in sells.groupby("reason"):
                rw = (grp["pnl_pct"] > 0).sum()
                print(f"  {reason:15s}: {len(grp):>4d} 笔 | 胜率 {rw/len(grp)*100:.0f}% | 均值 {grp['pnl_pct'].mean():>+6.2f}%")

    # Rebalance stats
    if not rebalance_df.empty:
        print(f"\n  --- 调仓统计 ---")
        for action, count in rebalance_df["action"].value_counts().items():
            print(f"  {action:15s}: {count:>4d} 次")

    return nav_df, trades_df


# ============================================================================
# Main
# ============================================================================

def generate_tearsheet_report(nav_df: pd.DataFrame, trades_df: pd.DataFrame) -> None:
    """Generate an interactive HTML tearsheet using NautilusTrader's analysis framework."""
    try:
        from nautilus_trader.analysis.tearsheet import create_tearsheet_from_stats
        from nautilus_trader.analysis.config import (
            TearsheetConfig,
            TearsheetRunInfoChart,
            TearsheetStatsTableChart,
            TearsheetEquityChart,
            TearsheetDrawdownChart,
            TearsheetMonthlyReturnsChart,
            TearsheetDistributionChart,
            TearsheetRollingSharpeChart,
            TearsheetYearlyReturnsChart,
        )
    except ImportError:
        print("\n  跳过报告生成 (需要 nautilus_trader 分析模块)")
        return

    # Build daily returns series
    returns = nav_df["daily_return"].dropna()
    returns.index = pd.to_datetime(returns.index)

    # Compute statistics
    initial_nav = nav_df["nav"].iloc[0]
    final_nav = nav_df["nav"].iloc[-1]
    total_return = (final_nav / initial_nav - 1)
    ann_return = (1 + returns.mean()) ** 252 - 1
    ann_vol = returns.std() * np.sqrt(252)
    sharpe = (ann_return - 0.02) / ann_vol if ann_vol > 0 else 0

    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()

    # Annualized sortino
    neg_returns = returns[returns < 0]
    downside_vol = neg_returns.std() * np.sqrt(252) if len(neg_returns) > 0 else ann_vol
    sortino = (ann_return - 0.02) / downside_vol if downside_vol > 0 else 0

    # Calmar
    calmar = ann_return / abs(max_dd) if max_dd != 0 else 0

    # Winning/losing stats
    sells = trades_df[trades_df["action"] == "SELL"] if not trades_df.empty else pd.DataFrame()
    total_trades = len(sells)
    winning_trades = len(sells[sells["pnl_pct"] > 0]) if total_trades > 0 else 0
    win_rate = winning_trades / total_trades if total_trades > 0 else 0

    # Build stats dicts for tearsheet
    stats_returns = {
        "Annual Return": round(ann_return * 100, 2),
        "Annual Volatility": round(ann_vol * 100, 2),
        "Sharpe Ratio": round(sharpe, 3),
        "Sortino Ratio": round(sortino, 3),
        "Calmar Ratio": round(calmar, 3),
        "Max Drawdown": round(max_dd * 100, 2),
        "Total Return": round(total_return * 100, 2),
    }

    stats_pnls = {
        "CNY": {
            "PnL (total)": round(final_nav - initial_nav, 2),
            "PnL% (total)": round(total_return * 100, 2),
            "Total Trades": total_trades,
            "Win Rate": round(win_rate * 100, 1),
        }
    }

    stats_general = {
        "Total Trades": total_trades,
        "Win Rate (%)": round(win_rate * 100, 1),
        "Initial Capital": round(initial_nav, 2),
        "Final Capital": round(final_nav, 2),
    }

    # Run info
    start_date = nav_df.index[0].strftime("%Y-%m-%d")
    end_date = nav_df.index[-1].strftime("%Y-%m-%d")
    run_info = {
        "策略": "多因子周频轮动",
        "回测区间": f"{start_date} ~ {end_date}",
        "交易日数": str(len(nav_df)),
        "持仓数量": str(NUM_HOLDINGS),
        "初始资金": f"{INITIAL_CAPITAL:,.0f} CNY",
    }

    account_info = {
        "起始资金 (CNY)": f"{initial_nav:,.2f}",
        "最终资金 (CNY)": f"{final_nav:,.2f}",
    }

    # Configure tearsheet with Chinese locale
    config = TearsheetConfig(
        charts=[
            TearsheetRunInfoChart(),
            TearsheetStatsTableChart(),
            TearsheetEquityChart(),
            TearsheetDrawdownChart(),
            TearsheetMonthlyReturnsChart(),
            TearsheetDistributionChart(),
            TearsheetRollingSharpeChart(),
            TearsheetYearlyReturnsChart(),
        ],
        theme="plotly_white",
        locale="zh_CN",
        title="多因子周频轮动策略 — 回测报告",
        show_logo=False,
    )

    output_path = "ashare_rotation_tearsheet.html"
    print(f"\n[3/3] 生成报告...")

    create_tearsheet_from_stats(
        stats_pnls=stats_pnls,
        stats_returns=stats_returns,
        stats_general=stats_general,
        returns=returns,
        output_path=output_path,
        title=config.title,
        config=config,
        run_info=run_info,
        account_info=account_info,
    )

    print(f"  报告已保存: {output_path}")


def main() -> None:
    print("=" * 70)
    print("  多因子周频轮动策略回测")
    print(f"  持有{NUM_HOLDINGS}只 | 周五调仓 | 动量+价值+质量+技术")
    print(f"  初始资金: {INITIAL_CAPITAL:,.0f} CNY")
    print("=" * 70)

    print("\n[1/2] 加载数据...")
    daily_data = load_data(CACHE_DIR)
    if not daily_data:
        return

    total_stocks = sum(len(df) for df in daily_data.values())
    print(f"  {len(daily_data)} 个交易日 | {total_stocks:,} 条记录")

    print("\n[2/2] 运行回测...")
    results = run_backtest(daily_data)

    nav_df, trades_df = analyze_results(results)

    # Generate HTML tearsheet report
    generate_tearsheet_report(nav_df, trades_df)

    nav_csv = "ashare_rotation_nav.csv"
    nav_df[["nav", "cash", "portfolio_value", "num_holdings", "drawdown"]].to_csv(nav_csv)
    print(f"\n  NAV: {nav_csv}")

    if not trades_df.empty:
        trades_csv = "ashare_rotation_trades.csv"
        trades_df.to_csv(trades_csv, index=False)
        print(f"  交易: {trades_csv}")

    print("\n  回测完成!")


if __name__ == "__main__":
    main()