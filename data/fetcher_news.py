"""NewsAPI + VADER感情分析"""

import os
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from config import CACHE_TTL_NEWS

_analyzer = SentimentIntensityAnalyzer()


@st.cache_data(ttl=CACHE_TTL_NEWS, show_spinner=False)
def fetch_news(query, days_back=7):
    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        return []
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        resp = requests.get("https://newsapi.org/v2/everything",
                            params={"q": query, "from": from_date,
                                    "sortBy": "relevancy", "pageSize": 50,
                                    "language": "en", "apiKey": api_key},
                            timeout=10)
        resp.raise_for_status()
        return [{"title": a.get("title", ""), "description": a.get("description", ""),
                 "publishedAt": a.get("publishedAt", ""),
                 "source": a.get("source", {}).get("name", "")}
                for a in resp.json().get("articles", []) if a.get("title")]
    except Exception:
        return []


def compute_sentiment(articles):
    if not articles:
        return pd.DataFrame()
    records = []
    for art in articles:
        text = f"{art.get('title', '')} {art.get('description', '')}"
        scores = _analyzer.polarity_scores(text)
        pub = art.get("publishedAt", "")
        if pub:
            records.append({"date": pub[:10], "compound": scores["compound"],
                            "pos": scores["pos"], "neg": scores["neg"],
                            "neu": scores["neu"]})
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    daily = df.groupby("date").agg({"compound": "mean", "pos": "mean",
                                     "neg": "mean", "neu": "mean"})
    daily = daily.rename(columns={"compound": "news_sentiment", "pos": "news_pos",
                                   "neg": "news_neg", "neu": "news_neu"})
    daily.index.name = None
    return daily


@st.cache_data(ttl=CACHE_TTL_NEWS, show_spinner=False)
def get_news_sentiment_features(ticker, company_name, days=30):
    articles = fetch_news(f"{ticker} OR {company_name}", days_back=days)
    return compute_sentiment(articles)
