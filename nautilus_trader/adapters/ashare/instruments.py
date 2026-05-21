#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Instrument Helpers
# -------------------------------------------------------------------------------------------------
"""
Utility functions for creating A-Share (Chinese stock market) instruments.
"""

from decimal import Decimal

from nautilus_trader.model.currencies import CNY
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity

# A-Share venues
SSE = Venue("SSE")  # Shanghai Stock Exchange
SZSE = Venue("SZSE")  # Shenzhen Stock Exchange

# Default A-Share commission rates
DEFAULT_MAKER_FEE = Decimal("0.00024")  # 佣金万2.3 + 过户费0.001% ≈ 0.024%
DEFAULT_TAKER_FEE = Decimal("0.00024")


def get_venue(symbol: str) -> Venue:
    """根据股票代码判断交易所。"""
    if symbol.startswith("6"):
        return SSE
    elif symbol.startswith("0") or symbol.startswith("3"):
        return SZSE
    else:
        return SSE  # default


def create_stock_instrument(
    symbol: str,
    price_precision: int = 2,
    lot_size: int = 100,
    maker_fee: Decimal | None = None,
    taker_fee: Decimal | None = None,
    ts_event: int = 0,
    ts_init: int = 0,
) -> Equity:
    """
    创建 A 股 Equity instrument。

    Parameters
    ----------
    symbol : str
        股票代码，如 "600519"（贵州茅台）
    price_precision : int
        价格精度（A 股默认 2 位小数）
    lot_size : int
        最小交易单位（A 股默认 100 股）
    maker_fee : Decimal, optional
        Maker 手续费率
    taker_fee : Decimal, optional
        Taker 手续费率
    """
    venue = get_venue(symbol)
    instrument_id = InstrumentId(symbol=Symbol(symbol), venue=venue)
    price_increment = Price(1 / 10**price_precision, precision=price_precision)
    lot_size_qty = Quantity.from_int(lot_size)

    return Equity(
        instrument_id=instrument_id,
        raw_symbol=Symbol(symbol),
        currency=CNY,
        price_precision=price_precision,
        price_increment=price_increment,
        lot_size=lot_size_qty,
        isin=f"CN{symbol.zfill(10)}",
        maker_fee=maker_fee or DEFAULT_MAKER_FEE,
        taker_fee=taker_fee or DEFAULT_TAKER_FEE,
        ts_event=ts_event,
        ts_init=ts_init,
    )