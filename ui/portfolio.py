"""ポートフォリオ管理UI"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from feedback.portfolio_db import PortfolioDB
from data.fetcher_yfinance import fetch_ticker_info, get_current_price
from ui.i18n import T


def _normalize_ticker(raw: str) -> str:
    t = raw.strip().upper()
    if not t:
        return t
    if t.isdigit() and len(t) == 4:
        return t + ".T"
    return t


def _get_portfolio_db():
    if "portfolio_db" not in st.session_state:
        st.session_state["portfolio_db"] = PortfolioDB()
    return st.session_state["portfolio_db"]


def render_portfolio_page():
    """ポートフォリオ管理ページ"""
    email = st.session_state.get("user_email", "guest")
    pdb = _get_portfolio_db()

    st.markdown(f"### {T('portfolio_title')}")

    with st.expander(f"+ {T('add_holding')}", expanded=False):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            add_ticker = st.text_input(T("ticker_code"), key="pf_add_ticker",
                                       help="例: 7203, AAPL")
        with c2:
            add_shares = st.number_input(T("shares"), min_value=0.0, value=100.0,
                                         step=1.0, key="pf_add_shares")
        with c3:
            add_price = st.number_input(T("buy_price"), min_value=0.0, value=0.0,
                                        step=0.01, key="pf_add_price")
        add_memo = st.text_input(T("memo"), key="pf_add_memo")
        if st.button(T("add_btn"), key="pf_add_btn", type="primary"):
            ticker = _normalize_ticker(add_ticker)
            if ticker and add_shares > 0:
                if add_price == 0:
                    add_price = get_current_price(ticker)
                pdb.add_holding(email, ticker, add_shares, add_price, add_memo)
                st.success(f"{ticker} OK")
                st.rerun()
            else:
                st.error("Enter ticker and shares")

    holdings = pdb.get_holdings(email)
    if holdings.empty:
        st.info(T("no_holdings"))
        return

    portfolio_data = []
    total_value = 0
    total_cost = 0
    for _, row in holdings.iterrows():
        ticker = row["ticker"]
        shares = row["shares"]
        avg_price = row["avg_price"]
        current = get_current_price(ticker)
        cost = shares * avg_price
        value = shares * current
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0
        total_value += value
        total_cost += cost
        info = fetch_ticker_info(ticker)
        portfolio_data.append({
            "name": f"{info['name']} ({ticker})",
            "shares": shares, "avg_price": avg_price,
            "current": current, "value": value,
            "pnl": pnl, "pnl_pct": pnl_pct,
            "ticker_raw": ticker,
        })

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    pnl_color = "#00d26a" if total_pnl >= 0 else "#f8312f"
    sign = "+" if total_pnl >= 0 else ""

    c1, c2, c3 = st.columns(3)
    c1.metric(T("total_value"), f"{total_value:,.0f}")
    c2.metric(T("total_cost"), f"{total_cost:,.0f}")
    c3.markdown(f"""
    <div style="background:#161b22; border-radius:8px; padding:12px; text-align:center;
                border:1px solid #30363d;">
        <div style="font-size:0.8em; color:#8b949e;">{T("total_pnl")}</div>
        <div style="font-size:1.5em; font-weight:bold; color:{pnl_color};">
            {sign}{total_pnl:,.0f} ({sign}{total_pnl_pct:.1f}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    for row in portfolio_data:
        pc = "#00d26a" if row["pnl"] >= 0 else "#f8312f"
        s = "+" if row["pnl"] >= 0 else ""
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 2, 1])
        with col1:
            st.markdown(f"**{row['name']}**")
        with col2:
            st.caption(f"{row['shares']:.0f}")
        with col3:
            st.caption(f"{row['current']:,.0f}")
        with col4:
            st.markdown(f"<span style='color:{pc}'>{s}{row['pnl']:,.0f} ({s}{row['pnl_pct']:.1f}%)</span>",
                        unsafe_allow_html=True)
        with col5:
            if st.button("X", key=f"del_{row['ticker_raw']}", help="Delete"):
                pdb.remove_holding(email, row["ticker_raw"])
                st.rerun()

    if len(portfolio_data) > 1:
        fig = go.Figure(go.Pie(
            labels=[d["name"] for d in portfolio_data],
            values=[d["value"] for d in portfolio_data],
            hole=0.4, textinfo="label+percent", textfont_size=12,
        ))
        fig.update_layout(
            template="plotly_dark", height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            paper_bgcolor="#0E1117", title=T("composition"),
        )
        st.plotly_chart(fig, use_container_width=True)
