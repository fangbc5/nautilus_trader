# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener - Strategies Package
# -------------------------------------------------------------------------------------------------
"""
Screening strategies package.

Built-in strategies:
- "value"        : 价值策略
- "quality"      : 质量策略
- "growth"       : 成长策略
- "garp"         : GARP策略
- "dividend"     : 红利策略
- "momentum"     : 动量策略
- "all_weather"  : 全天候策略
- "overnight_hold": 一夜持股法（杨永兴）
"""

from __future__ import annotations

import pandas as pd

from nautilus_trader.screener.strategies.base import ScreeningStrategy
from nautilus_trader.screener.strategies.builtin import AllWeatherStrategy
from nautilus_trader.screener.strategies.builtin import DividendStrategy
from nautilus_trader.screener.strategies.builtin import GARPStrategy
from nautilus_trader.screener.strategies.builtin import GrowthStrategy
from nautilus_trader.screener.strategies.builtin import MomentumStrategy
from nautilus_trader.screener.strategies.builtin import QualityStrategy
from nautilus_trader.screener.strategies.builtin import ValueStrategy
from nautilus_trader.screener.strategies.overnight_hold import OvernightHoldScreener
from nautilus_trader.screener.result import ScreeningResult


# Strategy Registry
STRATEGY_REGISTRY: dict[str, type[ScreeningStrategy]] = {
    "value": ValueStrategy,
    "quality": QualityStrategy,
    "growth": GrowthStrategy,
    "garp": GARPStrategy,
    "dividend": DividendStrategy,
    "momentum": MomentumStrategy,
    "all_weather": AllWeatherStrategy,
    "overnight_hold": OvernightHoldScreener,
}


def create_strategy(name: str, top_n: int = 20, min_score: float = 0.0) -> ScreeningStrategy:
    """Create a screening strategy by name."""
    cls = STRATEGY_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown strategy '{name}'. Available: {list(STRATEGY_REGISTRY.keys())}")
    return cls(top_n=top_n, min_score=min_score)


def list_strategies() -> list[dict[str, str]]:
    """List all available strategies."""
    strategies = []
    for _name, cls in STRATEGY_REGISTRY.items():
        instance = cls(top_n=1)
        strategies.append({
            "name": instance.name,
            "display_name": instance.display_name,
            "description": instance.description,
        })
    return strategies


def compare_strategies(
    data: pd.DataFrame,
    strategy_names: list[str] | None = None,
    top_n: int = 5,
) -> dict[str, ScreeningResult]:
    """Run multiple strategies on the same data and compare results."""
    if strategy_names is None:
        strategy_names = list(STRATEGY_REGISTRY.keys())
    results = {}
    for name in strategy_names:
        strategy = create_strategy(name, top_n=top_n)
        results[name] = strategy.screen(data)
    return results


__all__ = [
    "ScreeningStrategy",
    "OvernightHoldScreener",
    "ValueStrategy",
    "QualityStrategy",
    "GrowthStrategy",
    "GARPStrategy",
    "DividendStrategy",
    "MomentumStrategy",
    "AllWeatherStrategy",
    "STRATEGY_REGISTRY",
    "create_strategy",
    "list_strategies",
    "compare_strategies",
]
