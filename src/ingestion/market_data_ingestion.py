# src/ingestion/market_data_ingestion.py

import pandas as pd
import yfinance as yf


def fetch_market_data(
    ticker: str,
    period: str = "5y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch historical OHLCV market data from Yahoo Finance."""

    ticker = ticker.upper().strip()
    stock = yf.Ticker(ticker)

    info = stock.info
    shares_outstanding = info.get("sharesOutstanding")

    data = stock.history(
        period=period,
        interval=interval,
        auto_adjust=False,
    )

    if data.empty:
        raise ValueError(f"No market data found for ticker: {ticker}")

    data = data.reset_index()

    data = data.rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adjusted_close",
            "Volume": "volume",
        }
    )

    expected_columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
    ]

    data = data[expected_columns]
    data["ticker"] = ticker
    data["shares_outstanding"] = int(shares_outstanding) if shares_outstanding is not None else None

    return data


if __name__ == "__main__":
    stock = input("Enter stock ticker: ")
    df = fetch_market_data(stock)

    print(df.head())
    print(df.tail())
    print(f"Rows fetched: {len(df)}")