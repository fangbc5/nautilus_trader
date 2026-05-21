# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener Configuration
# -------------------------------------------------------------------------------------------------
"""
Configuration for stock screening.
"""

from __future__ import annotations

from typing import Any

import msgspec

from nautilus_trader.common.config import NautilusConfig


class FactorConfig(NautilusConfig, frozen=True, kw_only=True):
    """
    Configuration for a single screening factor.

    Parameters
    ----------
    name : str
        Factor name (e.g. "pe", "roe", "volume_breakout").
    params : dict[str, Any], default {}
        Factor-specific parameters.
    weight : float, default 1.0
        Weight for composite scoring (0.0 to 1.0+).
    direction : str, default "ascending"
        Sort direction for ranking: "ascending" (lower is better) or "descending" (higher is better).

    """

    name: str
    params: dict[str, Any] = msgspec.field(default_factory=dict)
    weight: float = 1.0
    direction: str = "descending"  # "ascending" = lower is better (e.g. PE), "descending" = higher is better (e.g. ROE)


class UniverseConfig(NautilusConfig, frozen=True, kw_only=True):
    """
    Configuration for the stock universe to screen.

    Parameters
    ----------
    market : str, default "ashare"
        Market identifier (e.g. "ashare", "hk", "us").
    indices : list[str], default []
        Filter by index membership (e.g. ["000300.SH"] for CSI 300).
    exclude_st : bool, default True
        Exclude ST (Special Treatment) stocks.
    exclude_new : int, default 60
        Exclude stocks listed within N days (0 = don't exclude).
    min_market_cap : float | None, default None
        Minimum market cap in billions CNY.
    max_market_cap : float | None, default None
        Maximum market cap in billions CNY.

    """

    market: str = "ashare"
    indices: list[str] = []
    exclude_st: bool = True
    exclude_new: int = 60
    min_market_cap: float | None = None
    max_market_cap: float | None = None


class ScreenerConfig(NautilusConfig, frozen=True, kw_only=True):
    """
    Configuration for the stock screening engine.

    Parameters
    ----------
    universe : UniverseConfig
        Stock universe configuration.
    factors : list[FactorConfig]
        List of factor configurations for screening.
    top_n : int, default 20
        Number of top-ranked stocks to return.
    sort_by : str, default "composite_score"
        How to sort final results: "composite_score" or a factor name.
    min_score : float, default 0.0
        Minimum composite score to include (0.0 = no minimum).

    """

    universe: UniverseConfig = UniverseConfig()
    factors: list[FactorConfig] = []
    top_n: int = 20
    sort_by: str = "composite_score"
    min_score: float = 0.0