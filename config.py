"""Prophit AI グローバル設定"""

import os

# Database
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "alpha_autolearn.db")

# Default ticker / period
DEFAULT_TICKER = "7203.T"
DEFAULT_PERIOD = "2y"
PREDICTION_HORIZONS = [1, 5, 10, 20, 60, 252]

# API Keys (環境変数から取得)
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")

# Prophet defaults
PROPHET_CHANGEPOINT_PRIOR = 0.05
PROPHET_SEASONALITY_PRIOR = 10.0

# XGBoost defaults (方向精度重視 + バランス正則化)
XGBOOST_DEFAULT_PARAMS = {
    "n_estimators": 500,
    "max_depth": 5,
    "learning_rate": 0.03,
    "subsample": 0.8,
    "colsample_bytree": 0.7,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "min_child_weight": 5,
    "gamma": 0.1,
    "objective": "reg:squarederror",
    "random_state": 42,
}
XGBOOST_N_SPLITS = 5  # TimeSeriesSplit分割数

# Ensemble defaults
ENSEMBLE_INITIAL_WEIGHTS = {"prophet": 0.4, "xgboost": 0.6}
ENSEMBLE_SMOOTHING_ALPHA = 0.3
ENSEMBLE_WEIGHT_CLAMP = (0.15, 0.85)

# FRED series (精度向上のため拡充)
FRED_SERIES = {
    # 金利・イールドカーブ
    "DFF": "米国FFレート",
    "DGS2": "米国2年金利",
    "DGS10": "米国10年金利",
    "T10Y2Y": "10年-2年スプレッド",
    "T10Y3M": "10年-3ヶ月スプレッド",
    # 恐怖指数・ボラティリティ
    "VIXCLS": "VIX恐怖指数",
    # インフレ・物価
    "CPIAUCSL": "米国CPI",
    "PCEPI": "PCE物価指数",
    # 雇用・景気
    "UNRATE": "米国失業率",
    "ICSA": "新規失業保険申請件数",
    # ドル・コモディティ
    "DTWEXBGS": "ドル実効レート",
    "DCOILWTICO": "WTI原油価格",
    "GOLDAMGBD228NLBM": "金価格",
    # 信用スプレッド
    "BAMLH0A0HYM2": "ハイイールドスプレッド",
}

# Cache TTL (seconds)
CACHE_TTL_PRICE = 300       # 5 min
CACHE_TTL_TRENDS = 21600    # 6 hours
CACHE_TTL_NEWS = 3600       # 1 hour
CACHE_TTL_FRED = 3600       # 1 hour

# Period options for UI
PERIOD_OPTIONS = {
    "6ヶ月": "6mo",
    "1年": "1y",
    "2年": "2y",
    "5年": "5y",
    "10年": "10y",
}

# Admin設定
# 管理者設定（Streamlit Cloud Secrets または環境変数で設定してください）
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# メール通知設定 (SMTP)
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "")

# 言語設定
DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "ja")
