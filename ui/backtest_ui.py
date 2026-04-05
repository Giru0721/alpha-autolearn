"""バックテストUI + 自動機械学習"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data.fetcher_yfinance import fetch_ohlcv
from models.backtest import BacktestEngine
from models.auto_ml import AutoMLOptimizer
from feedback.database import Database
from config import DATABASE_PATH, XGBOOST_DEFAULT_PARAMS
from ui.i18n import T


def _get_db():
    if "db" not in st.session_state:
        st.session_state["db"] = Database(DATABASE_PATH)
    return st.session_state["db"]


def render_backtest_page(ticker: str, period: str, horizon: int):
    """バックテストページ（自動学習・最適化対応）"""
    st.markdown(f"### {T('backtest_title')}")
    db = _get_db()

    # --- 設定 ---
    c1, c2 = st.columns(2)
    with c1:
        bt_ratio = st.slider(T("train_ratio"), 0.5, 0.9, 0.7, 0.05)
    with c2:
        bt_horizon = st.number_input(T("horizon_label"), 1, 60, horizon, key="bt_horizon")

    # --- DB最良パラメータ表示 ---
    prev_best_acc = db.get_best_direction_accuracy(ticker, bt_horizon)
    best_xgb_params = db.get_best_backtest_params(ticker, bt_horizon)

    if prev_best_acc is not None:
        st.markdown(f"""
        <div style="background:#1a2332; border-radius:8px; padding:10px 16px;
                    border-left:3px solid #4da6ff; margin-bottom:12px;">
            <span style="color:#8b949e;">過去最高方向精度:</span>
            <span style="color:#4da6ff; font-weight:bold; font-size:1.2em;">
                {prev_best_acc:.1f}%</span>
            <span style="color:#8b949e; font-size:0.85em; margin-left:12px;">
                {'(最適化パラメータあり)' if best_xgb_params else '(デフォルトパラメータ)'}</span>
        </div>
        """, unsafe_allow_html=True)

    # --- ボタン行 ---
    col_bt, col_opt = st.columns(2)

    with col_bt:
        use_optimized = False
        if best_xgb_params:
            use_optimized = st.checkbox(T("use_optimized_params"), value=True)

        run_bt = st.button(T("run_backtest"), type="primary", use_container_width=True)

    with col_opt:
        n_trials = st.select_slider(
            T("optimization_trials"),
            options=[10, 20, 30, 50],
            value=20)
        run_opt = st.button(T("auto_optimize"), type="secondary",
                            use_container_width=True)

    # --- 自動最適化実行 ---
    if run_opt:
        price_df = fetch_ohlcv(ticker, period)
        if price_df.empty:
            st.error(T("no_data"))
            return

        optimizer = AutoMLOptimizer(db, ticker, horizon=bt_horizon)
        progress_bar = st.progress(0)
        status_text = st.empty()

        def opt_progress(current, total):
            progress_bar.progress(current / total)
            status_text.text(f"{T('auto_optimize_running')} ({current}/{total})")

        with st.spinner(T("auto_optimize_running")):
            opt_result = optimizer.optimize(price_df, n_trials=n_trials,
                                            progress_callback=opt_progress)

        progress_bar.empty()
        status_text.empty()

        if "error" in opt_result:
            st.error(opt_result["error"])
        else:
            # 結果表示
            new_acc = opt_result["best_direction_accuracy"]
            st.session_state["last_optimization"] = opt_result

            # 改善度計算
            improvement = ""
            if prev_best_acc is not None:
                diff = new_acc - prev_best_acc
                if diff > 0:
                    improvement = f"  (+{diff:.1f}%)"
                elif diff < 0:
                    improvement = f"  ({diff:.1f}%)"

            st.success(f"""
            {T('auto_optimize_result')}:
            方向精度 {new_acc:.1f}%{improvement}
            {T('params_saved')}
            """)

            # 最適化過程グラフ
            _render_optimization_history(opt_result)

    # --- バックテスト実行 ---
    if run_bt:
        price_df = fetch_ohlcv(ticker, period)
        if price_df.empty:
            st.error(T("no_data"))
            return

        # パラメータ選択
        xgb_params = XGBOOST_DEFAULT_PARAMS.copy()
        if use_optimized and best_xgb_params:
            xgb_params = best_xgb_params.copy()
            xgb_params.setdefault("objective", "reg:squarederror")
            xgb_params.setdefault("random_state", 42)
            st.info("最適化済みパラメータでバックテストを実行します")

        weights = st.session_state.get("weights", {"prophet": 0.4, "xgboost": 0.6})
        engine = BacktestEngine(train_ratio=bt_ratio, horizon=bt_horizon)

        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total):
            progress_bar.progress(current / total)
            status_text.text(f"{T('backtest_running')} {current}/{total}")

        with st.spinner(T("backtest_running")):
            result = engine.run(price_df, weights,
                                progress_callback=update_progress,
                                xgb_params=xgb_params)

        progress_bar.empty()
        status_text.empty()

        if "error" in result:
            st.error(result["error"])
            return

        # バックテスト結果をDBに保存（学習用）
        try:
            engine.save_to_db(db, ticker)
            st.toast(T("learning_from_backtest"), icon="brain")
        except Exception:
            pass

        result["_ticker"] = ticker
        result["_horizon"] = bt_horizon
        st.session_state["backtest_result"] = result

    # --- 結果表示 ---
    result = st.session_state.get("backtest_result")
    if result and result.get("_ticker") != ticker:
        result = None
        st.session_state.pop("backtest_result", None)
    if not result:
        # 過去のバックテスト履歴があれば表示
        _render_backtest_history(db, ticker)
        return

    metrics = result["metrics"]
    preds = result["predictions"]

    # Metrics cards
    st.markdown(f"#### {T('backtest_result')}")
    cols = st.columns(5)
    metric_items = [
        (T("direction_accuracy"), f"{metrics['direction_accuracy']:.1f}%",
         "#00d26a" if metrics['direction_accuracy'] >= 50 else "#f8312f"),
        (T("sharpe_ratio"), f"{metrics['sharpe_ratio']:.2f}", "#4da6ff"),
        (T("max_drawdown"), f"{metrics['max_drawdown']:.1f}%", "#f8312f"),
        (T("win_rate"), f"{metrics['win_rate']:.1f}%",
         "#00d26a" if metrics['win_rate'] >= 50 else "#f8312f"),
        (T("total_return"), f"{metrics['total_return']:.1f}%",
         "#00d26a" if metrics['total_return'] >= 0 else "#f8312f"),
    ]
    for col, (label, val, color) in zip(cols, metric_items):
        with col:
            st.markdown(f"""
            <div style="background:#161b22; border-radius:8px; padding:12px;
                        text-align:center; border:1px solid #30363d;">
                <div style="font-size:1.3em; font-weight:bold; color:{color};">{val}</div>
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


