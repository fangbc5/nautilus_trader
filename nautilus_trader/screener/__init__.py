# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener Module
# -------------------------------------------------------------------------------------------------
"""
Stock screening module for NautilusTrader.

Provides a flexible, factor-based stock screening framework that integrates
with the NautilusTrader backtest engine.

Quick Start
-----------
>>> from nautilus_trader.screener import ScreenerEngine, ScreenerConfig
>>> from nautilus_trader.screener.factors import PEFactor, VolumeBreakoutFactor
>>> config = ScreenerConfig(factors=[PEFactor(max=30), VolumeBreakoutFactor(ratio=1.5)])
>>> engine = ScreenerEngine(config)
>>> results = engine.run("2024-01-01")
"""

from nautilus_trader.screener.config import FactorConfig
from nautilus_trader.screener.config import ScreenerConfig
from nautilus_trader.screener.engine import ScreenerEngine
from nautilus_trader.screener.factors import Factor
from nautilus_trader.screener.factors import AIFactor
from nautilus_trader.screener.providers import CachedScreenerProvider
from nautilus_trader.screener.providers import DemoDataProvider
from nautilus_trader.screener.providers import LiveScreenerProvider
from nautilus_trader.screener.providers import ScreenerDataProvider
from nautilus_trader.screener.result import ScreeningResult
from nautilus_trader.screener.rotation_strategy import RotationConfig
from nautilus_trader.screener.rotation_strategy import RotationStrategy
from nautilus_trader.screener.strategies import ScreeningStrategy
from nautilus_trader.screener.strategies import compare_strategies
from nautilus_trader.screener.strategies import create_strategy
from nautilus_trader.screener.strategies import list_strategies


__all__ = [
    "AIFactor",
    "CachedScreenerProvider",
    "DemoDataProvider",
    "Factor",
    "FactorConfig",
    "LiveScreenerProvider",
    "RotationConfig",
    "RotationStrategy",
    "ScreenerConfig",
    "ScreenerDataProvider",
    "ScreenerEngine",
    "ScreeningResult",
    "ScreeningStrategy",
    "compare_strategies",
    "create_strategy",
    "list_strategies",
]
