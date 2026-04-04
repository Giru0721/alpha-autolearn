"""yfinanceによる株価・仮想通貨・為替データ取得"""

import streamlit as st
import yfinance as yf
import pandas as pd

from config import CACHE_TTL_PRICE

SECTOR_JA = {
    "Technology": "テクノロジー", "Consumer Cyclical": "一般消費財",
    "Consumer Defensive": "生活必需品", "Healthcare": "ヘルスケア",
    "Financial Services": "金融", "Industrials": "資本財",
    "Energy": "エネルギー", "Utilities": "公益事業",
    "Real Estate": "不動産", "Communication Services": "通信",
    "Basic Materials": "素材",
}

EXCHANGE_JA = {
    "JPX": "東京証券取引所", "NMS": "NASDAQ", "NYQ": "ニューヨーク証券取引所",
    "NGM": "NASDAQ", "PCX": "NYSE Arca", "CCC": "暗号資産", "CCY": "外国為替",
}


@st.cache_data(ttl=CACHE_TTL_PRICE, show_spinner=False)
def fetch_ohlcv(ticker: str, period: str = "2y",
                interval: str = "1d") -> pd.DataFrame:
    """OHLCVデータを取得。DatetimeIndex付きDataFrameを返す。"""
    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period=period, interval=interval)
    except Exception:
        try:
            df = yf.download(ticker, period=period, interval=interval,
                             progress=False, auto_adjust=True)
        except Exception:
            return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns={"Stock Splits": "Stock_Splits",
                            "Capital Gains": "Capital_Gains"})
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.dropna(subset=["Close"], inplace=True)
    return df


@st.cache_data(ttl=CACHE_TTL_PRICE, show_spinner=False)
def fetch_ticker_info(ticker: str) -> dict:
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        sector = info.get("sector", "")
        exchange = info.get("exchange", "")
        return {
            "name": info.get("shortName") or info.get("longName") or ticker,
            "sector": SECTOR_JA.get(sector, sector) or "不明",
            "currency": info.get("currency", "不明"),
            "exchange": EXCHANGE_JA.get(exchange, exchange) or "不明",
            "market_cap": info.get("marketCap"),
        }
    except Exception:
        return {"name": ticker, "sector": "不明", "currency": "不明",
                "exchange": "不明", "market_cap": None}


def fetch_close_on_date(ticker: str, date: str) -> float | None:
    try:
        target = pd.Timestamp(date)
        start = target - pd.Timedelta(days=5)
        end = target + pd.Timedelta(days=5)
        tk = yf.Ticker(ticker)
        df = tk.history(start=start.strftime("%Y-%m-%d"),
                        end=end.strftime("%Y-%m-%d"))
        if df.empty:
            return None
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        mask = df.index <= target
        if mask.any():
            return float(df.loc[mask, "Close"].iloc[-1])
        return float(df["Close"].iloc[0])
    except Exception:
        return None