def _render_optimization_history(opt_result):
    """最適化過程のグラフ"""
    history = opt_result.get("history", [])
    if not history:
        return

    trials = [h["trial"] for h in history]
    accs = [h["direction_accuracy"] for h in history]

    # 累積最高精度
    best_so_far = []
    current_best = 0
    for acc in accs:
        current_best = max(current_best, acc)
        best_so_far.append(current_best)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trials, y=accs, name="各試行の精度",
        mode="markers", marker=dict(color="#4da6ff", size=6, opacity=0.6)))
    fig.add_trace(go.Scatter(
        x=trials, y=best_so_far, name="累積最高精度",
        line=dict(color="#00d26a", width=2)))
    fig.add_hline(y=50, line_dash="dot", line_color="#f8312f",
                  annotation_text="ランダム基準 (50%)")

    fig.update_layout(
        template="plotly_dark", height=300,
        margin=dict(l=0, r=0, t=30, b=0),
        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        xaxis_title="Trial", yaxis_title="Direction Accuracy (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_backtest_history(db, ticker):
    """過去のバックテスト実行履歴"""
    history = db.get_backtest_history(ticker, limit=10)
    if history.empty:
        st.info(T("no_history"))
        return

    st.markdown("#### 過去のバックテスト結果")
    for _, row in history.iterrows():
        acc = row.get("direction_accuracy", 0) or 0
        source = row.get("source", "manual")
        source_icon = "robot_face" if source == "auto_ml" else "chart_with_upwards_trend"
        color = "#00d26a" if acc >= 50 else "#f8312f"

        st.markdown(f"""
        <div style="background:#161b22; border-radius:6px; padding:8px 12px;
                    margin-bottom:6px; border:1px solid #30363d; display:flex;
                    justify-content:space-between; align-items:center;">
            <span style="color:#8b949e; font-size:0.85em;">
                {row.get('created_at', '')[:16]}
                &nbsp;|&nbsp; {row.get('horizon_days', '?')}日 &nbsp;|&nbsp;
                {source}
            </span>
            <span style="color:{color}; font-weight:bold;">{acc:.1f}%</span>
        </div>
        """, unsafe_allow_html=True)
