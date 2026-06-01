#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Full Market Data Downloader (新浪财经 API)
# -------------------------------------------------------------------------------------------------
"""
Downloads A-share market data from Sina Finance API.
Push2 (东方财富) is blocked from current network; Sina is stable and reliable.

Data:
- Daily K-line for all stocks (~5500 stocks, ~500 trading days ≈ 2 years)
- Per-stock parquet cache + daily cross-section files
- Resume capability for interrupted downloads

Usage:
    python scripts/download_ashare_data.py
    python scripts/download_ashare_data.py --max-stocks 100  # test run

Estimated time: 20-40 min for full market
Estimated disk: ~1.5GB
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CACHE_DIR = os.path.expanduser("~/.nautilus/ashare_cache")
PROGRESS_FILE = os.path.join(CACHE_DIR, "download_progress.json")

REQUEST_DELAY = 0.10   # seconds between requests
BATCH_PAUSE = 8        # pause seconds every BATCH_SIZE stocks
BATCH_SIZE = 100
MAX_RETRIES = 5
PAGE_SIZE = 80         # Sina stock list page size (max ~80)

# Sina Finance API
KLINE_URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
STOCK_COUNT_URL = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeStockCount"
STOCK_LIST_URL = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"


def _curl_get(url: str, timeout: int = 15) -> str:
    """HTTP GET via curl subprocess."""
    r = subprocess.run(
        ["curl", "-s", "--max-time", str(timeout), url],
        capture_output=True,
        text=True,
        timeout=timeout + 5,
    )
    if r.returncode != 0:
        raise ConnectionError(f"curl failed: rc={r.returncode}")
    if not r.stdout.strip():
        raise ConnectionError("curl returned empty response")
    return r.stdout


def _curl_get_json(url: str, timeout: int = 15) -> list | dict:
    """HTTP GET via curl, parse JSON response."""
    text = _curl_get(url, timeout)
    return json.loads(text)


def _get_sina_prefix(code: str) -> str:
    """股票代码转新浪前缀: 6开头=sh, 0/3开头=sz"""
    return "sh" if code.startswith("6") else "sz"


def get_all_stocks() -> pd.DataFrame:
    """获取全部A股股票列表（新浪财经API）。"""
    logger.info("获取全部A股股票列表...")

    # Get total count (with retry)
    total = 5500  # default fallback
    for attempt in range(MAX_RETRIES):
        try:
            count_text = _curl_get(f"{STOCK_COUNT_URL}?node=hs_a").strip().strip('"')
            total = int(count_text)
            break
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"  获取股票总数失败 (尝试 {attempt+1}/{MAX_RETRIES}): {e}")
                time.sleep((attempt + 1) * 3)
            else:
                logger.warning(f"  使用默认总数: {total}")
    logger.info(f"  新浪A股总数: {total}")

    # Paginate
    all_stocks = []
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    for page in range(1, pages + 1):
        url = (
            f"{STOCK_LIST_URL}?page={page}&num={PAGE_SIZE}"
            f"&sort=symbol&asc=1&node=hs_a"
        )
        for attempt in range(MAX_RETRIES):
            try:
                stocks = _curl_get_json(url)
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep((attempt + 1) * 3)
                else:
                    logger.warning(f"  第{page}页获取失败: {e}")
                    stocks = []

        if stocks:
            all_stocks.extend(stocks)

        if page % 10 == 0:
            logger.info(f"  已获取 {len(all_stocks)}/{total} 只股票 (page {page}/{pages})")
        time.sleep(0.15)

    if not all_stocks:
        raise RuntimeError("无法获取股票列表！")

    df = pd.DataFrame(all_stocks)
    logger.info(f"  共获取 {len(df)} 只股票, 列: {list(df.columns)[:10]}")

    # Ensure 'code' column exists and rename to 'symbol'
    if "code" in df.columns and "symbol" not in df.columns:
        df = df.rename(columns={"code": "symbol"})
    
    # Also rename other useful columns
    rename_map = {}
    for old, new in [("trade", "price"), ("changepercent", "pct_change"),
                     ("turnoverratio", "turnover_rate"), ("per", "pe"),
                     ("mktcap", "total_mv"), ("nmc", "circ_mv"),
                     ("settlement", "pre_close"), ("pricechange", "change")]:
        if old in df.columns and new not in df.columns:
            rename_map[old] = new
    if rename_map:
        df = df.rename(columns=rename_map)

    # Ensure symbol is string
    df["symbol"] = df["symbol"].astype(str)

    # Filter: only main board (6/0/3开头), exclude ST
    df = df[df["symbol"].str.match(r"^(6|0|3)\d{5}$")]
    if "name" in df.columns:
        df = df[~df["name"].astype(str).str.contains("ST|退", na=False)]

    # Numeric columns
    for col in ["price", "pct_change", "turnover_rate", "pe", "pb"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Exclude suspended
    df = df[df["price"] > 0]
    df = df.reset_index(drop=True)
    logger.info(f"共 {len(df)} 只有效股票（排除ST/退市/停牌）")
    return df


def download_stock_daily(
    symbol: str,
    datalen: int,
    cache_dir: str,
) -> pd.DataFrame:
    """下载单只股票日K数据（新浪财经API）。
    
    datalen: 获取最近N个交易日的数据 (500 ≈ 2年)
    """
    cache_path = os.path.join(cache_dir, f"daily_{symbol}_{datalen}_days.parquet")

    # Check cache
    if os.path.exists(cache_path):
        try:
            df = pd.read_parquet(cache_path)
            if len(df) > 10:
                return df
        except Exception:
            pass

    prefix = _get_sina_prefix(symbol)
    url = (
        f"{KLINE_URL}?symbol={prefix}{symbol}"
        f"&scale=240&ma=no&datalen={datalen}"
    )

    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY)
            data = _curl_get_json(url)

            if not data or not isinstance(data, list):
                return pd.DataFrame()

            rows = []
            for item in data:
                rows.append({
                    "trade_date": item["day"].replace("-", ""),
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": float(item["volume"]),
                })

            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            # Derived columns
            df["pct_change"] = df["close"].pct_change() * 100
            df["amplitude"] = (df["high"] - df["low"]) / df["close"].shift(1) * 100
            df["change"] = df["close"] - df["close"].shift(1)
            df["symbol"] = symbol

            # Save cache
            os.makedirs(cache_dir, exist_ok=True)
            df.to_parquet(cache_path, index=False, engine="pyarrow")
            return df

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = (attempt + 1) * 3
                logger.warning(f"  {symbol} 请求失败 (尝试 {attempt+1}/{MAX_RETRIES}): {e}")
                time.sleep(wait)
            else:
                logger.warning(f"  {symbol} 下载失败（已重试{MAX_RETRIES}次）")
                return pd.DataFrame()


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"completed": [], "failed": []}


def save_progress(progress: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)


def build_daily_cross_sections(
    cache_dir: str,
    datalen: int,
    stock_list: pd.DataFrame,
) -> None:
    """从已下载的单股票数据构建每日全市场截面文件。"""
    logger.info("构建每日全市场截面文件...")

    all_data = []
    symbols = stock_list["symbol"].tolist()

    loaded = 0
    for i, symbol in enumerate(symbols):
        cache_path = os.path.join(cache_dir, f"daily_{symbol}_{datalen}_days.parquet")
        if not os.path.exists(cache_path):
            continue
        try:
            df = pd.read_parquet(cache_path)
            if not df.empty:
                all_data.append(df)
                loaded += 1
        except Exception:
            pass

        if (i + 1) % 500 == 0:
            logger.info(f"  已加载 {i+1}/{len(symbols)} 只股票...")

    if not all_data:
        logger.error("没有数据可构建截面文件！")
        return

    combined = pd.concat(all_data, ignore_index=True)
    logger.info(f"  合并数据: {len(combined):,} 条记录, {loaded} 只股票")

    dates = sorted(combined["trade_date"].unique())
    logger.info(f"  交易日范围: {dates[0]} ~ {dates[-1]}, 共 {len(dates)} 天")

    # Merge with current stock info
    info_cols = [c for c in ["symbol", "name", "pe", "pb", "total_mv", "circ_mv", "turnover_rate"] if c in stock_list.columns]
    if info_cols:
        stock_info = stock_list[info_cols].copy()
        rename_map = {}
        for c in ["total_mv", "circ_mv"]:
            if c in stock_info.columns:
                rename_map[c] = f"{c}_current"
        if rename_map:
            stock_info = stock_info.rename(columns=rename_map)

        for date in dates:
            day_data = combined[combined["trade_date"] == date].copy()
            day_data = day_data.merge(stock_info, on="symbol", how="left")
            output_path = os.path.join(cache_dir, f"daily_all_{date}.parquet")
            day_data.to_parquet(output_path, index=False, engine="pyarrow")
    else:
        for date in dates:
            day_data = combined[combined["trade_date"] == date].copy()
            output_path = os.path.join(cache_dir, f"daily_all_{date}.parquet")
            day_data.to_parquet(output_path, index=False, engine="pyarrow")

    logger.info(f"  已生成 {len(dates)} 个截面文件 (daily_all_YYYYMMDD.parquet)")


def main():
    parser = argparse.ArgumentParser(description="A股全市场数据下载 (新浪财经API)")
    parser.add_argument("--datalen", type=int, default=500, help="获取最近N个交易日数据 (500≈2年)")
    parser.add_argument("--skip-download", action="store_true", help="跳过下载，只构建截面文件")
    parser.add_argument("--skip-cross-section", action="store_true", help="跳过截面文件构建")
    parser.add_argument("--max-stocks", type=int, default=0, help="最大下载股票数（0=全部）")
    parser.add_argument("--resume", action="store_true", help="从上次进度继续")
    args = parser.parse_args()

    datalen = args.datalen

    print("=" * 70)
    print("  A股全市场数据下载 (新浪财经 API)")
    print(f"  数据量: 最近 {datalen} 个交易日 (≈{datalen//250}年)")
    print(f"  缓存目录: {CACHE_DIR}")
    print("=" * 70)

    os.makedirs(CACHE_DIR, exist_ok=True)

    # Step 1: Get stock list
    stock_list = get_all_stocks()

    if args.max_stocks > 0:
        stock_list = stock_list.head(args.max_stocks)
        logger.info(f"限制下载: {args.max_stocks} 只股票")

    symbols = stock_list["symbol"].tolist()

    # Step 2: Download daily data
    if not args.skip_download:
        progress = load_progress() if args.resume else {"completed": [], "failed": []}
        completed = set(progress["completed"])

        to_download = [s for s in symbols if s not in completed]
        logger.info(f"需要下载: {len(to_download)} 只股票（已完成: {len(completed)}）")

        success_count = len(completed)
        fail_count = len(progress["failed"])
        start_time = time.time()

        for i, symbol in enumerate(to_download):
            try:
                df = download_stock_daily(symbol, datalen, CACHE_DIR)
                if not df.empty:
                    success_count += 1
                    progress["completed"].append(symbol)
                else:
                    fail_count += 1
                    progress["failed"].append(symbol)
            except Exception as e:
                fail_count += 1
                progress["failed"].append(symbol)
                logger.warning(f"  {symbol} 异常: {e}")

            # Progress report
            if (i + 1) % 50 == 0:
                save_progress(progress)
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                remaining = (len(to_download) - i - 1) / rate if rate > 0 else 0
                logger.info(
                    f"  进度: {i+1}/{len(to_download)} "
                    f"({(i+1)/len(to_download)*100:.1f}%) | "
                    f"成功: {success_count} | 失败: {fail_count} | "
                    f"速率: {rate:.1f}只/秒 | 剩余: ~{remaining/60:.0f}分钟"
                )

            # Batch pause
            if (i + 1) % BATCH_SIZE == 0:
                logger.info(f"  === 暂停 {BATCH_PAUSE}秒 ===")
                save_progress(progress)
                time.sleep(BATCH_PAUSE)

        save_progress(progress)
        elapsed = time.time() - start_time
        logger.info(f"\n下载完成! 成功: {success_count}, 失败: {fail_count}, 耗时: {elapsed/60:.1f}分钟")

    # Step 3: Build cross-section files
    if not args.skip_cross_section:
        build_daily_cross_sections(CACHE_DIR, datalen, stock_list)

    # Step 4: Quality check
    print("\n" + "=" * 70)
    print("  数据质量检查")
    print("=" * 70)

    parquet_files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".parquet")]
    daily_files = [f for f in parquet_files if f.startswith("daily_") and not f.startswith("daily_all_")]
    cross_files = [f for f in parquet_files if f.startswith("daily_all_")]

    print(f"  单股票日K文件: {len(daily_files)}")
    print(f"  全市场截面文件: {len(cross_files)}")

    total_size = sum(os.path.getsize(os.path.join(CACHE_DIR, f)) for f in parquet_files)
    print(f"  磁盘占用: {total_size / 1024 / 1024:.0f} MB")

    if daily_files:
        sample = pd.read_parquet(os.path.join(CACHE_DIR, daily_files[0]))
        print(f"\n  样本 ({daily_files[0]}):")
        print(f"    行数: {len(sample)}, 列: {list(sample.columns)}")
        print(f"    日期: {sample['trade_date'].iloc[0]} ~ {sample['trade_date'].iloc[-1]}")

    if cross_files:
        sample_file = sorted(cross_files)[len(cross_files) // 2]
        sample_df = pd.read_parquet(os.path.join(CACHE_DIR, sample_file))
        sorted_cross = sorted(cross_files)
        print(f"\n  截面样本 ({sample_file}):")
        print(f"    股票数: {len(sample_df)}")
        print(f"    日期范围: {sorted_cross[0]} ~ {sorted_cross[-1]}")

    print("\n" + "=" * 70)
    print("  全部完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()