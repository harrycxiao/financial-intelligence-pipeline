# scripts/filter_us_universe.py

import time
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf


RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


def normalize_yahoo_ticker(ticker: str) -> str:
    return (
        str(ticker)
        .upper()
        .strip()
        .replace(".", "-")
        .replace("/", "-")
    )


def looks_like_common_stock(security_name: str) -> bool:
    name = str(security_name).upper()

    blocked_terms = [
        "ETF",
        "ETN",
        "FUND",
        "MUTUAL FUND",
        "CLOSED-END FUND",
        "CLOSED END FUND",
        "BOND",
        "DEBENTURE",
        "NOTE",
        "NOTES",
        "PREFERRED",
        "PREFERENCE",
        "PFD",
        "WARRANT",
        "WARRANTS",
        "RIGHT",
        "RIGHTS",
        "UNIT",
        "UNITS",
        "SPAC",
        "ACQUISITION CORP",
        "ACQUISITION CORPORATION",
        "ACQUISITION COMPANY",
    ]

    return not any(term in name for term in blocked_terms)


def fetch_all_us_stock_candidates(limit: Optional[int] = None) -> pd.DataFrame:
    nasdaq = pd.read_csv(NASDAQ_LISTED_URL, sep="|", dtype=str)
    other = pd.read_csv(OTHER_LISTED_URL, sep="|", dtype=str)

    nasdaq = nasdaq.loc[nasdaq["Symbol"].notna()].copy()
    nasdaq = nasdaq[nasdaq["Symbol"] != "File Creation Time"]

    nasdaq_candidates = pd.DataFrame(
        {
            "ticker": nasdaq["Symbol"],
            "security_name": nasdaq["Security Name"],
            "exchange": "NASDAQ",
            "etf": nasdaq["ETF"],
            "test_issue": nasdaq["Test Issue"],
        }
    )

    other = other.loc[other["ACT Symbol"].notna()].copy()
    other = other[other["ACT Symbol"] != "File Creation Time"]

    other_candidates = pd.DataFrame(
        {
            "ticker": other["ACT Symbol"],
            "security_name": other["Security Name"],
            "exchange": other["Exchange"],
            "etf": other["ETF"],
            "test_issue": other["Test Issue"],
        }
    )

    candidates = pd.concat(
        [nasdaq_candidates, other_candidates],
        ignore_index=True,
    )

    candidates["ticker"] = candidates["ticker"].apply(normalize_yahoo_ticker)
    candidates["security_name"] = candidates["security_name"].astype(str)

    candidates = candidates.drop_duplicates(subset=["ticker"])

    candidates = candidates[
        (candidates["etf"].fillna("N") == "N")
        & (candidates["test_issue"].fillna("N") == "N")
    ].copy()

    candidates = candidates[
        candidates["security_name"].apply(looks_like_common_stock)
    ].copy()

    candidates = candidates.set_index("ticker")
    candidates = candidates.sort_index()
    candidates = candidates.reset_index()

    if limit is not None:
        candidates = candidates.head(limit).copy()

    return candidates


