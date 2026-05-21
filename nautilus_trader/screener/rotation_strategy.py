#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  NautilusTrader Stock Screener - Rotation Strategy
# -------------------------------------------------------------------------------------------------
"""
Multi-stock rotation strategy that integrates screener with NautilusTrader.

This strategy works identically in backtest and live mode:
- On rebalance dates, calls ScreenerEngine to select top stocks
- Sells positions not in the new selection
- Buys new selections with equal weight

Usage (Backtest)
----------------
>>> from nautilus_trader.screener.rotation_strategy import RotationConfig, RotationStrategy
>>> config = RotationConfig(
...     instrument_ids=[...],
...     bar_type=bar_type,
...     screener_provider=DemoDataProvider(),
...     rebalance_freq="monthly",
...     top_n=5,
... )
>>> strategy = RotationStrategy(config)

Usage (Live) - Same code, different provider
---------------------------------------------
>>> config = RotationConfig(
...     instrument_ids=[...],
...     bar_type=bar_type,
...     screener_provider=LiveScreenerProvider(token),
...     rebalance_freq="monthly",
...     top_n=5,
... )
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

import pandas as pd

from nautilus_trader.common.enums import LogColor
from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.model.currencies import CNY
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.screener.config import FactorConfig
from nautilus_trader.screener.config import ScreenerConfig
from nautilus_trader.screener.engine import ScreenerEngine
from nautilus_trader.screener.providers import ScreenerDataProvider
from nautilus_trader.trading.strategy import Strategy

logger = logging.getLogger(__name__)


class RotationConfig(StrategyConfig, frozen=True):
    """
    Configuration for multi-stock rotation strategy.

    Parameters
    ----------
    instrument_ids : list[InstrumentId]
        All candidate instrument IDs (pre-loaded into engine).
    bar_type : BarType
        Bar type for subscription.
    venue : Venue
        Trading venue (e.g. SSE, SZSE).
    rebalance_freq : str
        Rebalance frequency: "monthly", "weekly", "daily".
    top_n : int
        Number of top-ranked stocks to hold.
    factor_configs : list[dict]
        Factor configurations for screening.
    close_positions_on_stop : bool
        Close all positions on strategy stop.
    """

    instrument_ids: list[InstrumentId]
    bar_type: BarType
    venue: Venue
    rebalance_freq: str = "monthly"
    top_n: int = 5
    factor_configs: list[dict] = []
    close_positions_on_stop: bool = True

    def get_screener_config(self) -> ScreenerConfig:
        """Build ScreenerConfig from factor_configs dicts."""
        factor_configs = []
        for fc in self.factor_configs:
            params = dict(fc.get("params", {}))
            # Pass weight into factor params so the Factor instance uses it
            if "weight" in fc and "weight" not in params:
                params["weight"] = fc["weight"]
            factor_configs.append(FactorConfig(
                name=fc["name"],
                params=params,
                weight=fc.get("weight", 1.0),
            ))
        return ScreenerConfig(factors=factor_configs, top_n=self.top_n)


class RotationStrategy(Strategy):
    """
    Multi-stock rotation strategy with integrated screener.

    On each rebalance date:
    1. Get screening data from provider (backtest: cached, live: API)
    2. Run ScreenerEngine to rank stocks
    3. Sell positions not in top-N
    4. Buy top-N stocks with equal weight

    This strategy is identical in backtest and live mode.
    Only the ScreenerDataProvider differs.
    """

    def __init__(
        self,
        config: RotationConfig,
        screener_provider: ScreenerDataProvider,
        preloaded_screening: dict[str, pd.DataFrame] | None = None,
    ) -> None:
        super().__init__(config)

        self._provider = screener_provider
        self._screener = ScreenerEngine(config.get_screener_config())
        self._venue = config.venue
        self._top_n = config.top_n
        self._rebalance_freq = config.rebalance_freq

        # Pre-loaded screening data for backtest (date_str -> DataFrame)
        self._preloaded: dict[str, pd.DataFrame] = preloaded_screening or {}

        # Track current holdings and target
        self._current_holdings: set[str] = set()  # 6-digit symbols
        self._last_rebalance_month: int = -1
        self._last_rebalance_week: int = -1
        self._bar_count = 0

        # Symbol to instrument_id mapping
        self._symbol_to_instrument_id: dict[str, InstrumentId] = {}
        for iid in config.instrument_ids:
            symbol = iid.symbol.value
            self._symbol_to_instrument_id[symbol] = iid

    def on_start(self) -> None:
        """Strategy start."""
        for iid in self.config.instrument_ids:
            self.subscribe_bars(self.config.bar_type)
        self.log.info(
            f"Rotation Strategy started | freq={self._rebalance_freq} | "
            f"top_n={self._top_n} | candidates={len(self.config.instrument_ids)}",
        )

    def on_bar(self, bar: Bar) -> None:
        """Process bar - check for rebalance."""
        self._bar_count += 1

        if bar.is_single_price():
            return

        # Check if we should rebalance
        if not self._should_rebalance(bar):
            return

        # Get screening data
        bar_ts = bar.ts_event // 1_000_000  # nanos to millis
        date_str = datetime.fromtimestamp(bar_ts / 1000).strftime("%Y%m%d")

        screening_data = self._get_screening_data(date_str)
        if screening_data.empty:
            return

        # Run screener
        result = self._screener.screen(screening_data)
        if result.data.empty:
            return

        # Extract top-N stock symbols
        target_symbols: set[str] = set()
        for symbol in result.data.index[: self._top_n]:
            sym = str(symbol)
            if sym in self._symbol_to_instrument_id:
                target_symbols.add(sym)

        if not target_symbols:
            return

        self._rebalance(target_symbols, bar)

    def _should_rebalance(self, bar: Bar) -> bool:
        """Check if it's time to rebalance."""
        bar_ts = bar.ts_event // 1_000_000
        dt = datetime.fromtimestamp(bar_ts / 1000)
        current_month = dt.year * 12 + dt.month
        current_week = dt.isocalendar()[1] + dt.year * 100

        if self._rebalance_freq == "monthly":
            if current_month != self._last_rebalance_month:
                self._last_rebalance_month = current_month
                return True
        elif self._rebalance_freq == "weekly":
            if current_week != self._last_rebalance_week:
                self._last_rebalance_week = current_week
                return True
        elif self._rebalance_freq == "daily":
            return True

        return False

    def _get_screening_data(self, date_str: str) -> pd.DataFrame:
        """Get screening data - from preloaded cache or live provider."""
        if date_str in self._preloaded:
            return self._preloaded[date_str]
        return self._provider.get_screening_data(date_str)

    def _rebalance(self, target_symbols: set[str], bar: Bar) -> None:
        """Execute rebalance: sell old, buy new."""
        old_symbols = self._current_holdings.copy()

        # Determine what to sell and buy
        to_sell = old_symbols - target_symbols
        to_buy = target_symbols - old_symbols

        if not to_sell and not to_buy:
            return

        self.log.info(
            f"REBALANCE | Sell: {to_sell or 'none'} | Buy: {to_buy or 'none'} | "
            f"Hold: {target_symbols}",
            color=LogColor.YELLOW,
        )

        # Sell positions not in target
        for symbol in to_sell:
            iid = self._symbol_to_instrument_id.get(symbol)
            if iid and self.portfolio.is_net_long(iid):
                self.close_all_positions(iid)

        # Buy new positions with equal weight
        if to_buy:
            n_positions = len(target_symbols)
            self._buy_equal_weight(to_buy, n_positions, bar)

        self._current_holdings = target_symbols

    def _buy_equal_weight(self, symbols: set[str], n_positions: int, bar: Bar) -> None:
        """Buy stocks with equal weight allocation."""
        account = self.portfolio.account(self._venue)
        if account is None:
            return

        cash = account.balance_total(CNY)
        if cash is None:
            return

        available = float(cash.as_double())
        alloc_per_stock = available / n_positions

        for symbol in symbols:
            iid = self._symbol_to_instrument_id.get(symbol)
            if iid is None:
                continue

            instrument = self.cache.instrument(iid)
            if instrument is None:
                continue

            close_price = float(bar.close)
            if close_price <= 0:
                continue

            lot_size = 100
            fee_factor = 1.0 + float(instrument.taker_fee)
            max_shares = int(alloc_per_stock / (close_price * fee_factor))
            lots = max_shares // lot_size
            if lots > 1:
                lots -= 1  # Safety margin

            if lots <= 0:
                self.log.info(f"  Not enough cash for {symbol} (alloc={alloc_per_stock:.0f}, price={close_price:.2f})")
                continue

            shares = lots * lot_size
            self.log.info(
                f"  BUY {symbol} | Price={close_price:.2f} | Shares={shares} | "
                f"Value={shares * close_price:,.0f}",
                color=LogColor.GREEN,
            )

            order: MarketOrder = self.order_factory.market(
                instrument_id=iid,
                order_side=OrderSide.BUY,
                quantity=instrument.make_qty(Decimal(str(shares))),
                time_in_force=TimeInForce.IOC,
            )
            self.submit_order(order)

    def on_data(self, data: Data) -> None:
        pass

    def on_event(self, event: Event) -> None:
        pass

    def on_stop(self) -> None:
        """Strategy stop."""
        for iid in self.config.instrument_ids:
            self.cancel_all_orders(iid)
            if self.config.close_positions_on_stop:
                self.close_all_positions(iid)
        self.unsubscribe_bars(self.config.bar_type)

    def on_save(self) -> dict[str, bytes]:
        return {}

    def on_load(self, state: dict[str, bytes]) -> None:
        pass

    def on_reset(self) -> None:
        self._bar_count = 0
        self._current_holdings.clear()
        self._last_rebalance_month = -1
        self._last_rebalance_week = -1

    def on_dispose(self) -> None:
        pass