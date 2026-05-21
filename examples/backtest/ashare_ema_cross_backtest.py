#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Backtest: EMA Crossover with Real Market Data
# -------------------------------------------------------------------------------------------------

"""
A-Share backtest using real market data fetched from Tushare/AKShare.

This example demonstrates the complete workflow:
1. Fetch real daily bar data from Tushare (using TUSHARE_TOKEN from .env)
2. Create A-Share instrument (600519 Kweichow Moutai on SSE)
3. Convert data to NautilusTrader Bar objects
4. Run EMA Crossover LONG-ONLY backtest strategy
5. Generate account/fill/position reports
6. Generate interactive tearsheet (optional)

Requirements:
    pip install nautilus_trader tushare python-dotenv

Usage:
    python -m examples.backtest.ashare_ema_cross_backtest
"""

import time
from decimal import Decimal

import pandas as pd

from nautilus_trader.adapters.ashare import AShareDataConfig
from nautilus_trader.adapters.ashare import AShareDataLoader
from nautilus_trader.adapters.ashare import SSE
from nautilus_trader.adapters.ashare import create_stock_instrument
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import RiskEngineConfig
from nautilus_trader.examples.strategies.ema_cross_long_only import EMACrossLongOnly
from nautilus_trader.examples.strategies.ema_cross_long_only import EMACrossLongOnlyConfig
from nautilus_trader.model.currencies import CNY
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.objects import Money


# ============================================================================
# Configuration
# ============================================================================
SYMBOL = "600900"        # China Yangtze Power (长江电力)
START_DATE = "20230101"  # Backtest start
END_DATE = "20241231"    # Backtest end
DATA_SOURCE = "tushare"  # "tushare" or "akshare"
INITIAL_CAPITAL = 1_000_000.0  # CNY


def main() -> None:
    print("=" * 70)
    print("  A-Share Backtest: EMA Crossover Strategy")
    print(f"  Stock: {SYMBOL} | Period: {START_DATE} - {END_DATE}")
    print(f"  Data Source: {DATA_SOURCE}")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Step 1: Fetch real market data
    # -------------------------------------------------------------------------
    print("\n[1/5] Fetching market data...")

    data_config = AShareDataConfig(
        source=DATA_SOURCE,
        adj_type="qfq",  # Forward-adjusted prices
        cache_enabled=True,  # Cache to avoid re-downloading
    )
    print(f"  Config: source={data_config.source}, adj={data_config.adj_type}")
    if data_config.tushare_token:
        print(f"  Token: {data_config.tushare_token[:8]}...")

    loader = AShareDataLoader(data_config)

    # Fetch daily bars — this calls Tushare/AKShare API for real data
    bars = loader.load_daily_bars(
        symbol=SYMBOL,
        start_date=START_DATE,
        end_date=END_DATE,
    )

    if not bars:
        print(f"  ERROR: No data returned for {SYMBOL}. Check network/token.")
        return

    print(f"  Fetched {len(bars)} daily bars")
    print(f"  First: {bars[0]}")
    print(f"  Last:  {bars[-1]}")

    # -------------------------------------------------------------------------
    # Step 2: Create A-Share instrument
    # -------------------------------------------------------------------------
    print("\n[2/5] Creating instrument...")

    instrument = create_stock_instrument(SYMBOL)
    print(f"  Instrument: {instrument.id}")
    print(f"  Venue: {instrument.id.venue}")
    print(f"  Price precision: {instrument.price_precision}")
    print(f"  Lot size: {instrument.lot_size}")

    # -------------------------------------------------------------------------
    # Step 3: Configure backtest engine
    # -------------------------------------------------------------------------
    print("\n[3/5] Configuring backtest engine...")

    config = BacktestEngineConfig(
        trader_id=TraderId("ASHARE-BACKTEST-001"),
        logging=LoggingConfig(
            log_level="INFO",
            log_colors=True,
            use_pyo3=False,
        ),
        risk_engine=RiskEngineConfig(
            bypass=True,  # Bypass pre-trade risk for backtesting
        ),
    )

    engine = BacktestEngine(config=config)

    # Add SSE as trading venue
    engine.add_venue(
        venue=SSE,
        oms_type=OmsType.NETTING,
        book_type=BookType.L1_MBP,
        account_type=AccountType.CASH,  # A-Share uses cash accounts
        base_currency=None,  # Multi-currency (CNY)
        starting_balances=[Money(INITIAL_CAPITAL, CNY)],
        bar_execution=True,  # Bars move the market
        trade_execution=False,
    )

    # Add instrument and data
    engine.add_instrument(instrument)
    engine.add_data(bars)

    print(f"  Venue: {SSE}")
    print(f"  Starting capital: {INITIAL_CAPITAL:,.0f} CNY")

    # -------------------------------------------------------------------------
    # Step 4: Configure strategy
    # -------------------------------------------------------------------------
    print("\n[4/5] Configuring EMA Cross Long-Only strategy...")

    bar_type = bars[0].bar_type
    print(f"  Bar type: {bar_type}")

    strategy_config = EMACrossLongOnlyConfig(
        instrument_id=instrument.id,
        bar_type=bar_type,
        trade_size=Decimal("100"),  # 100 shares (minimum lot for A-Share)
        fast_ema_period=10,
        slow_ema_period=20,
        close_positions_on_stop=True,
    )

    strategy = EMACrossLongOnly(config=strategy_config)
    engine.add_strategy(strategy=strategy)

    print(f"  Strategy: EMA Cross Long-Only (10/20)")
    print(f"  Trade size: 100 shares")

    # -------------------------------------------------------------------------
    # Step 5: Run backtest
    # -------------------------------------------------------------------------
    print("\n[5/5] Running backtest...\n")
    print("-" * 70)

    time.sleep(0.1)
    engine.run()

    # -------------------------------------------------------------------------
    # Results
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  BACKTEST RESULTS")
    print("=" * 70)

    # Account report
    with pd.option_context(
        "display.max_rows",
        100,
        "display.max_columns",
        None,
        "display.width",
        300,
    ):
        print("\n--- Account Report ---")
        print(engine.trader.generate_account_report(SSE))

        print("\n--- Order Fills Report ---")
        print(engine.trader.generate_order_fills_report())

        print("\n--- Positions Report ---")
        print(engine.trader.generate_positions_report())

    # -------------------------------------------------------------------------
    # Optional: Generate tearsheet
    # -------------------------------------------------------------------------
    try:
        from nautilus_trader.analysis import TearsheetConfig
        from nautilus_trader.analysis.tearsheet import create_tearsheet

        print("\n--- Generating Tearsheet ---")
        tearsheet_config = TearsheetConfig(theme="plotly_white", locale="zh_CN")
        output_path = f"ashare_{SYMBOL}_tearsheet.html"
        create_tearsheet(
            engine=engine,
            output_path=output_path,
            config=tearsheet_config,
        )
        print(f"Tearsheet saved to: {output_path}")
        print("Open in browser to view interactive charts!")
    except ImportError:
        print("\nPlotly not installed. Install with: pip install plotly>=6.3.1")
    except Exception as e:
        print(f"\nTearsheet generation failed: {e}")

    # Clean up
    engine.reset()
    engine.dispose()

    print("\n" + "=" * 70)
    print("  Backtest complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()