import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from algo_trading.strategy.base import Signal
from algo_trading.strategy.momentum import MomentumStrategy


def _bars(closes):
    return pd.DataFrame({"close": closes})


def test_buys_on_strong_upward_momentum():
    strategy = MomentumStrategy(lookback_bars=3, entry_threshold_pct=0.3, exit_threshold_pct=-0.1)
    bars = _bars([100, 100.1, 100.2, 100.5])  # +0.5% over 3 bars
    assert strategy.generate_signal(bars, has_open_position=False) == Signal.BUY


def test_holds_on_weak_momentum():
    strategy = MomentumStrategy(lookback_bars=3, entry_threshold_pct=0.3, exit_threshold_pct=-0.1)
    bars = _bars([100, 100.0, 100.05, 100.1])  # +0.1% over 3 bars
    assert strategy.generate_signal(bars, has_open_position=False) == Signal.HOLD


def test_sells_on_pullback_when_holding_position():
    strategy = MomentumStrategy(lookback_bars=3, entry_threshold_pct=0.3, exit_threshold_pct=-0.1)
    bars = _bars([100, 99.9, 99.85, 99.8])  # -0.2% over 3 bars
    assert strategy.generate_signal(bars, has_open_position=True) == Signal.SELL


def test_holds_flat_when_no_position_and_no_momentum():
    strategy = MomentumStrategy(lookback_bars=3, entry_threshold_pct=0.3, exit_threshold_pct=-0.1)
    bars = _bars([100, 100, 100, 100])
    assert strategy.generate_signal(bars, has_open_position=False) == Signal.HOLD


def test_holds_when_not_enough_bars():
    strategy = MomentumStrategy(lookback_bars=5, entry_threshold_pct=0.3, exit_threshold_pct=-0.1)
    bars = _bars([100, 101])
    assert strategy.generate_signal(bars, has_open_position=False) == Signal.HOLD
