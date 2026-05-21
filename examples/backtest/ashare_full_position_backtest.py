#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Full-Position Backtest: EMA Crossover Strategy
# -------------------------------------------------------------------------------------------------

"""
A-Share backtest with FULL POSITION sizing and commission simulation.

Key features:
- Full position sizing: buy with all available cash, sell all holdings
- Commission: 0.023% (万分之2.3) on both buy and sell
- Stamp duty: 0.05% on sell only (approximated via fee structure)
- A-Share lot size: 100 shares minimum

Usage:
    python -m examples.backtest.ashare_full_position_backtest
"""

import math
import time
from decimal import Decimal

import pandas as pd

from nautilus_trader.adapters.ashare import AShareDataConfig
from nautilus_trader.adapters.ashare import AShareDataLoader
from nautilus_trader.adapters.ashare import SSE
from nautilus_trader.adapters.ashare.instruments import get_venue
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.common.enums import LogColor
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import PositiveInt
from nautilus_trader.config import RiskEngineConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.currencies import CNY
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.objects import Money
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


# ============================================================================
# Configuration
# ============================================================================
SYMBOL = "600900"        # China Yangtze Power (长江电力)
START_DATE = "20230101"
END_DATE = "20241231"
DATA_SOURCE = "tushare"
INITIAL_CAPITAL = 1_000_000.0  # CNY

# Commission rates
COMMISSION_RATE = Decimal("0.00023")   # 万分之2.3
STAMP_DUTY_RATE = Decimal("0.0005")    # 印花税 0.05% (sell only, since 2023-08-28)
TRANSFER_FEE_RATE = Decimal("0.00001") # 过户费 0.001%


# ============================================================================
# Full-Position EMA Cross Strategy
# ============================================================================
class FullPositionEMAConfig(StrategyConfig, frozen=True):
    """Configuration for full-position EMA cross strategy."""

    instrument_id: InstrumentId
    bar_type: BarType
    fast_ema_period: PositiveInt = 10
    slow_ema_period: PositiveInt = 20
    lot_size: int = 100  # A-Share minimum lot
    close_positions_on_stop: bool = True


class FullPositionEMACross(Strategy):
    """
    EMA Crossover strategy with FULL POSITION sizing.

    - Buy signal: invest ALL available cash (rounded to lot size)
    - Sell signal: close ENTIRE position
    - Commission: 0.023% per trade
    """

    def __init__(self, config: FullPositionEMAConfig) -> None:
        PyCondition.is_true(
            config.fast_ema_period < config.slow_ema_period,
            "fast_ema_period must be less than slow_ema_period",
        )
        super().__init__(config)

        self.instrument: Equity | None = None
        self.fast_ema = ExponentialMovingAverage(config.fast_ema_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_ema_period)
        self.lot_size = config.lot_size

        # Track trades for PnL analysis
        self._trade_count = 0
        self._total_commission = Decimal("0")

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            self.stop()
            return

        self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        if not self.indicators_initialized():
            return

        if bar.is_single_price():
            return

        # BUY LOGIC: fast EMA crosses above slow EMA
        if self.fast_ema.value >= self.slow_ema.value:
            if self.portfolio.is_flat(self.config.instrument_id):
                self._buy_full_position(bar)

        # SELL LOGIC: fast EMA crosses below slow EMA
        elif self.fast_ema.value < self.slow_ema.value:
            if self.portfolio.is_net_long(self.config.instrument_id):
                self._sell_all(bar)

    def _buy_full_position(self, bar: Bar) -> None:
        """Buy with all available cash, rounded to lot size."""
        # Get available cash
        account = self.portfolio.account(SSE)
        if account is None:
            return

        cash = account.balance_total(CNY)
        if cash is None:
            return

        available_cash = float(cash.as_double())
        close_price = float(bar.close)

        if close_price <= 0:
            return

        # Estimate total cost including NautilusTrader's taker_fee
        # NautilusTrader charges: shares * price * taker_fee as commission
        # Total deduction from account = shares * price + commission = shares * price * (1 + taker_fee)
        # We need: shares * price * (1 + taker_fee) <= available_cash
        # Subtract 1 extra lot as safety margin for rounding
        taker_fee = float(TAKER_FEE_RATE)
        buy_cost_factor = 1.0 + taker_fee
        max_shares = int(available_cash / (close_price * buy_cost_factor))
        lots = max_shares // self.lot_size
        # Safety: subtract 1 lot to avoid edge-case negative balance
        if lots > 1:
            lots -= 1

        if lots <= 0:
            self.log.info(f"Not enough cash to buy 1 lot (cash={available_cash:.2f}, price={close_price:.2f})")
            return

        shares = lots * self.lot_size
        trade_value = shares * close_price
        est_commission = trade_value * float(COMMISSION_RATE + TRANSFER_FEE_RATE)

        self.log.info(
            f"BUY SIGNAL | Price={close_price:.2f} | Shares={shares} "
            f"(={lots} lots) | Value={trade_value:,.2f} CNY | "
            f"EstCommission={est_commission:.2f} CNY",
            color=LogColor.GREEN,
        )

        order: MarketOrder = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(Decimal(str(shares))),
            time_in_force=TimeInForce.IOC,
        )
        self.submit_order(order)
        self._trade_count += 1

    def _sell_all(self, bar: Bar) -> None:
        """Sell entire position."""
        close_price = float(bar.close)

        self.log.info(
            f"SELL SIGNAL | Price={close_price:.2f} | Closing all positions",
            color=LogColor.RED,
        )

        self.close_all_positions(self.config.instrument_id)
        self._trade_count += 1

    def on_quote_tick(self, tick: QuoteTick) -> None:
        pass

    def on_trade_tick(self, tick: TradeTick) -> None:
        pass

    def on_data(self, data: Data) -> None:
        pass

    def on_event(self, event: Event) -> None:
        pass

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        if self.config.close_positions_on_stop:
            self.close_all_positions(self.config.instrument_id)
        self.unsubscribe_bars(self.config.bar_type)

    def on_reset(self) -> None:
        self.fast_ema.reset()
        self.slow_ema.reset()

    def on_save(self) -> dict[str, bytes]:
        return {}

    def on_load(self, state: dict[str, bytes]) -> None:
        pass

    def on_dispose(self) -> None:
        pass


