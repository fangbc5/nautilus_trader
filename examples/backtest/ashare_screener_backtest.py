#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Screener + Backtest Integration Demo
# -------------------------------------------------------------------------------------------------
"""
Demonstrates how to use the stock screener to select stocks,
then run EMA cross backtests on the selected stocks.

Usage:
    python -m examples.backtest.ashare_screener_backtest
"""

import pandas as pd

from nautilus_trader.screener import ScreenerEngine
from nautilus_trader.screener.config import FactorConfig
from nautilus_trader.screener.config import ScreenerConfig
from nautilus_trader.screener.providers import DemoDataProvider


def main() -> None:
    print("=" * 70)
    print("  🔍📈 Screener + Backtest Integration Demo")
    print("=" * 70)

    # ============================================================
    # Phase 1: Screen stocks using multi-factor model
    # ============================================================
    print("\n📊 Phase 1: Multi-Factor Screening")
    print("-" * 50)

    screener_config = ScreenerConfig(
        factors=[
            # Value: Low PE preferred
            FactorConfig(name="pe", params={"max_pe": 40}, weight=1.0, direction="ascending"),
            # Quality: High ROE preferred (highest weight)
            FactorConfig(name="roe", params={"min_roe": 12}, weight=2.0, direction="descending"),
            # Growth: Revenue growth
            FactorConfig(name="revenue_growth", params={"min_growth": -10}, weight=1.0, direction="descending"),
        ],
        top_n=10,
        sort_by="composite_score",
    )

    provider = DemoDataProvider()
    data = provider.get_screening_data()

    engine = ScreenerEngine(screener_config)
    result = engine.screen(data)

    print(f"\n  Selected {result.count} stocks from {len(data)} candidates:")
    display_cols = ["name", "industry", "composite_score", "pe", "roe", "revenue_growth"]
    available = [c for c in display_cols if c in result.data.columns]
    with pd.option_context("display.width", 180, "display.float_format", "{:.1f}".format):
        print(result.data[available].to_string())

    # ============================================================
    # Phase 2: Show how to feed into backtest
    # ============================================================
    print("\n\n📈 Phase 2: Backtest Integration")
    print("-" * 50)
    print("""
  The screener outputs a ranked list of stock symbols. To backtest:

  Option A: Single-stock backtest loop
  --------------------------------------
  from nautilus_trader.screener.providers import AShareScreenerDataProvider

  # Use real data
  provider = AShareScreenerDataProvider()
  data = provider.get_screening_data("20240101")
  result = engine.screen(data)

  # Run backtest for each screened stock
  for symbol in result.symbols[:5]:  # Top 5
      config = BacktestRunConfig(
          instruments=[f"{symbol}.SSE"],
          strategies=[EMACrossConfig(bar_type="1-Hour")],
          ...
      )
      node = BacktestNode(config)
      node.run()

  Option B: Portfolio backtest
  --------------------------------------
  # Use all screened stocks in a single portfolio backtest
  symbols = result.symbols[:10]
  config = BacktestRunConfig(
      instruments=[f"{s}.SSE" for s in symbols],
      strategies=[EMACrossConfig(bar_type="1-Hour")],
      ...
  )

  Option C: Periodic re-screening
  --------------------------------------
  # Re-screen monthly and adjust portfolio
  dates = pd.date_range("2024-01-01", "2024-12-31", freq="MS")
  for date in dates:
      data = provider.get_screening_data(date.strftime("%Y%m%d"))
      result = engine.screen(data)
      # Rebalance portfolio based on new selections
""")

    # ============================================================
    # Phase 3: Portfolio summary
    # ============================================================
    print("\n📋 Phase 3: Portfolio Summary")
    print("-" * 50)

    top5 = result.top(5)
    print(f"\n  Recommended portfolio (Top 5):")
    for symbol, row in top5.iterrows():
        name = row.get("name", symbol)
        industry = row.get("industry", "N/A")
        score = row.get("composite_score", 0)
        print(f"    ✅ {symbol} {name:8s} ({industry:6s}) | Score: {score:.1f}")

    avg_roe = top5["roe"].mean() if "roe" in top5.columns else 0
    avg_pe = top5["pe"].mean() if "pe" in top5.columns else 0
    print(f"\n  Portfolio Avg: ROE={avg_roe:.1f}% | PE={avg_pe:.1f}")

    print("\n" + "=" * 70)
    print("  ✅ Screener + Backtest demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
