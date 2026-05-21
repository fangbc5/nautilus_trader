#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Backtest: Enhanced Overnight Hold Strategy (增强版一夜持股法)
# -------------------------------------------------------------------------------------------------
"""
Enhanced overnight hold strategy with multi-stock selection, improved signals,
and risk management.

Improvements over basic version:
1. Multi-stock pool with daily selection
2. Momentum + volume confirmation signals
3. Next-day take-profit / stop-loss via intraday high/low simulation
4. Equal-weight position sizing (max N positions)
5. Comprehensive performance reporting

Usage:
    python -m examples.backtest.ashare_overnight_hold_enhanced_backtest
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from nautilus_trader.adapters.ashare import AShareDataConfig
from nautilus_trader.adapters.ashare import AShareDataLoader
from nautilus_trader.adapters.ashare import SSE
from nautilus_trader.adapters.ashare import SZSE
from nautilus_trader.adapters.ashare import create_stock_instrument
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.common.enums import LogColor
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import PositiveInt
from nautilus_trader.config import RiskEngineConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.core.message import Event
from nautilus_trader.model.currencies import CNY
from datetime import datetime

from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarSpecification
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import BarAggregation
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.objects import Money
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


# ============================================================================
# Configuration
# ============================================================================

# Candidate stock pool (diversified: large caps, dividend stocks, growth)
STOCK_POOL = [
    # 金融/蓝筹
    "600519",   # 贵州茅台
    "601318",   # 中国平安
    "600036",   # 招商银行
    "601398",   # 工商银行
    "600900",   # 长江电力
    # 科技/成长
    "000858",   # 五粮液
    "002475",   # 立讯精密
    "300750",   # 宁德时代
    "601012",   # 隆基绿能
    "002415",   # 海康威视
    # 消费/医药
    "600276",   # 恒瑞医药
    "000568",   # 泸州老窖
    "600887",   # 伊利股份
    "002304",   # 洋河股份
    "000333",   # 美的集团
]

START_DATE = "20230101"
END_DATE = "20241231"
DATA_SOURCE = "tushare"
INITIAL_CAPITAL = 100_000.0  # CNY


@dataclass
class StockInfo:
    """Per-stock tracking data."""
    symbol: str
    instrument_id: InstrumentId
    venue: Venue
    close_prices: list[float] = None
    volumes: list[float] = None
    high_prices: list[float] = None
    low_prices: list[float] = None

    def __post_init__(self):
        if self.close_prices is None:
            self.close_prices = []
        if self.volumes is None:
            self.volumes = []
        if self.high_prices is None:
            self.high_prices = []
        if self.low_prices is None:
            self.low_prices = []


# ============================================================================
# Strategy
# ============================================================================

class EnhancedOvernightConfig(StrategyConfig, frozen=True):
    """
    Configuration for enhanced overnight hold strategy.

    Parameters
    ----------
    instrument_ids : list[InstrumentId]
        All candidate instrument IDs.
    bar_type : BarType
        Bar type for subscription.
    lookback : int
        Lookback period for moving averages and indicators.
    max_positions : int
        Maximum number of concurrent positions.
    take_profit_pct : float
        Take-profit percentage for next-day exit.
    stop_loss_pct : float
        Stop-loss percentage for next-day exit.
    momentum_threshold : float
        Minimum daily return to consider as momentum signal.
    volume_ratio_threshold : float
        Minimum volume ratio (vs 20-day avg) for confirmation.
    position_pct : float
        Percentage of capital per position (0.0-1.0).
    close_positions_on_stop : bool
        Close all positions on strategy stop.
    """

    instrument_ids: list[InstrumentId]
    bar_type: BarType
    lookback: PositiveInt = 10
    max_positions: PositiveInt = 3
    take_profit_pct: float = 2.0
    stop_loss_pct: float = 1.5
    momentum_threshold: float = 0.5
    volume_ratio_threshold: float = 1.2
    position_pct: float = 0.30
    close_positions_on_stop: bool = True


class EnhancedOvernightStrategy(Strategy):
    """
    增强版一夜持股法策略。

    核心逻辑：
    1. 每日收盘前评估候选池中所有股票
    2. 综合打分：动量 + 成交量 + 趋势 + 波动率
    3. 选出 Top N 买入（等权重）
    4. 次日根据高低点模拟止盈止损
       - 如果日内最高价 >= 买入价 * (1 + take_profit_pct%) → 止盈
       - 如果日内最低价 <= 买入价 * (1 - stop_loss_pct%) → 止损
       - 否则收盘价卖出
    """

    def __init__(self, config: EnhancedOvernightConfig) -> None:
        super().__init__(config)

        self._lookback = config.lookback
        self._max_positions = config.max_positions
        self._take_profit_pct = config.take_profit_pct / 100.0
        self._stop_loss_pct = config.stop_loss_pct / 100.0
        self._momentum_threshold = config.momentum_threshold / 100.0
        self._volume_ratio_threshold = config.volume_ratio_threshold
        self._position_pct = config.position_pct

        # Per-stock tracking
        self._stocks: dict[str, StockInfo] = {}
        self._instruments: dict[str, Equity] = {}
        self._bar_types: dict[str, BarType] = {}  # symbol -> bar_type

        # Track pending sell orders (symbol -> buy price)
        self._pending_exits: dict[str, float] = {}  # symbol -> entry_price

        # Track processing state
        self._bar_count = 0
        self._current_date: str = ""
        self._bars_today: set[str] = set()  # symbols received today
        self._day_processed = False

    def on_start(self) -> None:
        """策略启动。"""
        for iid in self.config.instrument_ids:
            symbol = iid.symbol.value
            venue = iid.venue
            instrument = self.cache.instrument(iid)
            if instrument is None:
                self.log.warning(f"Instrument not found: {iid}")
                continue

            # Create per-instrument bar type
            bar_type = BarType(
                iid,
                BarSpecification(1, BarAggregation.DAY, PriceType.LAST),
            )
            self._bar_types[symbol] = bar_type
            self._stocks[symbol] = StockInfo(symbol=symbol, instrument_id=iid, venue=venue)
            self._instruments[symbol] = instrument
            self.subscribe_bars(bar_type)

        self.log.info(
            f"Enhanced Overnight Strategy started | "
            f"pool={len(self._stocks)} | max_pos={self._max_positions} | "
            f"TP={self.config.take_profit_pct}% | SL={self.config.stop_loss_pct}%",
        )

    def on_bar(self, bar: Bar) -> None:
        """每根 Bar 触发。"""
        self._bar_count += 1

        if bar.is_single_price():
            return

        symbol = bar.bar_type.instrument_id.symbol.value
        if symbol not in self._stocks:
            return

        # Store bar data for this stock
        self._stocks[symbol].close_prices.append(float(bar.close))
        self._stocks[symbol].volumes.append(float(bar.volume))
        self._stocks[symbol].high_prices.append(float(bar.high))
        self._stocks[symbol].low_prices.append(float(bar.low))

        # Get current date from bar
        bar_ts = bar.ts_event // 1_000_000
        current_date = datetime.fromtimestamp(bar_ts / 1000).strftime("%Y%m%d")

        # When date changes, process the previous day's signals
        if current_date != self._current_date:
            if self._current_date:  # not the very first bar
                self._process_day()
            self._current_date = current_date

    def _process_day(self) -> None:
        """Process all bars for a completed trading day."""
        # Step 1: Handle exits for positions held overnight
        self._process_exits()

        # Step 2: Score all candidate stocks for new entries
        self._process_entries()

    def _process_exits(self) -> None:
        """卖出昨日持仓，使用日内高低点模拟止盈止损。"""
        for symbol, entry_price in list(self._pending_exits.items()):
            stock = self._stocks.get(symbol)
            if stock is None or len(stock.high_prices) < 1:
                continue

            iid = stock.instrument_id
            if not self.portfolio.is_net_long(iid):
                self._pending_exits.pop(symbol, None)
                continue

            # Use today's high/low to simulate intraday exit
            today_high = stock.high_prices[-1]
            today_low = stock.low_prices[-1]
            today_close = stock.close_prices[-1]

            # Determine exit price
            tp_price = entry_price * (1 + self._take_profit_pct)
            sl_price = entry_price * (1 - self._stop_loss_pct)

            if today_high >= tp_price:
                # Take-profit hit (assume we sell at TP price)
                exit_price = tp_price
                exit_reason = "TP"
            elif today_low <= sl_price:
                # Stop-loss hit (assume we sell at SL price)
                exit_price = sl_price
                exit_reason = "SL"
            else:
                # No TP/SL hit, sell at close
                exit_price = today_close
                exit_reason = "CLOSE"

            pnl_pct = (exit_price - entry_price) / entry_price * 100
            self.log.info(
                f"SELL {symbol} | {exit_reason} | "
                f"Entry={entry_price:.2f} | Exit≈{exit_price:.2f} | "
                f"PnL={pnl_pct:+.2f}%",
                color=LogColor.RED if pnl_pct < 0 else LogColor.GREEN,
            )

            self.close_all_positions(iid)
            self._pending_exits.pop(symbol, None)

    def _process_entries(self) -> None:
        """评分候选股票并买入 Top N。"""
        # Count current positions
        current_positions = sum(
            1 for s in self._stocks.values()
            if self.portfolio.is_net_long(s.instrument_id)
        )
        available_slots = self._max_positions - current_positions
        if available_slots <= 0:
            return

        # Score all candidates
        scores: dict[str, float] = {}
        for symbol, stock in self._stocks.items():
            # Skip if already holding
            if self.portfolio.is_net_long(stock.instrument_id):
                continue
            # Skip if already pending exit
            if symbol in self._pending_exits:
                continue

            score = self._score_stock(stock)
            if score > 0:
                scores[symbol] = score

        if not scores:
            return

        # Sort by score, take top N
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_stocks = ranked[:available_slots]

        for symbol, score in top_stocks:
            self._buy_stock(symbol, score)

    def _score_stock(self, stock: StockInfo) -> float:
        """
        综合评分一只股票。

        评分维度:
        1. 动量 (40%) - 近N日涨幅
        2. 成交量 (25%) - 今日量/20日均量
        3. 趋势 (20%) - 收盘价vs均线
        4. 波动率 (15%) - ATR/价格 (适中波动最佳)

        Returns
        -------
        float
            综合评分 (0-100), <= 0 表示不合格
        """
        n = len(stock.close_prices)
        if n < self._lookback + 5:
            return 0.0

        closes = stock.close_prices
        volumes = stock.volumes
        current_close = closes[-1]

        if current_close <= 0:
            return 0.0

        # --- 1. Momentum (动量) ---
        # 近 lookback 日涨幅
        past_close = closes[-self._lookback - 1]
        if past_close <= 0:
            return 0.0
        momentum = (current_close - past_close) / past_close

        # 今日涨幅
        today_open_like = closes[-2]  # approximate with yesterday close
        daily_return = (current_close - today_open_like) / today_open_like if today_open_like > 0 else 0

        # 过滤: 今日必须上涨且超过阈值
        if daily_return < self._momentum_threshold:
            return 0.0

        momentum_score = min(momentum * 100, 10) / 10 * 40  # Cap at 40

        # --- 2. Volume (成交量) ---
        avg_vol = sum(volumes[-21:-1]) / 20 if len(volumes) > 21 else (sum(volumes[:-1]) / max(len(volumes) - 1, 1))
        vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0

        # 过滤: 成交量必须放大
        if vol_ratio < self._volume_ratio_threshold:
            return 0.0

        volume_score = min(vol_ratio / 3.0, 1.0) * 25

        # --- 3. Trend (趋势) ---
        ma = sum(closes[-self._lookback:]) / self._lookback
        if current_close <= ma:
            return 0.0  # Must be above MA

        # MA slope (5-day regression)
        recent = closes[-5:]
        x = list(range(5))
        mean_x = 2.0
        mean_y = sum(recent) / 5
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, recent))
        denominator = sum((xi - mean_x) ** 2 for xi in x)
        slope = numerator / denominator if denominator > 0 else 0
        slope_pct = slope / current_close * 100 if current_close > 0 else 0

        trend_score = min(max(slope_pct * 50, 0), 20)

        # --- 4. Volatility (波动率) - ATR/Price ---
        atr_periods = min(14, n - 1)
        if atr_periods < 5:
            return 0.0

        tr_sum = 0
        for i in range(-atr_periods, 0):
            h = stock.high_prices[i]
            l = stock.low_prices[i]
            prev_c = closes[i - 1]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            tr_sum += tr
        atr = tr_sum / atr_periods
        atr_pct = atr / current_close

        # Sweet spot: 1-3% daily ATR
        if atr_pct < 0.005:
            vol_score = atr_pct / 0.005 * 10  # Too quiet
        elif atr_pct > 0.05:
            vol_score = max(0, 15 - (atr_pct - 0.05) * 300)  # Too volatile
        else:
            vol_score = 10 + (1 - abs(atr_pct - 0.02) / 0.02) * 5  # Good range

        # --- Composite Score ---
        total = momentum_score + volume_score + trend_score + vol_score
        return total

    def _buy_stock(self, symbol: str, score: float) -> None:
        """买入指定股票。"""
        stock = self._stocks[symbol]
        instrument = self._instruments.get(symbol)
        if instrument is None:
            return

        # Calculate position size
        account = self.portfolio.account(stock.venue)
        if account is None:
            return

        cash = account.balance_total(CNY)
        if cash is None:
            return

        available = float(cash.as_double())
        alloc = available * self._position_pct
        close_price = stock.close_prices[-1]

        if close_price <= 0:
            return

        lot_size = 100
        fee_factor = 1.0 + float(instrument.taker_fee)
        max_shares = int(alloc / (close_price * fee_factor))
        lots = max_shares // lot_size
        if lots > 1:
            lots -= 1  # Safety margin

        if lots <= 0:
            self.log.info(
                f"  Skip {symbol} | Not enough cash (alloc={alloc:.0f}, price={close_price:.2f})",
            )
            return

        shares = lots * lot_size
        self.log.info(
            f"BUY {symbol} | Score={score:.1f} | Price={close_price:.2f} | "
            f"Shares={shares} | Value={shares * close_price:,.0f}",
            color=LogColor.GREEN,
        )

        order: MarketOrder = self.order_factory.market(
            instrument_id=stock.instrument_id,
            order_side=OrderSide.BUY,
            quantity=instrument.make_qty(Decimal(str(shares))),
            time_in_force=TimeInForce.IOC,
        )
        self.submit_order(order)
        self._pending_exits[symbol] = close_price

    def on_data(self, data: Data) -> None:
        pass

    def on_event(self, event: Event) -> None:
        pass

    def on_stop(self) -> None:
        """策略停止。"""
        for stock in self._stocks.values():
            self.cancel_all_orders(stock.instrument_id)
            if self.config.close_positions_on_stop:
                self.close_all_positions(stock.instrument_id)
            self.unsubscribe_bars(self.config.bar_type)

    def on_save(self) -> dict[str, bytes]:
        return {}

    def on_load(self, state: dict[str, bytes]) -> None:
        pass

    def on_reset(self) -> None:
        self._bar_count = 0
        self._current_date = ""
        self._pending_exits.clear()
        for stock in self._stocks.values():
            stock.close_prices.clear()
            stock.volumes.clear()
            stock.high_prices.clear()
            stock.low_prices.clear()

    def on_dispose(self) -> None:
        pass


# ============================================================================
# Main
# ============================================================================

def get_venue(symbol: str) -> Venue:
    """Determine venue from symbol."""
    if symbol.startswith("6"):
        return SSE
    return SZSE


def main() -> None:
    print("=" * 70)
    print("  增强版一夜持股法回测 (Enhanced Overnight Hold)")
    print(f"  股票池: {len(STOCK_POOL)} 只 | 周期: {START_DATE} - {END_DATE}")
    print(f"  初始资金: {INITIAL_CAPITAL:,.0f} CNY")
    print("=" * 70)

    # -----------------------------------------------------------------
    # Step 1: Load data for all stocks
    # -----------------------------------------------------------------
    print("\n[1/5] 加载市场数据...")

    data_config = AShareDataConfig(
        source=DATA_SOURCE,
        adj_type="qfq",
        cache_enabled=True,
    )
    loader = AShareDataLoader(data_config)

    all_instruments: dict[str, Equity] = {}
    all_bars: dict[str, list] = {}

    for symbol in STOCK_POOL:
        bars = loader.load_daily_bars(
            symbol=symbol,
            start_date=START_DATE,
            end_date=END_DATE,
        )
        if bars:
            all_bars[symbol] = bars
            all_instruments[symbol] = create_stock_instrument(symbol)
            print(f"  ✓ {symbol}: {len(bars)} 根日线")
        else:
            print(f"  ✗ {symbol}: 无数据")

    if not all_bars:
        print("  ERROR: 无法获取任何股票数据。")
        return

    print(f"  共加载 {len(all_bars)} 只股票数据")

    # -----------------------------------------------------------------
    # Step 2: Configure BacktestEngine
    # -----------------------------------------------------------------
    print("\n[2/5] 配置回测引擎...")

    config = BacktestEngineConfig(
        trader_id=TraderId("ASHARE-ENHANCED-001"),
        logging=LoggingConfig(
            log_level="WARNING",
            log_colors=True,
            use_pyo3=False,
        ),
        risk_engine=RiskEngineConfig(
            bypass=True,
        ),
    )

    engine = BacktestEngine(config=config)

    # Add both venues
    for venue in [SSE, SZSE]:
        engine.add_venue(
            venue=venue,
            oms_type=OmsType.NETTING,
            book_type=BookType.L1_MBP,
            account_type=AccountType.CASH,
            base_currency=None,
            starting_balances=[Money(INITIAL_CAPITAL, CNY)],
            bar_execution=True,
            trade_execution=False,
        )

    # Add all instruments and bars
    bar_type = None
    for symbol, instrument in all_instruments.items():
        engine.add_instrument(instrument)
        bars = all_bars[symbol]
        engine.add_data(bars)
        if bar_type is None:
            bar_type = bars[0].bar_type

    print(f"  Venues: SSE, SZSE | Starting: {INITIAL_CAPITAL:,.0f} CNY")

    # -----------------------------------------------------------------
    # Step 3: Configure strategy
    # -----------------------------------------------------------------
    print("\n[3/5] 配置增强版策略...")

    instrument_ids = [inst.id for inst in all_instruments.values()]

    strategy_config = EnhancedOvernightConfig(
        instrument_ids=instrument_ids,
        bar_type=bar_type,
        lookback=10,
        max_positions=3,
        take_profit_pct=3.5,
        stop_loss_pct=2.0,
        momentum_threshold=0.5,
        volume_ratio_threshold=1.2,
        position_pct=0.30,
        close_positions_on_stop=True,
    )

    strategy = EnhancedOvernightStrategy(config=strategy_config)
    engine.add_strategy(strategy=strategy)

    print(
        f"  策略参数: lookback=10, max_pos=3, TP=3.5%, SL=2.0%\n"
        f"  动量阈值=0.5%, 放量阈值=1.2x, 仓位=30%",
    )

    # -----------------------------------------------------------------
    # Step 4: Run backtest
    # -----------------------------------------------------------------
    print("\n[4/5] 运行回测...\n")
    print("-" * 70)

    time.sleep(0.1)
    engine.run()

    # -----------------------------------------------------------------
    # Step 5: Results
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  增强版一夜持股法回测结果")
    print("=" * 70)

    # Collect all positions across venues
    all_positions_data = []
    for venue in [SSE, SZSE]:
        try:
            report = engine.trader.generate_account_report(venue)
            with pd.option_context(
                "display.max_rows", 200,
                "display.max_columns", None,
                "display.width", 300,
            ):
                print(f"\n--- {venue} Account Report ---")
                print(report)
        except Exception:
            pass

    # Positions report
    positions = engine.trader.generate_positions_report()
    if positions is not None and not positions.empty:
        print("\n--- Positions Report ---")
        with pd.option_context(
            "display.max_rows", 200,
            "display.max_columns", None,
            "display.width", 300,
        ):
            print(positions[[
                "instrument_id", "entry", "side", "quantity",
                "avg_px_open", "avg_px_close", "realized_return", "realized_pnl",
                "commissions", "ts_opened", "ts_closed",
            ]])

    # Summary
    print("\n" + "-" * 70)
    print("  SUMMARY")
    print("-" * 70)

    # Calculate total balance across venues
    total_balance = 0.0
    for venue in [SSE, SZSE]:
        try:
            report = engine.trader.generate_account_report(venue)
            if report is not None and not report.empty:
                balance_col = "total" if "total" in report.columns else "balance_total"
                total_balance += float(report.iloc[-1][balance_col])
        except Exception:
            pass

    total_pnl = total_balance - INITIAL_CAPITAL
    total_return = (total_pnl / INITIAL_CAPITAL) * 100

    print(f"  初始资金:    {INITIAL_CAPITAL:>12,.2f} CNY")
    print(f"  最终资金:    {total_balance:>12,.2f} CNY")
    print(f"  总盈亏:      {total_pnl:>12,.2f} CNY")
    print(f"  总收益率:    {total_return:>11.2f} %")

    if positions is not None and not positions.empty:
        returns = positions["realized_return"].astype(float)
        wins_count = (returns > 0).sum()
        losses_count = (returns < 0).sum()
        total_trades = len(positions)
        win_rate = wins_count / total_trades * 100 if total_trades > 0 else 0

        print(f"  总交易次数:  {total_trades:>12d}")
        print(f"  盈利次数:    {wins_count:>12d}")
        print(f"  亏损次数:    {losses_count:>12d}")
        print(f"  胜率:        {win_rate:>11.1f} %")
        if total_trades > 0:
            print(f"  平均收益:    {returns.mean() * 100:>11.2f} %")
            print(f"  最佳交易:    {returns.max() * 100:>11.2f} %")
            print(f"  最差交易:    {returns.min() * 100:>11.2f} %")

            # Profit factor
            gross_profit = returns[returns > 0].sum()
            gross_loss = abs(returns[returns < 0].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
            print(f"  盈亏比:      {profit_factor:>11.2f}")

            # Annualized return (approximate)
            years = 2.0  # 2023-2024
            annualized = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if total_return > -100 else 0
            print(f"  年化收益:    {annualized:>11.2f} %")

    # -----------------------------------------------------------------
    # Tearsheet
    # -----------------------------------------------------------------
    try:
        from nautilus_trader.analysis import TearsheetConfig
        from nautilus_trader.analysis.tearsheet import create_tearsheet

        print("\n--- 生成 Tearsheet 报告 ---")
        tearsheet_config = TearsheetConfig(theme="plotly_white", locale="zh_CN")
        output_path = "ashare_enhanced_overnight_tearsheet.html"
        create_tearsheet(
            engine=engine,
            output_path=output_path,
            config=tearsheet_config,
        )
        print(f"Tearsheet 已保存: {output_path}")
    except Exception as e:
        print(f"Tearsheet 生成失败: {e}")

    engine.reset()
    engine.dispose()

    print("\n" + "=" * 70)
    print("  回测完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
