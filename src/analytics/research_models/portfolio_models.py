# src/analytics/research_models/portfolio_models.py

from typing import Optional
from datetime import date

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, to_tree
from scipy.spatial.distance import squareform

from src.analytics.derived_metrics.market_analysis import calculate_returns_dataframe
from src.analytics.research_models.factor_models import calculate_factor_scores


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------


def validate_risk_aversion(risk_aversion: float) -> None:
    """Require risk_aversion >= 1 so exposure never exceeds full capital."""

    if risk_aversion < 1:
        raise ValueError("risk_aversion must be at least 1.")


def normalize_weights(raw_weights: pd.Series) -> dict:
    """Convert raw positive weights into normalized portfolio weights."""

    raw_weights = raw_weights.fillna(0)
    raw_weights = raw_weights.where(raw_weights >= 0, 0)

    total = raw_weights.sum()

    if total == 0:
        return {}

    weights = raw_weights / total

    return weights.to_dict()


def get_returns_matrix(tickers: list, as_of_date: Optional[date] = None,) -> pd.DataFrame:
    """Create aligned daily returns matrix for multiple tickers."""

    returns_data = []

    for ticker in tickers:
        ticker = ticker.upper().strip()
        df = calculate_returns_dataframe(ticker, as_of_date=as_of_date)

        if df.empty:
            continue

        df = df.loc[:, ["date", "daily_return"]].copy()
        df.columns = ["date", ticker]

        returns_data.append(df)

    if not returns_data:
        return pd.DataFrame()

    merged = returns_data[0]

    for df in returns_data[1:]:
        merged = merged.merge(df, on="date", how="inner")

    merged = merged.dropna().sort_values("date").reset_index(drop=True)

    return merged.set_index("date")


def calculate_ewma_covariance_matrix(
    returns: pd.DataFrame,
    ewma_span: int = 60,
    trading_days: int = 252,
) -> pd.DataFrame:
    """Calculate exponentially weighted annualized covariance matrix."""

    if returns.empty:
        return pd.DataFrame()

    returns_array = returns.to_numpy(dtype=float)
    n_observations = len(returns_array)

    if n_observations < 2:
        return pd.DataFrame()

    decay_weights = np.exp(
        np.linspace(
            -1.0,
            0.0,
            n_observations,
        )
    )

    if ewma_span > 1:
        decay_weights = np.exp(
            np.linspace(
                -n_observations / ewma_span,
                0.0,
                n_observations,
            )
        )

    decay_weights = decay_weights / decay_weights.sum()

    weighted_mean = np.sum(
        returns_array * decay_weights.reshape(-1, 1),
        axis=0,
    )

    demeaned_returns = returns_array - weighted_mean

    covariance_array = (
        demeaned_returns.T
        @ (demeaned_returns * decay_weights.reshape(-1, 1))
    ) * trading_days

    return pd.DataFrame(
        covariance_array,
        index=returns.columns,
        columns=returns.columns,
    )


def get_covariance_matrix(
    tickers: list,
    covariance_method: str = "sample",
    ewma_span: int = 60,
    trading_days: int = 252,
    as_of_date: Optional[date] = None,
) -> pd.DataFrame:
    """
    Calculate annualized covariance matrix.

    Supported methods:
    sample, ewma, ledoit_wolf, oas
    """

    returns = get_returns_matrix(tickers, as_of_date=as_of_date)

    if returns.empty:
        return pd.DataFrame()

    returns_array = returns.to_numpy(dtype=float)

    if len(returns_array) < 2:
        return pd.DataFrame()

    method = covariance_method.lower().strip()

    if method == "sample":
        covariance_array = np.cov(returns_array, rowvar=False) * trading_days

    elif method == "ewma":
        return calculate_ewma_covariance_matrix(
            returns=returns,
            ewma_span=ewma_span,
            trading_days=trading_days,
        )

    elif method == "ledoit_wolf":
        from sklearn.covariance import LedoitWolf

        model = LedoitWolf()
        model.fit(returns_array)
        covariance_array = model.covariance_ * trading_days

    elif method == "oas":
        from sklearn.covariance import OAS

        model = OAS()
        model.fit(returns_array)
        covariance_array = model.covariance_ * trading_days

    else:
        raise ValueError(
            "covariance_method must be one of: sample, ewma, ledoit_wolf, oas."
        )

    return pd.DataFrame(
        covariance_array,
        index=returns.columns,
        columns=returns.columns,
    )


