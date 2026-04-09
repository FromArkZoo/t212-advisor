import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"

T212_BASE_URL = "https://live.trading212.com/api/v0"
T212_API_KEY = os.getenv("T212_API_KEY", "")
T212_API_SECRET = os.getenv("T212_API_SECRET", "")
T212_ENV = os.getenv("T212_ENV", "live")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Illustrative mapping of Trading 212 legacy tickers to enriched metadata.
# Extend with your own holdings as needed — keys follow the T212 format
# (e.g. SYMBOL_US_EQ for US equities, SYMBOLl_EQ for LSE-listed instruments).
# Unknown tickers fall through to get_ticker_info() defaults.
TICKER_MAP = {
    "MSFT_US_EQ": {"name": "Microsoft", "ticker": "MSFT", "sector": "Mega-cap Tech", "geo": "USD", "asset_class": "Equity"},
    "NVDA_US_EQ": {"name": "NVIDIA", "ticker": "NVDA", "sector": "Semiconductors", "geo": "USD", "asset_class": "Equity"},
    "TSLA_US_EQ": {"name": "Tesla", "ticker": "TSLA", "sector": "Automotive / EV", "geo": "USD", "asset_class": "Equity"},
    "META_US_EQ": {"name": "Meta Platforms", "ticker": "META", "sector": "Mega-cap Tech", "geo": "USD", "asset_class": "Equity"},
    "SPY_US_EQ": {"name": "SPDR S&P 500 ETF", "ticker": "SPY", "sector": "US ETF", "geo": "USD", "asset_class": "ETF"},
    "QQQ_US_EQ": {"name": "Invesco QQQ Trust", "ticker": "QQQ", "sector": "US Tech ETF", "geo": "USD", "asset_class": "ETF"},
}


def get_ticker_info(t212_ticker: str) -> dict:
    return TICKER_MAP.get(t212_ticker, {
        "name": t212_ticker,
        "ticker": t212_ticker,
        "sector": "Unknown",
        "geo": "Unknown",
        "asset_class": "Unknown",
    })
