#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Data Manager (Tushare Pro API)
# -------------------------------------------------------------------------------------------------
"""
A股数据管理器 —— 基础数据 + 行情数据 + 每日同步

数据源: Tushare Pro (https://tushare.pro)
存储:   Parquet文件 (按日期组织)

命令:
    python scripts/ashare_data_manager.py init          # 初始化：下载股票列表
    python scripts/ashare_data_manager.py backfill      # 历史回补：下载过去N天
    python scripts/ashare_data_manager.py sync          # 每日同步：更新最新数据
    python scripts/ashare_data_manager.py status        # 查看数据状态
    python scripts/ashare_data_manager.py test          # 快速测试

Tushare API频率（当前积分等级）:
    - stock_basic:  1次/小时   ← 慎用
    - trade_cal:    5次/天     ← 慎用
    - daily_basic:  5次/天     ← 每日sync用1次
    - daily:        200次/分钟 ← 主力接口！
    - adj_factor:   200次/分钟 ← 主力接口！

数据目录: ~/.nautilus/ashare_data/
├── stock_list.parquet          # 股票列表
├── trade_cal.parquet           # 交易日历
├── daily/                      # 每日全市场行情(OHLCV+复权因子)
│   ├── 20240102.parquet        # 每文件 ≈ 5500行
│   └── ...
└── daily_basic/                # 每日指标(PE/PB/市值/换手率)
    ├── 20240102.parquet
    └── ...
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import tushare as ts
from dotenv import load_dotenv

# ─── 配置 ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = os.path.expanduser("~/.nautilus/ashare_data")
DAILY_DIR = os.path.join(DATA_DIR, "daily")
BASIC_DIR = os.path.join(DATA_DIR, "daily_basic")

TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# 主板代码正则：6开头(沪), 0/3开头(深)
MAIN_BOARD = r"^(6|0|3)\d{5}$"


# ─── Tushare API ───────────────────────────────────────────────────────────
class TushareAPI:
    """Tushare Pro API封装，带限频和重试。"""

    def __init__(self, token: str):
        if not token:
            raise ValueError("TUSHARE_TOKEN 未设置！请在 .env 中配置。")
        ts.set_token(token)
        self.pro = ts.pro_api()
        self._last_call = 0.0
        self._min_interval = 0.35  # 最小调用间隔

    def _rate_limit(self):
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()

    def call(self, api_name: str, max_retries: int = 3, wait_on_limit: int = 65, **kwargs) -> pd.DataFrame:
        """调用Tushare接口。"""
        func = getattr(self.pro, api_name)
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                df = func(**kwargs)
                return df if df is not None else pd.DataFrame()
            except Exception as e:
                msg = str(e)
                if "频率超限" in msg or "超限" in msg:
                    log.warning(f"  频率超限({api_name}), 等待{wait_on_limit}s... [{attempt+1}/{max_retries}]")
                    time.sleep(wait_on_limit)
                elif attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 3)
                else:
                    raise
        return pd.DataFrame()


# ─── 数据管理器 ─────────────────────────────────────────────────────────────
class AShareDataManager:
    def __init__(self):
        self.api = TushareAPI(TUSHARE_TOKEN)
        os.makedirs(DAILY_DIR, exist_ok=True)
        os.makedirs(BASIC_DIR, exist_ok=True)

    # ── 基础数据 ────────────────────────────────────────────────────────

    def init_stock_list(self):
        """下载股票列表。优先用stock_basic，超限则从daily()推断。"""
        path = os.path.join(DATA_DIR, "stock_list.parquet")
        if os.path.exists(path):
            existing = pd.read_parquet(path)
            if len(existing) > 1000:
                log.info(f"股票列表已存在({len(existing)}只)，跳过。如需更新请先删除 {path}")
                return

        log.info("下载股票列表...")
        try:
            df = self.api.call(
                "stock_basic", max_retries=1,
                exchange="", list_status="L",
                fields="ts_code,symbol,name,area,industry,market,list_date",
            )
            if not df.empty:
                df = df[df["symbol"].str.match(MAIN_BOARD)].copy()
                df = df.sort_values("symbol").reset_index(drop=True)
                df.to_parquet(path, index=False, engine="pyarrow")
                log.info(f"  ✓ 保存 {len(df)} 只股票")
                return
        except Exception as e:
            log.warning(f"  stock_basic失败: {e}")

        # Fallback: 从最新一天daily数据推断
        log.info("  回退：从最新日K线数据推断股票列表...")
        self._build_stock_list_from_daily(path)

    def _build_stock_list_from_daily(self, path: str):
        """从daily文件构建股票列表（无需API调用）。"""
        daily_files = sorted(f for f in os.listdir(DAILY_DIR) if f.endswith(".parquet"))
        if not daily_files:
            log.error("  无daily数据！请先运行 backfill 或 init")
            return

        latest = pd.read_parquet(os.path.join(DAILY_DIR, daily_files[-1]))
        if "ts_code" in latest.columns:
            stock_list = latest[["ts_code"]].copy()
            stock_list["symbol"] = stock_list["ts_code"].str[:6]
            stock_list["name"] = ""
            stock_list["industry"] = ""
            stock_list["list_date"] = ""
            stock_list = stock_list[["ts_code", "symbol", "name", "industry", "list_date"]]
        elif "symbol" in latest.columns:
            stock_list = latest[["symbol"]].copy()
            stock_list["ts_code"] = stock_list["symbol"].apply(
                lambda s: f"{s}.SH" if s.startswith("6") else f"{s}.SZ"
            )
            stock_list["name"] = ""
            stock_list["industry"] = ""
            stock_list["list_date"] = ""
        else:
            log.error("  daily文件格式不符")
            return

        stock_list.to_parquet(path, index=False, engine="pyarrow")
        log.info(f"  ✓ 从daily数据构建 {len(stock_list)} 只股票")

    def init_trade_calendar(self):
        """下载交易日历。超限则从已有数据推断。"""
        path = os.path.join(DATA_DIR, "trade_cal.parquet")
        if os.path.exists(path):
            existing = pd.read_parquet(path)
            if len(existing) > 100:
                log.info(f"交易日历已存在({len(existing)}天)，跳过。")
                return

        log.info("下载交易日历...")
        try:
            df = self.api.call(
                "trade_cal", max_retries=1,
                exchange="SSE", start_date="20200101", end_date="20271231", is_open="1",
            )
            if not df.empty:
                df.to_parquet(path, index=False, engine="pyarrow")
                log.info(f"  ✓ 保存 {len(df)} 个交易日")
                return
        except Exception as e:
            log.warning(f"  trade_cal失败: {e}")

        # Fallback: 从daily文件推断
        log.info("  回退：从已有daily数据推断交易日历...")
        daily_files = sorted(f.replace(".parquet", "") for f in os.listdir(DAILY_DIR) if f.endswith(".parquet"))
        if daily_files:
            cal = pd.DataFrame({"cal_date": daily_files})
            cal.to_parquet(path, index=False, engine="pyarrow")
            log.info(f"  ✓ 从daily数据推断 {len(cal)} 个交易日")
        else:
            log.warning("  无daily数据，将在backfill时自动推断")

    def load_trade_dates(self) -> list[str]:
        """加载交易日列表。"""
        path = os.path.join(DATA_DIR, "trade_cal.parquet")
        if os.path.exists(path):
            cal = pd.read_parquet(path)
            return cal["cal_date"].astype(str).tolist()
        # fallback: 从daily文件名
        return sorted(f.replace(".parquet", "") for f in os.listdir(DAILY_DIR) if f.endswith(".parquet"))

    def get_trade_dates_between(self, start: str, end: str) -> list[str]:
        dates = self.load_trade_dates()
        return [d for d in dates if start <= d <= end]

    # ── 行情数据 ────────────────────────────────────────────────────────

    def download_daily(self, trade_date: str, include_adj: bool = True) -> pd.DataFrame:
        """下载单日全市场行情(OHLCV + 可选复权因子)。"""
        # 1) 日K线 (主力接口，200次/分钟)
        df = self.api.call("daily", trade_date=trade_date)
        if df.empty:
            return pd.DataFrame()

        df["symbol"] = df["ts_code"].str[:6]
        df = df[df["symbol"].str.match(MAIN_BOARD)].copy()

        # 2) 复权因子 (可选，某些积分等级限频)
        if include_adj:
            try:
                adj = self.api.call("adj_factor", trade_date=trade_date, max_retries=1)
                if not adj.empty:
                    adj["symbol"] = adj["ts_code"].str[:6]
                    df = df.merge(adj[["symbol", "adj_factor"]], on="symbol", how="left")
            except Exception as e:
                log.debug(f"  adj_factor({trade_date})跳过: {e}")

        # 保存
        path = os.path.join(DAILY_DIR, f"{trade_date}.parquet")
        df.to_parquet(path, index=False, engine="pyarrow")
        return df

    def download_daily_basic(self, trade_date: str) -> pd.DataFrame:
        """下载每日指标(PE/PB/市值)。注意：限5次/天！超限快速跳过。"""
        df = self.api.call(
            "daily_basic", max_retries=1, wait_on_limit=5,
            trade_date=trade_date,
            fields="ts_code,trade_date,close,turnover_rate,volume_ratio,pe,pb,total_mv,circ_mv",
        )
        if df.empty:
            return pd.DataFrame()

        df["symbol"] = df["ts_code"].str[:6]
        df = df[df["symbol"].str.match(MAIN_BOARD)].copy()

        path = os.path.join(BASIC_DIR, f"{trade_date}.parquet")
        df.to_parquet(path, index=False, engine="pyarrow")
        return df

    # ── 命令 ────────────────────────────────────────────────────────────

    def cmd_init(self):
        """初始化：股票列表 + 交易日历。"""
        print("=" * 60)
        print("  A股数据初始化 (Tushare Pro)")
        print("=" * 60)

        self.init_stock_list()
        self.init_trade_calendar()

        # 如果都没有交易日历但有daily接口，生成近2年日历
        cal_path = os.path.join(DATA_DIR, "trade_cal.parquet")
        if not os.path.exists(cal_path):
            log.info("生成近2年交易日历(用daily接口验证)...")
            self._generate_trade_calendar_via_daily()

        self.cmd_status()

    def _generate_trade_calendar_via_daily(self):
        """通过尝试调用daily接口来探测交易日（用于没有trade_cal权限的情况）。"""
        # 中国A股大约每年250个交易日
        # 周末/节假日不交易
        # 策略：逐日调用daily，非空=交易日（太慢，不适合大量）
        # 更好：假设已有部分数据，直接从文件名推断
        daily_files = sorted(f.replace(".parquet", "") for f in os.listdir(DAILY_DIR) if f.endswith(".parquet"))
        if len(daily_files) > 10:
            cal = pd.DataFrame({"cal_date": daily_files})
            path = os.path.join(DATA_DIR, "trade_cal.parquet")
            cal.to_parquet(path, index=False, engine="pyarrow")
            log.info(f"  从已有{len(daily_files)}个daily文件生成交易日历")

    def cmd_backfill(self, days: int = 500, include_basic: bool = False):
        """历史回补。"""
        # 确保有交易日历
        cal_path = os.path.join(DATA_DIR, "trade_cal.parquet")
        if not os.path.exists(cal_path):
            log.info("无交易日历，先用daily接口快速探测...")
            self._fast_probe_trade_calendar(days)

        trade_dates = self.load_trade_dates()
        if not trade_dates:
            log.error("无交易日历！请先运行 init。")
            return

        target_dates = trade_dates[-days:]

        # 已有的跳过
        existing = set(f.replace(".parquet", "") for f in os.listdir(DAILY_DIR) if f.endswith(".parquet"))
        to_download = [d for d in target_dates if d not in existing]

        log.info(f"历史回补: 目标{len(target_dates)}天, 已有{len(existing)}天, 待下载{len(to_download)}天")

        success, failed = 0, 0
        t0 = time.time()
        basic_count = 0

        for i, date in enumerate(to_download):
            try:
                df = self.download_daily(date, include_adj=False)
                if not df.empty:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                log.warning(f"  {date}: {e}")

            # daily_basic (限5次/天)
            if include_basic and basic_count < 4:
                try:
                    self.download_daily_basic(date)
                    basic_count += 1
                except Exception:
                    pass

            # 进度
            if (i + 1) % 50 == 0 or (i + 1) == len(to_download):
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed if elapsed > 0 else 1
                remaining = (len(to_download) - i - 1) / rate / 60
                log.info(
                    f"  {i+1}/{len(to_download)} ({(i+1)/len(to_download)*100:.0f}%) "
                    f"| 成功:{success} 失败:{failed} | {rate:.1f}天/秒 | ~{remaining:.0f}分钟"
                )

        elapsed = time.time() - t0
        log.info(f"\n回补完成! 成功:{success}, 失败:{failed}, 耗时:{elapsed/60:.1f}分钟, daily_basic:{basic_count}天")

        # 更新股票列表（如果还没有）
        stock_path = os.path.join(DATA_DIR, "stock_list.parquet")
        if not os.path.exists(stock_path):
            self._build_stock_list_from_daily(stock_path)

    def _fast_probe_trade_calendar(self, days: int):
        """快速探测交易日历（调用daily接口，空=非交易日）。
        策略：跳过周末，只探测工作日。
        """
        log.info(f"探测最近{days}天的交易日历(跳过周末)...")
        today = datetime.now()
        trade_dates = []

        # 逐日探测（跳过周末）
        for i in range(int(days * 1.8), 0, -1):
            d = today - timedelta(days=i)
            if d.weekday() >= 5:  # 跳过周末
                continue
            date_str = d.strftime("%Y%m%d")
            # 检查是否已有
            fpath = os.path.join(DAILY_DIR, f"{date_str}.parquet")
            if os.path.exists(fpath):
                trade_dates.append(date_str)
                continue
            # 尝试调用
            try:
                df = self.api.call("daily", trade_date=date_str, max_retries=1)
                if not df.empty:
                    trade_dates.append(date_str)
                    # 顺便保存
                    df["symbol"] = df["ts_code"].str[:6]
                    df = df[df["symbol"].str.match(MAIN_BOARD)].copy()
                    df.to_parquet(fpath, index=False, engine="pyarrow")
            except Exception:
                pass
            time.sleep(0.35)

        if trade_dates:
            cal = pd.DataFrame({"cal_date": sorted(trade_dates)})
            cal.to_parquet(os.path.join(DATA_DIR, "trade_cal.parquet"), index=False, engine="pyarrow")
            log.info(f"  探测到 {len(trade_dates)} 个交易日")

    def cmd_sync(self):
        """每日同步：更新最新交易日数据。"""
        today = datetime.now().strftime("%Y%m%d")
        log.info(f"每日同步 {today}...")

        # 检查是否已存在
        if os.path.exists(os.path.join(DAILY_DIR, f"{today}.parquet")):
            log.info(f"  {today} 数据已存在，跳过。")
            return

        df = self.download_daily(today)
        if df.empty:
            log.warning("  未获取到数据（可能非交易日或盘中）")
            return
        log.info(f"  ✓ 行情: {len(df)} 只股票")

        # daily_basic (用1次/5的配额)
        try:
            df_b = self.download_daily_basic(today)
            log.info(f"  ✓ 指标: {len(df_b)} 只股票")
        except Exception as e:
            log.info(f"  指标: 跳过 ({e})")

        # 更新交易日历
        cal_dates = self.load_trade_dates()
        if today not in cal_dates:
            cal_dates.append(today)
            pd.DataFrame({"cal_date": sorted(cal_dates)}).to_parquet(
                os.path.join(DATA_DIR, "trade_cal.parquet"), index=False, engine="pyarrow"
            )

        log.info("同步完成! ✓")

    def cmd_status(self):
        """显示数据状态。"""
        print("\n" + "=" * 60)
        print("  A股数据状态 (Tushare Pro)")
        print("=" * 60)

        # 股票列表
        sp = os.path.join(DATA_DIR, "stock_list.parquet")
        if os.path.exists(sp):
            sl = pd.read_parquet(sp)
            print(f"  股票列表:   {len(sl)} 只", end="")
            if "industry" in sl.columns and sl["industry"].notna().any():
                print(f" ({sl['industry'].nunique()} 个行业)")
            else:
                print()
        else:
            print("  股票列表:   ❌ 未初始化")

        # 交易日历
        cp = os.path.join(DATA_DIR, "trade_cal.parquet")
        if os.path.exists(cp):
            cal = pd.read_parquet(cp)
            dates = cal["cal_date"].astype(str).tolist()
            print(f"  交易日历:   {len(dates)} 天 ({dates[0]} ~ {dates[-1]})")
        else:
            print("  交易日历:   ❌ 未初始化")

        # 行情数据
        df_files = sorted(f for f in os.listdir(DAILY_DIR) if f.endswith(".parquet"))
        if df_files:
            first, last = df_files[0].replace(".parquet", ""), df_files[-1].replace(".parquet", "")
            print(f"  行情数据:   {len(df_files)} 天 ({first} ~ {last})")
            sample = pd.read_parquet(os.path.join(DAILY_DIR, df_files[-1]))
            print(f"  最新日股票: {len(sample)} 只")
            print(f"  行情列:     {list(sample.columns)}")
        else:
            print("  行情数据:   ❌ 无数据")

        # 每日指标
        bf_files = sorted(f for f in os.listdir(BASIC_DIR) if f.endswith(".parquet"))
        if bf_files:
            first, last = bf_files[0].replace(".parquet", ""), bf_files[-1].replace(".parquet", "")
            print(f"  每日指标:   {len(bf_files)} 天 ({first} ~ {last})")
        else:
            print("  每日指标:   ❌ 无数据")

        # 磁盘
        total = sum(
            os.path.getsize(os.path.join(root, f))
            for root, _, files in os.walk(DATA_DIR)
            for f in files
        )
        print(f"  磁盘占用:   {total / 1024 / 1024:.0f} MB")
        print("=" * 60)

    def cmd_test(self):
        """快速测试：下载最近3天数据。"""
        log.info("=== 快速测试 ===")

        # 1. 下载最近3天
        today = datetime.now()
        dates_downloaded = []
        for i in range(14):  # 往前找14天确保找到3个交易日
            d = today - timedelta(days=i)
            if d.weekday() >= 5:
                continue
            date_str = d.strftime("%Y%m%d")
            fpath = os.path.join(DAILY_DIR, f"{date_str}.parquet")
            if os.path.exists(fpath):
                log.info(f"  {date_str}: 已存在，跳过")
                dates_downloaded.append(date_str)
                continue

            try:
                df = self.download_daily(date_str, include_adj=False)
                if not df.empty:
                    dates_downloaded.append(date_str)
                    log.info(f"  ✓ {date_str}: {len(df)} 只股票, 列={list(df.columns)}")
                else:
                    log.info(f"  - {date_str}: 非交易日")
            except Exception as e:
                log.warning(f"  ✗ {date_str}: {e}")

            if len(dates_downloaded) >= 3:
                break
            time.sleep(0.5)

        # 2. 尝试daily_basic (1次)
        if dates_downloaded:
            try:
                df_b = self.download_daily_basic(dates_downloaded[0])
                if not df_b.empty:
                    log.info(f"  ✓ 指标({dates_downloaded[0]}): {len(df_b)} 只, 列={list(df_b.columns)}")
            except Exception as e:
                log.warning(f"  指标: {e}")

        # 3. 生成stock_list和trade_cal
        self._build_stock_list_from_daily(os.path.join(DATA_DIR, "stock_list.parquet"))
        cal_dates = self.load_trade_dates()
        new_dates = sorted(set(cal_dates + dates_downloaded))
        pd.DataFrame({"cal_date": new_dates}).to_parquet(
            os.path.join(DATA_DIR, "trade_cal.parquet"), index=False, engine="pyarrow"
        )

        log.info("=== 测试完成 ===")
        self.cmd_status()


# ─── CLI ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="A股数据管理器 (Tushare Pro)")
    parser.add_argument("command", choices=["init", "backfill", "sync", "status", "test"],
                        help="init=初始化 | backfill=历史回补 | sync=每日同步 | status=状态 | test=测试")
    parser.add_argument("--days", type=int, default=500, help="回补天数 (默认500≈2年)")
    parser.add_argument("--with-basic", action="store_true", help="回补时下载daily_basic (限5次/天)")
    args = parser.parse_args()

    mgr = AShareDataManager()

    {"init": mgr.cmd_init, "backfill": lambda: mgr.cmd_backfill(args.days, args.with_basic),
     "sync": mgr.cmd_sync, "status": mgr.cmd_status, "test": mgr.cmd_test}[args.command]()


if __name__ == "__main__":
    main()