def get_annualized_covariance_matrix(tickers: list, as_of_date: Optional[date] = None) -> pd.DataFrame:
    """Backward-compatible wrapper for sample covariance."""

    return get_covariance_matrix(
        tickers=tickers,
        covariance_method="sample",
        as_of_date=as_of_date,
    )


def apply_max_weight_cap(
    weights: pd.Series,
    max_weight: Optional[float],
) -> pd.Series:
    """Apply a true long-only max-weight cap and redistribute excess weight."""

    if max_weight is None:
        return weights

    if max_weight <= 0:
        raise ValueError("max_weight must be positive.")

    weights = weights.fillna(0)
    weights = weights.where(weights >= 0, 0)

    if weights.sum() == 0:
        return weights

    weights = weights / weights.sum()

    if max_weight * len(weights) < 1:
        raise ValueError(
            "max_weight is too small for the number of assets. "
            "For N assets, max_weight must be at least 1 / N."
        )

    capped = pd.Series(0.0, index=weights.index)
    remaining = weights.copy()
    remaining_weight = 1.0

    while True:
        if remaining.empty:
            break

        normalized_remaining = remaining / remaining.sum()
        proposed = normalized_remaining * remaining_weight

        over_cap = proposed > max_weight

        if not over_cap.any():
            capped.loc[remaining.index] = proposed
            break

        capped_assets = proposed[over_cap].index
        capped.loc[capped_assets] = max_weight

        remaining_weight -= max_weight * len(capped_assets)
        remaining = remaining.drop(index=capped_assets)

    return capped


def apply_gross_max_weight_cap(
    weights: pd.Series,
    max_abs_weight: Optional[float],
    target_gross_exposure: float = 1.0,
) -> pd.Series:
    """Apply max absolute cap for gross-normalized long-short weights."""

    weights = weights.fillna(0)
    gross_exposure = weights.abs().sum()

    if gross_exposure == 0:
        return weights

    weights = weights / gross_exposure * target_gross_exposure

    if max_abs_weight is None:
        return weights

    signs = np.sign(weights)
    abs_weights = weights.abs()

    capped_abs = apply_max_weight_cap(
        abs_weights,
        max_abs_weight,
    )

    return capped_abs * signs * target_gross_exposure


def apply_net_max_weight_cap(
    weights: pd.Series,
    max_abs_weight: Optional[float],
    target_net_exposure: float = 1.0,
    max_iterations: int = 100,
    tolerance: float = 1e-10,
) -> pd.Series:
    """Apply max absolute cap for net-normalized long-short weights."""

    weights = weights.fillna(0)

    if weights.sum() == 0:
        raise ValueError(
            "Raw weights sum to zero, so net exposure normalization is not possible."
        )

    if max_abs_weight is not None and max_abs_weight <= 0:
        raise ValueError("max_abs_weight must be positive.")

    weights = weights / weights.sum() * target_net_exposure

    if max_abs_weight is None:
        return weights

    if max_abs_weight * len(weights) < abs(target_net_exposure):
        raise ValueError(
            "max_abs_weight is too small to reach target_net_exposure."
        )

    capped = weights.copy()
    fixed = pd.Series(False, index=weights.index)

    for _ in range(max_iterations):
        over_cap = (capped.abs() > max_abs_weight + tolerance) & (~fixed)

        if not over_cap.any():
            break

        capped.loc[over_cap] = np.sign(capped.loc[over_cap]) * max_abs_weight
        fixed.loc[over_cap] = True

        remaining_target = target_net_exposure - capped.loc[fixed].sum()
        remaining = capped.loc[~fixed]

        if remaining.empty:
            break

        if abs(remaining_target) > max_abs_weight * len(remaining) + tolerance:
            raise ValueError(
                "Remaining target net exposure cannot be reached under max_abs_weight."
            )

        if remaining.sum() == 0:
            equal_remaining = remaining_target / len(remaining)
            capped.loc[~fixed] = equal_remaining
        else:
            capped.loc[~fixed] = remaining / remaining.sum() * remaining_target

    else:
        raise RuntimeError(
            "Maximum iterations exceeded while applying net max weight cap."
        )

    if abs(capped.sum() - target_net_exposure) > tolerance:
        raise ValueError("Final weights do not match target_net_exposure.")

    if (capped.abs() > max_abs_weight + tolerance).any():
        raise ValueError("Final weights violate max_abs_weight.")

    return capped


