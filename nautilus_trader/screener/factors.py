# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener - Factor Library
# -------------------------------------------------------------------------------------------------
"""
Built-in screening factors for stock selection.

Factors are the building blocks of the screener. Each factor evaluates a single
dimension of a stock (e.g. valuation, quality, momentum) and produces a score.

Built-in factors:
- PEFactor: Price-to-Earnings ratio (valuation)
- PBFactor: Price-to-Book ratio (valuation)
- ROEFactor: Return on Equity (quality)
- RevenueGrowthFactor: Revenue growth rate (growth)
- VolumeBreakoutFactor: Volume breakout (technical)
- TrendFactor: Moving average trend (technical)
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

import pandas as pd


class Factor(ABC):
    """
    Abstract base class for screening factors.

    Subclasses must implement ``evaluate()`` which receives a DataFrame of stock data
    and returns a Series of factor scores (float, 0-100 scale).

    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Factor identifier name."""
        raise NotImplementedError

    @property
    def direction(self) -> str:
        """
        Sort direction for ranking.

        - "ascending": lower values are better (e.g. PE - cheaper is better)
        - "descending": higher values are better (e.g. ROE - higher is better)
        """
        return "descending"

    @property
    def weight(self) -> float:
        """Weight for composite scoring."""
        return 1.0

    @abstractmethod
    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        """
        Evaluate factor for all stocks.

        Parameters
        ----------
        data : pd.DataFrame
            Stock data with columns depending on the factor.
            Index is typically stock symbols.

        Returns
        -------
        pd.Series
            Factor values indexed by stock symbol.

        """
        raise NotImplementedError

    def score(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate normalized scores (0-100) for all stocks.

        Higher score = better. The direction of the raw values is handled automatically.
        """
        raw = self.evaluate(data)
        if raw.empty:
            return raw

        if self.direction == "ascending":
            ranks = raw.rank(ascending=True, pct=True)
        else:
            ranks = raw.rank(ascending=False, pct=True)

        scores = ranks * 100
        return scores


class PEFactor(Factor):
    """Price-to-Earnings ratio factor. Lower PE = cheaper valuation."""

    def __init__(self, min_pe: float = 0, max_pe: float = 100, weight: float = 1.0) -> None:
        self.min_pe = min_pe
        self.max_pe = max_pe
        self._weight = weight

    @property
    def name(self) -> str:
        return "pe"

    @property
    def direction(self) -> str:
        return "ascending"

    @property
    def weight(self) -> float:
        return self._weight

    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        if "pe" not in data.columns:
            return pd.Series(dtype=float)
        pe = data["pe"].clip(lower=self.min_pe, upper=self.max_pe)
        return pe


class PBFactor(Factor):
    """Price-to-Book ratio factor. Lower PB = cheaper valuation."""

    def __init__(self, min_pb: float = 0, max_pb: float = 20, weight: float = 1.0) -> None:
        self.min_pb = min_pb
        self.max_pb = max_pb
        self._weight = weight

    @property
    def name(self) -> str:
        return "pb"

    @property
    def direction(self) -> str:
        return "ascending"

    @property
    def weight(self) -> float:
        return self._weight

    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        if "pb" not in data.columns:
            return pd.Series(dtype=float)
        pb = data["pb"].clip(lower=self.min_pb, upper=self.max_pb)
        return pb


class ROEFactor(Factor):
    """Return on Equity factor. Higher ROE = better profitability."""

    def __init__(self, min_roe: float = 0, weight: float = 1.0) -> None:
        self.min_roe = min_roe
        self._weight = weight

    @property
    def name(self) -> str:
        return "roe"

    @property
    def direction(self) -> str:
        return "descending"

    @property
    def weight(self) -> float:
        return self._weight

    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        if "roe" not in data.columns:
            return pd.Series(dtype=float)
        roe = data["roe"].where(data["roe"] >= self.min_roe, other=float("nan"))
        return roe


class RevenueGrowthFactor(Factor):
    """Revenue growth rate factor. Higher growth = better."""

    def __init__(self, min_growth: float = -100, weight: float = 1.0) -> None:
        self.min_growth = min_growth
        self._weight = weight

    @property
    def name(self) -> str:
        return "revenue_growth"

    @property
    def direction(self) -> str:
        return "descending"

    @property
    def weight(self) -> float:
        return self._weight

    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        col = "revenue_growth" if "revenue_growth" in data.columns else "yoy_revenue"
        if col not in data.columns:
            return pd.Series(dtype=float)
        return data[col].where(data[col] >= self.min_growth, other=float("nan"))


class VolumeBreakoutFactor(Factor):
    """Volume breakout factor. Higher volume ratio = more interest."""

    def __init__(self, ratio: float = 1.5, avg_period: int = 20, weight: float = 1.0) -> None:
        self.ratio = ratio
        self.avg_period = avg_period
        self._weight = weight

    @property
    def name(self) -> str:
        return "volume_breakout"

    @property
    def direction(self) -> str:
        return "descending"

    @property
    def weight(self) -> float:
        return self._weight

    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        vol_col = "volume_ratio" if "volume_ratio" in data.columns else "vol_ratio"
        if vol_col in data.columns:
            return data[vol_col].copy()
        return pd.Series(dtype=float)


class TrendFactor(Factor):
    """Moving average trend factor. Higher trend score = stronger uptrend."""

    def __init__(self, period: int = 20, weight: float = 1.0) -> None:
        self.period = period
        self._weight = weight

    @property
    def name(self) -> str:
        return f"trend_ma{self.period}"

    @property
    def direction(self) -> str:
        return "descending"

    @property
    def weight(self) -> float:
        return self._weight

    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        col = f"trend_ma{self.period}" if f"trend_ma{self.period}" in data.columns else "trend_score"
        if col in data.columns:
            return data[col].copy()
        return pd.Series(dtype=float)


