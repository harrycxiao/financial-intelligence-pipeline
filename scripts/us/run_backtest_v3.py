# scripts/us/run_backtest_v3.py

import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from src.analytics.research_models.backtesting import (
    build_portfolio_weights,
    calculate_backtest_metrics,
    calculate_equity_curve,
    calculate_portfolio_return_series,
    filter_returns_by_date,
)
from src.analytics.research_models.portfolio_models import get_returns_matrix


RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

SOURCE_PICKLE_PATH = Path("results/us3/backtest_v2_full_results_20260701_185016.pkl")

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

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

TOP_N_TO_TEST = 10

RISK_FREE_RATE = 0.04


def load_source_result(path: Path) -> dict:
    with open(path, "rb") as file:
        return pickle.load(file)


def get_cached_rebalance_periods(
    source_result: dict,
    reference_method: str = "equal_weight",
    final_portfolio_n: Optional[int] = None,
) -> list[dict]:
    history = source_result["results"][reference_method]["rebalance_history"]

    periods = []

    for period in history:
        selected_tickers = period.get("selected_tickers", [])

        if final_portfolio_n is not None:
            selected_tickers = selected_tickers[:final_portfolio_n]

        periods.append(
            {
                "as_of_date": period["as_of_date"],
                "start_date": period["start_date"],
                "end_date": period["end_date"],
                "selected_tickers": selected_tickers,
            }
        )

    return periods


def run_cached_rebalanced_backtest_for_method(
    method_name: str,
    periods: list[dict],
    initial_value: float = 1.0,
    risk_free_rate: float = 0.04,
    trading_days: int = 252,
    top_n: int = 10,
    covariance_method: str = "sample",
    ewma_span: int = 60,
    max_weight: Optional[float] = 1.0,
    long_only: bool = True,
    risk_aversion: float = 1.0,
) -> dict:
    current_value = initial_value
    all_period_returns = []
    rebalance_history = []

    for period in periods:
        as_of_date = period["as_of_date"]
        period_start = period["start_date"]
        period_end = period["end_date"]
        selected_tickers = period["selected_tickers"]

        try:
            weights = build_portfolio_weights(
                method_name=method_name,
                tickers=selected_tickers,
                as_of_date=as_of_date,
                period_mode="quarterly",
                top_n=top_n,
                covariance_method=covariance_method,
                ewma_span=ewma_span,
                max_weight=max_weight,
                long_only=long_only,
                risk_aversion=risk_aversion,
            )

            returns = get_returns_matrix(list(weights.keys()))
            returns = filter_returns_by_date(
                returns=returns,
                start_date=period_start,
                end_date=period_end,
            )

            portfolio_returns = calculate_portfolio_return_series(
                weights=weights,
                returns=returns,
            )

            if portfolio_returns.empty:
                period_return = None
            else:
                period_equity = calculate_equity_curve(
                    portfolio_returns=portfolio_returns,
                    initial_value=current_value,
                )

                period_return = (float(period_equity.iloc[-1]) / current_value) - 1
                current_value = float(period_equity.iloc[-1])
                all_period_returns.append(portfolio_returns)

            rebalance_history.append(
                {
                    "method_name": method_name,
                    "as_of_date": as_of_date,
                    "start_date": period_start,
                    "end_date": period_end,
                    "selected_tickers": selected_tickers,
                    "weights": weights,
                    "period_return": period_return,
                    "ending_value": current_value,
                    "error": None,
                }
            )

        except Exception as error:
            rebalance_history.append(
                {
                    "method_name": method_name,
                    "as_of_date": as_of_date,
                    "start_date": period_start,
                    "end_date": period_end,
                    "selected_tickers": selected_tickers,
                    "weights": {},
                    "period_return": None,
                    "ending_value": current_value,
                    "error": str(error),
                }
            )

    if all_period_returns:
        combined_returns = pd.concat(all_period_returns).sort_index()
    else:
        combined_returns = pd.Series(dtype=float)

    metrics = calculate_backtest_metrics(
        portfolio_returns=combined_returns,
        risk_free_rate=risk_free_rate,
        trading_days=trading_days,
    )

    return {
        "method_name": method_name,
        "metrics": metrics,
        "final_value": current_value,
        "daily_returns": combined_returns.reset_index().to_dict(orient="records"),
        "rebalance_history": rebalance_history,
        "error": None,
    }