def finalize_optimized_weights(
    raw_weights: pd.Series,
    long_only: bool = True,
    max_weight: Optional[float] = 0.40,
    max_abs_weight: Optional[float] = 0.40,
    exposure_mode: str = "gross",
    target_gross_exposure: float = 1.0,
    target_net_exposure: float = 1.0,
) -> dict:
    """Apply long-only or long-short normalization/caps to raw optimizer weights."""

    raw_weights = raw_weights.fillna(0)

    if long_only:
        weights = raw_weights.where(raw_weights >= 0, 0)

        if weights.sum() == 0:
            return equal_weight_portfolio(list(raw_weights.index))

        weights = weights / weights.sum()
        weights = apply_max_weight_cap(weights, max_weight)

        return weights.to_dict()

    if exposure_mode == "gross":
        weights = apply_gross_max_weight_cap(
            raw_weights,
            max_abs_weight=max_abs_weight,
            target_gross_exposure=target_gross_exposure,
        )

        return weights.to_dict()

    if exposure_mode == "net":
        weights = apply_net_max_weight_cap(
            raw_weights,
            max_abs_weight=max_abs_weight,
            target_net_exposure=target_net_exposure,
        )

        return weights.to_dict()

    raise ValueError("exposure_mode must be either 'gross' or 'net'.")


def get_expected_return_signal(
    tickers: list,
    score_column: str = "overall_score",
    as_of_date: Optional[date] = None,
) -> pd.Series:
    """
    Return the current expected-return signal.

    Phase 1: this uses factor scores as an attractiveness signal.
    Future: replace this function with true expected return predictions.
    """

    scores = calculate_factor_scores(tickers, as_of_date=as_of_date)

    if scores.empty or score_column not in scores.columns:
        return pd.Series(dtype=float)

    return pd.Series(
        scores[score_column].values,
        index=scores["ticker"],
    )


def calculate_inverse_variance_weights(covariance_matrix: pd.DataFrame) -> pd.Series:
    """Calculate inverse-variance weights for a covariance submatrix."""

    diagonal = np.diag(covariance_matrix.to_numpy(dtype=float))
    inverse_variance = 1 / diagonal
    inverse_variance = np.where(np.isfinite(inverse_variance), inverse_variance, 0)

    weights = pd.Series(
        inverse_variance,
        index=covariance_matrix.index,
    )

    if weights.sum() == 0:
        return pd.Series(1 / len(weights), index=weights.index)

    return weights / weights.sum()


def calculate_cluster_variance(
    covariance_matrix: pd.DataFrame,
    cluster_tickers: list,
) -> float:
    """Calculate variance of an inverse-variance portfolio inside one cluster."""

    cluster_covariance = covariance_matrix.loc[cluster_tickers, cluster_tickers]
    cluster_weights = calculate_inverse_variance_weights(cluster_covariance)

    weight_array = cluster_weights.to_numpy(dtype=float)
    covariance_array = cluster_covariance.to_numpy(dtype=float)

    variance = weight_array.T @ covariance_array @ weight_array

    return float(variance)


def calculate_cluster_signal(
    expected_return_signal: Optional[pd.Series],
    cluster_tickers: list,
) -> Optional[float]:
    """Calculate average expected-return signal for one cluster."""

    if expected_return_signal is None:
        return None

    available_tickers = [
        ticker
        for ticker in cluster_tickers
        if ticker in expected_return_signal.index
    ]

    if not available_tickers:
        return None

    cluster_signal = expected_return_signal.loc[available_tickers].dropna()

    if cluster_signal.empty:
        return None

    return float(cluster_signal.mean())


def calculate_cluster_attractiveness(
    covariance_matrix: pd.DataFrame,
    cluster_tickers: list,
    expected_return_signal: Optional[pd.Series],
    return_risk_metric: str = "volatility",
) -> Optional[float]:
    """Calculate return-adjusted attractiveness for one HRP cluster."""

    cluster_signal = calculate_cluster_signal(
        expected_return_signal=expected_return_signal,
        cluster_tickers=cluster_tickers,
    )

    if cluster_signal is None:
        return None

    cluster_variance = calculate_cluster_variance(
        covariance_matrix=covariance_matrix,
        cluster_tickers=cluster_tickers,
    )

    if cluster_variance <= 0:
        return max(cluster_signal, 0)

    if return_risk_metric == "variance":
        risk_measure = cluster_variance
    elif return_risk_metric == "volatility":
        risk_measure = np.sqrt(cluster_variance)
    else:
        raise ValueError("return_risk_metric must be either 'variance' or 'volatility'.")

    if risk_measure == 0:
        return max(cluster_signal, 0)

    return max(cluster_signal, 0) / risk_measure


