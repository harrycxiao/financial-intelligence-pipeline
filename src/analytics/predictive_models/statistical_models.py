# src/analytics/predictive_models/statistical_models.py

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import BayesianRidge, ElasticNetCV, HuberRegressor, RidgeCV
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_EXCLUDED_COLUMNS = {
    "ticker",
    "as_of_date",
    "start_date",
    "end_date",
    "target",
    "forward_return",
    "forward_excess_return",
    "realized_return",
    "realized_excess_return",
}


@dataclass
class StatisticalExpectedReturnModel:
    """Container for trained statistical expected-return models."""

    feature_columns: list[str]
    target_column: str
    base_models: dict[str, Any]
    meta_model: Any
    base_model_names: list[str]
    target_clip_lower: Optional[float]
    target_clip_upper: Optional[float]


def infer_feature_columns(
    df: pd.DataFrame,
    target_column: str = "forward_excess_return",
    excluded_columns: Optional[set[str]] = None,
) -> list[str]:
    """Infer numeric feature columns."""

    if excluded_columns is None:
        excluded_columns = DEFAULT_EXCLUDED_COLUMNS

    excluded = set(excluded_columns)
    excluded.add(target_column)

    feature_columns = []

    for column in df.columns:
        if column in excluded:
            continue

        if pd.api.types.is_numeric_dtype(df[column]):
            feature_columns.append(column)

    return feature_columns


def prepare_training_data(
    df: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    clip_target_quantiles: Optional[tuple[float, float]] = (0.01, 0.99),
) -> tuple[pd.DataFrame, pd.Series, Optional[float], Optional[float]]:
    """Prepare X/y for model training."""

    needed_columns = feature_columns + [target_column]
    clean_df = df.loc[:, needed_columns].copy()

    clean_df[target_column] = pd.to_numeric(clean_df[target_column], errors="coerce")
    clean_df = clean_df.dropna(subset=[target_column])

    if clean_df.empty:
        raise ValueError("No valid training rows after dropping missing target values.")

    y = clean_df[target_column].astype(float)

    target_clip_lower = None
    target_clip_upper = None

    if clip_target_quantiles is not None:
        lower_q, upper_q = clip_target_quantiles
        target_clip_lower = float(y.quantile(lower_q))
        target_clip_upper = float(y.quantile(upper_q))
        y = y.clip(lower=target_clip_lower, upper=target_clip_upper)

    X = clean_df.loc[:, feature_columns].copy()

    return X, y, target_clip_lower, target_clip_upper


def make_standard_regression_pipeline(model: Any) -> Pipeline:
    """Create a standard impute-scale-regress pipeline."""

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", model),
        ]
    )


def train_ridge_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Train Ridge regression."""

    model = RidgeCV(
        alphas=np.array([0.01, 0.1, 1.0, 3.0, 10.0, 30.0, 100.0]),
    )

    pipeline = make_standard_regression_pipeline(model)
    pipeline.fit(X, y)

    return pipeline


def predict_ridge_returns(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Predict expected excess returns using Ridge."""

    return np.asarray(model.predict(X), dtype=float)


def train_elastic_net_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Train ElasticNet regression."""

    model = ElasticNetCV(
        l1_ratio=[0.1, 0.3, 0.5, 0.7, 0.9],
        alphas=[0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0],
        max_iter=10000,
        cv=5,
    )

    pipeline = make_standard_regression_pipeline(model)
    pipeline.fit(X, y)

    return pipeline


def predict_elastic_net_returns(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Predict expected excess returns using ElasticNet."""

    return np.asarray(model.predict(X), dtype=float)


def train_bayesian_ridge_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Train Bayesian Ridge regression."""

    model = BayesianRidge()

    pipeline = make_standard_regression_pipeline(model)
    pipeline.fit(X, y)

    return pipeline


def predict_bayesian_ridge_returns(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Predict expected excess returns using Bayesian Ridge."""

    return np.asarray(model.predict(X), dtype=float)


def train_huber_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Train robust Huber regression."""

    model = HuberRegressor(
        epsilon=1.35,
        alpha=0.0001,
        max_iter=1000,
    )

    pipeline = make_standard_regression_pipeline(model)
    pipeline.fit(X, y)

    return pipeline


def predict_huber_returns(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Predict expected excess returns using Huber regression."""

    return np.asarray(model.predict(X), dtype=float)


def train_pcr_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Train principal-component regression."""

    n_features = len(X.columns)
    n_components = max(1, min(8, n_features))

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("pca", PCA(n_components=n_components)),
            ("model", RidgeCV(alphas=np.array([0.01, 0.1, 1.0, 3.0, 10.0, 30.0, 100.0]))),
        ]
    )

    model.fit(X, y)

    return model


def predict_pcr_returns(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Predict expected excess returns using PCR."""

    return np.asarray(model.predict(X), dtype=float)


