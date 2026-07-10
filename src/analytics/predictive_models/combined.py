from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from sklearn.linear_model import RidgeCV
from sklearn.pipeline import Pipeline

from src.analytics.predictive_models.statistical_models import (
    prepare_training_data,
    make_standard_regression_pipeline,
    make_expanding_time_splits,
    make_fallback_kfold_splits,
    train_ridge_model,
    train_elastic_net_model,
    train_bayesian_ridge_model,
    train_huber_model,
    train_pcr_model,
    train_pls_model,
)

from src.analytics.predictive_models.machine_learning_models import (
    train_random_forest_model,
    train_extra_trees_model,
    train_hist_gradient_boosting_model,
    train_mlp_model,
)


COMBINED_OUTPUT_COLUMN = "combined_expected_excess_return"


@dataclass
class CombinedExpectedReturnModel:
    statistical_feature_columns: list[str]
    ml_feature_columns: list[str]
    target_column: str
    base_models: dict[str, Any]
    meta_model: Any
    base_model_names: list[str]


def get_combined_model_trainers() -> dict[str, Any]:
    return {
        "stat_ridge": train_ridge_model,
        "stat_elastic_net": train_elastic_net_model,
        "stat_bayesian_ridge": train_bayesian_ridge_model,
        "stat_huber": train_huber_model,
        "stat_pcr": train_pcr_model,
        "stat_pls": train_pls_model,
        "ml_random_forest": train_random_forest_model,
        "ml_extra_trees": train_extra_trees_model,
        "ml_hist_gradient_boosting": train_hist_gradient_boosting_model,
        "ml_mlp": train_mlp_model,
    }


def get_feature_columns_for_model(
    model_name: str,
    statistical_feature_columns: list[str],
    ml_feature_columns: list[str],
) -> list[str]:
    if model_name.startswith("stat_"):
        return statistical_feature_columns

    if model_name.startswith("ml_"):
        return ml_feature_columns

    raise ValueError(f"Unknown combined model type: {model_name}")


def generate_combined_oof_predictions(
    training_df: pd.DataFrame,
    statistical_feature_columns: list[str],
    ml_feature_columns: list[str],
    target_column: str,
    model_trainers: dict[str, Any],
    date_column: str = "as_of_date",
    min_train_periods: int = 8,
) -> pd.DataFrame:
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
        raise ValueError("Not enough data to create combined OOF predictions.")

    oof_predictions = pd.DataFrame(index=clean_df.index)

    for model_name in model_trainers:
        oof_predictions[model_name] = np.nan

    for train_index, test_index in splits:
        train_df = clean_df.loc[train_index]
        test_df = clean_df.loc[test_index]

        for model_name, train_function in model_trainers.items():
            feature_columns = get_feature_columns_for_model(
                model_name=model_name,
                statistical_feature_columns=statistical_feature_columns,
                ml_feature_columns=ml_feature_columns,
            )

            try:
                X_train, y_train, _, _ = prepare_training_data(
                    df=train_df,
                    feature_columns=feature_columns,
                    target_column=target_column,
                    clip_target_quantiles=(0.01, 0.99),
                )

                X_test = test_df.loc[:, feature_columns].copy()

                fitted_model = train_function(X_train, y_train)
                preds = fitted_model.predict(X_test)

                oof_predictions.loc[test_df.index, model_name] = np.asarray(
                    preds,
                    dtype=float,
                ).reshape(-1)

            except Exception:
                continue

    oof_predictions[target_column] = clean_df[target_column]

    if "ticker" in clean_df.columns:
        oof_predictions["ticker"] = clean_df["ticker"]

    if date_column in clean_df.columns:
        oof_predictions[date_column] = clean_df[date_column]

    return oof_predictions.dropna(
        subset=list(model_trainers.keys()),
        how="all",
    )


def train_combined_meta_model(
    oof_predictions: pd.DataFrame,
    target_column: str,
    base_model_names: list[str],
) -> Pipeline:
    clean = oof_predictions.dropna(subset=[target_column]).copy()

    if clean.empty:
        raise ValueError("No valid rows for combined meta-model training.")

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