def get_correlation_distance(covariance_matrix: pd.DataFrame) -> pd.DataFrame:
    """Convert a covariance matrix into a correlation-distance matrix."""

    covariance_array = covariance_matrix.to_numpy(dtype=float)
    standard_deviations = np.sqrt(np.diag(covariance_array))
    denominator = np.outer(standard_deviations, standard_deviations)

    correlation_array = np.divide(
        covariance_array,
        denominator,
        out=np.zeros_like(covariance_array),
        where=denominator != 0,
    )

    correlation_array = np.clip(correlation_array, -1, 1)
    distance_array = np.sqrt((1 - correlation_array) / 2)

    return pd.DataFrame(
        distance_array,
        index=covariance_matrix.index,
        columns=covariance_matrix.columns,
    )


def get_tickers_from_cluster_node(node, ordered_tickers: list) -> list:
    """Return all tickers contained inside a scipy cluster tree node."""

    if node.is_leaf():
        return [ordered_tickers[node.id]]

    left_tickers = get_tickers_from_cluster_node(node.left, ordered_tickers)
    right_tickers = get_tickers_from_cluster_node(node.right, ordered_tickers)

    return left_tickers + right_tickers


def allocate_hrp_node(
    node,
    covariance_matrix: pd.DataFrame,
    weights: pd.Series,
    ordered_tickers: list,
    expected_return_signal: Optional[pd.Series] = None,
    use_expected_return_signal: bool = False,
    return_risk_metric: str = "volatility",
) -> None:
    """Recursively allocate HRP weights using true dendrogram tree splits."""

    if node.is_leaf():
        return

    left_tickers = get_tickers_from_cluster_node(node.left, ordered_tickers)
    right_tickers = get_tickers_from_cluster_node(node.right, ordered_tickers)

    left_variance = calculate_cluster_variance(
        covariance_matrix,
        left_tickers,
    )
    right_variance = calculate_cluster_variance(
        covariance_matrix,
        right_tickers,
    )

    allocation_to_left = None

    if use_expected_return_signal:
        left_attractiveness = calculate_cluster_attractiveness(
            covariance_matrix=covariance_matrix,
            cluster_tickers=left_tickers,
            expected_return_signal=expected_return_signal,
            return_risk_metric=return_risk_metric,
        )

        right_attractiveness = calculate_cluster_attractiveness(
            covariance_matrix=covariance_matrix,
            cluster_tickers=right_tickers,
            expected_return_signal=expected_return_signal,
            return_risk_metric=return_risk_metric,
        )

        if (
            left_attractiveness is not None
            and right_attractiveness is not None
            and left_attractiveness > 0
            and right_attractiveness > 0
        ):
            allocation_to_left = (
                left_attractiveness
                / (left_attractiveness + right_attractiveness)
            )

    if allocation_to_left is None:
        if left_variance + right_variance == 0:
            allocation_to_left = 0.5
        else:
            allocation_to_left = 1 - (
                left_variance / (left_variance + right_variance)
            )

    weights.loc[left_tickers] *= allocation_to_left
    weights.loc[right_tickers] *= 1 - allocation_to_left

    allocate_hrp_node(
        node.left,
        covariance_matrix,
        weights,
        ordered_tickers,
        expected_return_signal,
        use_expected_return_signal,
        return_risk_metric,
    )

    allocate_hrp_node(
        node.right,
        covariance_matrix,
        weights,
        ordered_tickers,
        expected_return_signal,
        use_expected_return_signal,
        return_risk_metric,
    )


# ---------------------------------------------------------------------
# Portfolio construction models
# ---------------------------------------------------------------------


def equal_weight_portfolio(tickers: list) -> dict:
    """Allocate equal weight to each ticker."""

    clean_tickers = [ticker.upper().strip() for ticker in tickers]

    if not clean_tickers:
        return {}

    weight = 1 / len(clean_tickers)

    return {ticker: weight for ticker in clean_tickers}