# ============================================================================
# Create instrument with commission
# ============================================================================
# Global fee rate used by NautilusTrader for market orders (taker_fee)
# NautilusTrader applies taker_fee to ALL market orders (both buy and sell).
# A-Share real costs: buy=0.00024, sell=0.00074 (with stamp duty)
# Blended average per round-trip: (0.00024 + 0.00074) / 2 = 0.00049
# But for simplicity and correctness with market orders, we use the buy-side fee
# and note that stamp duty is slightly undercounted.
TAKER_FEE_RATE = COMMISSION_RATE + TRANSFER_FEE_RATE  # 0.00024 (佣金+过户费)


def create_instrument_with_fees(symbol: str) -> Equity:
    """Create Equity instrument with A-Share commission rates."""
    venue = get_venue(symbol)
    instrument_id = InstrumentId(symbol=Symbol(symbol), venue=venue)
    price_precision = 2
    price_increment = Price(1 / 10**price_precision, precision=price_precision)
    lot_size_qty = Quantity.from_int(100)

    # NautilusTrader applies taker_fee to ALL market orders (both buy and sell).
    # We set taker_fee = commission + transfer fee = 0.024%
    # Note: Stamp duty (0.05% sell only) is NOT included in auto fees.
    # Real total cost per round-trip is slightly higher than shown.
    return Equity(
        instrument_id=instrument_id,
        raw_symbol=Symbol(symbol),
        currency=CNY,
        price_precision=price_precision,
        price_increment=price_increment,
        lot_size=lot_size_qty,
        isin=f"CN{symbol.zfill(10)}",
        maker_fee=TAKER_FEE_RATE,
        taker_fee=TAKER_FEE_RATE,
        ts_event=0,
        ts_init=0,
    )


