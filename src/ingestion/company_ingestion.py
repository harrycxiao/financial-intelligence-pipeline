from typing import Optional

import yfinance as yf


EXCHANGE_MAP = {
    "NMS": "NASDAQ",
    "NGM": "NASDAQ",
    "NCM": "NASDAQ",
    "NYQ": "NYSE",
    "ASE": "NYSE American",
    "PCX": "NYSE Arca",
    "PNK": "OTC Pink",
    "OTC": "OTC",
}


def normalize_exchange(exchange_code: Optional[str]) -> Optional[str]:
    if exchange_code is None:
        return None

    return EXCHANGE_MAP.get(exchange_code, exchange_code)


def fetch_company_metadata(ticker: str) -> dict:
    ticker = ticker.upper().strip()
    stock = yf.Ticker(ticker)

    info = stock.info
    exchange_code = info.get("exchange")

    return {
        "ticker": ticker,
        "name": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "exchange": normalize_exchange(exchange_code),

        # CIK is better sourced from SEC data, so sec_ingestion.py will update this later.
        "cik": None,
    }


if __name__ == "__main__":
    stock = input("Enter stock ticker: ")
    data = fetch_company_metadata(stock)
    print(data)