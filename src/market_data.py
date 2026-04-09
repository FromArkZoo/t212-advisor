"""Market data enrichment using yfinance."""

import yfinance as yf
from src.config import TICKER_MAP

_cache = {}


def get_market_data(t212_ticker: str) -> dict:
    """Fetch market data for a single position. Returns dict with:
    - name, real_ticker, sector, geo, asset_class (from TICKER_MAP)
    - pe_ratio, dividend_yield, market_cap, fifty_two_week_low, fifty_two_week_high
    - currency, industry
    Caches results in memory to avoid repeated API calls.
    """
    if t212_ticker in _cache:
        return _cache[t212_ticker]

    info = TICKER_MAP.get(t212_ticker, {})
    real_ticker = info.get("ticker", t212_ticker)

    result = {
        "name": info.get("name", t212_ticker),
        "real_ticker": real_ticker,
        "sector": info.get("sector", "Unknown"),
        "geo": info.get("geo", "Unknown"),
        "asset_class": info.get("asset_class", "Unknown"),
    }

    try:
        stock = yf.Ticker(real_ticker)
        yf_info = stock.info
        result.update({
            "pe_ratio": yf_info.get("trailingPE"),
            "dividend_yield": yf_info.get("dividendYield"),
            "market_cap": yf_info.get("marketCap"),
            "fifty_two_week_low": yf_info.get("fiftyTwoWeekLow"),
            "fifty_two_week_high": yf_info.get("fiftyTwoWeekHigh"),
            "currency": yf_info.get("currency", info.get("geo", "USD")),
            "industry": yf_info.get("industry", info.get("sector", "Unknown")),
        })
    except Exception:
        result.update({
            "pe_ratio": None,
            "dividend_yield": None,
            "market_cap": None,
            "fifty_two_week_low": None,
            "fifty_two_week_high": None,
            "currency": info.get("geo", "USD"),
            "industry": info.get("sector", "Unknown"),
        })

    _cache[t212_ticker] = result
    return result


def enrich_positions(positions: list) -> list:
    """Enrich a list of position dicts with market data.
    Each position dict has at minimum a 'ticker' field (T212 ticker).
    Returns list of dicts with position data + market data merged.
    """
    enriched = []
    for pos in positions:
        t212_ticker = pos.get("ticker") if isinstance(pos, dict) else pos.ticker
        market = get_market_data(t212_ticker)
        if isinstance(pos, dict):
            merged = {**pos, **market}
        else:
            merged = {**pos.model_dump(), **market}
        enriched.append(merged)
    return enriched


def get_all_market_data(t212_tickers: list) -> dict:
    """Batch fetch market data for multiple tickers. Returns {t212_ticker: market_data_dict}."""
    return {t: get_market_data(t) for t in t212_tickers}
