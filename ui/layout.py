"""メインページレイアウト"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

from config import DEFAULT_TICKER, PERIOD_OPTIONS, NEWSAPI_KEY
from ui.i18n import TEXTS, T, get_lang
from ui.charts import (create_candlestick_chart, create_technical_chart, create_sentiment_gauge,
                        create_feature_importance_chart, create_weight_donut, create_error_timeline,
                        create_actual_vs_predicted, create_scenario_forecast_chart)
from ui.components import render_prediction_card, render_metrics_row, render_model_info
from ui.portfolio import render_portfolio_page
from ui.backtest_ui import render_backtest_page
from data.fetcher_yfinance import fetch_ohlcv, fetch_ticker_info
from data.feature_engineer import build_feature_matrix, add_technical_indicators
from models.ensemble import EnsemblePredictor
from feedback.tracker import PredictionTracker
from feedback.auto_adjuster import AutoAdjuster


def _normalize_ticker(raw: str) -> str:
    """銘柄コードを正規化。数字4桁なら.Tを自動付与。"""
    t = raw.strip().upper()
    if not t:
        return t
    # 4桁数字 → 日本株とみなし .T を付与
    if t.isdigit() and len(t) == 4:
        return t + ".T"
    # 数字のみ(5桁以上)で拡張子なし → .T 付与 (例: 99830 → 99830.T は不要なので4桁のみ)
    return t


def render_sidebar():
    from ui.auth_ui import render_user_badge, render_language_selector
    show_subscription = False
    show_admin = False
    with st.sidebar:
        render_user_badge()
        st.title(TEXTS["sidebar_title"])
        raw_ticker = st.text_input(TEXTS["ticker_input"], value=DEFAULT_TICKER,
                                   help=TEXTS["ticker_help"])
        lang = get_lang()
        if lang == "ja":
            period_label = st.selectbox(TEXTS["period_select"], options=list(PERIOD_OPTIONS.keys()), index=2)
            period = PERIOD_OPTIONS[period_label]
        else:
            en_periods = {"6 months": "6mo", "1 year": "1y", "2 years": "2y", "5 years": "5y", "10 years": "10y"}
            period_label = st.selectbox(TEXTS["period_select"], options=list(en_periods.keys()), index=2)
            period = en_periods[period_label]
        horizon = st.slider(TEXTS["horizon_label"], min_value=1, max_value=365,
                            value=5, step=1)
        st.divider()
        st.markdown(f"**{TEXTS['data_sources']}**")
        enable_fred = st.checkbox(TEXTS["enable_fred"], value=True)
        enable_trends = st.checkbox(TEXTS["enable_trends"], value=False)
        enable_news = st.checkbox(TEXTS["enable_news"], value=bool(NEWSAPI_KEY))
        st.divider()
        if "weights" in st.session_state:
            render_model_info(st.session_state["weights"])
        st.divider()
        predict_clicked = st.button(TEXTS["predict_button"], type="primary", use_container_width=True)
        adjust_clicked = st.button(TEXTS["auto_adjust"], use_container_width=True)
        st.divider()
        if st.button("Plan" if lang == "en" else "プラン管理",
                     use_container_width=True):
            st.session_state["page"] = "subscription"
            st.rerun()
        # Admin button
        user = st.session_state.get("user", {})
        if user.get("role") == "admin":
            if st.button("Admin Panel" if lang == "en" else "管理者パネル",
                         use_container_width=True):
                st.session_state["page"] = "admin"
                st.rerun()
        if st.session_state.get("page") in ("subscription", "admin"):
            if st.button("← " + ("Back" if lang == "en" else "戻る"),
                         use_container_width=True):
                st.session_state["page"] = "main"
                st.rerun()
        st.divider()
        render_language_selector()
        if "last_updated" in st.session_state:
            st.caption(f"{TEXTS['last_updated']}: {st.session_state['last_updated']}")
    ticker = _normalize_ticker(raw_ticker)
    page = st.session_state.get("page", "main")
    return {"ticker": ticker, "period": period, "horizon": horizon,
            "enable_fred": enable_fred, "enable_trends": enable_trends,
            "enable_news": enable_news, "predict_clicked": predict_clicked,
            "adjust_clicked": adjust_clicked,
            "show_subscription": page == "subscription",
            "show_admin": page == "admin"}


def render_main_content(settings):
    ticker = settings["ticker"]
    if not ticker:
        st.warning(TEXTS["no_data"]); return
    db = st.session_state["db"]
    with st.spinner(TEXTS["fetching_data"]):
        price_df = fetch_ohlcv(ticker, settings["period"])
    if price_df.empty:
        st.error(f"{TEXTS['no_data']}: {ticker}"); return
    info = fetch_ticker_info(ticker)
    st.markdown(f"### {info['name']} ({ticker})")
    mc = st.columns(4)
    mc[0].caption(f"セクター: {info['sector']}")
    mc[1].caption(f"通貨: {info['currency']}")
    mc[2].caption(f"取引所: {info['exchange']}")
    if info['market_cap']:
        _mc = info['market_cap']
        if _mc >= 1_000_000_000_000:
            mc[3].caption(f"時価総額: {_mc / 1_000_000_000_000:.2f}兆")
        elif _mc >= 100_000_000:
            mc[3].caption(f"時価総額: {_mc / 100_000_000:.0f}億")
        else:
            mc[3].caption(f"時価総額: {_mc:,.0f}")
    tech_df = add_technical_indicators(price_df)
    macro_df = trends_df = sentiment_df = None
    if settings["enable_fred"]:
        try:
            from data.fetcher_fred import fetch_all_macro
            macro_df = fetch_all_macro(price_df.index[0].strftime("%Y-%m-%d"), price_df.index[-1].strftime("%Y-%m-%d"))
        except Exception: pass
    if settings["enable_trends"]:
        try:
            from data.fetcher_trends import fetch_search_interest
            trends_df = fetch_search_interest([ticker.split(".")[0], info["name"].split()[0]])
        except Exception: pass
    if settings["enable_news"]:
        try:
            from data.fetcher_news import get_news_sentiment_features
            sentiment_df = get_news_sentiment_features(ticker, info["name"])
        except Exception: pass
    feature_matrix = build_feature_matrix(price_df, macro_df, trends_df, sentiment_df)
    if settings["adjust_clicked"]:
        with st.spinner(TEXTS["training_status"]):
            result = AutoAdjuster(db).run_adjustment_cycle(ticker)
            if result:
                st.session_state["weights"] = db.load_weights(ticker)
                st.success(TEXTS["adjustment_complete"])
            else:
                st.info(TEXTS["no_history"])
    prediction = st.session_state.get("last_prediction")
    if settings["predict_clicked"]:
        # プラン制限チェック
        email = st.session_state.get("user_email", "guest")
        if email != "guest":
            from auth.subscription import AuthManager
            auth = AuthManager()
            check = auth.check_prediction_limit(email)
            if not check["allowed"]:
                st.warning(check["message"])
                if prediction:
                    syms = {"JPY": "\u00a5", "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "CNY": "\u00a5"}
                    render_prediction_card(prediction, syms.get(info.get("currency", ""), ""))
                return
        with st.spinner(TEXTS["training_status"]):
            PredictionTracker(db).resolve_pending_predictions(ticker)
            ensemble = EnsemblePredictor(db, ticker)
            prediction = ensemble.train_and_predict(feature_matrix, settings["horizon"])
            prediction["horizon"] = settings["horizon"]
            st.session_state["last_prediction"] = prediction
            st.session_state["weights"] = ensemble.weights
            st.session_state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            # 予測カウント
            if email != "guest":
                auth.increment_prediction_count(email)
    if prediction:
        syms = {"JPY": "\u00a5", "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "CNY": "\u00a5"}
        render_prediction_card(prediction, syms.get(info.get("currency", ""), ""))
    tabs = st.tabs([TEXTS["tab_price"], TEXTS["tab_technical"], TEXTS["tab_scenario"],
                    TEXTS["tab_prediction"], TEXTS["tab_performance"],
                    TEXTS["tab_portfolio"], TEXTS["tab_backtest"], TEXTS["tab_settings"]])
    with tabs[0]:
        st.plotly_chart(create_candlestick_chart(tech_df, prediction), use_container_width=True)
    with tabs[1]:
        st.plotly_chart(create_technical_chart(tech_df), use_container_width=True)
    with tabs[2]:
        if prediction and prediction.get("scenario_forecast") is not None:
            st.markdown(f"### {TEXTS['scenario_chart_title']}")
            st.plotly_chart(create_scenario_forecast_chart(price_df, prediction["scenario_forecast"],
                                                           prediction["current_price"]), use_container_width=True)
            if not prediction["scenario_forecast"].empty:
                last = prediction["scenario_forecast"].iloc[-1]
                cp = prediction["current_price"]
                sc = st.columns(3)
                for col_st, name, key, color in [
                    (sc[0], TEXTS["scenario_optimistic"], "optimistic", "#00d26a"),
                    (sc[1], TEXTS["scenario_standard"], "standard", "#4da6ff"),
                    (sc[2], TEXTS["scenario_pessimistic"], "pessimistic", "#f8312f")]:
                    val = last[key]
                    pct = (val - cp) / cp * 100
                    sign = "+" if pct >= 0 else ""
                    with col_st:
                        st.markdown(f"""<div class="metric-card">
                            <div style="color:{color}; font-size:0.85em; font-weight:bold;">{name}</div>
                            <div class="value" style="color:{color};">{val:,.0f}</div>
                            <div class="label">{sign}{pct:.1f}%</div></div>""", unsafe_allow_html=True)
        else:
            st.info("予測を実行すると、1年先までの3シナリオ予測が表示されます。")
    with tabs[3]:
        if prediction:
            c1, c2 = st.columns(2)
            with c1:
                score = max(-1, min(1, prediction["predicted_return"] * 10))
                st.plotly_chart(create_sentiment_gauge(score, TEXTS["sentiment_meter"]), use_container_width=True)
                st.markdown(f"**{TEXTS['model_weights']}**")
                st.plotly_chart(create_weight_donut(prediction["weights"]), use_container_width=True)
            with c2:
                st.markdown(f"**{TEXTS['feature_importance']}**")
                st.plotly_chart(create_feature_importance_chart(
                    prediction.get("feature_importance", pd.DataFrame())), use_container_width=True)
            if prediction.get("xgb_metrics"):
                m = prediction["xgb_metrics"]
                mc1, mc2 = st.columns(2)
                if m.get("train_mae") is not None: mc1.metric("学習誤差 (MAE)", f"{m['train_mae']:.4f}")
                if m.get("val_mae") is not None: mc2.metric("検証誤差 (MAE)", f"{m['val_mae']:.4f}")
        else:
            st.info(TEXTS["no_history"])
    with tabs[4]:
        resolved = db.get_resolved_predictions(ticker)
        if not resolved.empty:
            errors = (resolved["predicted_return"] - resolved["actual_return"]).dropna()
            if not errors.empty:
                render_metrics_row({"mae": float(errors.abs().mean() * 100),
                                    "rmse": float(np.sqrt((errors**2).mean()) * 100),
                                    "directional_accuracy": float(resolved["direction_correct"].dropna().mean() * 100) if "direction_correct" in resolved else 0,
                                    "total_predictions": len(resolved)})
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**{TEXTS['actual_vs_predicted']}**")
                st.plotly_chart(create_actual_vs_predicted(resolved), use_container_width=True)
            with c2:
                st.markdown("**誤差推移**")
                st.plotly_chart(create_error_timeline(db.get_error_history(ticker)), use_container_width=True)
            st.markdown(f"**{TEXTS['prediction_history']}**")
            dcols = [c for c in ["prediction_date", "target_date", "horizon_days",
                                  "predicted_price", "actual_price", "error", "direction_correct"] if c in resolved.columns]
            col_rename = {"prediction_date": "予測日", "target_date": "対象日", "horizon_days": "予測日数",
                          "predicted_price": "予測価格", "actual_price": "実績価格", "error": "誤差", "direction_correct": "方向正解"}
            st.dataframe(resolved[dcols].head(20).rename(columns=col_rename), use_container_width=True)
        else:
            st.info(TEXTS["no_history"])
        wh = db.get_weight_history(ticker)
        if not wh.empty:
            st.markdown("**重み調整履歴**")
            wh_rename = {"created_at": "日時", "prophet_weight": "Prophet重み", "xgboost_weight": "XGBoost重み",
                         "mae_prophet": "Prophet誤差", "mae_xgboost": "XGBoost誤差", "reason": "調整理由"}
            st.dataframe(wh[["created_at", "prophet_weight", "xgboost_weight", "mae_prophet", "mae_xgboost", "reason"]].head(10).rename(columns=wh_rename), use_container_width=True)
    with tabs[5]:
        render_portfolio_page()
    with tabs[6]:
        render_backtest_page(ticker, settings["period"], settings["horizon"])
    with tabs[7]:
        st.markdown("### API設定")
        nk = st.text_input(TEXTS["newsapi_key"], value=NEWSAPI_KEY, type="password", help=TEXTS["newsapi_help"])
        if nk:
            import os; os.environ["NEWSAPI_KEY"] = nk
        st.markdown("### マクロ経済データ (FRED)")
        if macro_df is not None and not macro_df.empty:
            st.dataframe(macro_df.tail(10), use_container_width=True)
        else:
            st.caption("FREDデータ未取得")
        st.markdown("### Googleトレンド")
        if trends_df is not None and not trends_df.empty:
            st.line_chart(trends_df.tail(30))
        else:
            st.caption("トレンドデータ未取得")