class LateDaySurgeFactor(Factor):
    """
    尾盘拉升因子 (杨永兴一夜持股法核心因子).

    Measures the price surge in the last 30 minutes of trading (14:30-15:00).
    Higher surge = stronger buying pressure at close.
    """

    def __init__(self, min_surge: float = 0.0, weight: float = 1.0) -> None:
        self.min_surge = min_surge
        self._weight = weight

    @property
    def name(self) -> str:
        return "late_day_surge"

    @property
    def direction(self) -> str:
        return "descending"

    @property
    def weight(self) -> float:
        return self._weight

    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        col = "late_day_surge" if "late_day_surge" in data.columns else "pm_surge_pct"
        if col not in data.columns:
            return pd.Series(dtype=float)
        return data[col].where(data[col] >= self.min_surge, other=float("nan"))


class LateDayVolumeFactor(Factor):
    """
    尾盘放量因子 (杨永兴一夜持股法).

    Measures the volume ratio in the last 30 minutes vs average.
    Higher ratio = more institutional activity at close.
    """

    def __init__(self, min_ratio: float = 1.0, weight: float = 1.0) -> None:
        self.min_ratio = min_ratio
        self._weight = weight

    @property
    def name(self) -> str:
        return "late_day_volume"

    @property
    def direction(self) -> str:
        return "descending"

    @property
    def weight(self) -> float:
        return self._weight

    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        col = "late_day_volume" if "late_day_volume" in data.columns else "pm_vol_ratio"
        if col not in data.columns:
            return pd.Series(dtype=float)
        return data[col].where(data[col] >= self.min_ratio, other=float("nan"))


class TurnoverRateFactor(Factor):
    """
    换手率因子.

    Measures the daily turnover rate. Moderate turnover preferred for overnight hold.
    """

    def __init__(self, min_turnover: float = 0.0, max_turnover: float = 100.0, weight: float = 1.0) -> None:
        self.min_turnover = min_turnover
        self.max_turnover = max_turnover
        self._weight = weight

    @property
    def name(self) -> str:
        return "turnover_rate"

    @property
    def direction(self) -> str:
        return "descending"

    @property
    def weight(self) -> float:
        return self._weight

    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        if "turnover_rate" not in data.columns:
            return pd.Series(dtype=float)
        tr = data["turnover_rate"]
        # Filter to range, score middle of range highest
        mask = (tr >= self.min_turnover) & (tr <= self.max_turnover)
        return tr.where(mask, other=float("nan"))


class AIFactor(Factor):
    """
    AI/ML factor base class for integrating machine learning models.

    Subclass this to create factors powered by:
    - scikit-learn models (XGBoost, LightGBM, etc.)
    - PyTorch / TensorFlow neural networks
    - LLM-based analysis (sentiment, fundamentals)
    - Any Python ML framework

    Usage
    -----
    >>> class MyXGBoostFactor(AIFactor):
    ...     def __init__(self, model_path="model.json"):
    ...         self._model = xgboost.Booster()
    ...         self._model.load_model(model_path)
    ...
    ...     @property
    ...     def name(self) -> str:
    ...         return "xgboost_alpha"
    ...
    ...     def evaluate(self, data: pd.DataFrame) -> pd.Series:
    ...         features = self._prepare_features(data)
    ...         predictions = self._model.predict(xgb.DMatrix(features))
    ...         return pd.Series(predictions, index=data.index)
    ...
    ...     def _prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
    ...         return data[["pe", "pb", "roe", "revenue_growth"]].fillna(0)
    """

    @property
    def name(self) -> str:
        return "ai_factor"

    @property
    def direction(self) -> str:
        return "descending"  # Higher AI score = better

    def evaluate(self, data: pd.DataFrame) -> pd.Series:
        """
        Evaluate AI factor.

        Override this method to integrate your ML model.

        Parameters
        ----------
        data : pd.DataFrame
            Stock data with fundamental/technical columns.

        Returns
        -------
        pd.Series
            AI model predictions/scores indexed by stock symbol.
        """
        raise NotImplementedError(
            "Subclass AIFactor and implement evaluate() with your ML model. "
            "Example: return pd.Series(model.predict(features), index=data.index)"
        )

    def train(self, data: pd.DataFrame, labels: pd.Series) -> None:
        """
        Train the AI model (optional).

        Override to implement model training logic.

        Parameters
        ----------
        data : pd.DataFrame
            Training features.
        labels : pd.Series
            Target labels (e.g. future returns).
        """
        raise NotImplementedError("Override train() to implement model training")

    def save(self, path: str) -> None:
        """Save model to disk (optional)."""
        raise NotImplementedError("Override save() to persist model")

    def load_model(self, path: str) -> None:
        """Load model from disk (optional)."""
        raise NotImplementedError("Override load_model() to restore model")


# Factor Registry
FACTOR_REGISTRY: dict[str, type[Factor]] = {
    "pe": PEFactor,
    "pb": PBFactor,
    "roe": ROEFactor,
    "revenue_growth": RevenueGrowthFactor,
    "volume_breakout": VolumeBreakoutFactor,
    "trend": TrendFactor,
    "late_day_surge": LateDaySurgeFactor,
    "late_day_volume": LateDayVolumeFactor,
    "turnover_rate": TurnoverRateFactor,
    "ai": AIFactor,
}


def create_factor(name: str, **params: Any) -> Factor:
    """Create a factor instance by name."""
    cls = FACTOR_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown factor '{name}'. Available: {list(FACTOR_REGISTRY.keys())}")
    return cls(**params)