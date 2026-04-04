"""多言語テキスト辞書 (日本語 / English)"""

import streamlit as st
from config import DEFAULT_LANGUAGE

_JA = {
    "app_title": "Alpha-AutoLearn \u2014 AI株価予測システム",
    "app_icon": "\U0001f4c8",
    "sidebar_title": "設定パネル",
    "ticker_input": "銘柄コード / ティッカー",
    "ticker_help": "例: 7203.T (トヨタ), AAPL, BTC-USD, USDJPY=X",
    "period_select": "データ期間",
    "horizon_label": "予測日数",
    "predict_button": "予測を実行",
    "auto_adjust": "自動調整を実行",
    "data_sources": "データソース設定",
    "enable_fred": "FRED経済データを使用",
    "enable_trends": "Googleトレンドを使用",
    "enable_news": "ニュースセンチメントを使用",
    "model_info": "モデル情報",
    "prophet_weight": "Prophet重み",
    "xgboost_weight": "XGBoost重み",
    "last_updated": "最終更新",
    "tab_price": "価格チャート",
    "tab_technical": "テクニカル指標",
    "tab_scenario": "シナリオ予測",
    "tab_prediction": "予測分析",
    "tab_performance": "パフォーマンス追跡",
    "tab_settings": "詳細設定",
    "tab_portfolio": "ポートフォリオ",
    "tab_backtest": "バックテスト",
    "prediction_result": "予測結果",
    "bullish": "\u25b2 強気 (ブリッシュ)",
    "bearish": "\u25bc 弱気 (ベアリッシュ)",
    "neutral": "\u25c6 中立",
    "predicted_price": "予測価格",
    "current_price": "現在価格",
    "confidence_interval": "信頼区間",
    "confidence": "信頼度",
    "error_metrics": "誤差指標",
    "mae_label": "平均絶対誤差 (MAE)",
    "rmse_label": "二乗平均平方根誤差 (RMSE)",
    "mape_label": "平均絶対率誤差 (MAPE)",
    "directional_acc": "方向正解率",
    "total_predictions": "総予測数",
    "price_chart": "価格チャート",
    "news_sentiment": "ニュースセンチメント",
    "feature_importance": "特徴量重要度",
    "model_weights": "モデル重み",
    "actual_vs_predicted": "実績 vs 予測",
    "prediction_history": "予測履歴",
    "sentiment_meter": "AI市場判定メーター",
    "macro_data": "マクロ経済データ",
    "google_trends": "Google検索トレンド",
    "training_status": "モデル学習中...",
    "fetching_data": "データ取得中...",
    "no_data": "データが見つかりません",
    "api_error": "APIエラーが発生しました",
    "insufficient_data": "データが不足しています（最低252取引日分必要）",
    "prediction_saved": "予測が保存されました",
    "weights_updated": "モデル重みが更新されました",
    "adjustment_complete": "自動調整が完了しました",
    "no_history": "予測履歴がまだありません",
    "newsapi_key": "NewsAPI キー",
    "newsapi_help": "https://newsapi.org で無料キーを取得",
    "horizon_1": "1日後",
    "horizon_5": "5日後",
    "horizon_10": "10日後",
    "horizon_20": "20日後",
    "horizon_60": "3ヶ月後",
    "horizon_252": "1年後",
    "scenario_optimistic": "楽観シナリオ",
    "scenario_standard": "標準シナリオ",
    "scenario_pessimistic": "悲観シナリオ",
    "scenario_chart_title": "1年予測シナリオ（楽観・標準・悲観）",
    # Portfolio
    "portfolio_title": "ポートフォリオ管理",
    "add_holding": "銘柄を追加",
    "ticker_code": "銘柄コード",
    "shares": "株数",
    "buy_price": "取得単価",
    "memo": "メモ（任意）",
    "add_btn": "追加",
    "total_value": "総評価額",
    "total_cost": "総投資額",
    "total_pnl": "総損益",
    "no_holdings": "ポートフォリオに銘柄がありません。",
    "composition": "ポートフォリオ構成",
    # Backtest
    "backtest_title": "バックテスト",
    "run_backtest": "バックテスト実行",
    "train_ratio": "学習期間比率",
    "backtest_running": "バックテスト実行中...",
    "backtest_result": "バックテスト結果",
    "sharpe_ratio": "シャープレシオ",
    "max_drawdown": "最大ドローダウン",
    "win_rate": "勝率",
    "profit_factor": "プロフィットファクター",
    "total_return": "累計リターン",
    "backtest_chart": "予測 vs 実績",
    "equity_curve": "資産推移",
    # Admin
    "admin_panel": "管理者パネル",
    "user_management": "ユーザー管理",
    "total_users": "総ユーザー数",
    "plan_distribution": "プラン分布",
    # Language
    "language": "言語 / Language",
    "lang_ja": "日本語",
    "lang_en": "English",
}