def train_pls_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Train partial least squares regression."""

    n_features = len(X.columns)
    n_components = max(1, min(6, n_features))

    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", PLSRegression(n_components=n_components)),
        ]
    )

    model.fit(X, y)

    return model


def predict_pls_returns(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Predict expected excess returns using PLS."""

    predictions = model.predict(X)
    return np.asarray(predictions, dtype=float).reshape(-1)


def get_base_statistical_model_trainers() -> dict[str, Any]:
    """Return base statistical model training functions."""

    return {
        "ridge": train_ridge_model,
        "elastic_net": train_elastic_net_model,
        "bayesian_ridge": train_bayesian_ridge_model,
        "huber": train_huber_model,
        "pcr": train_pcr_model,
        "pls": train_pls_model,
    }


def get_base_statistical_model_predictors() -> dict[str, Any]:
    """Return base statistical model prediction functions."""

    return {
        "ridge": predict_ridge_returns,
        "elastic_net": predict_elastic_net_returns,
        "bayesian_ridge": predict_bayesian_ridge_returns,
        "huber": predict_huber_returns,
        "pcr": predict_pcr_returns,
        "pls": predict_pls_returns,
    }


def make_expanding_time_splits(
    df: pd.DataFrame,
    date_column: str = "as_of_date",
    min_train_periods: int = 8,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Create expanding-window train/test splits by rebalance date."""

    if date_column not in df.columns:
        return []

    date_values = pd.Series(
        pd.to_datetime(df[date_column]),
        index=df.index,
    )

    dates = (
        date_values
        .dropna()
        .sort_values()
        .unique()
    )

    if len(dates) <= min_train_periods:
        return []

    splits = []

    for test_position in range(min_train_periods, len(dates)):
        train_dates = dates[:test_position]
        test_date = dates[test_position]

        train_index = df.index[date_values.isin(train_dates)].to_numpy()
        test_index = df.index[date_values == test_date].to_numpy()

        if len(train_index) > 0 and len(test_index) > 0:
            splits.append((train_index, test_index))

    return splits


def make_fallback_kfold_splits(
    df: pd.DataFrame,
    n_splits: int = 5,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Create fallback KFold splits if date-based splits are unavailable."""

    if len(df) < n_splits:
        return []

    splitter = KFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=42,
    )

    return [
        (train_index, test_index)
        for train_index, test_index in splitter.split(df)
    ]


def generate_out_of_fold_base_predictions(
    training_df: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    model_trainers: dict[str, Any],
    date_column: str = "as_of_date",
    min_train_periods: int = 8,
) -> pd.DataFrame:
    """Generate out-of-fold predictions for meta-model training."""

    clean_df = training_df.copy()
    clean_df[target_column] = pd.to_numeric(clean_df[target_column], errors="coerce")
    clean_df = clean_df.dropna(subset=[target_column]).copy()

    splits = make_expanding_time_splits(
        df=clean_df,
        date_column=date_column,
        min_train_periods=min_train_periods,
    )

    if not splits:
        splits = make_fallback_kfold_splits(clean_df)

    if not splits:
        raise ValueError("Not enough data to create out-of-fold predictions.")

    oof_predictions = pd.DataFrame(index=clean_df.index)

    for model_name in model_trainers:
        oof_predictions[model_name] = np.nan

    for train_index, test_index in splits:
        train_df = clean_df.loc[train_index]
        test_df = clean_df.loc[test_index]

        X_train, y_train, _, _ = prepare_training_data(
            df=train_df,
            feature_columns=feature_columns,
            target_column=target_column,
            clip_target_quantiles=(0.01, 0.99),
        )

        X_test = test_df.loc[:, feature_columns].copy()

        for model_name, train_function in model_trainers.items():
            try:
                fitted_model = train_function(X_train, y_train)
                predictions = fitted_model.predict(X_test)
                predictions = np.asarray(predictions, dtype=float).reshape(-1)
                oof_predictions.loc[test_df.index, model_name] = predictions
            except Exception:
                continue

    oof_predictions[target_column] = clean_df[target_column]

    if "ticker" in clean_df.columns:
        oof_predictions["ticker"] = clean_df["ticker"]

    if date_column in clean_df.columns:
        oof_predictions[date_column] = clean_df[date_column]

    oof_predictions = oof_predictions.dropna(subset=list(model_trainers.keys()), how="all")

    return oof_predictions


def train_statistical_meta_model(
    oof_predictions: pd.DataFrame,
    target_column: str,
    base_model_names: list[str],
) -> Pipeline:
    """Train a Ridge meta-model to combine base statistical predictions."""

    clean = oof_predictions.dropna(subset=[target_column]).copy()

    if clean.empty:
        raise ValueError("No valid rows for statistical meta-model training.")

    X_meta = clean.loc[:, base_model_names].copy()
    y_meta = pd.to_numeric(clean[target_column], errors="coerce")

    valid = y_meta.notna()
    X_meta = X_meta.loc[valid]
    y_meta = y_meta.loc[valid]

    meta_model = make_standard_regression_pipeline(
        RidgeCV(alphas=np.array([0.01, 0.1, 1.0, 3.0, 10.0, 30.0]))
    )

    meta_model.fit(X_meta, y_meta)

    return meta_model


