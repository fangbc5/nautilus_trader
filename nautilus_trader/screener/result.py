# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener - Result
# -------------------------------------------------------------------------------------------------
"""
Screening result container.
"""

from __future__ import annotations

import pandas as pd


class ScreeningResult:
    """
    Container for stock screening results.
    """

    def __init__(self, data: pd.DataFrame) -> None:
        self._data = data

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def symbols(self) -> list[str]:
        if self._data.empty:
            return []
        return self._data.index.tolist()

    @property
    def top_10(self) -> pd.DataFrame:
        return self._data.head(10)

    @property
    def count(self) -> int:
        return len(self._data)

    @property
    def composite_scores(self) -> pd.Series:
        if "composite_score" not in self._data.columns:
            return pd.Series(dtype=float)
        return self._data["composite_score"]

    def top(self, n: int = 20) -> pd.DataFrame:
        return self._data.head(n)

    def __repr__(self) -> str:
        if self._data.empty:
            return "ScreeningResult(empty)"
        return f"ScreeningResult(count={self.count}, top={self.symbols[:5]}...)"

    def __len__(self) -> int:
        return self.count

    def __getitem__(self, key: str) -> pd.Series:
        return self._data[key]

    def to_string(self, max_rows: int = 30) -> str:
        if self._data.empty:
            return "No stocks passed screening criteria."
        display = self._data.head(max_rows)
        cols = [c for c in ["composite_score"] if c in display.columns]
        factor_cols = [c for c in display.columns if c.endswith("_score")]
        cols.extend(factor_cols[:5])
        with pd.option_context("display.max_rows", max_rows, "display.width", 200):
            return str(display[cols] if cols else display)
