"""Claude-powered AI portfolio advisor."""

import anthropic

from src.config import ANTHROPIC_API_KEY

DISCLAIMER = (
    "⚠️ This is not financial advice. All analysis is for informational "
    "purposes only. Investment decisions are your own responsibility."
)

SYSTEM_PROMPT = """You are an elite portfolio manager with 20+ years experience across equities, ETFs, and thematic investing. You are assisting a UK-based private investor using Trading 212. Their primary goal is revenue generation — maximising total returns through a combination of capital appreciation and dividend income. You think in terms of risk-adjusted returns, position sizing, concentration risk, sector rotation, and macro tailwinds. You are direct, opinionated, and back every recommendation with clear reasoning. You flag when a position is dead money that should be recycled into higher-conviction ideas. You always caveat that this is analysis, not regulated financial advice."""


class Advisor:
    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=api_key or ANTHROPIC_API_KEY)
        self.model = "claude-opus-4-6"

    def _build_context(self, portfolio_data: dict) -> str:
        """Format portfolio data into a readable context string for the prompt."""
        lines = []

        # Account overview
        acct = portfolio_data.get("account", {})
        lines.append("## Account Overview")
        lines.append(f"- Total Value: £{acct.get('total_value', 0):,.2f}")
        lines.append(f"- Invested: £{acct.get('invested', 0):,.2f}")
        lines.append(f"- Cash Available: £{acct.get('cash', 0):,.2f}")
        lines.append(f"- Unrealised P&L: £{acct.get('unrealised_pnl', 0):,.2f}")
        lines.append(f"- Realised P&L: £{acct.get('realised_pnl', 0):,.2f}")
        lines.append("")

        # Holdings
        alloc = portfolio_data.get("allocation", [])
        if alloc:
            lines.append("## Holdings (by value)")
            for h in alloc:
                lines.append(
                    f"- {h['name']}: £{h['value_gbp']:,.2f} ({h['pct']:.1f}%)"
                )
            lines.append("")

        # P&L by position
        pnl = portfolio_data.get("pnl", [])
        if pnl:
            lines.append("## P&L by Position")
            for p in pnl:
                sign = "+" if p["total_pnl"] >= 0 else ""
                lines.append(
                    f"- {p['name']}: {sign}£{p['total_pnl']:,.2f} "
                    f"({sign}{p['pct_return']:.1f}%)"
                )
            lines.append("")

        # Sector allocation
        sectors = portfolio_data.get("sectors", {})
        if sectors:
            lines.append("## Sector Exposure")
            for s, v in sectors.items():
                lines.append(f"- {s}: £{v:,.2f}")
            lines.append("")

        # FX exposure
        fx = portfolio_data.get("fx_exposure", {})
        if fx:
            lines.append("## FX Exposure")
            for cur, val in fx.items():
                lines.append(f"- {cur}: £{val:,.2f}")
            lines.append("")

        # Cash drag
        cd = portfolio_data.get("cash_drag", {})
        if cd:
            lines.append(
                f"## Cash: £{cd.get('cash_gbp', 0):,.2f} "
                f"({cd.get('pct', 0):.1f}% of portfolio)"
            )
            lines.append("")

        # Dividends
        divs = portfolio_data.get("dividends")
        if divs:
            lines.append("## Dividends")
            lines.append(f"- Total received: £{divs['total_received']:,.2f}")
            lines.append(f"- Projected annual: £{divs['projected_annual']:,.2f}")
            lines.append("")

        return "\n".join(lines)

    def chat(self, message: str, portfolio_data: dict) -> str:
        """Free-form chat about the portfolio. Returns the advisor's response."""
        context = self._build_context(portfolio_data)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Here is my current portfolio:\n\n{context}\n\n"
                        f"My question: {message}"
                    ),
                }
            ],
        )

        return DISCLAIMER + "\n\n" + response.content[0].text

    def analyze(
        self, mode: str, portfolio_data: dict, extra_context: str = ""
    ) -> str:
        """Run a structured analysis mode.

        Modes:
        - health_check: Overall portfolio health assessment
        - rebalancing: Rebalancing suggestions
        - dividend_optimisation: Dividend yield analysis and optimisation
        - position_deep_dive: Deep dive into specific holding (pass ticker in extra_context)
        - what_if: Scenario analysis (pass scenario in extra_context)
        """
        context = self._build_context(portfolio_data)

        mode_prompts = {
            "health_check": (
                "Perform a comprehensive portfolio health check. Assess: "
                "diversification, concentration risk, sector balance, FX exposure, "
                "cash drag, and any red flags. Rate the overall portfolio health."
            ),
            "rebalancing": (
                "Suggest rebalancing moves for this portfolio. Consider: reducing "
                "concentration in top holdings, sector diversification, deploying "
                "the available cash, and cutting deep losers. Be specific about amounts."
            ),
            "dividend_optimisation": (
                "Analyse the dividend income from this portfolio. Assess: current "
                "yield, income sustainability, opportunities to increase income, "
                "and whether the dividend strategy aligns with the portfolio size."
            ),
            "position_deep_dive": (
                f"Do a deep dive analysis on this specific holding: {extra_context}. "
                "Cover: thesis, risk/reward, position sizing, and whether to hold/add/trim."
            ),
            "what_if": (
                f"Analyse this scenario: {extra_context}. Show the impact on "
                "portfolio allocation, risk profile, and expected outcomes."
            ),
        }

        prompt = mode_prompts.get(mode, f"Analyse: {mode}")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Here is my current portfolio:\n\n{context}\n\n{prompt}"
                    ),
                }
            ],
        )

        return DISCLAIMER + "\n\n" + response.content[0].text
