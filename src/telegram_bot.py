"""Telegram bot integration — library module for command routing and response formatting."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.t212_client import T212Client
from src.portfolio import (
    get_allocation_by_holding,
    get_allocation_by_sector,
    get_cash_drag,
    get_dividend_summary,
    get_pnl_by_position,
    get_portfolio_summary,
)
from src.advisor import Advisor, DISCLAIMER
from src.config import TICKER_MAP

FREE_COMMANDS = {"summary", "positions", "pnl", "dividends", "help", "start"}
PAID_COMMANDS = {"analyze", "health", "rebalance", "ask"}

CONFIRMATION_PROMPT = (
    "This request will incur an API fee. Proceed?\n\n"
    "Reply *YES* to confirm, or anything else to cancel."
)


@dataclass
class PendingConfirmation:
    command: str
    args: str = ""


@dataclass
class ParsedCommand:
    command: str
    args: str = ""
    is_free: bool = True


# Track pending confirmations per chat_id
_pending: dict[str, PendingConfirmation] = {}


def classify_message(text: str) -> ParsedCommand | None:
    text = text.strip()
    if not text:
        return None

    if text.upper() in ("YES", "Y"):
        return ParsedCommand(command="confirm", args="", is_free=True)
    if text.upper() in ("NO", "N", "CANCEL"):
        return ParsedCommand(command="cancel", args="", is_free=True)

    if not text.startswith("/"):
        return ParsedCommand(command="ask", args=text, is_free=False)

    parts = text.split(maxsplit=1)
    cmd = parts[0].lstrip("/").lower().split("@")[0]  # strip bot mention
    args = parts[1] if len(parts) > 1 else ""

    if cmd in FREE_COMMANDS:
        return ParsedCommand(command=cmd, args=args, is_free=True)
    if cmd in PAID_COMMANDS:
        return ParsedCommand(command=cmd, args=args, is_free=False)

    return None


def _fmt_gbp(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}£{value:,.2f}"


def _load_data(client: T212Client) -> tuple[dict, list, list]:
    account = client.get_account_summary()
    positions = client.get_positions()
    dividends = client.get_dividends()
    return account, positions, dividends


# --- Free command handlers ---

def handle_summary(client: T212Client) -> str:
    account, positions, _ = _load_data(client)
    inv = account["investments"]
    cash = account["cash"]

    total = account["totalValue"]
    invested = inv["currentValue"]
    unrealised = inv["unrealizedProfitLoss"]
    realised = inv["realizedProfitLoss"]
    available = cash["availableToTrade"]

    sectors = get_allocation_by_sector(positions)
    cash_info = get_cash_drag(account)

    lines = [
        "*Portfolio Summary*",
        "",
        f"Total Value: £{total:,.2f}",
        f"Invested: £{invested:,.2f}",
        f"Cash: £{available:,.2f} ({cash_info['pct']:.1f}%)",
        f"Unrealised P&L: {_fmt_gbp(unrealised)}",
        f"Realised P&L: {_fmt_gbp(realised)}",
        "",
        f"*Positions:* {len(positions)}",
        "",
        "*Sector Breakdown:*",
    ]
    for sector, val in sectors.items():
        lines.append(f"  {sector}: £{val:,.2f}")

    return "\n".join(lines)


def handle_positions(client: T212Client) -> str:
    account, positions, _ = _load_data(client)
    alloc = get_allocation_by_holding(positions, account)

    lines = ["*Positions by Value*", ""]
    for h in alloc:
        if h["t212_ticker"] == "CASH":
            lines.append(f"  Cash: £{h['value_gbp']:,.2f} ({h['pct']:.1f}%)")
        else:
            lines.append(f"  {h['name']}: £{h['value_gbp']:,.2f} ({h['pct']:.1f}%)")

    return "\n".join(lines)


def handle_pnl(client: T212Client) -> str:
    _, positions, _ = _load_data(client)
    pnl = get_pnl_by_position(positions)

    lines = ["*P&L by Position*", ""]
    for p in pnl:
        emoji = "🟢" if p["total_pnl"] >= 0 else "🔴"
        lines.append(
            f"  {emoji} {p['name']}: {_fmt_gbp(p['total_pnl'])} ({p['pct_return']:+.1f}%)"
        )

    return "\n".join(lines)


def handle_dividends(client: T212Client) -> str:
    _, _, dividends = _load_data(client)
    if not dividends:
        return "No dividend history found."

    summary = get_dividend_summary(dividends)
    lines = [
        "*Dividend Summary*",
        "",
        f"Total Received: £{summary['total_received']:,.2f}",
        f"Projected Annual: £{summary['projected_annual']:,.2f}",
        "",
        "*By Holding:*",
    ]
    for name, amount in summary["by_ticker"].items():
        lines.append(f"  {name}: £{amount:,.2f}")

    return "\n".join(lines)


def handle_help() -> str:
    return (
        "*T212 Portfolio Advisor*\n"
        "\n"
        "*Free commands:*\n"
        "  /summary — Portfolio overview\n"
        "  /positions — Holdings by value\n"
        "  /pnl — P\\&L breakdown\n"
        "  /dividends — Dividend history\n"
        "\n"
        "*AI-powered commands* (incur API fee):\n"
        "  /health — Portfolio health check\n"
        "  /analyze — Full portfolio analysis\n"
        "  /rebalance — Rebalancing suggestions\n"
        "  /ask <question> — Ask anything about your portfolio\n"
        "\n"
        "Just type a question to use /ask implicitly."
    )


# --- Paid command handlers ---

def handle_health(client: T212Client, advisor: Advisor) -> str:
    account, positions, dividends = _load_data(client)
    portfolio_data = get_portfolio_summary(positions, account, dividends)
    return advisor.analyze("health_check", portfolio_data)


def handle_analyze(client: T212Client, advisor: Advisor) -> str:
    account, positions, dividends = _load_data(client)
    portfolio_data = get_portfolio_summary(positions, account, dividends)
    return advisor.analyze("health_check", portfolio_data)


def handle_rebalance(client: T212Client, advisor: Advisor) -> str:
    account, positions, dividends = _load_data(client)
    portfolio_data = get_portfolio_summary(positions, account, dividends)
    return advisor.analyze("rebalancing", portfolio_data)


def handle_ask(question: str, client: T212Client, advisor: Advisor) -> str:
    account, positions, dividends = _load_data(client)
    portfolio_data = get_portfolio_summary(positions, account, dividends)
    return advisor.chat(question, portfolio_data)


# --- Confirmation flow ---

def set_pending(chat_id: str, command: str, args: str = "") -> None:
    _pending[chat_id] = PendingConfirmation(command=command, args=args)


def get_pending(chat_id: str) -> PendingConfirmation | None:
    return _pending.get(chat_id)


def clear_pending(chat_id: str) -> None:
    _pending.pop(chat_id, None)


# --- Main dispatcher ---

def handle_message(
    chat_id: str,
    text: str,
    client: T212Client,
    advisor: Advisor,
) -> str:
    """Route an incoming message and return the response text."""
    parsed = classify_message(text)
    if parsed is None:
        return handle_help()

    # Handle confirmation responses
    if parsed.command == "confirm":
        pending = get_pending(chat_id)
        if not pending:
            return "Nothing pending. Send /help to see available commands."
        clear_pending(chat_id)
        return _execute_paid(pending.command, pending.args, client, advisor)

    if parsed.command == "cancel":
        if get_pending(chat_id):
            clear_pending(chat_id)
            return "Cancelled."
        return "Nothing to cancel."

    # Free commands
    if parsed.is_free:
        clear_pending(chat_id)
        return _execute_free(parsed.command, client)

    # Paid commands — require confirmation
    set_pending(chat_id, parsed.command, parsed.args)
    return CONFIRMATION_PROMPT


def _execute_free(command: str, client: T212Client) -> str:
    if command == "summary":
        return handle_summary(client)
    if command == "positions":
        return handle_positions(client)
    if command == "pnl":
        return handle_pnl(client)
    if command == "dividends":
        return handle_dividends(client)
    if command in ("help", "start"):
        return handle_help()
    return handle_help()


def _execute_paid(
    command: str, args: str, client: T212Client, advisor: Advisor
) -> str:
    if command == "health":
        return handle_health(client, advisor)
    if command == "analyze":
        return handle_analyze(client, advisor)
    if command == "rebalance":
        return handle_rebalance(client, advisor)
    if command == "ask":
        return handle_ask(args, client, advisor)
    return f"Unknown command: {command}"
