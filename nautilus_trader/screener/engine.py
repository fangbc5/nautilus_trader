# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener - Engine
# -------------------------------------------------------------------------------------------------
"""
Core screening engine that orchestrates factor evaluation and ranking.
"""

from __future__ import annotations

import logging

import pandas as pd

from nautilus_trader.screener.config import FactorConfig
from nautilus_trader.screener.config import ScreenerConfig
from nautilus_trader.screener.factors import Factor
from nautilus_trader.screener.factors import create_factor
from nautilus_trader.screener.result import ScreeningResult

logger = logging.getLogger(__name__)


class ScreenerEngine:
    """
    Stock screening engine.

    Evaluates multiple factors on a universe of stocks, computes composite scores,
    and returns ranked results.
    """

    def __init__(self, config: ScreenerConfig | None = None) -> None:
        self._config = config or ScreenerConfig()
        self._factors: list[Factor] = []
        self._build_factors()

    @property
    def config(self) -> ScreenerConfig:
        return self._config

    @property
    def factors(self) -> list[Factor]:
        return self._factors

    def _build_factors(self) -> None:
        for fc in self._config.factors:
            factor = create_factor(fc.name, **fc.params)
            self._factors.append(factor)

    def add_factor(self, factor: Factor) -> None:
        self._factors.append(factor)

    def screen(self, data: pd.DataFrame) -> ScreeningResult:
        if data.empty:
            return ScreeningResult(pd.DataFrame())

        if not self._factors:
            return ScreeningResult(data)

        score_df = pd.DataFrame(index=data.index)
        score_df["composite_score"] = 0.0

        total_weight = sum(f.weight for f in self._factors)

        for factor in self._factors:
            scores = factor.score(data)
            if scores.empty:
                continue
            col_name = f"{factor.name}_score"
            score_df[col_name] = scores
            weighted = scores.fillna(0) * (factor.weight / total_weight)
            score_df["composite_score"] += weighted

        for col in data.columns:
            if col not in score_df.columns:
                score_df[col] = data[col]

        if self._config.min_score > 0:
            score_df = score_df[score_df["composite_score"] >= self._config.min_score]

        sort_col = self._config.sort_by if self._config.sort_by in score_df.columns else "composite_score"
        score_df = score_df.sort_values(by=sort_col, ascending=False)

        if self._config.top_n > 0:
            score_df = score_df.head(self._config.top_n)

        return ScreeningResult(score_df)