def get_yahoo_price_and_market_cap(
    ticker: str,
    max_retries: int = 3,
    retry_sleep_seconds: float = 10.0,
    cooldown_seconds: float = 3600.0,
) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Fetch latest price and market cap from Yahoo Finance.

    If Yahoo appears rate-limited or temporarily broken, sleep and retry
    the same ticker instead of incorrectly treating it as ineligible.
    """

    rate_limit_keywords = [
        "too many requests",
        "rate limited",
        "rate limit",
        "429",
        "temporarily unavailable",
        "connection aborted",
        "connection reset",
        "remote end closed",
        "timed out",
        "timeout",
        "dns",
        "name resolution",
    ]
    
    lookup_error: Optional[str] = None
    attempt = 1

    while attempt <= max_retries:
        try:
            stock = yf.Ticker(ticker)

            price = None
            market_cap = None

            try:
                fast_info = stock.fast_info
                price = fast_info.get("last_price")
                market_cap = fast_info.get("market_cap")
            except Exception as fast_info_error:
                fast_info_error_message = str(fast_info_error)
            else:
                fast_info_error_message = None

            if price is None or market_cap is None:
                info = stock.info
                price = price if price is not None else info.get("currentPrice")
                market_cap = market_cap if market_cap is not None else info.get("marketCap")

            price = float(price) if price is not None else None
            market_cap = float(market_cap) if market_cap is not None else None

            if price is not None and market_cap is not None:
                return price, market_cap, None

            lookup_error = (
                fast_info_error_message
                if fast_info_error_message is not None
                else "Missing price or market_cap"
            )

        except Exception as error:
            lookup_error = str(error)

        lower_error = lookup_error.lower()

        is_rate_limit_like_error = any(
            keyword in lower_error for keyword in rate_limit_keywords
        )

        if is_rate_limit_like_error:
            print(
                f"\nYahoo request issue detected for {ticker}: {lookup_error}"
            )
            print(
                f"Sleeping for {int(cooldown_seconds)} seconds, "
                f"then retrying the same ticker..."
            )
            time.sleep(cooldown_seconds)
            attempt = 1
            continue

        print(
            f"Retry {attempt}/{max_retries} for {ticker}: {lookup_error}"
        )

        if attempt < max_retries:
            time.sleep(retry_sleep_seconds)

        attempt += 1

    return None, None, lookup_error


def filter_us_universe(
    limit: Optional[int] = None,
    min_price: float = 2.00,
    min_market_cap: float = 300_000_000,
    sleep_seconds: float = 0.10,
    all_candidates_csv_path: str = "results/us_universe_all_candidates.csv",
    filter_csv_path: str = "results/us_universe_filter_results.csv",
    eligible_csv_path: str = "results/us_universe_eligible_tickers.csv",
) -> pd.DataFrame:
    candidates = fetch_all_us_stock_candidates(limit=limit)
    candidates.to_csv(all_candidates_csv_path, index=False)

    rows = []

    print(f"Filtering {len(candidates)} candidates...")

    for position, (_, row) in enumerate(candidates.iterrows(), start=1):
        ticker = row["ticker"]

        print(f"[{position}/{len(candidates)}] Checking {ticker}...")

        price, market_cap, lookup_error = get_yahoo_price_and_market_cap(
            ticker=ticker,
            max_retries=3,
            retry_sleep_seconds=10.0,
            cooldown_seconds=3600.0,
        )

        eligible = (
            price is not None
            and market_cap is not None
            and price >= min_price
            and market_cap >= min_market_cap
        )

        rows.append(
            {
                "ticker": ticker,
                "security_name": row["security_name"],
                "exchange": row["exchange"],
                "price": price,
                "market_cap": market_cap,
                "eligible": eligible,
                "lookup_error": lookup_error,
            }
        )

        pd.DataFrame(rows).to_csv(filter_csv_path, index=False)

        if eligible:
            print(f"ELIGIBLE {ticker}: price={price}, market_cap={market_cap}")
        else:
            print(
                f"SKIP {ticker}: price={price}, market_cap={market_cap}, "
                f"lookup_error={lookup_error}"
            )

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    filter_df = pd.DataFrame(rows)
    filter_df.to_csv(filter_csv_path, index=False)

    eligible_df = filter_df[filter_df["eligible"]].copy()
    eligible_df = eligible_df.set_index("market_cap")
    eligible_df = eligible_df.sort_index(ascending=False)
    eligible_df = eligible_df.reset_index()

    eligible_df.to_csv(eligible_csv_path, index=False)

    print("\n--- Filter Complete ---")
    print(f"All candidates: {len(candidates)}")
    print(f"Eligible: {len(eligible_df)}")
    print(f"Saved all candidates to: {all_candidates_csv_path}")
    print(f"Saved filter results to: {filter_csv_path}")
    print(f"Saved eligible tickers to: {eligible_csv_path}")

    return eligible_df


if __name__ == "__main__":
    filter_us_universe(
        limit=None,
        min_price=2.00,
        min_market_cap=300_000_000,
        sleep_seconds=0.05,
    )