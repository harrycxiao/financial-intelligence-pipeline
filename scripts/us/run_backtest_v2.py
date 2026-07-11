# scripts/run_backtest_v2.py

import pickle
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from scripts.us.store_us_universe import fetch_us_universe_tickers

from src.analytics.research_models.backtesting import (
    compare_rebalanced_portfolio_methods_backtest,
)


RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

START_DATE = date(2024, 4, 1)
END_DATE = date(2026, 3, 31)

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


RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")


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


def flatten_rebalance_history(result: dict) -> pd.DataFrame:
    """Convert nested rebalance histories into one row per method/period."""

    rows = []

    for method_name, method_result in result["results"].items():
        history = method_result.get("rebalance_history", [])

        for period in history:
            rows.append(
                {
                    "method_name": method_name,
                    "as_of_date": period.get("as_of_date"),
                    "start_date": period.get("start_date"),
                    "end_date": period.get("end_date"),
                    "selected_tickers": ",".join(period.get("selected_tickers", [])),
                    "number_selected": len(period.get("selected_tickers", [])),
                    "number_weighted": len(period.get("weights", {})),
                    "period_return": period.get("period_return"),
                    "ending_value": period.get("ending_value"),
                    "error": period.get("error"),
                }
            )

    return pd.DataFrame(rows)


def flatten_rebalance_weights(result: dict) -> pd.DataFrame:
    """Convert nested rebalance weights into one row per method/period/ticker."""

    rows = []

    for method_name, method_result in result["results"].items():
        history = method_result.get("rebalance_history", [])

        for period in history:
            weights = period.get("weights", {})

            for ticker, weight in weights.items():
                rows.append(
                    {
                        "method_name": method_name,
                        "as_of_date": period.get("as_of_date"),
                        "start_date": period.get("start_date"),
                        "end_date": period.get("end_date"),
                        "ticker": ticker,
                        "weight": weight,
                        "period_return": period.get("period_return"),
                        "ending_value": period.get("ending_value"),
                    }
                )

    return pd.DataFrame(rows)


def save_results(result: dict) -> None:
    """Save full results, summary, rebalance history, and weights."""

    summary_df = pd.DataFrame(result["summary"])
    history_df = flatten_rebalance_history(result)
    weights_df = flatten_rebalance_weights(result)

    pkl_path = RESULTS_DIR / f"backtest_v2_full_results_{RUN_ID}.pkl"
    summary_csv_path = RESULTS_DIR / f"backtest_v2_summary_{RUN_ID}.csv"
    history_csv_path = RESULTS_DIR / f"backtest_v2_rebalance_history_{RUN_ID}.csv"
    weights_csv_path = RESULTS_DIR / f"backtest_v2_rebalance_weights_{RUN_ID}.csv"
    xlsx_path = RESULTS_DIR / f"backtest_v2_results_{RUN_ID}.xlsx"

    with open(pkl_path, "wb") as file:
        pickle.dump(result, file)

    summary_df.to_csv(summary_csv_path, index=False)
    history_df.to_csv(history_csv_path, index=False)
    weights_df.to_csv(weights_csv_path, index=False)

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="summary", index=False)
        history_df.to_excel(writer, sheet_name="rebalance_history", index=False)
        weights_df.to_excel(writer, sheet_name="rebalance_weights", index=False)

    print("\n--- Saved Results ---")
    print(f"Full pickle: {pkl_path}")
    print(f"Summary CSV: {summary_csv_path}")
    print(f"History CSV: {history_csv_path}")
    print(f"Weights CSV: {weights_csv_path}")
    print(f"Excel: {xlsx_path}")


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
        final_portfolio_n=5,
        two_stage_selection=True,
        minimum_return_rows=252,
        top_n=5,
        covariance_method="sample",
        ewma_span=60,
        max_weight=0.40,
        long_only=True,
        risk_aversion=1.0,
    )


def run_full_comparison() -> dict:
    universe_tickers = fetch_us_universe_tickers(limit=None)

    print(f"Running v2 backtest on {len(universe_tickers)} universe tickers.")
    print(f"Period: {START_DATE} to {END_DATE}")

    rebalanced_result = run_rebalanced_backtest(universe_tickers)

    for row in rebalanced_result["summary"]:
        row["strategy_type"] = "quarterly_rebalanced"

    print_summary("Quarterly Rebalanced Backtest", rebalanced_result["summary"])

    save_results(rebalanced_result)

    return {
        "rebalanced": rebalanced_result,
    }


if __name__ == "__main__":
    run_full_comparison()