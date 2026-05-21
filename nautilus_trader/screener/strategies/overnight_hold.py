# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener - Overnight Hold Strategy (杨永兴一夜持股法)
# -------------------------------------------------------------------------------------------------
"""
Overnight hold screening strategy (杨永兴一夜持股法 - 选股层).

Selects stocks at market close for next-morning sell.

Criteria:
- Late-day volume surge (量比 > 1.5)
- Late-day price surge (尾盘拉升 > 1%)
- Not at limit-up (涨幅 < 9.5%)
- Mid-small cap (流通市值 50-300亿)
- Reasonable turnover rate (换手率 2-15%)
"""

from __future__ import annotations

from typing import Any

from nautilus_trader.screener.config import FactorConfig
from nautilus_trader.screener.config import ScreenerConfig
from nautilus_trader.screener.strategies.base import ScreeningStrategy


class OvernightHoldScreener(ScreeningStrategy):
    """
    杨永兴一夜持股法 - 选股策略.

    尾盘选股，次日早盘卖出。筛选条件：
    - 尾盘放量拉升
    - 未涨停
    - 中小市值
    - 换手率适中
    """

    @property
    def name(self) -> str:
        return "overnight_hold"

    @property
    def display_name(self) -> str:
        return "一夜持股法"

    @property
    def description(self) -> str:
        return "杨永兴一夜持股法：尾盘放量拉升选股，次日早盘冲高卖出"

    def build_config(self, **kwargs: Any) -> ScreenerConfig:
        return ScreenerConfig(
            factors=[
                # 尾盘拉升因子（权重最高）
                FactorConfig(name="late_day_surge", params={"min_surge": 1.0}, weight=2.5, direction="descending"),
                # 尾盘放量因子
                FactorConfig(name="late_day_volume", params={"min_ratio": 1.5}, weight=2.0, direction="descending"),
                # 换手率因子
                FactorConfig(name="turnover_rate", params={"min_turnover": 2.0, "max_turnover": 15.0}, weight=1.0, direction="descending"),
                # 趋势因子（均线多头）
                FactorConfig(name="trend", params={"period": 20}, weight=0.5, direction="descending"),
            ],
            top_n=kwargs.get("top_n", self._top_n),
            min_score=kwargs.get("min_score", self._min_score),
            sort_by="composite_score",
        )