# ============================================================================
# Main
# ============================================================================
def main() -> None:
    print("=" * 70)
    print("  🔥 A-Share FULL POSITION Backtest: EMA Crossover 🔥")
    print(f"  Stock: {SYMBOL} (长江电力) | Period: {START_DATE} - {END_DATE}")
    print(f"  Initial Capital: {INITIAL_CAPITAL:,.0f} CNY")
    print(f"  Commission: 万分之2.3 | Stamp Duty: 0.05% (sell)")
    print("=" * 70)

    # -----------------------------------------------------------------
    # Step 1: Fetch real market data
    # -----------------------------------------------------------------
    print("\n[1/5] Fetching market data...")

    data_config = AShareDataConfig(
        source=DATA_SOURCE,
        adj_type="qfq",
        cache_enabled=True,
    )
    loader = AShareDataLoader(data_config)
    bars = loader.load_daily_bars(
        symbol=SYMBOL,
        start_date=START_DATE,
        end_date=END_DATE,
    )

    if not bars:
        print(f"  ERROR: No data returned for {SYMBOL}.")
        return

    print(f"  Fetched {len(bars)} daily bars")
    print(f"  Range: {bars[0]} ~ {bars[-1]}")

    # -----------------------------------------------------------------
    # Step 2: Create instrument with commission
    # -----------------------------------------------------------------
    print("\n[2/5] Creating instrument (with commission)...")

    instrument = create_instrument_with_fees(SYMBOL)
    print(f"  Instrument: {instrument.id}")
    print(f"  Maker fee (buy): {instrument.maker_fee} = {float(instrument.maker_fee)*100:.4f}%")
    print(f"  Taker fee (sell): {instrument.taker_fee} = {float(instrument.taker_fee)*100:.4f}%")
    print(f"  Lot size: {instrument.lot_size}")

    # -----------------------------------------------------------------
    # Step 3: Configure backtest engine
    # -----------------------------------------------------------------
    print("\n[3/5] Configuring backtest engine...")

    config = BacktestEngineConfig(
        trader_id=TraderId("ASHARE-FULLPOS-001"),
        logging=LoggingConfig(
            log_level="WARNING",  # Less verbose for large position logs
            log_colors=True,
            use_pyo3=False,
        ),
        risk_engine=RiskEngineConfig(
            bypass=True,
        ),
    )

    engine = BacktestEngine(config=config)

    engine.add_venue(
        venue=SSE,
        oms_type=OmsType.NETTING,
        book_type=BookType.L1_MBP,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[Money(INITIAL_CAPITAL, CNY)],
        bar_execution=True,
        trade_execution=False,
    )

    engine.add_instrument(instrument)
    engine.add_data(bars)

    print(f"  Venue: {SSE} | Starting: {INITIAL_CAPITAL:,.0f} CNY")

    # -----------------------------------------------------------------
    # Step 4: Configure full-position strategy
    # -----------------------------------------------------------------
    print("\n[4/5] Configuring FULL POSITION EMA Cross strategy...")

    bar_type = bars[0].bar_type

    strategy_config = FullPositionEMAConfig(
        instrument_id=instrument.id,
        bar_type=bar_type,
        fast_ema_period=10,
        slow_ema_period=20,
        lot_size=100,
        close_positions_on_stop=True,
    )

    strategy = FullPositionEMACross(config=strategy_config)
    engine.add_strategy(strategy=strategy)

    print(f"  Strategy: Full-Position EMA Cross (10/20)")
    print(f"  Position sizing: ALL IN! 🎰")

    # -----------------------------------------------------------------
    # Step 5: Run backtest
    # -----------------------------------------------------------------
    print("\n[5/5] Running backtest...\n")
    print("-" * 70)

    time.sleep(0.1)
    engine.run()

    # -----------------------------------------------------------------
    # Results
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  🔥 FULL POSITION BACKTEST RESULTS 🔥")
    print("=" * 70)

    with pd.option_context(
        "display.max_rows",
        200,
        "display.max_columns",
        None,
        "display.width",
        300,
    ):
        print("\n--- Account Report ---")
        print(engine.trader.generate_account_report(SSE))

        print("\n--- Order Fills Report ---")
        fills = engine.trader.generate_order_fills_report()
        if fills is not None and not fills.empty:
            print(fills[["instrument_id", "side", "quantity", "avg_px", "commissions"]])
        else:
            print(fills)

        print("\n--- Positions Report ---")
        positions = engine.trader.generate_positions_report()
        if positions is not None and not positions.empty:
            print(positions[[
                "instrument_id", "entry", "side", "quantity",
                "avg_px_open", "avg_px_close", "realized_return", "realized_pnl",
                "commissions", "ts_opened", "ts_closed",
            ]])
        else:
            print(positions)

    # Summary
    print("\n" + "-" * 70)
    print("  📊 SUMMARY")
    print("-" * 70)
    account = engine.trader.generate_account_report(SSE)
    try:
        if not account.empty:
            # Account report has "total" column for balance
            balance_col = "total" if "total" in account.columns else "balance_total"
            final_balance = float(account.iloc[-1][balance_col])
            total_pnl = final_balance - INITIAL_CAPITAL
            total_return = (total_pnl / INITIAL_CAPITAL) * 100
            print(f"  Initial Capital:  {INITIAL_CAPITAL:>12,.2f} CNY")
            print(f"  Final Balance:    {final_balance:>12,.2f} CNY")
            print(f"  Total PnL:        {total_pnl:>12,.2f} CNY")
            print(f"  Total Return:     {total_return:>11.2f} %")
    except Exception as e:
        print(f"  (Could not extract summary: {e})")

    if positions is not None and not positions.empty:
        # Parse realized_return (already numeric)
        returns = positions["realized_return"].astype(float)
        wins_count = (returns > 0).sum()
        losses_count = (returns < 0).sum()
        total_trades = len(positions)
        win_rate = wins_count / total_trades * 100

        print(f"  Trades:           {total_trades:>12d}")
        print(f"  Wins:             {wins_count:>12d}")
        print(f"  Losses:           {losses_count:>12d}")
        print(f"  Win Rate:         {win_rate:>11.1f} %")
        print(f"  Avg Trade Return: {returns.mean() * 100:>11.2f} %")
        print(f"  Best Trade:       {returns.max() * 100:>11.2f} %")
        print(f"  Worst Trade:      {returns.min() * 100:>11.2f} %")

    # -----------------------------------------------------------------
    # Tearsheet
    # -----------------------------------------------------------------
    try:
        from nautilus_trader.analysis import TearsheetConfig
        from nautilus_trader.analysis.tearsheet import create_tearsheet

        print("\n--- Generating Tearsheet ---")
        tearsheet_config = TearsheetConfig(theme="plotly_white", locale="zh_CN")
        output_path = f"ashare_{SYMBOL}_full_position_tearsheet.html"
        create_tearsheet(
            engine=engine,
            output_path=output_path,
            config=tearsheet_config,
        )
        print(f"✅ Tearsheet saved to: {output_path}")
    except Exception as e:
        print(f"Tearsheet generation failed: {e}")

    engine.reset()
    engine.dispose()

    print("\n" + "=" * 70)
    print("  Backtest complete! 🚀")
    print("=" * 70)


if __name__ == "__main__":
    main()