def top_n_equal_weight_portfolio(
    tickers: list,
    n: int = 5,
    score_column: str = "overall_score",
    as_of_date: Optional[date] = None,
) -> dict:
    """Select top N stocks by factor score and equal-weight them."""

    scores = calculate_factor_scores(tickers, as_of_date=as_of_date)

    if scores.empty or score_column not in scores.columns:
        return {}

    top = scores.sort_values(score_column, ascending=False).head(n)
    selected_tickers = top["ticker"].tolist()

    return equal_weight_portfolio(selected_tickers)


def score_weighted_portfolio(
    tickers: list,
    score_column: str = "overall_score",
    top_n: Optional[int] = None,
    as_of_date: Optional[date] = None,
) -> dict:
    """Allocate weights proportional to factor scores."""

    scores = calculate_factor_scores(tickers, as_of_date=as_of_date)

    if scores.empty or score_column not in scores.columns:
        return {}

    scores = scores.sort_values(score_column, ascending=False)

    if top_n is not None:
        scores = scores.head(top_n)

    raw_weights = pd.Series(
        scores[score_column].values,
        index=scores["ticker"],
    )

    return normalize_weights(raw_weights)


def risk_adjusted_score_portfolio(
    tickers: list,
    score_column: str = "overall_score",
    risk_column: str = "annualized_volatility",
    top_n: Optional[int] = None,
    as_of_date: Optional[date] = None,
) -> dict:
    """Allocate using score divided by risk."""

    scores = calculate_factor_scores(tickers, as_of_date=as_of_date)

    if scores.empty or score_column not in scores.columns or risk_column not in scores.columns:
        return {}

    scores = scores.sort_values(score_column, ascending=False)

    if top_n is not None:
        scores = scores.head(top_n)

    risk = scores[risk_column].replace(0, np.nan)
    raw_values = scores[score_column] / risk

    raw_weights = pd.Series(
        raw_values.values,
        index=scores["ticker"],
    )

    return normalize_weights(raw_weights)


def minimum_variance_portfolio(
    tickers: list,
    max_weight: Optional[float] = 0.40,
    long_only: bool = True,
    max_abs_weight: Optional[float] = 0.40,
    exposure_mode: str = "gross",
    target_gross_exposure: float = 1.0,
    target_net_exposure: float = 1.0,
    covariance_method: str = "sample",
    ewma_span: int = 60,
    as_of_date: Optional[date] = None,
) -> dict:
    """Create a minimum variance portfolio."""

    clean_tickers = [ticker.upper().strip() for ticker in tickers]

    covariance_matrix = get_covariance_matrix(
        tickers=clean_tickers,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        as_of_date=as_of_date,
    )

    if covariance_matrix.empty:
        return {}

    common_tickers = list(covariance_matrix.columns)

    try:
        inverse_covariance = np.linalg.pinv(covariance_matrix.values)
    except np.linalg.LinAlgError:
        return {}

    ones = np.ones(len(common_tickers))

    raw_weights = inverse_covariance @ ones
    denominator = ones.T @ inverse_covariance @ ones

    if denominator == 0:
        return equal_weight_portfolio(common_tickers)

    weights = pd.Series(raw_weights / denominator, index=common_tickers)

    return finalize_optimized_weights(
        raw_weights=weights,
        long_only=long_only,
        max_weight=max_weight,
        max_abs_weight=max_abs_weight,
        exposure_mode=exposure_mode,
        target_gross_exposure=target_gross_exposure,
        target_net_exposure=target_net_exposure,
    )


