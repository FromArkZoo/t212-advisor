# Trading 212 Portfolio Advisor

A local CLI + web dashboard that connects to the Trading 212 API, pulls portfolio data, and provides AI-powered investment analysis and rebalancing recommendations using the Claude API.

> **Not financial advice.** This tool provides analysis and information only. All investment decisions are the user's own.

## What it does

- Pulls current positions, order history, dividends, and transactions from the Trading 212 API (read-only)
- Enriches holdings with market data: sector, P/E, dividend yield, market cap, 52-week range
- Runs portfolio analysis: allocation breakdowns (holding / sector / geography / asset class), concentration risk, unrealised P&L, cash drag, FX exposure
- Uses Claude (`claude-opus-4-6`) for portfolio health checks, rebalancing suggestions, dividend optimisation, position deep dives, and what-if scenarios
- Serves a local dashboard with charts, a dividend calendar, and a chat interface for portfolio questions

## Architecture

```
t212-advisor/
├── README.md
├── .env                    # API keys (gitignored)
├── requirements.txt
├── src/
│   ├── t212_client.py      # Trading 212 API client (read-only)
│   ├── market_data.py      # Market data enrichment
│   ├── portfolio.py        # Portfolio analysis engine
│   ├── advisor.py          # Claude-powered analysis & recommendations
│   ├── models.py           # Data models (Position, Order, Dividend, …)
│   └── config.py           # Configuration & env loading
├── dashboard/
│   └── app.py              # Local web dashboard
├── data/
│   ├── samples/            # Synthetic demo fixtures (safe to commit)
│   └── snapshots/          # Runtime portfolio snapshots (gitignored)
└── tests/
```

## Tech stack

- Python 3.12+
- `anthropic` (Claude API)
- `requests` (T212 API)
- `streamlit` + `plotly` (dashboard + charts)
- `pydantic` (data models)
- `python-dotenv` (config)

## Trading 212 API notes

- Base URL: `https://live.trading212.com/api/v0`
- Auth: Basic auth (base64 of `key:secret`)
- Key endpoints:
  - `GET /equity/account/summary` (rate: 1 req / 5s)
  - `GET /equity/portfolio`
  - `GET /equity/history/orders?limit=50` (paginated)
  - `GET /equity/history/dividends?limit=50` (paginated)
  - `GET /equity/history/transactions?limit=50` (paginated)
- Pagination: cursor-based via `nextPagePath`; client handles relative-path quirks
- Rate limits surfaced in response headers (`x-ratelimit-remaining`, `x-ratelimit-reset`); client caches responses locally
- **Read-only** — no order-placing endpoints are enabled

## AI advisor modes

- **Portfolio Health Check** — overall assessment, concentration risk, diversification
- **Rebalancing Suggestions** — target vs actual allocation
- **Dividend Optimisation** — yield analysis, coverage, ex-date calendar
- **Position Deep Dive** — detailed analysis of any single holding
- **What-If Scenarios** — "What if I sell X and buy Y?"

All recommendations include reasoning and trade-offs, and are prefaced with the "not financial advice" disclaimer.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the project root:

```
T212_API_KEY=your_key_here
T212_API_SECRET=your_secret_here
T212_ENV=live
ANTHROPIC_API_KEY=your_anthropic_key
```

Run the dashboard:

```bash
streamlit run dashboard/app.py
```

## Sample data

`data/samples/` contains synthetic fixtures matching the T212 API schema (fake tickers, round-number quantities, obvious test values). Use these to explore the repo without a live API key or account. Real portfolio snapshots are runtime-generated from the T212 API and are never committed.

## Development notes

- Always handle T212 API rate limits gracefully
- Cache API responses locally to avoid hammering the API
- Never store API keys in code — always via `.env`
- All financial figures in GBP unless stated otherwise
- ISA tax wrapper context is relevant for UK-based recommendations