_EN = {
    "app_title": "Alpha-AutoLearn \u2014 AI Stock Predictor",
    "app_icon": "\U0001f4c8",
    "sidebar_title": "Settings",
    "ticker_input": "Ticker / Symbol",
    "ticker_help": "e.g. 7203.T (Toyota), AAPL, BTC-USD, USDJPY=X",
    "period_select": "Data Period",
    "horizon_label": "Forecast Days",
    "predict_button": "Run Prediction",
    "auto_adjust": "Auto-Adjust",
    "data_sources": "Data Sources",
    "enable_fred": "Use FRED Economic Data",
    "enable_trends": "Use Google Trends",
    "enable_news": "Use News Sentiment",
    "model_info": "Model Info",
    "prophet_weight": "Prophet Weight",
    "xgboost_weight": "XGBoost Weight",
    "last_updated": "Last Updated",
    "tab_price": "Price Chart",
    "tab_technical": "Technical",
    "tab_scenario": "Scenarios",
    "tab_prediction": "Analysis",
    "tab_performance": "Performance",
    "tab_settings": "Settings",
    "tab_portfolio": "Portfolio",
    "tab_backtest": "Backtest",
    "prediction_result": "Prediction Result",
    "bullish": "\u25b2 Bullish",
    "bearish": "\u25bc Bearish",
    "neutral": "\u25c6 Neutral",
    "predicted_price": "Predicted Price",
    "current_price": "Current Price",
    "confidence_interval": "Confidence Interval",
    "confidence": "Confidence",
    "error_metrics": "Error Metrics",
    "mae_label": "MAE",
    "rmse_label": "RMSE",
    "mape_label": "MAPE",
    "directional_acc": "Directional Accuracy",
    "total_predictions": "Total Predictions",
    "price_chart": "Price Chart",
    "news_sentiment": "News Sentiment",
    "feature_importance": "Feature Importance",
    "model_weights": "Model Weights",
    "actual_vs_predicted": "Actual vs Predicted",
    "prediction_history": "Prediction History",
    "sentiment_meter": "AI Market Gauge",
    "macro_data": "Macro Economic Data",
    "google_trends": "Google Search Trends",
    "training_status": "Training model...",
    "fetching_data": "Fetching data...",
    "no_data": "No data found",
    "api_error": "API error occurred",
    "insufficient_data": "Insufficient data (min 252 trading days required)",
    "prediction_saved": "Prediction saved",
    "weights_updated": "Model weights updated",
    "adjustment_complete": "Auto-adjustment complete",
    "no_history": "No prediction history yet",
    "newsapi_key": "NewsAPI Key",
    "newsapi_help": "Get a free key at https://newsapi.org",
    "horizon_1": "1 day",
    "horizon_5": "5 days",
    "horizon_10": "10 days",
    "horizon_20": "20 days",
    "horizon_60": "3 months",
    "horizon_252": "1 year",
    "scenario_optimistic": "Optimistic",
    "scenario_standard": "Standard",
    "scenario_pessimistic": "Pessimistic",
    "scenario_chart_title": "1-Year Forecast Scenarios",
    # Portfolio
    "portfolio_title": "Portfolio Management",
    "add_holding": "Add Holding",
    "ticker_code": "Ticker",
    "shares": "Shares",
    "buy_price": "Buy Price",
    "memo": "Memo (optional)",
    "add_btn": "Add",
    "total_value": "Total Value",
    "total_cost": "Total Cost",
    "total_pnl": "Total P&L",
    "no_holdings": "No holdings in portfolio.",
    "composition": "Portfolio Composition",
    # Backtest
    "backtest_title": "Backtest",
    "run_backtest": "Run Backtest",
    "train_ratio": "Training Ratio",
    "backtest_running": "Running backtest...",
    "backtest_result": "Backtest Results",
    "sharpe_ratio": "Sharpe Ratio",
    "max_drawdown": "Max Drawdown",
    "win_rate": "Win Rate",
    "profit_factor": "Profit Factor",
    "total_return": "Total Return",
    "backtest_chart": "Predicted vs Actual",
    "equity_curve": "Equity Curve",
    # Admin
    "admin_panel": "Admin Panel",
    "user_management": "User Management",
    "total_users": "Total Users",
    "plan_distribution": "Plan Distribution",
    # Language
    "language": "Language / 言語",
    "lang_ja": "日本語",
    "lang_en": "English",
}

_TEXTS_MAP = {"ja": _JA, "en": _EN}


def get_lang() -> str:
    """現在の言語設定を取得"""
    return st.session_state.get("language", DEFAULT_LANGUAGE)


def set_lang(lang: str):
    """言語設定を変更"""
    st.session_state["language"] = lang


def T(key: str) -> str:
    """現在の言語でテキスト取得"""
    lang = get_lang()
    texts = _TEXTS_MAP.get(lang, _JA)
    return texts.get(key, _JA.get(key, key))


# 後方互換: 旧コードが TEXTS["key"] で参照するためのプロキシ
class _TextProxy(dict):
    def __getitem__(self, key):
        return T(key)

    def get(self, key, default=None):
        val = T(key)
        return val if val != key else (default or val)


TEXTS = _TextProxy()

HORIZON_LABELS = {
    1: "horizon_1", 5: "horizon_5",
    10: "horizon_10", 20: "horizon_20",
    60: "horizon_60", 252: "horizon_252",
}
