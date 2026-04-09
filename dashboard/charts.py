import plotly.graph_objects as go
import plotly.express as px

COLORS = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
          '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52',
          '#7F7F7F', '#BCBD22', '#17BECF', '#AEC7E8', '#FFBB78', '#98DF8A']

LAYOUT_DEFAULTS = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=20, r=20, t=40, b=20),
)


def allocation_donut(allocation_data: list, title: str = "Portfolio Allocation") -> go.Figure:
    """Create a donut chart from allocation data.
    allocation_data: list of dicts with 'name' and 'value_gbp' keys.
    Groups holdings under 2% into 'Other'.
    """
    total = sum(h["value_gbp"] for h in allocation_data)
    main = []
    other_val = 0
    for h in allocation_data:
        if h["value_gbp"] / total >= 0.02:
            main.append(h)
        else:
            other_val += h["value_gbp"]
    if other_val > 0:
        main.append({"name": "Other", "value_gbp": other_val})

    fig = go.Figure(data=[go.Pie(
        labels=[h["name"] for h in main],
        values=[h["value_gbp"] for h in main],
        hole=0.45,
        marker=dict(colors=COLORS[:len(main)]),
        textinfo='label+percent',
        textposition='outside',
        hovertemplate='%{label}<br>£%{value:,.2f}<br>%{percent}<extra></extra>',
    )])
    fig.update_layout(title=title, showlegend=False, **LAYOUT_DEFAULTS)
    return fig


def pnl_bar_chart(pnl_data: list, title: str = "P&L by Position") -> go.Figure:
    """Create a bar chart of P&L by position.
    pnl_data: list of dicts with 'name', 'ppl', 'fxPpl', 'total_pnl' keys.
    Colors: green for profit, red for loss.
    """
    names = [p["name"] for p in pnl_data]
    ppl = [p["ppl"] for p in pnl_data]
    fx = [p["fxPpl"] for p in pnl_data]
    colors = ['#00CC96' if p["total_pnl"] >= 0 else '#EF553B' for p in pnl_data]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Price P&L',
        x=names, y=ppl,
        marker_color=colors,
        hovertemplate='%{x}<br>Price P&L: £%{y:,.2f}<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        name='FX P&L',
        x=names, y=fx,
        marker_color=['rgba(0,204,150,0.5)' if f >= 0 else 'rgba(239,85,59,0.5)' for f in fx],
        hovertemplate='%{x}<br>FX P&L: £%{y:,.2f}<extra></extra>',
    ))
    fig.update_layout(title=title, barmode='group', xaxis_tickangle=-45, **LAYOUT_DEFAULTS)
    return fig


def sector_bar_chart(sector_data: dict, title: str = "Sector Exposure") -> go.Figure:
    """Horizontal bar chart of sector allocation.
    sector_data: {sector_name: value_gbp}
    """
    sectors = list(sector_data.keys())
    values = list(sector_data.values())

    fig = go.Figure(data=[go.Bar(
        x=values,
        y=sectors,
        orientation='h',
        marker_color=COLORS[:len(sectors)],
        hovertemplate='%{y}<br>£%{x:,.2f}<extra></extra>',
    )])
    fig.update_layout(title=title, yaxis=dict(autorange="reversed"), **LAYOUT_DEFAULTS)
    return fig


def fx_pie_chart(fx_data: dict, title: str = "Currency Exposure") -> go.Figure:
    """Pie chart of FX exposure.
    fx_data: {currency: value_gbp}
    """
    fig = go.Figure(data=[go.Pie(
        labels=list(fx_data.keys()),
        values=list(fx_data.values()),
        hole=0.4,
        marker=dict(colors=['#636EFA', '#EF553B', '#00CC96'][:len(fx_data)]),
        textinfo='label+percent',
        hovertemplate='%{label}<br>£%{value:,.2f}<br>%{percent}<extra></extra>',
    )])
    fig.update_layout(title=title, showlegend=False, **LAYOUT_DEFAULTS)
    return fig


def dividend_bar_chart(div_by_ticker: dict, title: str = "Dividends by Holding") -> go.Figure:
    """Bar chart of dividends received by ticker."""
    names = list(div_by_ticker.keys())
    amounts = list(div_by_ticker.values())

    fig = go.Figure(data=[go.Bar(
        x=names, y=amounts,
        marker_color='#00CC96',
        hovertemplate='%{x}<br>£%{y:.2f}<extra></extra>',
    )])
    fig.update_layout(title=title, xaxis_tickangle=-45, **LAYOUT_DEFAULTS)
    return fig
