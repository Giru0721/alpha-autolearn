"""Google Trends データ取得"""

import time
import streamlit as st
import pandas as pd
from pytrends.request import TrendReq

from config import CACHE_TTL_TRENDS


@st.cache_data(ttl=CACHE_TTL_TRENDS, show_spinner=False)
def fetch_search_interest(keywords, timeframe="today 3-m"):
    kw_list = keywords[:5]
    for attempt in range(4):
        try:
            pytrends = TrendReq(hl="ja-JP", tz=540)
            pytrends.build_payload(kw_list, timeframe=timeframe)
            df = pytrends.interest_over_time()
            if not df.empty and "isPartial" in df.columns:
                df = df.drop(columns=["isPartial"])
            df = df.rename(columns={c: f"trend_{c}" for c in df.columns})
            return df
        except Exception:
            time.sleep(2 ** (attempt + 1))
    return pd.DataFrame()