def train_statistical_expected_return_model(
    training_df: pd.DataFrame,
    feature_columns: Optional[list[str]] = None,
    target_column: str = "forward_excess_return",
    date_column: str = "as_of_date",
    model_names: Optional[list[str]] = None,
    min_train_periods: int = 8,
) -> StatisticalExpectedReturnModel:
    """
    Train a stacked statistical expected-excess-return model.

    Base models:
    ridge, elastic_net, bayesian_ridge, huber, pcr, pls

    Meta-model:
    Ridge regression on out-of-fold base predictions.
    """

    if feature_columns is None:
        feature_columns = infer_feature_columns(
            training_df,
            target_column=target_column,
        )

    if not feature_columns:
        raise ValueError("No feature columns found for statistical model training.")

    all_trainers = get_base_statistical_model_trainers()

    if model_names is None:
        model_names = list(all_trainers.keys())

    model_trainers = {
        name: all_trainers[name]
        for name in model_names
        if name in all_trainers
    }

    if not model_trainers:
        raise ValueError("No valid statistical model names were provided.")

    X, y, target_clip_lower, target_clip_upper = prepare_training_data(
        df=training_df,
        feature_columns=feature_columns,
        target_column=target_column,
        clip_target_quantiles=(0.01, 0.99),
    )

    base_models = {}

    for model_name, train_function in model_trainers.items():
        base_models[model_name] = train_function(X, y)

    oof_predictions = generate_out_of_fold_base_predictions(
        training_df=training_df,
        feature_columns=feature_columns,
        target_column=target_column,
        model_trainers=model_trainers,
        date_column=date_column,
        min_train_periods=min_train_periods,
    )

    base_model_names = list(model_trainers.keys())

    meta_model = train_statistical_meta_model(
        oof_predictions=oof_predictions,
        target_column=target_column,
        base_model_names=base_model_names,
    )

    return StatisticalExpectedReturnModel(
        feature_columns=feature_columns,
        target_column=target_column,
        base_models=base_models,
        meta_model=meta_model,
        base_model_names=base_model_names,
        target_clip_lower=target_clip_lower,
        target_clip_upper=target_clip_upper,
    )


def predict_base_statistical_returns(
    model: StatisticalExpectedReturnModel,
    current_features: pd.DataFrame,
) -> pd.DataFrame:
    """Predict expected excess returns from every base statistical model."""

    X = current_features.loc[:, model.feature_columns].copy()

    predictors = get_base_statistical_model_predictors()

    prediction_df = pd.DataFrame(index=current_features.index)

    if "ticker" in current_features.columns:
        prediction_df["ticker"] = current_features["ticker"].values

    for model_name in model.base_model_names:
        fitted_model = model.base_models.get(model_name)

        if fitted_model is None:
            prediction_df[model_name] = np.nan
            continue

        try:
            predict_function = predictors.get(model_name)
            if predict_function is None:
                predictions = fitted_model.predict(X)
            else:
                predictions = predict_function(fitted_model, X)

            prediction_df[model_name] = np.asarray(predictions, dtype=float).reshape(-1)

        except Exception:
            prediction_df[model_name] = np.nan

    return prediction_df


def predict_statistical_expected_returns(
    model: StatisticalExpectedReturnModel,
    current_features: pd.DataFrame,
    output_column: str = "statistical_expected_excess_return",
) -> pd.DataFrame:
    """Predict final statistical expected excess returns."""

    base_predictions = predict_base_statistical_returns(
        model=model,
        current_features=current_features,
    )

    X_meta = base_predictions.loc[:, model.base_model_names].copy()

    final_predictions = model.meta_model.predict(X_meta)
    final_predictions = np.asarray(final_predictions, dtype=float).reshape(-1)

    result = base_predictions.copy()
    result[output_column] = final_predictions

    return result


def train_and_predict_statistical_expected_returns(
    training_df: pd.DataFrame,
    current_features: pd.DataFrame,
    feature_columns: Optional[list[str]] = None,
    target_column: str = "forward_excess_return",
    date_column: str = "as_of_date",
    model_names: Optional[list[str]] = None,
    min_train_periods: int = 8,
) -> pd.DataFrame:
    """
    Convenience function:
    train statistical model on historical rows, then predict current expected returns.
    """

    model = train_statistical_expected_return_model(
        training_df=training_df,
        feature_columns=feature_columns,
        target_column=target_column,
        date_column=date_column,
        model_names=model_names,
        min_train_periods=min_train_periods,
    )

    return predict_statistical_expected_returns(
        model=model,
        current_features=current_features,
    )