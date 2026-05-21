#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Stock Screener Demo: Multi-Factor Screening
# -------------------------------------------------------------------------------------------------
"""
Demo of the NautilusTrader stock screener module.

Uses built-in demo data (no API token required) to demonstrate:
1. Multi-factor screening (PE, PB, ROE, Revenue Growth)
2. Composite scoring and ranking
3. Output of top-ranked stocks

Usage:
    python -m examples.backtest.ashare_screener_demo
"""

import pandas as pd

from nautilus_trader.screener import ScreenerEngine
from nautilus_trader.screener.config import FactorConfig
from nautilus_trader.screener.config import ScreenerConfig
from nautilus_trader.screener.providers import DemoDataProvider


def main() -> None:
    print("=" * 70)
    print("  🔍 NautilusTrader Stock Screener Demo")
    print("  Market: A-Share | Data: Demo (30 well-known stocks)")
    print("=" * 70)

    # -----------------------------------------------------------------
    # Step 1: Configure screening factors
    # -----------------------------------------------------------------
    print("\n[1/3] Configuring screening factors...")

    config = ScreenerConfig(
        factors=[
            FactorConfig(
                name="pe",
                params={"max_pe": 50},
                weight=1.0,
                direction="ascending",  # Lower PE is better
            ),
            FactorConfig(
                name="pb",
                params={"max_pb": 15},
                weight=0.5,
                direction="ascending",  # Lower PB is better
            ),
            FactorConfig(
                name="roe",
                params={"min_roe": 10},
                weight=2.0,  # ROE has highest weight
                direction="descending",  # Higher ROE is better
            ),
            FactorConfig(
                name="revenue_growth",
                params={"min_growth": -20},
                weight=1.0,
                direction="descending",  # Higher growth is better
            ),
        ],
        top_n=15,
        sort_by="composite_score",
        min_score=0,
    )

    print(f"  Factors: {[f.name for f in config.factors]}")
    print(f"  Weights: {[f.weight for f in config.factors]}")
    print(f"  Top N: {config.top_n}")

    # -----------------------------------------------------------------
    # Step 2: Fetch data
    # -----------------------------------------------------------------
    print("\n[2/3] Fetching stock data...")

    provider = DemoDataProvider()
    data = provider.get_screening_data()

    print(f"  Loaded {len(data)} stocks")
    print(f"  Columns: {list(data.columns)}")

    # -----------------------------------------------------------------
    # Step 3: Run screener
    # -----------------------------------------------------------------
    print("\n[3/3] Running multi-factor screening...\n")

    engine = ScreenerEngine(config)
    result = engine.screen(data)

    # -----------------------------------------------------------------
    # Display Results
    # -----------------------------------------------------------------
    print("=" * 70)
    print("  📊 SCREENING RESULTS")
    print("=" * 70)

    if result.count == 0:
        print("  No stocks passed the screening criteria.")
        return

    # Display top stocks with key metrics
    display_cols = ["name", "industry", "composite_score", "pe", "pb", "roe", "revenue_growth"]
    available_cols = [c for c in display_cols if c in result.data.columns]

    with pd.option_context("display.width", 200, "display.max_rows", 30, "display.float_format", "{:.1f}".format):
        print(result.data[available_cols].to_string())

    print("\n" + "-" * 70)
    print(f"  Total screened: {len(data)} | Selected: {result.count}")
    print(f"  Top 5: {result.symbols[:5]}")

    # -----------------------------------------------------------------
    # Strategy interpretation
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  💡 How to use these results")
    print("=" * 70)
    print("""
  1. Take the top-ranked stocks and run backtests with your strategy
  2. Example workflow:

     from nautilus_trader.screener import ScreenerEngine
     from nautilus_trader.screener.providers import AShareScreenerDataProvider

     # Real data from Tushare
     provider = AShareScreenerDataProvider()
     data = provider.get_screening_data("20240101")

     # Screen
     engine = ScreenerEngine(config)
     result = engine.screen(data)

     # Backtest each selected stock
     for symbol in result.symbols:
         run_backtest(symbol)  # Your backtest function

  3. Or use with the existing EMA cross strategy for timing
""")

    print("=" * 70)
    print("  Screener demo complete! 🔍")
    print("=" * 70)


if __name__ == "__main__":
    main()
