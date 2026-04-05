"""バックテストUI"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data.fetcher_yfinance import fetch_ohlcv
from models.backtest import BacktestEngine
from ui.i18n import T


def render_backtest_page(ticker: str, period: str, horizon: int):
    """バックテストページ"""
    st.markdown(f"### {T('backtest_title')}")

    c1, c2 = st.columns(2)
    with c1:
        bt_ratio = st.slider(T("train_ratio"), 0.5, 0.9, 0.7, 0.05)
    with c2:
        bt_horizon = st.number_input(T("horizon_label"), 1, 60, horizon, key="bt_horizon")

    if st.button(T("run_backtest"), type="primary", use_container_width=True):
        price_df = fetch_ohlcv(ticker, period)
        if price_df.empty:
            st.error(T("no_data"))
            return

        weights = st.session_state.get("weights", {"prophet": 0.4, "xgboost": 0.6})
        engine = BacktestEngine(train_ratio=bt_ratio, horizon=bt_horizon)

        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total):
            progress_bar.progress(current / total)
            status_text.text(f"{T('backtest_running')} {current}/{total}")

        with st.spinner(T("backtest_running")):
            result = engine.run(price_df, weights, progress_callback=update_progress)

        progress_bar.empty()
        status_text.empty()

        if "error" in result:
            st.error(result["error"])
            return

        result["_ticker"] = ticker
        result["_horizon"] = bt_horizon
        st.session_state["backtest_result"] = result

    result = st.session_state.get("backtest_result")
    if result and result.get("_ticker") != ticker:
        result = None
        st.session_state.pop("backtest_result", None)
    if not result:
        st.info(T("no_history"))
        return

    metrics = result["metrics"]
    preds = result["predictions"]

    # Metrics cards
    st.markdown(f"#### {T('backtest_result')}")
    cols = st.columns(5)
    metric_items = [
        (T("direction_accuracy"), f"{metrics['direction_accuracy']:.1f}%"),
        (T("sharpe_ratio"), f"{metrics['sharpe_ratio']:.2f}"),
        (T("max_drawdown"), f"{metrics['max_drawdown']:.1f}%"),
        (T("win_rate"), f"{metrics['win_rate']:.1f}%"),
        (T("total_return"), f"{metrics['total_return']:.1f}%"),
    ]
    for col, (label, val) in zip(cols, metric_items):
        with col:
            st.markdown(f"""
            <div style="background:#161b22; border-radius:8px; padding:12px;
                        text-align:center; border:1px solid #30363d;">
                <div style="font-size:1.3em; font-weight:bold; color:#4da6ff;">{val}</div>
                <div style="font-size:0.75em; color:#8b949e;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    cols2 = st.columns(3)
    cols2[0].metric(T("mae_label"), f"{metrics['mae']:,.1f}")
    cols2[1].metric(T("profit_factor"), f"{metrics['profit_factor']:.2f}")
    cols2[2].metric(T("total_predictions"), str(metrics["total_predictions"]))

    # Predicted vs Actual chart
    st.markdown(f"#### {T('backtest_chart')}")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        row_heights=[0.65, 0.35])

    fig.add_trace(go.Scatter(
        x=preds["date"], y=preds["actual_price"],
        name="Actual", line=dict(color="white", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=preds["date"], y=preds["ensemble_price"],
        name="Predicted", line=dict(color="#4da6ff", width=2, dash="dash")), row=1, col=1)

    # Error bars
    colors = ["#00d26a" if dc else "#f8312f" for dc in preds["direction_correct"]]
    fig.add_trace(go.Bar(
        x=preds["date"], y=preds["pct_error"],
        marker_color=colors, opacity=0.6, name="Error %"), row=2, col=1)

    fig.update_layout(
        template="plotly_dark", height=550,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Error %", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # Equity curve
    st.markdown(f"#### {T('equity_curve')}")
    equity = (1 + preds["ensemble_return"]).cumprod()
    buy_hold = (1 + preds["actual_return"]).cumprod()
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=preds["date"], y=equity, name="Strategy",
                              line=dict(color="#4da6ff", width=2)))
    fig2.add_trace(go.Scatter(x=preds["date"], y=buy_hold, name="Buy & Hold",
                              line=dict(color="#8b949e", width=1.5, dash="dot")))
    fig2.update_layout(
        template="plotly_dark", height=350,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="Cumulative Return",
    )
    st.plotly_chart(fig2, use_container_width=True)
