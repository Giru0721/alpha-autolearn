"""再利用可能なUIコンポーネント"""

import streamlit as st
from ui.i18n import TEXTS


def render_prediction_card(prediction, currency=""):
    d = prediction["direction"]
    dir_text = TEXTS["bullish"] if d == "bullish" else (TEXTS["bearish"] if d == "bearish" else TEXTS["neutral"])
    dir_class = d if d in ("bullish", "bearish") else "neutral"
    pct = prediction["predicted_return"] * 100
    sign = "+" if pct >= 0 else ""
    color = "#00d26a" if pct >= 0 else "#f8312f"

    # 予測理由テキスト
    reason = prediction.get("reason", "")
    reason_html = ""
    if reason:
        lines = reason.split("\n")
        summary_line = lines[0] if lines else ""
        bullet_lines = lines[1:] if len(lines) > 1 else []
        bullets_html = "".join(
            f'<div style="font-size:0.85em; color:#c9d1d9; margin:3px 0 3px 4px;">{line}</div>'
            for line in bullet_lines if line.strip()
        )
        reason_html = f"""
        <div style="margin-top:14px; padding:12px 14px; background:rgba(255,255,255,0.04);
                    border-radius:8px; border-left:3px solid {color};">
            <div style="font-size:0.9em; font-weight:600; color:#e6edf3; margin-bottom:6px;">
                {summary_line}
            </div>
            {bullets_html}
        </div>"""

    st.markdown(f"""
    <div class="prediction-card">
        <h2 class="{dir_class}">{dir_text}</h2>
        <div class="price">{currency}{prediction['ensemble_price']:,.1f}
            <span style="font-size:0.5em; color:{color}">({sign}{pct:.2f}%)</span>
        </div>
        <div class="sub">
            {TEXTS['current_price']}: {currency}{prediction['current_price']:,.1f}
            <span class="sep">&nbsp;|&nbsp;</span>
            {TEXTS['confidence_interval']}: {currency}{prediction['confidence_lower']:,.1f}
            ~ {currency}{prediction['confidence_upper']:,.1f}
        </div>
        <div class="sub" style="margin-top:8px;">
            Prophet: {currency}{prediction['prophet_price']:,.1f}
            <span class="sep">&nbsp;|&nbsp;</span>
            XGBoost: {currency}{prediction['xgboost_price']:,.1f}
        </div>
        {reason_html}
    </div>
    """, unsafe_allow_html=True)


def render_metrics_row(metrics):
    cols = st.columns(4)
    items = [
        (TEXTS["mae_label"], f"{metrics.get('mae', 0):.2f}%"),
        (TEXTS["rmse_label"], f"{metrics.get('rmse', 0):.2f}%"),
        (TEXTS["directional_acc"], f"{metrics.get('directional_accuracy', 0):.1f}%"),
        (TEXTS["total_predictions"], str(metrics.get("total_predictions", 0))),
    ]
    for col, (label, value) in zip(cols, items):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="value">{value}</div>
                <div class="label">{label}</div>
            </div>
            """, unsafe_allow_html=True)


def render_model_info(weights):
    st.markdown(f"**{TEXTS['model_info']}**")
    c1, c2 = st.columns(2)
    c1.metric(TEXTS["prophet_weight"], f"{weights['prophet']:.1%}")
    c2.metric(TEXTS["xgboost_weight"], f"{weights['xgboost']:.1%}")