def maximum_sharpe_portfolio(
    tickers: list,
    score_column: str = "overall_score",
    risk_free_signal: float = 0.0,
    max_weight: Optional[float] = 0.40,
    long_only: bool = True,
    max_abs_weight: Optional[float] = 0.40,
    exposure_mode: str = "gross",
    target_gross_exposure: float = 1.0,
    target_net_exposure: float = 1.0,
    covariance_method: str = "sample",
    ewma_span: int = 60,
    as_of_date: Optional[date] = None,
) -> dict:
    """Create a maximum Sharpe-style portfolio."""

    clean_tickers = [ticker.upper().strip() for ticker in tickers]

    covariance_matrix = get_covariance_matrix(
        tickers=clean_tickers,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        as_of_date=as_of_date,
    )

    if covariance_matrix.empty:
        return {}

    expected_return_signal = get_expected_return_signal(
        tickers=clean_tickers,
        score_column=score_column,
        as_of_date=as_of_date
    )

    common_tickers = [
        ticker
        for ticker in covariance_matrix.columns
        if ticker in expected_return_signal.index
    ]

    if not common_tickers:
        return {}

    covariance_matrix = covariance_matrix.loc[common_tickers, common_tickers]
    expected_return_signal = expected_return_signal.loc[common_tickers]

    excess_signal = expected_return_signal - risk_free_signal

    try:
        inverse_covariance = np.linalg.pinv(covariance_matrix.values)
    except np.linalg.LinAlgError:
        return {}

    raw_weights = inverse_covariance @ excess_signal.values
    weights = pd.Series(raw_weights, index=common_tickers)

    return finalize_optimized_weights(
        raw_weights=weights,
        long_only=long_only,
        max_weight=max_weight,
        max_abs_weight=max_abs_weight,
        exposure_mode=exposure_mode,
        target_gross_exposure=target_gross_exposure,
        target_net_exposure=target_net_exposure,
    )


def mean_variance_portfolio(
    tickers: list,
    risk_aversion: float = 3.0,
    score_column: str = "overall_score",
    max_weight: Optional[float] = 0.40,
    long_only: bool = True,
    max_abs_weight: Optional[float] = 0.40,
    exposure_mode: str = "gross",
    target_net_exposure: float = 1.0,
    covariance_method: str = "sample",
    ewma_span: int = 60,
    as_of_date: Optional[date] = None,
) -> dict:
    """Create a mean-variance-style portfolio."""

    validate_risk_aversion(risk_aversion)

    clean_tickers = [ticker.upper().strip() for ticker in tickers]

    covariance_matrix = get_covariance_matrix(
        tickers=clean_tickers,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        as_of_date=as_of_date
    )

    if covariance_matrix.empty:
        return {}

    expected_return_signal = get_expected_return_signal(
        tickers=clean_tickers,
        score_column=score_column,
        as_of_date=as_of_date
    )

    common_tickers = [
        ticker
        for ticker in covariance_matrix.columns
        if ticker in expected_return_signal.index
    ]

    if not common_tickers:
        return {}

    covariance_matrix = covariance_matrix.loc[common_tickers, common_tickers]
    expected_return_signal = expected_return_signal.loc[common_tickers]

    try:
        inverse_covariance = np.linalg.pinv(covariance_matrix.values)
    except np.linalg.LinAlgError:
        return {}

    centered_signal = expected_return_signal - expected_return_signal.mean()

    raw_weights = inverse_covariance @ centered_signal.values
    weights = pd.Series(raw_weights, index=common_tickers)

    target_exposure = 1 / risk_aversion

    return finalize_optimized_weights(
        raw_weights=weights,
        long_only=long_only,
        max_weight=max_weight,
        max_abs_weight=max_abs_weight,
        exposure_mode=exposure_mode,
        target_gross_exposure=target_exposure,
        target_net_exposure=target_net_exposure * target_exposure,
    )


def risk_parity_portfolio(
    tickers: list,
    max_weight: Optional[float] = 0.40,
    max_iterations: int = 1000,
    tolerance: float = 1e-8,
    covariance_method: str = "sample",
    ewma_span: int = 60,
    as_of_date: Optional[date] = None,
) -> dict:
    """Create a long-only risk parity portfolio."""

    clean_tickers = [ticker.upper().strip() for ticker in tickers]

    covariance_matrix = get_covariance_matrix(
        tickers=clean_tickers,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        as_of_date=as_of_date
    )

    if covariance_matrix.empty:
        return {}

    tickers_used = list(covariance_matrix.columns)
    covariance_array = covariance_matrix.to_numpy(dtype=float)

    weights = np.ones(len(tickers_used)) / len(tickers_used)
    target_risk_contribution = np.ones(len(tickers_used)) / len(tickers_used)

    for _ in range(max_iterations):
        portfolio_variance = weights.T @ covariance_array @ weights

        if portfolio_variance <= 0:
            return equal_weight_portfolio(tickers_used)

        marginal_risk = covariance_array @ weights
        risk_contribution = (weights * marginal_risk) / portfolio_variance

        difference = risk_contribution - target_risk_contribution

        if np.max(np.abs(difference)) < tolerance:
            break

        adjustment = target_risk_contribution / np.where(
            risk_contribution == 0,
            tolerance,
            risk_contribution,
        )

        weights = weights * adjustment
        weights = np.where(weights < 0, 0, weights)

        if weights.sum() == 0:
            return equal_weight_portfolio(tickers_used)

        weights = weights / weights.sum()

    weights_series = pd.Series(weights, index=tickers_used)
    weights_series = apply_max_weight_cap(weights_series, max_weight)

    return weights_series.to_dict()


