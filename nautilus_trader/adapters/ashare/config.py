#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Data Configuration
# -------------------------------------------------------------------------------------------------
"""
Configuration for A-Share data loading.
"""

import os


class AShareDataConfig:
    """
    A 股数据源配置。

    Parameters
    ----------
    source : str
        数据源，"tushare" 或 "akshare"
    adj_type : str
        复权类型，"qfq"(前复权)、"hfq"(后复权)、None(不复权)
    cache_enabled : bool
        是否启用 Parquet 本地缓存
    cache_dir : str
        缓存目录路径
    tushare_token : str, optional
        Tushare API token
    """

    def __init__(
        self,
        source: str = "tushare",
        adj_type: str = "qfq",
        cache_enabled: bool = True,
        cache_dir: str | None = None,
        tushare_token: str | None = None,
    ) -> None:
        self.source = source
        self.adj_type = adj_type
        self.cache_enabled = cache_enabled
        self.cache_dir = cache_dir or os.path.expanduser("~/.nautilus/ashare_cache")

        # Try loading token from env if not provided
        self.tushare_token = tushare_token or os.getenv("TUSHARE_TOKEN", "")
        if not self.tushare_token:
            env_path = os.path.join(os.getcwd(), ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("TUSHARE_TOKEN="):
                            self.tushare_token = line.split("=", 1)[1].strip()
                            break