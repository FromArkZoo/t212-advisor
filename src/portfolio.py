"""Portfolio analysis engine for Trading 212 portfolio data."""

from datetime import datetime

from src.config import TICKER_MAP

DEFAULT_FX_RATE = 1.29  # approximate USD/GBP


def get_position_value_gbp(pos: dict, fx_rate: float = DEFAULT_FX_RATE) -> float:
    """Calculate position value in GBP."""
    info = TICKER_MAP.get(pos["ticker"], {})
    native_value = pos["quantity"] * pos["currentPrice"]
    if info.get("geo") == "GBP":
        return native_value
    return native_value / fx_rate


def get_allocation_by_holding(
    positions: list, account: dict, fx_rate: float = DEFAULT_FX_RATE
) -> list:
    """Returns list of dicts: [{name, t212_ticker, value_gbp, pct}] sorted by value descending."""
    total = account["totalValue"]
    result = []
    for pos in positions:
        info = TICKER_MAP.get(pos["ticker"], {"name": pos["ticker"]})
        val = get_position_value_gbp(pos, fx_rate)
        result.append(
            {
                "name": info.get("name", pos["ticker"]),
                "t212_ticker": pos["ticker"],
                "value_gbp": round(val, 2),
                "pct": round(val / total * 100, 2) if total else 0,
            }
        )
    # Add cash
    cash = account["cash"]["availableToTrade"] + account["cash"].get("inPies", 0)
    result.append(
        {
            "name": "Cash",
            "t212_ticker": "CASH",
            "value_gbp": round(cash, 2),
            "pct": round(cash / total * 100, 2) if total else 0,
        }
    )
    result.sort(key=lambda x: x["value_gbp"], reverse=True)
    return result


def get_allocation_by_sector(
    positions: list, fx_rate: float = DEFAULT_FX_RATE
) -> dict:
    """Returns {sector: total_value_gbp} sorted by value descending."""
    sectors = {}
    for pos in positions:
        info = TICKER_MAP.get(pos["ticker"], {"sector": "Unknown"})
        sector = info.get("sector", "Unknown")
        val = get_position_value_gbp(pos, fx_rate)
        sectors[sector] = sectors.get(sector, 0) + val
    return {
        k: round(v, 2)
        for k, v in sorted(sectors.items(), key=lambda x: x[1], reverse=True)
    }


def get_allocation_by_asset_class(
    positions: list, fx_rate: float = DEFAULT_FX_RATE
) -> dict:
    """Returns {asset_class: total_value_gbp} sorted by value descending."""
    classes = {}
    for pos in positions:
        info = TICKER_MAP.get(pos["ticker"], {"asset_class": "Unknown"})
        ac = info.get("asset_class", "Unknown")
        val = get_position_value_gbp(pos, fx_rate)
        classes[ac] = classes.get(ac, 0) + val
    return {
        k: round(v, 2)
        for k, v in sorted(classes.items(), key=lambda x: x[1], reverse=True)
    }


def get_pnl_by_position(positions: list) -> list:
    """Returns list of dicts with P&L info sorted by total_pnl ascending (worst first)."""
    result = []
    for pos in positions:
        info = TICKER_MAP.get(pos["ticker"], {"name": pos["ticker"]})
        ppl = pos.get("ppl", 0) or 0
        fx = pos.get("fxPpl", 0) or 0
        cost = pos["quantity"] * pos["averagePrice"]
        total_pnl = ppl + fx
        pct = (total_pnl / cost * 100) if cost else 0
        result.append(
            {
                "name": info.get("name", pos["ticker"]),
                "t212_ticker": pos["ticker"],
                "ppl": round(ppl, 2),
                "fxPpl": round(fx, 2),
                "total_pnl": round(total_pnl, 2),
                "cost_basis": round(cost, 2),
                "pct_return": round(pct, 2),
            }
        )
    result.sort(key=lambda x: x["total_pnl"])
    return result


def get_fx_exposure(
    positions: list, account: dict, fx_rate: float = DEFAULT_FX_RATE
) -> dict:
    """Returns {currency: value_gbp} showing FX exposure."""
    exposure = {"GBP": account["cash"]["availableToTrade"]}
    for pos in positions:
        info = TICKER_MAP.get(pos["ticker"], {})
        geo = info.get("geo", "USD")
        val = get_position_value_gbp(pos, fx_rate)
        exposure[geo] = exposure.get(geo, 0) + val
    return {k: round(v, 2) for k, v in exposure.items()}


def get_concentration_risk(
    positions: list, account: dict, fx_rate: float = DEFAULT_FX_RATE
) -> list:
    """Returns positions as pct of total portfolio, sorted descending. Flags >10% as concentrated."""
    alloc = get_allocation_by_holding(positions, account, fx_rate)
    for item in alloc:
        item["concentrated"] = item["pct"] > 10
    return alloc


def get_dividend_summary(dividends: list) -> dict:
    """Analyze dividend history. Returns {total_received, by_ticker, projected_annual}."""
    total = sum(d["amount"] for d in dividends)
    by_ticker = {}
    for d in dividends:
        name = d.get("instrument", {}).get("name", d.get("ticker", "Unknown"))
        by_ticker[name] = by_ticker.get(name, 0) + d["amount"]
    by_ticker = {
        k: round(v, 2)
        for k, v in sorted(by_ticker.items(), key=lambda x: x[1], reverse=True)
    }
    projected = 0.0
    if dividends:
        dates = []
        for d in dividends:
            paid_on = d.get("paidOn", "")
            if not paid_on:
                continue
            try:
                dt = datetime.fromisoformat(
                    paid_on.replace("+02:00", "+00:00").replace("+03:00", "+00:00")
                )
                dates.append(dt)
            except (ValueError, TypeError):
                pass
        if len(dates) >= 2:
            span_days = (max(dates) - min(dates)).days or 1
            projected = total / span_days * 365
        else:
            projected = total * 4  # rough quarterly estimate
    return {
        "total_received": round(total, 2),
        "by_ticker": by_ticker,
        "projected_annual": round(projected, 2),
    }


def get_cash_drag(account: dict) -> dict:
    """Calculate cash drag - uninvested cash as % of total portfolio."""
    cash = account["cash"]["availableToTrade"] + account["cash"].get("inPies", 0)
    total = account["totalValue"]
    return {
        "cash_gbp": round(cash, 2),
        "total_gbp": round(total, 2),
        "pct": round(cash / total * 100, 2) if total else 0,
    }


def get_portfolio_summary(
    positions: list,
    account: dict,
    dividends: list = None,
    fx_rate: float = DEFAULT_FX_RATE,
) -> dict:
    """Complete portfolio summary for AI advisor context."""
    return {
        "account": {
            "total_value": account["totalValue"],
            "currency": account.get("currency", "GBP"),
            "cash": account["cash"]["availableToTrade"],
            "invested": account["investments"]["currentValue"],
            "total_cost": account["investments"]["totalCost"],
            "realised_pnl": account["investments"]["realizedProfitLoss"],
            "unrealised_pnl": account["investments"]["unrealizedProfitLoss"],
        },
        "allocation": get_allocation_by_holding(positions, account, fx_rate),
        "sectors": get_allocation_by_sector(positions, fx_rate),
        "asset_classes": get_allocation_by_asset_class(positions, fx_rate),
        "pnl": get_pnl_by_position(positions),
        "fx_exposure": get_fx_exposure(positions, account, fx_rate),
        "concentration": get_concentration_risk(positions, account, fx_rate),
        "cash_drag": get_cash_drag(account),
        "dividends": get_dividend_summary(dividends) if dividends else None,
    }