def hierarchical_risk_parity_portfolio(
    tickers: list,
    max_weight: Optional[float] = 0.40,
    linkage_method: str = "single",
    covariance_method: str = "sample",
    ewma_span: int = 60,
    use_expected_return_signal: bool = True,
    score_column: str = "overall_score",
    return_risk_metric: str = "volatility",
    as_of_date: Optional[date] = None,
) -> dict:
    """Create a long-only hierarchical risk parity portfolio."""

    clean_tickers = [ticker.upper().strip() for ticker in tickers]

    covariance_matrix = get_covariance_matrix(
        tickers=clean_tickers,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        as_of_date=as_of_date
    )

    if covariance_matrix.empty:
        return {}

    ordered_tickers = list(covariance_matrix.columns)

    if len(ordered_tickers) == 1:
        return {ordered_tickers[0]: 1.0}

    expected_return_signal = None

    if use_expected_return_signal:
        expected_return_signal = get_expected_return_signal(
            tickers=ordered_tickers,
            score_column=score_column,
            as_of_date=as_of_date
        )

    distance_matrix = get_correlation_distance(covariance_matrix)

    condensed_distance = squareform(
        distance_matrix.to_numpy(dtype=float),
        checks=False,
    )

    linkage_matrix = linkage(condensed_distance, method=linkage_method)
    root_node = to_tree(linkage_matrix)

    weights = pd.Series(1.0, index=ordered_tickers)

    allocate_hrp_node(
        node=root_node,
        covariance_matrix=covariance_matrix,
        weights=weights,
        ordered_tickers=ordered_tickers,
        expected_return_signal=expected_return_signal,
        use_expected_return_signal=use_expected_return_signal,
        return_risk_metric=return_risk_metric,
    )

    weights = weights / weights.sum()
    weights = apply_max_weight_cap(weights, max_weight)

    return weights.to_dict()


# ---------------------------------------------------------------------
# Portfolio summary / comparison functions
# ---------------------------------------------------------------------


def calculate_portfolio_performance(
    weights: dict,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
    as_of_date: Optional[date] = None
) -> dict:
    """Calculate historical annual return, volatility, and excess-return Sharpe."""

    tickers = list(weights.keys())
    returns = get_returns_matrix(tickers, as_of_date=as_of_date)

    if returns.empty:
        return {}

    weight_vector = np.array([weights[ticker] for ticker in returns.columns])
    daily_portfolio_returns = returns.to_numpy(dtype=float) @ weight_vector

    annual_return = float(np.mean(daily_portfolio_returns) * trading_days)
    annual_volatility = float(np.std(daily_portfolio_returns) * np.sqrt(trading_days))

    excess_annual_return = annual_return - risk_free_rate

    sharpe_ratio = (
        excess_annual_return / annual_volatility
        if annual_volatility != 0
        else None
    )

    return {
        "annual_return": annual_return,
        "risk_free_rate": risk_free_rate,
        "excess_annual_return": excess_annual_return,
        "annual_volatility": annual_volatility,
        "sharpe_ratio": sharpe_ratio,
    }


def build_portfolio_summary(
    weights: dict,
    risk_free_rate: float = 0.0,
    as_of_date: Optional[date] = None,
) -> dict:
    """Return weights plus portfolio-level performance metrics."""

    performance = calculate_portfolio_performance(
        weights=weights,
        risk_free_rate=risk_free_rate,
        as_of_date=as_of_date,
    )

    return {
        "weights": weights,
        "performance": performance,
    }


