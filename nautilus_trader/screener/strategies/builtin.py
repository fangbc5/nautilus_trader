# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener - Built-in Strategies
# -------------------------------------------------------------------------------------------------
"""Pre-built screening strategies: value, quality, growth, garp, dividend, momentum, all_weather."""

from __future__ import annotations

from typing import Any

from nautilus_trader.screener.config import FactorConfig
from nautilus_trader.screener.config import ScreenerConfig
from nautilus_trader.screener.strategies.base import ScreeningStrategy


class ValueStrategy(ScreeningStrategy):
    """价值策略：低PE、低PB、稳健ROE。"""
    @property
    def name(self) -> str: return "value"
    @property
    def display_name(self) -> str: return "价值策略"
    @property
    def description(self) -> str: return "选择低PE、低PB的股票，适合稳健投资者"
    def build_config(self, **kwargs: Any) -> ScreenerConfig:
        return ScreenerConfig(
            factors=[
                FactorConfig(name="pe", params={"max_pe": 25}, weight=1.5, direction="ascending"),
                FactorConfig(name="pb", params={"max_pb": 5}, weight=1.0, direction="ascending"),
                FactorConfig(name="roe", params={"min_roe": 8}, weight=0.8, direction="descending"),
            ],
            top_n=kwargs.get("top_n", self._top_n), min_score=kwargs.get("min_score", self._min_score), sort_by="composite_score",
        )

class QualityStrategy(ScreeningStrategy):
    """质量策略：高ROE优质公司。"""
    @property
    def name(self) -> str: return "quality"
    @property
    def display_name(self) -> str: return "质量策略"
    @property
    def description(self) -> str: return "选择高ROE、稳定盈利增长的优质公司"
    def build_config(self, **kwargs: Any) -> ScreenerConfig:
        return ScreenerConfig(
            factors=[
                FactorConfig(name="roe", params={"min_roe": 15}, weight=2.5, direction="descending"),
                FactorConfig(name="revenue_growth", params={"min_growth": -5}, weight=1.0, direction="descending"),
                FactorConfig(name="pe", params={"max_pe": 40}, weight=0.5, direction="ascending"),
            ],
            top_n=kwargs.get("top_n", self._top_n), min_score=kwargs.get("min_score", self._min_score), sort_by="composite_score",
        )

class GrowthStrategy(ScreeningStrategy):
    """成长策略：高增长公司。"""
    @property
    def name(self) -> str: return "growth"
    @property
    def display_name(self) -> str: return "成长策略"
    @property
    def description(self) -> str: return "选择营收高增长的公司，追求资本增值"
    def build_config(self, **kwargs: Any) -> ScreenerConfig:
        return ScreenerConfig(
            factors=[
                FactorConfig(name="revenue_growth", params={"min_growth": 10}, weight=2.5, direction="descending"),
                FactorConfig(name="roe", params={"min_roe": 10}, weight=1.0, direction="descending"),
                FactorConfig(name="pe", params={"max_pe": 60}, weight=0.3, direction="ascending"),
            ],
            top_n=kwargs.get("top_n", self._top_n), min_score=kwargs.get("min_score", self._min_score), sort_by="composite_score",
        )

class GARPStrategy(ScreeningStrategy):
    """GARP策略：合理价格成长。"""
    @property
    def name(self) -> str: return "garp"
    @property
    def display_name(self) -> str: return "GARP策略"
    @property
    def description(self) -> str: return "兼顾成长性与估值，选择增长良好且估值合理的股票"
    def build_config(self, **kwargs: Any) -> ScreenerConfig:
        return ScreenerConfig(
            factors=[
                FactorConfig(name="roe", params={"min_roe": 12}, weight=1.5, direction="descending"),
                FactorConfig(name="revenue_growth", params={"min_growth": 5}, weight=1.5, direction="descending"),
                FactorConfig(name="pe", params={"max_pe": 35}, weight=1.0, direction="ascending"),
                FactorConfig(name="pb", params={"max_pb": 8}, weight=0.5, direction="ascending"),
            ],
            top_n=kwargs.get("top_n", self._top_n), min_score=kwargs.get("min_score", self._min_score), sort_by="composite_score",
        )

class DividendStrategy(ScreeningStrategy):
    """红利策略：低估值高分红。"""
    @property
    def name(self) -> str: return "dividend"
    @property
    def display_name(self) -> str: return "红利策略"
    @property
    def description(self) -> str: return "选择低估值、高ROE的股票，偏重分红能力"
    def build_config(self, **kwargs: Any) -> ScreenerConfig:
        return ScreenerConfig(
            factors=[
                FactorConfig(name="pe", params={"max_pe": 15}, weight=1.5, direction="ascending"),
                FactorConfig(name="pb", params={"max_pb": 2}, weight=1.0, direction="ascending"),
                FactorConfig(name="roe", params={"min_roe": 10}, weight=1.5, direction="descending"),
            ],
            top_n=kwargs.get("top_n", self._top_n), min_score=kwargs.get("min_score", self._min_score), sort_by="composite_score",
        )

class MomentumStrategy(ScreeningStrategy):
    """动量策略：趋势追踪。"""
    @property
    def name(self) -> str: return "momentum"
    @property
    def display_name(self) -> str: return "动量策略"
    @property
    def description(self) -> str: return "追踪成交量突破和价格趋势，短线择时"
    def build_config(self, **kwargs: Any) -> ScreenerConfig:
        return ScreenerConfig(
            factors=[
                FactorConfig(name="volume_breakout", params={"ratio": 1.5}, weight=2.0, direction="descending"),
                FactorConfig(name="trend", params={"period": 20}, weight=1.5, direction="descending"),
                FactorConfig(name="roe", params={"min_roe": 5}, weight=0.5, direction="descending"),
            ],
            top_n=kwargs.get("top_n", self._top_n), min_score=kwargs.get("min_score", self._min_score), sort_by="composite_score",
        )

class AllWeatherStrategy(ScreeningStrategy):
    """全天候策略：多因子均衡。"""
    @property
    def name(self) -> str: return "all_weather"
    @property
    def display_name(self) -> str: return "全天候策略"
    @property
    def description(self) -> str: return "价值+质量+成长均衡配置，适合长期定投"
    def build_config(self, **kwargs: Any) -> ScreenerConfig:
        return ScreenerConfig(
            factors=[
                FactorConfig(name="pe", params={"max_pe": 40}, weight=1.0, direction="ascending"),
                FactorConfig(name="pb", params={"max_pb": 10}, weight=0.5, direction="ascending"),
                FactorConfig(name="roe", params={"min_roe": 12}, weight=1.5, direction="descending"),
                FactorConfig(name="revenue_growth", params={"min_growth": -10}, weight=1.0, direction="descending"),
            ],
            top_n=kwargs.get("top_n", self._top_n), min_score=kwargs.get("min_score", self._min_score), sort_by="composite_score",
        )