def build_summary(results: dict) -> list[dict]:
    rows = []

    for method_name, result in results.items():
        metrics = result.get("metrics", {})

        rows.append(
            {
                "method_name": method_name,
                "strategy_type": f"cached_top_{TOP_N_TO_TEST}",
                "total_return": metrics.get("total_return"),
                "annualized_return": metrics.get("annualized_return"),
                "annualized_volatility": metrics.get("annualized_volatility"),
                "sharpe_ratio": metrics.get("sharpe_ratio"),
                "max_drawdown": metrics.get("max_drawdown"),
                "win_rate": metrics.get("win_rate"),
                "number_of_days": metrics.get("number_of_days"),
                "final_value": result.get("final_value"),
                "error": result.get("error"),
            }
        )

    return sorted(
        rows,
        key=lambda row: row["sharpe_ratio"] if row["sharpe_ratio"] is not None else -999,
        reverse=True,
    )


def flatten_rebalance_history(results: dict) -> pd.DataFrame:
    rows = []

    for method_name, result in results.items():
        for period in result.get("rebalance_history", []):
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


def flatten_rebalance_weights(results: dict) -> pd.DataFrame:
    rows = []

    for method_name, result in results.items():
        for period in result.get("rebalance_history", []):
            for ticker, weight in period.get("weights", {}).items():
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


def save_cached_results(output: dict) -> None:
    summary_df = pd.DataFrame(output["summary"])
    history_df = flatten_rebalance_history(output["results"])
    weights_df = flatten_rebalance_weights(output["results"])

    pkl_path = RESULTS_DIR / f"backtest_v3_cached_top_{TOP_N_TO_TEST}_{RUN_ID}.pkl"
    summary_path = RESULTS_DIR / f"backtest_v3_cached_top_{TOP_N_TO_TEST}_summary_{RUN_ID}.csv"
    history_path = RESULTS_DIR / f"backtest_v3_cached_top_{TOP_N_TO_TEST}_history_{RUN_ID}.csv"
    weights_path = RESULTS_DIR / f"backtest_v3_cached_top_{TOP_N_TO_TEST}_weights_{RUN_ID}.csv"
    xlsx_path = RESULTS_DIR / f"backtest_v3_cached_top_{TOP_N_TO_TEST}_{RUN_ID}.xlsx"

    with open(pkl_path, "wb") as file:
        pickle.dump(output, file)

    summary_df.to_csv(summary_path, index=False)
    history_df.to_csv(history_path, index=False)
    weights_df.to_csv(weights_path, index=False)

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="summary", index=False)
        history_df.to_excel(writer, sheet_name="rebalance_history", index=False)
        weights_df.to_excel(writer, sheet_name="rebalance_weights", index=False)

    print("\n--- Saved Results ---")
    print(pkl_path)
    print(summary_path)
    print(history_path)
    print(weights_path)
    print(xlsx_path)


def print_summary(summary: list[dict]) -> None:
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
        "final_value",
        "error",
    ]

    print("\n--- Cached Rebalanced Backtest Summary ---")
    print(df.loc[:, columns].to_string(index=False))


def run_cached_backtest() -> dict:
    source_result = load_source_result(SOURCE_PICKLE_PATH)

    periods = get_cached_rebalance_periods(
        source_result=source_result,
        reference_method="equal_weight",
        final_portfolio_n=TOP_N_TO_TEST,
    )

    results = {}

    for method_name in METHODS:
        print(f"Running cached method: {method_name}")

        results[method_name] = run_cached_rebalanced_backtest_for_method(
            method_name=method_name,
            periods=periods,
            initial_value=1.0,
            risk_free_rate=RISK_FREE_RATE,
            top_n=TOP_N_TO_TEST,
            covariance_method="sample",
            ewma_span=60,
            max_weight=1.0,
            long_only=True,
            risk_aversion=1.0,
        )

    summary = build_summary(results)

    output = {
        "source_pickle_path": str(SOURCE_PICKLE_PATH),
        "top_n_tested": TOP_N_TO_TEST,
        "results": results,
        "summary": summary,
    }

    print_summary(summary)
    save_cached_results(output)

    return output


if __name__ == "__main__":
    run_cached_backtest()