def compare_basic_portfolios(
    tickers: list,
    top_n: int = 5,
    risk_free_rate: float = 0.0,
    score_column: str = "overall_score",
    risk_column: str = "annualized_volatility",
    covariance_method: str = "sample",
    ewma_span: int = 60,
    max_weight: Optional[float] = 0.40,
    long_only: bool = True,
    max_abs_weight: Optional[float] = 0.40,
    exposure_mode: str = "gross",
    target_gross_exposure: float = 1.0,
    target_net_exposure: float = 1.0,
    risk_aversion: float = 3.0,
    risk_free_signal: float = 0.0,
    risk_parity_max_iterations: int = 1000,
    risk_parity_tolerance: float = 1e-8,
    hrp_linkage_method: str = "single",
    hrp_use_expected_return_signal: bool = True,
    hrp_return_risk_metric: str = "volatility",
    as_of_date: Optional[date] = None,
) -> dict:
    """Compare portfolio construction methods with shared configurable parameters."""

    equal_weights = equal_weight_portfolio(tickers)

    top_n_equal_weights = top_n_equal_weight_portfolio(
        tickers=tickers,
        n=top_n,
        score_column=score_column,
        as_of_date=as_of_date,
    )

    score_weights = score_weighted_portfolio(
        tickers=tickers,
        score_column=score_column,
        top_n=top_n,
        as_of_date=as_of_date,
    )

    risk_adjusted_weights = risk_adjusted_score_portfolio(
        tickers=tickers,
        score_column=score_column,
        risk_column=risk_column,
        top_n=top_n,
        as_of_date=as_of_date,
    )

    minimum_variance_weights = minimum_variance_portfolio(
        tickers=tickers,
        max_weight=max_weight,
        long_only=long_only,
        max_abs_weight=max_abs_weight,
        exposure_mode=exposure_mode,
        target_gross_exposure=target_gross_exposure,
        target_net_exposure=target_net_exposure,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        as_of_date=as_of_date
    )

    maximum_sharpe_weights = maximum_sharpe_portfolio(
        tickers=tickers,
        score_column=score_column,
        risk_free_signal=risk_free_signal,
        max_weight=max_weight,
        long_only=long_only,
        max_abs_weight=max_abs_weight,
        exposure_mode=exposure_mode,
        target_gross_exposure=target_gross_exposure,
        target_net_exposure=target_net_exposure,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        as_of_date=as_of_date
    )

    mean_variance_weights = mean_variance_portfolio(
        tickers=tickers,
        risk_aversion=risk_aversion,
        score_column=score_column,
        max_weight=max_weight,
        long_only=long_only,
        max_abs_weight=max_abs_weight,
        exposure_mode=exposure_mode,
        target_net_exposure=target_net_exposure,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        as_of_date=as_of_date
    )

    risk_parity_weights = risk_parity_portfolio(
        tickers=tickers,
        max_weight=max_weight,
        max_iterations=risk_parity_max_iterations,
        tolerance=risk_parity_tolerance,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        as_of_date=as_of_date
    )

    hierarchical_risk_parity_weights = hierarchical_risk_parity_portfolio(
        tickers=tickers,
        max_weight=max_weight,
        linkage_method=hrp_linkage_method,
        covariance_method=covariance_method,
        ewma_span=ewma_span,
        use_expected_return_signal=hrp_use_expected_return_signal,
        score_column=score_column,
        return_risk_metric=hrp_return_risk_metric,
        as_of_date=as_of_date
    )

    return {
        "equal_weight": build_portfolio_summary(equal_weights, risk_free_rate, as_of_date),
        "top_n_equal_weight": build_portfolio_summary(top_n_equal_weights, risk_free_rate, as_of_date),
        "score_weighted": build_portfolio_summary(score_weights, risk_free_rate, as_of_date),
        "risk_adjusted_score_weighted": build_portfolio_summary(
            risk_adjusted_weights,
            risk_free_rate,
            as_of_date
        ),
        "minimum_variance": build_portfolio_summary(minimum_variance_weights, risk_free_rate, as_of_date),
        "maximum_sharpe": build_portfolio_summary(maximum_sharpe_weights, risk_free_rate, as_of_date),
        "mean_variance": build_portfolio_summary(mean_variance_weights, risk_free_rate, as_of_date),
        "risk_parity": build_portfolio_summary(risk_parity_weights, risk_free_rate, as_of_date),
        "hierarchical_risk_parity": build_portfolio_summary(
            hierarchical_risk_parity_weights,
            risk_free_rate,
            as_of_date
        ),
    }