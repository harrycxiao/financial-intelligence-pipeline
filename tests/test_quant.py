#tests/test_quant.py

from src.analytics.derived_metrics import (
    calculate_fundamental_metrics,
    calculate_fundamental_summary,
    calculate_latest_technical_snapshot,
    calculate_market_summary,
)

from src.analytics.research_models.factor_models import (
    build_factor_dataset,
    calculate_factor_scores,
    get_company_factor_profile,
    rank_companies,
)


TEST_TICKER = "AAPL"
FACTOR_TICKERS = ["AAPL", "MSFT", "NVDA", "JPM", "XOM"]


def test_fundamental_metrics() -> None:
    print("\n--- Fundamental Metrics ---")
    metrics = calculate_fundamental_metrics(TEST_TICKER)
    latest = metrics[0] if metrics else None
    print(latest)


def test_fundamental_summary() -> None:
    print("\n--- Fundamental Summary ---")
    print(calculate_fundamental_summary(TEST_TICKER))


def test_market_summary() -> None:
    print("\n--- Market Summary ---")
    print(calculate_market_summary(TEST_TICKER))


def test_technical_snapshot() -> None:
    print("\n--- Technical Snapshot ---")
    print(calculate_latest_technical_snapshot(TEST_TICKER))


def test_factor_dataset() -> None:
    print("\n--- Raw Factor Dataset ---")
    df = build_factor_dataset(FACTOR_TICKERS)

    print(
        df[
            [
                "ticker",
                "earnings_yield",
                "free_cash_flow_yield",
                "ev_to_sales",
                "ev_to_ebitda",
                "revenue_growth",
                "return_on_invested_capital",
                "one_year_return",
                "sharpe_ratio",
                "volume_ratio",
            ]
        ]
    )


def test_factor_scores() -> None:
    print("\n--- Factor Scores ---")
    df = calculate_factor_scores(FACTOR_TICKERS)

    print(
        df[
            [
                "ticker",
                "value_score",
                "growth_score",
                "quality_score",
                "financial_strength_score",
                "efficiency_score",
                "momentum_score",
                "risk_score",
                "technical_score",
                "overall_score",
            ]
        ]
    )


def test_rank_companies() -> None:
    print("\n--- Ranked Companies ---")
    rankings = rank_companies(FACTOR_TICKERS)

    for row in rankings:
        print(
            row["ticker"],
            "overall:",
            row["overall_score"],
            "value:",
            row["value_score"],
            "quality:",
            row["quality_score"],
            "momentum:",
            row["momentum_score"],
        )


def test_company_factor_profile() -> None:
    print("\n--- Company Factor Profile ---")
    profile = get_company_factor_profile(
        ticker=TEST_TICKER,
        peer_tickers=FACTOR_TICKERS,
    )

    keys_to_print = [
        "ticker",
        "overall_score",
        "value_score",
        "growth_score",
        "quality_score",
        "financial_strength_score",
        "efficiency_score",
        "momentum_score",
        "risk_score",
        "technical_score",
    ]

    for key in keys_to_print:
        print(key, ":", profile.get(key))


if __name__ == "__main__":
    #test_fundamental_metrics()
    #test_fundamental_summary()
    #test_technical_snapshot()

    #test_factor_dataset()
    #test_factor_scores()
    test_rank_companies()
    #test_company_factor_profile()