"""テクニカル指標算出・特徴量マトリクス構築 (pandas/numpy のみ)"""

import pandas as pd
import numpy as np


# === TA ヘルパー関数 (pandas-ta 不要) ===

def _sma(series, length):
    return series.rolling(window=length, min_periods=length).mean()


def _ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def _rsi(series, length=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series, fast=12, slow=26, signal=9):
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _bbands(series, length=20, std=2):
    mid = _sma(series, length)
    rolling_std = series.rolling(window=length, min_periods=length).std()
    upper = mid + std * rolling_std
    lower = mid - std * rolling_std
    bandwidth = (upper - lower) / mid.replace(0, np.nan)
    pct = (series - lower) / (upper - lower).replace(0, np.nan)
    return lower, mid, upper, bandwidth, pct


def _adx(high, low, close, length=14):
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / length, min_periods=length, adjust=False).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1 / length, min_periods=length, adjust=False).mean() / atr.replace(0, np.nan))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    return adx, plus_di, minus_di


def _stoch(high, low, close, k_period=14, d_period=3):
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = _sma(k, d_period)
    return k, d


def _atr(high, low, close, length=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()


def _obv(close, volume):
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    return (volume * direction).cumsum()


# === メイン関数 ===

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # === 基本テクニカル ===
    out["RSI_14"] = _rsi(out["Close"], 14)
    out["RSI_7"] = _rsi(out["Close"], 7)
    macd_line, macd_signal, macd_hist = _macd(out["Close"], 12, 26, 9)
    out["MACD"] = macd_line
    out["MACD_hist"] = macd_hist
    out["MACD_signal"] = macd_signal
    bb_lower, bb_mid, bb_upper, bb_bw, bb_pct = _bbands(out["Close"], 20, 2)
    out["BB_lower"] = bb_lower
    out["BB_mid"] = bb_mid
    out["BB_upper"] = bb_upper
    out["BB_bandwidth"] = bb_bw
    out["BB_pct"] = bb_pct
    out["SMA_20"] = _sma(out["Close"], 20)
    out["SMA_50"] = _sma(out["Close"], 50)
    out["SMA_200"] = _sma(out["Close"], 200)
    out["EMA_12"] = _ema(out["Close"], 12)
    out["EMA_26"] = _ema(out["Close"], 26)

    # === ADX（トレンド強度） ===
    adx_val, di_plus, di_minus = _adx(out["High"], out["Low"], out["Close"], 14)
    out["ADX_14"] = adx_val
    out["DI_plus"] = di_plus
    out["DI_minus"] = di_minus

    # === ストキャスティクス ===
    stoch_k, stoch_d = _stoch(out["High"], out["Low"], out["Close"])
    out["STOCH_K"] = stoch_k
    out["STOCH_D"] = stoch_d

    # === ATR（ボラティリティ） ===
    atr = _atr(out["High"], out["Low"], out["Close"], 14)
    out["ATR_14"] = atr
    out["ATR_pct"] = atr / out["Close"].replace(0, np.nan)

    # === OBV（出来高トレンド） ===
    if "Volume" in out.columns:
        obv = _obv(out["Close"], out["Volume"])
        out["OBV"] = obv
        out["OBV_SMA_20"] = _sma(obv, 20)
        out["Volume_SMA_20"] = _sma(out["Volume"], 20)
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
