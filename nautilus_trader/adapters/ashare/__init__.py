#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Adapter
# -------------------------------------------------------------------------------------------------
"""
A-Share (Chinese stock market) adapter for NautilusTrader.

Provides data loading and instrument creation for backtesting.
"""

from nautilus_trader.adapters.ashare.config import AShareDataConfig
from nautilus_trader.adapters.ashare.instruments import SSE
from nautilus_trader.adapters.ashare.instruments import SZSE
from nautilus_trader.adapters.ashare.instruments import create_stock_instrument
from nautilus_trader.adapters.ashare.instruments import get_venue
from nautilus_trader.adapters.ashare.loaders import AShareDataLoader

__all__ = [
    "AShareDataConfig",
    "AShareDataLoader",
    "SSE",
    "SZSE",
    "create_stock_instrument",
    "get_venue",
]