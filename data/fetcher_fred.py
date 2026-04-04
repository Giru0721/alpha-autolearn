"""FRED経済指標データ取得"""

import streamlit as st
import pandas as pd
from pandas_datareader import data as pdr

from config import FRED_SERIES, CACHE_TTL_FRED


@st.cache_data(ttl=CACHE_TTL_FRED, show_spinner=False)
def fetch_fred_series(series_id, start, end):
    try:
        df = pdr.DataReader(series_id, "fred", start, end)
        return df.iloc[:, 0].ffill()
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=CACHE_TTL_FRED, show_spinner=False)
def fetch_all_macro(start, end):
    frames = {}
    for sid, label in FRED_SERIES.items():
        s = fetch_fred_series(sid, start, end)
        if not s.empty:
            frames[sid] = s
    if not frames:
        return pd.DataFrame()
    df = pd.DataFrame(frames)
    df = df.asfreq("B").ffill()
    # マクロ指標の変化率を追加（精度向上用）
    for col in list(df.columns):
        df[f"{col}_chg5"] = df[col].pct_change(5)
        df[f"{col}_chg20"] = df[col].pct_change(20)
    return df
