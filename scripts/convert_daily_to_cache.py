#!/usr/bin/env python3
"""
将 ~/.nautilus/ashare_data/daily/*.parquet 转换为
~/.nautilus/ashare_cache/daily_all_YYYYMMDD.parquet 格式，
供一夜持股法回测使用。

列名映射：
  pct_chg → pct_change
  vol     → volume

缺失列（来自 daily_basic）用 NaN 填充，回测脚本会跳过这些过滤条件。
"""

import os
import glob
import pandas as pd
import numpy as np

DAILY_DIR = os.path.expanduser("~/.nautilus/ashare_data/daily")
BASIC_DIR = os.path.expanduser("~/.nautilus/ashare_data/daily_basic")
CACHE_DIR = os.path.expanduser("~/.nautilus/ashare_cache")

os.makedirs(CACHE_DIR, exist_ok=True)


def main():
    daily_files = sorted(glob.glob(os.path.join(DAILY_DIR, "*.parquet")))
    print(f"找到 {len(daily_files)} 个 daily 文件")

    # 加载已有的 daily_basic 数据
    basic_data = {}
    basic_files = glob.glob(os.path.join(BASIC_DIR, "*.parquet"))
    for f in basic_files:
        date = os.path.basename(f).replace(".parquet", "")
        basic_data[date] = pd.read_parquet(f)
    print(f"找到 {len(basic_data)} 个 daily_basic 文件")

    converted = 0
    for f in daily_files:
        date = os.path.basename(f).replace(".parquet", "")
        cache_path = os.path.join(CACHE_DIR, f"daily_all_{date}.parquet")

        if os.path.exists(cache_path):
            converted += 1
            continue

        df = pd.read_parquet(f)

        # 重命名列
        rename_map = {
            "pct_chg": "pct_change",
            "vol": "volume",
        }
        df = df.rename(columns=rename_map)

        # 确保 amount 列是浮点数（单位：千元 → 保持原样，回测只用 pct_change）
        # 添加缺失列（如果 daily_basic 有就用，没有填 NaN）
        basic_cols = ["total_mv", "circ_mv", "turnover_rate", "volume_ratio", "pe", "pb"]
        for col in basic_cols:
            if col not in df.columns:
                df[col] = np.nan

        # 如果有 daily_basic 数据，合并进来
        if date in basic_data:
            bd = basic_data[date]
            if "symbol" in bd.columns:
                for col in basic_cols:
                    if col in bd.columns:
                        # 按 symbol 对齐
                        bd_subset = bd[["symbol", col]].drop_duplicates(subset="symbol")
                        df = df.drop(columns=[col], errors="ignore")
                        df = df.merge(bd_subset, on="symbol", how="left")

        df.to_parquet(cache_path, index=False, engine="pyarrow")
        converted += 1

        if converted % 100 == 0:
            print(f"  已转换 {converted}/{len(daily_files)}")

    print(f"\n完成！共转换 {converted} 个文件到 {CACHE_DIR}")

    # 验证
    sample_file = os.path.join(CACHE_DIR, f"daily_all_{os.path.basename(daily_files[-1]).replace('.parquet', '')}.parquet")
    if os.path.exists(sample_file):
        df = pd.read_parquet(sample_file)
        print(f"\n样本文件: {os.path.basename(sample_file)}")
        print(f"列: {list(df.columns)}")
        print(f"行数: {len(df)}")
        # 检查 daily_basic 列覆盖率
        for col in basic_cols:
            valid = df[col].notna().sum()
            print(f"  {col}: {valid}/{len(df)} ({valid/len(df)*100:.0f}%)")


if __name__ == "__main__":
    main()