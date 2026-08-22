from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv
import os

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class StrategyConfig:
    name: str
    lookback_bars: int
    entry_threshold_pct: float
    exit_threshold_pct: float
    stop_loss_pct: float
    timeframe: str
    position_size_usd: float


@dataclass
class Settings:
    asset_class: str
    symbols: list
    strategy: StrategyConfig
    poll_interval_seconds: int
    max_daily_loss_usd: float
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_paper: bool


def load_settings(path: Path = None) -> Settings:
    path = path or REPO_ROOT / "config" / "settings.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)

    strategy = StrategyConfig(**raw["strategy"])

    return Settings(
        asset_class=raw["asset_class"],
        symbols=raw["symbols"],
        strategy=strategy,
        poll_interval_seconds=raw["loop"]["poll_interval_seconds"],
        max_daily_loss_usd=raw["risk"]["max_daily_loss_usd"],
        alpaca_api_key=os.environ.get("ALPACA_API_KEY", ""),
        alpaca_secret_key=os.environ.get("ALPACA_SECRET_KEY", ""),
        alpaca_paper=os.environ.get("ALPACA_PAPER", "true").lower() == "true",
    )
