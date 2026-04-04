"""Plotly チャート群"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

DARK_TEMPLATE = "plotly_dark"
COLORS = {"bullish": "#00d26a", "bearish": "#f8312f", "neutral": "#ffd000",
          "primary": "#4da6ff", "secondary": "#8b949e", "bg": "#0E1117", "card_bg": "#161b22"}


def create_candlestick_chart(df, prediction=None):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                                  increasing_line_color=COLORS["bullish"], decreasing_line_color=COLORS["bearish"],
                                  name="価格"), row=1, col=1)
    if "SMA_20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA_20"], line=dict(color=COLORS["primary"], width=1),
                                  name="移動平均20日", opacity=0.7), row=1, col=1)
    if "SMA_50" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], line=dict(color="#e040fb", width=1),
                                  name="移動平均50日", opacity=0.7), row=1, col=1)
    if prediction:
        last_date = df.index[-1]
        pred_date = last_date + pd.Timedelta(days=prediction.get("horizon", 5))
        color = COLORS["bullish"] if prediction["direction"] == "bullish" else (
            COLORS["bearish"] if prediction["direction"] == "bearish" else COLORS["neutral"])
        fig.add_trace(go.Scatter(x=[pred_date], y=[prediction["ensemble_price"]], mode="markers+text",
                                  marker=dict(size=14, color=color, symbol="star"),
                                  text=[f"予測: {prediction['ensemble_price']:,.0f}"],
                                  textposition="top center", textfont=dict(color=color), name="予測価格"), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=[last_date, pred_date, pred_date, last_date],
            y=[prediction["current_price"], prediction["confidence_upper"],
               prediction["confidence_lower"], prediction["current_price"]],
            fill="toself", fillcolor="rgba(77,166,255,0.1)",
            line=dict(color="rgba(77,166,255,0.3)"), name="信頼区間"), row=1, col=1)
    if "Volume" in df.columns:
        colors = [COLORS["bullish"] if c >= o else COLORS["bearish"] for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=colors, opacity=0.5,
                              name="出来高", showlegend=False), row=2, col=1)
    fig.update_layout(template=DARK_TEMPLATE, height=600, xaxis_rangeslider_visible=False,
                      margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02),
                      paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"])
    fig.update_yaxes(title_text="価格", row=1, col=1)
    fig.update_yaxes(title_text="出来高", row=2, col=1)
    return fig


def create_technical_chart(df):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.4, 0.2, 0.2, 0.2],
                        subplot_titles=("価格 + ボリンジャーバンド", "RSI（14日）", "MACD", "出来高"))
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], line=dict(color=COLORS["primary"], width=1.5),
                              name="終値"), row=1, col=1)
    if "BB_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"], line=dict(color=COLORS["secondary"], width=0.5, dash="dot"),
                                  name="BB上限", showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_lower"], line=dict(color=COLORS["secondary"], width=0.5, dash="dot"),
                                  fill="tonexty", fillcolor="rgba(139,148,158,0.1)", name="BB下限", showlegend=False), row=1, col=1)
    if "SMA_20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA_20"], line=dict(color="#ffd000", width=1), name="移動平均20日"), row=1, col=1)
    if "RSI_14" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI_14"], line=dict(color=COLORS["primary"], width=1.5), name="RSI（14日）"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=COLORS["bearish"], opacity=0.5, row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=COLORS["bullish"], opacity=0.5, row=2, col=1)
    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], line=dict(color=COLORS["primary"], width=1.5), name="MACD線"), row=3, col=1)
        if "MACD_signal" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], line=dict(color=COLORS["bearish"], width=1), name="シグナル線"), row=3, col=1)
        if "MACD_hist" in df.columns:
            ch = [COLORS["bullish"] if v >= 0 else COLORS["bearish"] for v in df["MACD_hist"]]
            fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], marker_color=ch, opacity=0.5, showlegend=False), row=3, col=1)
    if "Volume" in df.columns:
        cv = [COLORS["bullish"] if c >= o else COLORS["bearish"] for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=cv, opacity=0.5, showlegend=False), row=4, col=1)
        if "Volume_SMA_20" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["Volume_SMA_20"], line=dict(color=COLORS["neutral"], width=1), showlegend=False), row=4, col=1)
    fig.update_layout(template=DARK_TEMPLATE, height=800, margin=dict(l=0, r=0, t=30, b=0),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02), paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"])
    return fig


def create_scenario_forecast_chart(price_df, scenario_df, current_price):
    fig = go.Figure()
    recent = price_df.tail(126)
    fig.add_trace(go.Scatter(x=recent.index, y=recent["Close"], line=dict(color="white", width=2), name="過去実績"))
    if scenario_df is not None and not scenario_df.empty:
        fig.add_trace(go.Scatter(x=scenario_df["ds"], y=scenario_df["optimistic"],
                                  line=dict(color=COLORS["bullish"], width=2, dash="dash"), name="楽観シナリオ"))
        fig.add_trace(go.Scatter(x=scenario_df["ds"], y=scenario_df["standard"],
                                  line=dict(color=COLORS["primary"], width=2.5), name="標準シナリオ"))
        fig.add_trace(go.Scatter(x=scenario_df["ds"], y=scenario_df["pessimistic"],
                                  line=dict(color=COLORS["bearish"], width=2, dash="dash"), name="悲観シナリオ"))
        fig.add_trace(go.Scatter(
            x=pd.concat([scenario_df["ds"], scenario_df["ds"][::-1]], ignore_index=True),
            y=pd.concat([scenario_df["optimistic"], scenario_df["pessimistic"][::-1]], ignore_index=True),
            fill="toself", fillcolor="rgba(77,166,255,0.08)", line=dict(width=0), name="予測レンジ", showlegend=False))
        fig.add_hline(y=current_price, line_dash="dot", line_color=COLORS["secondary"], opacity=0.5,
                      annotation_text=f"現在: {current_price:,.0f}", annotation_font_color=COLORS["secondary"])
        last = scenario_df.iloc[-1]
        for name, col, color in [("楽観", "optimistic", COLORS["bullish"]),
                                  ("標準", "standard", COLORS["primary"]),
                                  ("悲観", "pessimistic", COLORS["bearish"])]:
            pct = (last[col] - current_price) / current_price * 100
            sign = "+" if pct >= 0 else ""
            fig.add_annotation(x=last["ds"], y=last[col], text=f"{name}: {last[col]:,.0f} ({sign}{pct:.1f}%)",
                              font=dict(color=color, size=12), showarrow=True, arrowhead=2, arrowcolor=color, ax=60, ay=0)
    fig.update_layout(template=DARK_TEMPLATE, height=500, margin=dict(l=0, r=120, t=30, b=0),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02),
                      paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"], yaxis_title="価格")
    return fig


def create_sentiment_gauge(score, label=""):
    fig = go.Figure(go.Indicator(mode="gauge+number", value=score, number={"font": {"size": 36}},
                                  title={"text": label, "font": {"size": 16}},
                                  gauge={"axis": {"range": [-1, 1]}, "bar": {"color": COLORS["primary"]},
                                         "bgcolor": COLORS["card_bg"], "borderwidth": 0,
                                         "steps": [{"range": [-1, -0.3], "color": "rgba(248,49,47,0.3)"},
                                                   {"range": [-0.3, 0.3], "color": "rgba(255,208,0,0.2)"},
                                                   {"range": [0.3, 1], "color": "rgba(0,210,106,0.3)"}],
                                         "threshold": {"line": {"color": "white", "width": 3}, "thickness": 0.8, "value": score}}))
    fig.update_layout(template=DARK_TEMPLATE, height=280, margin=dict(l=30, r=30, t=50, b=20), paper_bgcolor=COLORS["bg"])
    return fig


def create_feature_importance_chart(importance_df):
    if importance_df.empty:
        fig = go.Figure()
        fig.update_layout(template=DARK_TEMPLATE, annotations=[dict(text="データなし", showarrow=False)])
        return fig
    df = importance_df.sort_values("importance", ascending=True)
    fig = go.Figure(go.Bar(x=df["importance"], y=df["feature"], orientation="h", marker_color=COLORS["primary"]))
    fig.update_layout(template=DARK_TEMPLATE, height=max(300, len(df) * 28), margin=dict(l=0, r=0, t=10, b=0),
                      paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"], yaxis=dict(tickfont=dict(size=11)))
    return fig


def create_weight_donut(weights):
    fig = go.Figure(go.Pie(labels=["Prophet（トレンド）", "XGBoost（短期）"], values=[weights["prophet"], weights["xgboost"]],
                            hole=0.55, marker_colors=["#4da6ff", "#e040fb"], textinfo="label+percent", textfont_size=14))
    fig.update_layout(template=DARK_TEMPLATE, height=280, margin=dict(l=20, r=20, t=20, b=20),
                      paper_bgcolor=COLORS["bg"], showlegend=False)
    return fig


def create_error_timeline(error_df):
    if error_df.empty:
        fig = go.Figure()
        fig.update_layout(template=DARK_TEMPLATE, annotations=[dict(text="予測履歴がまだありません", showarrow=False, font=dict(size=16))])
        return fig
    fig = go.Figure()
    for col, name, color, dash in [("ensemble_mae", "アンサンブル誤差", COLORS["primary"], None),
                                    ("prophet_mae", "Prophet誤差", "#4da6ff", "dot"),
                                    ("xgboost_mae", "XGBoost誤差", "#e040fb", "dot")]:
        if col in error_df.columns:
            fig.add_trace(go.Scatter(x=error_df["snapshot_date"], y=error_df[col], mode="lines+markers" if dash is None else "lines",
                                      name=name, line=dict(color=color, width=2 if dash is None else 1, dash=dash)))
    fig.update_layout(template=DARK_TEMPLATE, height=350, margin=dict(l=0, r=0, t=10, b=0),
                      paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"],
                      legend=dict(orientation="h", yanchor="bottom", y=1.02), yaxis_title="平均絶対誤差")
    return fig


def create_actual_vs_predicted(history_df):
    if history_df.empty:
        fig = go.Figure()
        fig.update_layout(template=DARK_TEMPLATE, annotations=[dict(text="予測履歴がまだありません", showarrow=False, font=dict(size=16))])
        return fig
    df = history_df.dropna(subset=["actual_price", "predicted_price"])
    if df.empty:
        return go.Figure().update_layout(template=DARK_TEMPLATE)
    mn, mx = min(df["actual_price"].min(), df["predicted_price"].min()) * 0.95, max(df["actual_price"].max(), df["predicted_price"].max()) * 1.05
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["actual_price"], y=df["predicted_price"], mode="markers",
                              marker=dict(size=8, color=COLORS["primary"], opacity=0.7), name="予測",
                              text=df["prediction_date"], hovertemplate="日付: %{text}<br>実績: %{x:,.0f}<br>予測: %{y:,.0f}"))
    fig.add_trace(go.Scatter(x=[mn, mx], y=[mn, mx], mode="lines",
                              line=dict(color=COLORS["secondary"], width=1, dash="dash"), name="完全一致"))
    fig.update_layout(template=DARK_TEMPLATE, height=400, margin=dict(l=0, r=0, t=10, b=0),
                      paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"], xaxis_title="実績価格", yaxis_title="予測価格")
    return fig
