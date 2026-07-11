# scripts/run_backtest_v1.py

from datetime import date

import pandas as pd

from scripts.sp.ingest_sp500 import fetch_sp500_tickers

from src.analytics.research_models.backtesting import (
    compare_portfolio_methods_backtest,
    compare_rebalanced_portfolio_methods_backtest,
    select_portfolio_candidates,
)


START_DATE = date(2023, 1, 1)
END_DATE = date(2026, 3, 31)
SIGNAL_AS_OF_DATE = date(2023, 1, 1)

RISK_FREE_RATE = 0.04

METHODS = [
    "equal_weight",
    "top_n_equal_weight",
    "score_weighted",
    "risk_adjusted_score_weighted",
    "minimum_variance",
    "maximum_sharpe",
    "mean_variance",
    "risk_parity",
    "hierarchical_risk_parity",
]


def print_summary(title: str, summary: list[dict]) -> None:
    print(f"\n--- {title} ---")

    if not summary:
        print("No summary results.")
        return

    df = pd.DataFrame(summary)

    columns = [
        "method_name",
        "strategy_type",
        "total_return",
        "annualized_return",
        "annualized_volatility",
        "sharpe_ratio",
        "max_drawdown",
        "win_rate",
        "number_of_days",
        "error",
    ]

    existing_columns = [column for column in columns if column in df.columns]
    print(df.loc[:, existing_columns].to_string(index=False))


def run_rebalanced_backtest(universe_tickers: list[str]) -> dict:
    return compare_rebalanced_portfolio_methods_backtest(
        universe_tickers=universe_tickers,
        methods=METHODS,
        start_date=START_DATE,
        end_date=END_DATE,
        rebalance_months=3,
        initial_value=1.0,
        risk_free_rate=RISK_FREE_RATE,
        top_screen_n=100,
        final_portfolio_n=10,
        two_stage_selection=True,
        minimum_return_rows=252,
        covariance_method="sample",
        ewma_span=60,
        max_weight=0.40,
        long_only=True,
        risk_aversion=1.0,
    )


def run_static_backtest(universe_tickers: list[str]) -> dict:
    selected_tickers = select_portfolio_candidates(
        universe_tickers=universe_tickers,
        as_of_date=SIGNAL_AS_OF_DATE,
        top_screen_n=100,
        final_portfolio_n=10,
        score_column="overall_score",
        two_stage=True,
        minimum_return_rows=252,
        period_mode="annual",
    )

    result = compare_portfolio_methods_backtest(
        tickers=selected_tickers,
        methods=METHODS,
        start_date=START_DATE,
        end_date=END_DATE,
        as_of_date=SIGNAL_AS_OF_DATE,
        period_mode="annual",
        initial_value=1.0,
        risk_free_rate=RISK_FREE_RATE,
        covariance_method="sample",
        ewma_span=60,
        max_weight=0.40,
        long_only=True,
        risk_aversion=1.0,
    )

    result["selected_tickers"] = selected_tickers
    return result


def run_full_comparison() -> dict:
    universe_tickers = fetch_sp500_tickers(limit=None)

    rebalanced_result = run_rebalanced_backtest(universe_tickers)
    static_result = run_static_backtest(universe_tickers)

    rebalanced_summary = rebalanced_result["summary"]
    static_summary = static_result["summary"]

    for row in rebalanced_summary:
        row["strategy_type"] = "quarterly_rebalanced"

    for row in static_summary:
        row["strategy_type"] = "static_2023_signal"

    combined_summary = rebalanced_summary + static_summary

    print_summary("Quarterly Rebalanced Backtest", rebalanced_summary)
    print_summary("Static 2023 Signal Backtest", static_summary)
    print_summary("Combined Comparison", combined_summary)

    return {
        "rebalanced": rebalanced_result,
        "static": static_result,
        "combined_summary": combined_summary,
    }


if __name__ == "__main__":
    run_full_comparison()