"""テクニカル指標算出・特徴量マトリクス構築"""

import pandas as pd
import numpy as np
import pandas_ta as ta


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # === 基本テクニカル ===
    out["RSI_14"] = ta.rsi(out["Close"], length=14)
    out["RSI_7"] = ta.rsi(out["Close"], length=7)
    macd = ta.macd(out["Close"], fast=12, slow=26, signal=9)
    if macd is not None:
        out["MACD"] = macd.iloc[:, 0]
        out["MACD_hist"] = macd.iloc[:, 1]
        out["MACD_signal"] = macd.iloc[:, 2]
    bb = ta.bbands(out["Close"], length=20, std=2)
    if bb is not None:
        out["BB_lower"] = bb.iloc[:, 0]
        out["BB_mid"] = bb.iloc[:, 1]
        out["BB_upper"] = bb.iloc[:, 2]
        out["BB_bandwidth"] = bb.iloc[:, 3] if bb.shape[1] > 3 else None
        out["BB_pct"] = bb.iloc[:, 4] if bb.shape[1] > 4 else None
    out["SMA_20"] = ta.sma(out["Close"], length=20)
    out["SMA_50"] = ta.sma(out["Close"], length=50)
    out["SMA_200"] = ta.sma(out["Close"], length=200)
    out["EMA_12"] = ta.ema(out["Close"], length=12)
    out["EMA_26"] = ta.ema(out["Close"], length=26)

    # === ADX（トレンド強度） ===
    adx = ta.adx(out["High"], out["Low"], out["Close"], length=14)
    if adx is not None:
        out["ADX_14"] = adx.iloc[:, 0]
        out["DI_plus"] = adx.iloc[:, 1]
        out["DI_minus"] = adx.iloc[:, 2]

    # === ストキャスティクス ===
    stoch = ta.stoch(out["High"], out["Low"], out["Close"])
    if stoch is not None:
        out["STOCH_K"] = stoch.iloc[:, 0]
        out["STOCH_D"] = stoch.iloc[:, 1]

    # === ATR（ボラティリティ） ===
    atr = ta.atr(out["High"], out["Low"], out["Close"], length=14)
    if atr is not None:
        out["ATR_14"] = atr
        out["ATR_pct"] = atr / out["Close"].replace(0, np.nan)

    # === OBV（出来高トレンド） ===
    if "Volume" in out.columns:
        obv = ta.obv(out["Close"], out["Volume"])
        if obv is not None:
            out["OBV"] = obv
            out["OBV_SMA_20"] = ta.sma(obv, length=20)
        out["Volume_SMA_20"] = ta.sma(out["Volume"], length=20)
        out["Volume_ratio"] = out["Volume"] / out["Volume_SMA_20"].replace(0, np.nan)

    # === リターン（複数期間） ===
    out["Returns_1d"] = out["Close"].pct_change(1)
    out["Returns_5d"] = out["Close"].pct_change(5)
    out["Returns_10d"] = out["Close"].pct_change(10)
    out["Returns_20d"] = out["Close"].pct_change(20)
    out["Returns_60d"] = out["Close"].pct_change(60)

    # === ボラティリティ（複数ウィンドウ） ===
    out["Volatility_5d"] = out["Returns_1d"].rolling(5).std()
    out["Volatility_20d"] = out["Returns_1d"].rolling(20).std()
    out["Volatility_60d"] = out["Returns_1d"].rolling(60).std()

    # === ラグ特徴量（過去のリターンをXGBoostに供給） ===
    for lag in [1, 2, 3, 5, 10, 20]:
        out[f"Return_lag_{lag}"] = out["Returns_1d"].shift(lag)
    for lag in [1, 2, 5]:
        out[f"Vol_lag_{lag}"] = out["Volatility_20d"].shift(lag)

    # === 価格位置・乖離率 ===
    out["HL_pct"] = (out["High"] - out["Low"]) / out["Close"].replace(0, np.nan)
    out["Dist_SMA20"] = (out["Close"] - out["SMA_20"]) / out["SMA_20"].replace(0, np.nan)
    out["Dist_SMA50"] = (out["Close"] - out["SMA_50"]) / out["SMA_50"].replace(0, np.nan)
    if "SMA_200" in out.columns:
        out["Dist_SMA200"] = (out["Close"] - out["SMA_200"]) / out["SMA_200"].replace(0, np.nan)

    # === ゴールデンクロス / デッドクロス シグナル ===
    if "SMA_20" in out.columns and "SMA_50" in out.columns:
        out["SMA20_above_50"] = (out["SMA_20"] > out["SMA_50"]).astype(float)

    # === 曜日・月（季節性） ===
    if hasattr(out.index, 'dayofweek'):
        out["DayOfWeek"] = out.index.dayofweek.astype(float)
        out["Month"] = out.index.month.astype(float)
        out["IsMonthEnd"] = out.index.is_month_end.astype(float)

    return out


def create_target_variables(df, horizons):
    out = df.copy()
    for h in horizons:
        out[f"target_{h}d"] = out["Close"].pct_change(h).shift(-h)
    return out


def build_feature_matrix(price_df, macro_df=None, trends_df=None, sentiment_df=None):
    df = add_technical_indicators(price_df)
    for extra_df in [macro_df, trends_df, sentiment_df]:
        if extra_df is not None and not extra_df.empty:
            extra_df.index = pd.to_datetime(extra_df.index)
            if extra_df.index.tz is not None:
                extra_df.index = extra_df.index.tz_localize(None)
            df = df.join(extra_df, how="left")
            for col in extra_df.columns:
                if col in df.columns:
                    df[col] = df[col].ffill()
    return df


def get_feature_columns(df):
    exclude_prefixes = ("target_", "Open", "High", "Low", "Close", "Volume")
    exclude_exact = {"Stock_Splits", "Capital_Gains", "Dividends"}
    cols = []
    for c in df.columns:
        if c in exclude_exact:
            continue
        if any(c.startswith(p) for p in exclude_prefixes):
            continue
        if df[c].dtype in ("float64", "float32", "int64", "int32"):
            cols.append(c)
    return cols
