"""T212 Portfolio Advisor - Streamlit Dashboard."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

try:
    from src.t212_client import T212Client
    from src.portfolio import (
        get_allocation_by_holding,
        get_allocation_by_sector,
        get_allocation_by_asset_class,
        get_pnl_by_position,
        get_fx_exposure,
        get_concentration_risk,
        get_dividend_summary,
        get_cash_drag,
        get_portfolio_summary,
    )
    from src.config import TICKER_MAP, ANTHROPIC_API_KEY
    from src.advisor import Advisor, DISCLAIMER
except ImportError as e:
    st.error(f"Failed to import project modules: {e}")
    st.stop()

# -- Page config --
st.set_page_config(page_title="T212 Portfolio Advisor", page_icon="\U0001f4ca", layout="wide")
st.title("\U0001f4ca T212 Portfolio Advisor")
st.caption("\u26a0\ufe0f This tool provides analysis only \u2014 not financial advice.")

# -- Chart style --
COLORS = [
    "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
    "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
    "#7F7F7F", "#BCBD22", "#17BECF", "#AEC7E8", "#FFBB78", "#98DF8A",
]

LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="white"),
    margin=dict(l=20, r=20, t=40, b=20),
)


def fmt_gbp(val: float) -> str:
    """Format a number as GBP with comma separators."""
    return f"\u00a3{val:,.2f}"


# -- Sidebar --
st.sidebar.title("T212 Portfolio Advisor")
st.sidebar.caption("Analysis tool \u2014 not financial advice.")
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()


# -- Data loading --
@st.cache_data(ttl=300)
def load_data():
    client = T212Client()
    account = client.get_account_summary()
    positions = client.get_positions()
    orders = client.get_orders()
    dividends = client.get_dividends()
    transactions = client.get_transactions()
    return account, positions, orders, dividends, transactions


try:
    account, positions, orders, dividends, transactions = load_data()
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()


# ================================================================
# TABS
# ================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "\U0001f4c8 Portfolio Overview",
    "\U0001f4cb Positions",
    "\U0001f4b0 Dividends",
    "\U0001f916 AI Advisor",
])


# ================================================================
# TAB 1: Portfolio Overview
# ================================================================
with tab1:
    inv = account["investments"]
    cash_info = account["cash"]

    # Top-level metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Value", fmt_gbp(account["totalValue"]))
    c2.metric("Cash Available", fmt_gbp(cash_info["availableToTrade"]))
    c3.metric(
        "Unrealised P&L",
        fmt_gbp(inv["unrealizedProfitLoss"]),
        delta=f"{inv['unrealizedProfitLoss']:+,.2f}",
        delta_color="normal",
    )
    c4.metric(
        "Realised P&L",
        fmt_gbp(inv["realizedProfitLoss"]),
        delta=f"{inv['realizedProfitLoss']:+,.2f}",
        delta_color="normal",
    )

    st.divider()

    # Charts row: allocation donut + sector bar
    left, right = st.columns(2)

    with left:
        st.subheader("Allocation by Holding")
        alloc = get_allocation_by_holding(positions, account)
        # Group tiny holdings (<2%) as "Other"
        main_items = [a for a in alloc if a["pct"] >= 2]
        other_pct = sum(a["pct"] for a in alloc if a["pct"] < 2)
        other_val = sum(a["value_gbp"] for a in alloc if a["pct"] < 2)
        labels = [a["name"] for a in main_items]
        values = [a["value_gbp"] for a in main_items]
        if other_pct > 0:
            labels.append("Other")
            values.append(other_val)

        fig_alloc = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            marker=dict(colors=COLORS[: len(labels)]),
            textinfo="label+percent",
            textposition="outside",
            hovertemplate="%{label}<br>\u00a3%{value:,.2f}<br>%{percent}<extra></extra>",
        )])
        fig_alloc.update_layout(**LAYOUT_DEFAULTS, showlegend=False, height=450)
        st.plotly_chart(fig_alloc, width="stretch")

    with right:
        st.subheader("Sector Exposure")
        sectors = get_allocation_by_sector(positions)
        sector_names = list(sectors.keys())
        sector_vals = list(sectors.values())

        fig_sector = go.Figure(data=[go.Bar(
            y=sector_names[::-1],
            x=sector_vals[::-1],
            orientation="h",
            marker_color=COLORS[: len(sector_names)],
            hovertemplate="%{y}<br>\u00a3%{x:,.2f}<extra></extra>",
        )])
        fig_sector.update_layout(
            **LAYOUT_DEFAULTS,
            height=450,
            xaxis=dict(title="Value (GBP)", gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(automargin=True),
        )
        st.plotly_chart(fig_sector, width="stretch")

    st.divider()

    # P&L by position (full width, grouped price + FX)
    st.subheader("P&L by Position")
    pnl_data = get_pnl_by_position(positions)

    fig_pnl = go.Figure()
    fig_pnl.add_trace(go.Bar(
        x=[p["name"] for p in pnl_data],
        y=[p["ppl"] for p in pnl_data],
        name="Price P&L",
        marker_color=["#00CC96" if p["ppl"] >= 0 else "#EF553B" for p in pnl_data],
        hovertemplate="%{x}<br>Price P&L: \u00a3%{y:,.2f}<extra></extra>",
    ))
    fig_pnl.add_trace(go.Bar(
        x=[p["name"] for p in pnl_data],
        y=[p["fxPpl"] for p in pnl_data],
        name="FX P&L",
        marker_color=[
            "rgba(0,204,150,0.5)" if p["fxPpl"] >= 0 else "rgba(239,85,59,0.5)"
            for p in pnl_data
        ],
        hovertemplate="%{x}<br>FX P&L: \u00a3%{y:,.2f}<extra></extra>",
    ))
    fig_pnl.update_layout(
        **LAYOUT_DEFAULTS,
        barmode="group",
        height=400,
        xaxis=dict(tickangle=-45),
        yaxis=dict(title="P&L (GBP)", gridcolor="rgba(128,128,128,0.2)"),
        legend=dict(orientation="h", y=1.12),
    )
    st.plotly_chart(fig_pnl, width="stretch")

    st.divider()

    # FX Exposure + Asset Class + Cash Drag
    col_fx, col_ac, col_cd = st.columns(3)

    with col_fx:
        st.subheader("Currency Exposure")
        fx = get_fx_exposure(positions, account)
        fig_fx = go.Figure(data=[go.Pie(
            labels=list(fx.keys()),
            values=list(fx.values()),
            hole=0.4,
            marker=dict(colors=["#636EFA", "#FFA15A", "#00CC96"][: len(fx)]),
            textinfo="label+percent",
            hovertemplate="%{label}<br>\u00a3%{value:,.2f}<extra></extra>",
        )])
        fig_fx.update_layout(**LAYOUT_DEFAULTS, showlegend=False, height=320)
        st.plotly_chart(fig_fx, width="stretch")

    with col_ac:
        st.subheader("Asset Class")
        classes = get_allocation_by_asset_class(positions)
        fig_ac = go.Figure(data=[go.Bar(
            y=list(classes.keys()),
            x=list(classes.values()),
            orientation="h",
            marker_color="#f59e0b",
            hovertemplate="%{y}<br>\u00a3%{x:,.2f}<extra></extra>",
        )])
        fig_ac.update_layout(
            **LAYOUT_DEFAULTS,
            height=320,
            xaxis=dict(title="Value (GBP)", gridcolor="rgba(128,128,128,0.2)"),
        )
        st.plotly_chart(fig_ac, width="stretch")

    with col_cd:
        st.subheader("Cash Drag")
        cd = get_cash_drag(account)
        st.metric("Uninvested Cash", fmt_gbp(cd["cash_gbp"]))
        st.metric("% of Portfolio", f"{cd['pct']:.1f}%")
        if cd["pct"] > 10:
            st.warning(f"Cash drag is {cd['pct']:.1f}% \u2014 consider deploying some capital.")
        elif cd["pct"] > 5:
            st.info(f"Cash at {cd['pct']:.1f}% \u2014 moderate buffer.")
        else:
            st.success(f"Cash at {cd['pct']:.1f}% \u2014 well deployed.")

    st.divider()

    # Concentration Risk Table
    st.subheader("Concentration Risk")
    conc = get_concentration_risk(positions, account)
    st.dataframe(
        [
            {
                "Holding": c["name"],
                "Value (\u00a3)": f"\u00a3{c['value_gbp']:,.2f}",
                "% of Portfolio": f"{c['pct']:.1f}%",
                "Status": "\u26a0\ufe0f Concentrated" if c["concentrated"] else "\u2713 OK",
            }
            for c in conc
        ],
        width="stretch",
        hide_index=True,
    )


# ================================================================
# TAB 2: Positions
# ================================================================
with tab2:
    st.subheader("All Positions")

    rows = []
    for pos in positions:
        info = TICKER_MAP.get(pos["ticker"], {
            "name": pos["ticker"], "ticker": pos["ticker"],
            "sector": "Unknown", "geo": "USD",
        })
        qty = pos["quantity"]
        avg = pos["averagePrice"]
        cur = pos["currentPrice"]
        ppl = pos.get("ppl", 0) or 0
        fx_pnl = pos.get("fxPpl", 0) or 0
        total_pnl = ppl + fx_pnl
        cost = qty * avg
        pct_return = (total_pnl / cost * 100) if cost else 0

        native_val = qty * cur
        if info.get("geo") == "GBP":
            val_gbp = native_val
        else:
            val_gbp = native_val / 1.29

        rows.append({
            "Name": info.get("name", pos["ticker"]),
            "Ticker": info.get("ticker", pos["ticker"]),
            "Qty": round(qty, 4),
            "Avg Price": round(avg, 2),
            "Current Price": round(cur, 2),
            "Value (\u00a3)": round(val_gbp, 2),
            "P&L (\u00a3)": round(total_pnl, 2),
            "Return (%)": round(pct_return, 2),
            "Sector": info.get("sector", "Unknown"),
        })

    df = pd.DataFrame(rows).sort_values("Value (\u00a3)", ascending=False).reset_index(drop=True)

    def color_pnl(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return "color: #00CC96"
            elif val < 0:
                return "color: #EF553B"
        return ""

    styled = df.style.map(color_pnl, subset=["P&L (\u00a3)", "Return (%)"])
    styled = styled.format({
        "Value (\u00a3)": "\u00a3{:,.2f}",
        "P&L (\u00a3)": "{:+,.2f}",
        "Return (%)": "{:+.2f}%",
        "Avg Price": "{:.2f}",
        "Current Price": "{:.2f}",
        "Qty": "{:.4f}",
    })
    st.dataframe(styled, width="stretch", height=620)


# ================================================================
# TAB 3: Dividends
# ================================================================
with tab3:
    st.subheader("Dividend Income")

    div_summary = get_dividend_summary(dividends)

    # Summary metrics
    dc1, dc2, dc3 = st.columns(3)
    dc1.metric("Total Received", fmt_gbp(div_summary["total_received"]))
    dc2.metric("Projected Annual Income", fmt_gbp(div_summary["projected_annual"]))
    dc3.metric("Dividend Payments", str(len(dividends)))

    st.divider()

    left_div, right_div = st.columns(2)

    with left_div:
        st.subheader("Dividends by Stock")
        by_ticker = div_summary["by_ticker"]
        if by_ticker:
            fig_div = go.Figure(data=[go.Bar(
                x=list(by_ticker.keys()),
                y=list(by_ticker.values()),
                marker_color=COLORS[: len(by_ticker)],
                hovertemplate="%{x}<br>\u00a3%{y:,.2f}<extra></extra>",
            )])
            fig_div.update_layout(
                **LAYOUT_DEFAULTS,
                height=380,
                xaxis=dict(tickangle=-45),
                yaxis=dict(title="Total Dividends (GBP)", gridcolor="rgba(128,128,128,0.2)"),
            )
            st.plotly_chart(fig_div, width="stretch")
        else:
            st.info("No dividend data available.")

    with right_div:
        st.subheader("Monthly Dividend Timeline")
        if dividends:
            timeline_data = []
            for d in dividends:
                paid_on = d.get("paidOn", "")
                if not paid_on:
                    continue
                name = d.get("instrument", {}).get("name", d.get("ticker", "Unknown"))
                try:
                    dt = pd.to_datetime(paid_on)
                    timeline_data.append({"Date": dt, "Amount": d["amount"], "Stock": name})
                except Exception:
                    pass

            if timeline_data:
                tl_df = pd.DataFrame(timeline_data)
                tl_df["Date"] = pd.to_datetime(tl_df["Date"], utc=True)
                tl_df["Month"] = tl_df["Date"].dt.to_period("M").astype(str)
                monthly = tl_df.groupby("Month")["Amount"].sum().reset_index()
                monthly = monthly.sort_values("Month")

                fig_tl = go.Figure(data=[go.Bar(
                    x=monthly["Month"],
                    y=monthly["Amount"],
                    marker_color="#636EFA",
                    hovertemplate="%{x}<br>\u00a3%{y:,.2f}<extra></extra>",
                )])
                fig_tl.update_layout(
                    **LAYOUT_DEFAULTS,
                    height=380,
                    xaxis=dict(tickangle=-45),
                    yaxis=dict(title="Monthly Dividends (GBP)", gridcolor="rgba(128,128,128,0.2)"),
                )
                st.plotly_chart(fig_tl, width="stretch")
            else:
                st.info("No timeline data.")
        else:
            st.info("No dividend data.")

    st.divider()

    # Full dividend history table
    st.subheader("Dividend History")
    if dividends:
        div_rows = []
        for d in dividends:
            name = d.get("instrument", {}).get("name", d.get("ticker", "Unknown"))
            div_rows.append({
                "Date": d.get("paidOn", "")[:10],
                "Stock": name,
                "Shares": round(d["quantity"], 4),
                "Amount (\u00a3)": round(d["amount"], 2),
                "Per Share": round(d.get("grossAmountPerShare", 0), 4),
                "Currency": d.get("currency", ""),
            })
        div_df = pd.DataFrame(div_rows)
        st.dataframe(div_df, width="stretch", height=400)
    else:
        st.info("No dividend history available.")


# ================================================================
# TAB 4: AI Advisor
# ================================================================
with tab4:
    st.header("AI Portfolio Advisor")
    st.warning(DISCLAIMER)

    has_api_key = bool(ANTHROPIC_API_KEY)
    if not has_api_key:
        st.error(
            "ANTHROPIC_API_KEY not set in .env \u2014 AI Advisor is unavailable. "
            "Add your key to the .env file and restart."
        )

    st.info(
        "Each question sends your portfolio data to Claude for analysis. "
        "Responses may take 10\u201330 seconds."
    )

    # Initialise session state
    if "advisor_messages" not in st.session_state:
        st.session_state.advisor_messages = []

    # Preset analysis buttons
    st.subheader("Quick Analysis")
    preset_cols = st.columns(3)
    with preset_cols[0]:
        if st.button("\U0001f3e5 Health Check", disabled=not has_api_key, width="stretch"):
            st.session_state.advisor_pending = ("analyze", "health_check", "")
    with preset_cols[1]:
        if st.button("\u2696\ufe0f Rebalancing", disabled=not has_api_key, width="stretch"):
            st.session_state.advisor_pending = ("analyze", "rebalancing", "")
    with preset_cols[2]:
        if st.button("\U0001f4b0 Dividend Optimisation", disabled=not has_api_key, width="stretch"):
            st.session_state.advisor_pending = ("analyze", "dividend_optimisation", "")

    st.divider()

    # Display conversation history
    for msg in st.session_state.advisor_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Ask about your portfolio...", disabled=not has_api_key)

    # Determine what to send (chat input or preset button)
    pending = st.session_state.pop("advisor_pending", None)

    if user_input and has_api_key:
        st.session_state.advisor_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Analysing..."):
                try:
                    advisor = Advisor()
                    portfolio_data = get_portfolio_summary(positions, account, dividends)
                    response = advisor.chat(user_input, portfolio_data)
                except Exception as e:
                    response = f"Error: {e}"
            st.markdown(response)

        st.session_state.advisor_messages.append({"role": "assistant", "content": response})

    elif pending and has_api_key:
        mode_type, mode, extra = pending
        label = mode.replace("_", " ").title()

        st.session_state.advisor_messages.append(
            {"role": "user", "content": f"Run analysis: **{label}**"}
        )
        with st.chat_message("user"):
            st.markdown(f"Run analysis: **{label}**")

        with st.chat_message("assistant"):
            with st.spinner(f"Running {label}..."):
                try:
                    advisor = Advisor()
                    portfolio_data = get_portfolio_summary(positions, account, dividends)
                    response = advisor.analyze(mode, portfolio_data, extra)
                except Exception as e:
                    response = f"Error: {e}"
            st.markdown(response)

        st.session_state.advisor_messages.append({"role": "assistant", "content": response})

    # Clear conversation button
    if st.session_state.advisor_messages:
        if st.button("Clear Conversation"):
            st.session_state.advisor_messages = []
            st.rerun()