def train_combined_expected_return_model(
    training_df: pd.DataFrame,
    statistical_feature_columns: list[str],
    ml_feature_columns: list[str],
    target_column: str = "forward_excess_return",
    date_column: str = "as_of_date",
    min_train_periods: int = 8,
) -> CombinedExpectedReturnModel:
    model_trainers = get_combined_model_trainers()
    base_models = {}

    for model_name, train_function in model_trainers.items():
        feature_columns = get_feature_columns_for_model(
            model_name=model_name,
            statistical_feature_columns=statistical_feature_columns,
            ml_feature_columns=ml_feature_columns,
        )

        X, y, _, _ = prepare_training_data(
            df=training_df,
            feature_columns=feature_columns,
            target_column=target_column,
            clip_target_quantiles=(0.01, 0.99),
        )

        base_models[model_name] = train_function(X, y)

    oof_predictions = generate_combined_oof_predictions(
        training_df=training_df,
        statistical_feature_columns=statistical_feature_columns,
        ml_feature_columns=ml_feature_columns,
        target_column=target_column,
        model_trainers=model_trainers,
        date_column=date_column,
        min_train_periods=min_train_periods,
    )

    base_model_names = list(model_trainers.keys())

    meta_model = train_combined_meta_model(
        oof_predictions=oof_predictions,
        target_column=target_column,
        base_model_names=base_model_names,
    )

    return CombinedExpectedReturnModel(
        statistical_feature_columns=statistical_feature_columns,
        ml_feature_columns=ml_feature_columns,
        target_column=target_column,
        base_models=base_models,
        meta_model=meta_model,
        base_model_names=base_model_names,
    )


def predict_combined_base_returns(
    model: CombinedExpectedReturnModel,
    current_features: pd.DataFrame,
) -> pd.DataFrame:
    prediction_df = pd.DataFrame(index=current_features.index)

    if "ticker" in current_features.columns:
        prediction_df["ticker"] = current_features["ticker"].values

    for model_name in model.base_model_names:
        fitted_model = model.base_models.get(model_name)

        if fitted_model is None:
            prediction_df[model_name] = np.nan
            continue

        feature_columns = get_feature_columns_for_model(
            model_name=model_name,
            statistical_feature_columns=model.statistical_feature_columns,
            ml_feature_columns=model.ml_feature_columns,
        )

        try:
            X = current_features.loc[:, feature_columns].copy()

            prediction_df[model_name] = np.asarray(
                fitted_model.predict(X),
                dtype=float,
            ).reshape(-1)

        except Exception:
            prediction_df[model_name] = np.nan

    return prediction_df


def predict_combined_expected_returns(
    model: CombinedExpectedReturnModel,
    current_features: pd.DataFrame,
    output_column: str = COMBINED_OUTPUT_COLUMN,
) -> pd.DataFrame:
    base_predictions = predict_combined_base_returns(
        model=model,
        current_features=current_features,
    )

    X_meta = base_predictions.loc[:, model.base_model_names].copy()

    final_predictions = model.meta_model.predict(X_meta)
    final_predictions = np.asarray(final_predictions, dtype=float).reshape(-1)

    result = base_predictions.copy()
    result[output_column] = final_predictions

    return result


def train_and_predict_combined_expected_returns(
    training_df: pd.DataFrame,
    current_features: pd.DataFrame,
    statistical_feature_columns: list[str],
    ml_feature_columns: list[str],
    target_column: str = "forward_excess_return",
    date_column: str = "as_of_date",
    min_train_periods: int = 8,
) -> pd.DataFrame:
    model = train_combined_expected_return_model(
        training_df=training_df,
        statistical_feature_columns=statistical_feature_columns,
        ml_feature_columns=ml_feature_columns,
        target_column=target_column,
        date_column=date_column,
        min_train_periods=min_train_periods,
    )

    return predict_combined_expected_returns(
        model=model,
        current_features=current_features,
    )