# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener - Strategy Base Class
# -------------------------------------------------------------------------------------------------
"""Abstract base class for all screening strategies."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

import pandas as pd

from nautilus_trader.screener.config import FactorConfig
from nautilus_trader.screener.config import ScreenerConfig
from nautilus_trader.screener.engine import ScreenerEngine
from nautilus_trader.screener.result import ScreeningResult


class ScreeningStrategy(ABC):
    """
    Abstract base class for screening strategies.

    A strategy is a pre-configured combination of factors, weights, and filters.
    Subclasses define ``build_config()`` to specify their factor composition.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy identifier."""
        raise NotImplementedError

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable strategy name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Strategy description."""
        raise NotImplementedError

    @abstractmethod
    def build_config(self, **kwargs: Any) -> ScreenerConfig:
        """Build the ScreenerConfig for this strategy."""
        raise NotImplementedError

    def __init__(self, top_n: int = 20, min_score: float = 0.0) -> None:
        self._top_n = top_n
        self._min_score = min_score
        self._config = self.build_config(top_n=top_n, min_score=min_score)
        self._engine = ScreenerEngine(self._config)

    @property
    def config(self) -> ScreenerConfig:
        return self._config

    @property
    def factor_names(self) -> list[str]:
        return [f.name for f in self._config.factors]

    def screen(self, data: pd.DataFrame) -> ScreeningResult:
        """Run this strategy on stock data."""
        return self._engine.screen(data)

    def info(self) -> str:
        """Return strategy info string."""
        factors_str = ", ".join(f"{fc.name}(w={fc.weight})" for fc in self._config.factors)
        return (
            f"Strategy: {self.display_name} [{self.name}]\n"
            f"  {self.description}\n"
            f"  Factors: {factors_str}\n"
            f"  Top N: {self._top_n}"
        )
