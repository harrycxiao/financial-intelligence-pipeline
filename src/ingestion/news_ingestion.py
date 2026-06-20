# src/ingestion/news_ingestion.py

import os
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()


FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"


def fetch_news_articles(
    ticker: str,
    days_back: int = 90,
    max_articles: int = 100,
) -> pd.DataFrame:
    """Fetch recent company news from Finnhub."""

    if FINNHUB_API_KEY is None:
        raise ValueError("FINNHUB_API_KEY not found. Add it to your .env file.")

    ticker = ticker.upper().strip()

    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)

    params = {
        "symbol": ticker,
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
        "token": FINNHUB_API_KEY,
    }

    response = requests.get(
        FINNHUB_COMPANY_NEWS_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    articles = response.json()

    rows = []

    for article in articles[:max_articles]:
        published_at = article.get("datetime")

        rows.append(
            {
                "ticker": ticker,
                "title": article.get("headline"),
                "source": article.get("source"),
                "author": None,
                "published_at": pd.to_datetime(published_at, unit="s", utc=True)
                if published_at is not None
                else None,
                "url": article.get("url"),
                "raw_text": None,
                "summary": article.get("summary"),
                "sentiment_score": None,
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    stock = input("Enter stock ticker: ")
    df = fetch_news_articles(stock)

    print(df[["ticker", "published_at", "source", "title", "url"]])
    print(f"Rows fetched: {len(df)}")
