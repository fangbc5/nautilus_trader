#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
#  A-Share Strategy Switching Demo
# -------------------------------------------------------------------------------------------------
"""
Demonstrates the screening strategy adapter interface.

Shows how to:
1. List all available strategies
2. Switch between strategies by name
3. Compare strategies side-by-side
4. One-liner usage for each strategy

Usage:
    python -m examples.backtest.ashare_strategy_switch_demo
"""

import pandas as pd

from nautilus_trader.screener import compare_strategies
from nautilus_trader.screener import create_strategy
from nautilus_trader.screener import list_strategies
from nautilus_trader.screener.providers import DemoDataProvider


def main() -> None:
    print("=" * 70)
    print("  🎯 选股策略适配器演示 - Strategy Adapter Demo")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. 列出所有可用策略
    # ------------------------------------------------------------------
    print("\n📋 可用策略列表:")
    print("-" * 70)
    strategies = list_strategies()
    for i, s in enumerate(strategies, 1):
        print(f"  {i}. {s['display_name']} (name=\"{s['name']}\")")
        print(f"     {s['description']}")
    print()

    # ------------------------------------------------------------------
    # 2. 加载数据
    # ------------------------------------------------------------------
    print("[数据加载] 使用 Demo 数据 (30 只 A 股)")
    provider = DemoDataProvider()
    data = provider.get_screening_data()
    print(f"  已加载 {len(data)} 只股票\n")

    # ------------------------------------------------------------------
    # 3. 逐个策略切换演示
    # ------------------------------------------------------------------
    demo_strategies = ["value", "quality", "growth", "garp", "all_weather"]

    for strat_name in demo_strategies:
        strategy = create_strategy(strat_name, top_n=5)
        print("=" * 70)
        print(f"  🔀 切换策略: {strategy.display_name}")
        print(f"  {strategy.description}")
        print(f"  因子: {strategy.factor_names}")
        print("-" * 70)

        result = strategy.screen(data)

        if result.count > 0:
            display_cols = ["name", "industry", "composite_score"]
            available = [c for c in display_cols if c in result.data.columns]
            with pd.option_context("display.width", 150, "display.float_format", "{:.1f}".format):
                print(result.data[available].to_string())
        else:
            print("  (无符合条件的股票)")
        print()

    # ------------------------------------------------------------------
    # 4. 策略对比
    # ------------------------------------------------------------------
    print("=" * 70)
    print("  ⚖️  策略对比: 不同策略选出 Top 3")
    print("=" * 70)

    comparison = compare_strategies(data, strategy_names=demo_strategies, top_n=3)

    print(f"\n{'策略':<12} {'Top 1':<20} {'Top 2':<20} {'Top 3':<20}")
    print("-" * 72)
    for strat_name, result in comparison.items():
        strategy = create_strategy(strat_name, top_n=3)
        names = []
        for sym in result.symbols[:3]:
            if "name" in result.data.columns:
                n = result.data.loc[sym, "name"]
                names.append(f"{n}({sym})")
            else:
                names.append(sym)
        row = " | ".join(f"{n:<18}" for n in names)
        print(f"  {strategy.display_name:<10} {row}")

    # ------------------------------------------------------------------
    # 5. 一行代码切换策略
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  💡 一行代码切换策略")
    print("=" * 70)
    print("""
  # 价值策略
  result = create_strategy("value", top_n=10).screen(data)

  # 质量策略
  result = create_strategy("quality", top_n=10).screen(data)

  # GARP策略
  result = create_strategy("garp", top_n=10).screen(data)

  # 成长策略
  result = create_strategy("growth", top_n=10).screen(data)

  # 全天候策略
  result = create_strategy("all_weather", top_n=10).screen(data)

  # 红利策略
  result = create_strategy("dividend", top_n=10).screen(data)

  # 动量策略
  result = create_strategy("momentum", top_n=10).screen(data)

  # 对比所有策略
  results = compare_strategies(data, top_n=5)
""")

    # ------------------------------------------------------------------
    # 6. 自定义策略
    # ------------------------------------------------------------------
    print("=" * 70)
    print("  🔧 自定义策略 - 继承 ScreeningStrategy")
    print("=" * 70)
    print("""
  from nautilus_trader.screener.strategies import ScreeningStrategy

  class MyStrategy(ScreeningStrategy):
      @property
      def name(self) -> str:
          return "my_strategy"

      @property
      def display_name(self) -> str:
          return "自定义策略"

      @property
      def description(self) -> str:
          return "我的选股逻辑"

      def build_config(self, **kwargs) -> ScreenerConfig:
          return ScreenerConfig(
              factors=[
                  FactorConfig(name="roe", params={"min_roe": 20}, weight=2.0),
                  FactorConfig(name="pe", params={"max_pe": 30}, weight=1.0),
              ],
              top_n=kwargs.get("top_n", self._top_n),
          )

  # 注册到全局注册表
  from nautilus_trader.screener.strategies import STRATEGY_REGISTRY
  STRATEGY_REGISTRY["my_strategy"] = MyStrategy

  # 使用
  result = create_strategy("my_strategy").screen(data)
""")

    print("=" * 70)
    print("  ✅ 策略适配器演示完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
