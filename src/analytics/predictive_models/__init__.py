# src/analytics/predictive_models/__init__.py

"""
Predictive modeling package for expected excess-return estimation.

Main production interface:
- Build point-in-time predictive datasets.
- Train the stacked statistical expected-return model.
- Produce final alpha expected-return signals.

Experimental interfaces:
- Machine-learning expected-return models.
- Combined statistical and machine-learning stack.
"""

# ---------------------------------------------------------------------
# Feature definitions and predictive data construction
# ---------------------------------------------------------------------

from src.analytics.predictive_models.data_structures import (
    DEFAULT_DATE_COLUMN,
    DEFAULT_TARGET_COLUMN,
    ML_FEATURE_COLUMNS,
    PREDICTIVE_RESULTS_DIR,
    STATISTICAL_FEATURE_COLUMNS,
    add_forward_excess_returns,
    build_alpha_model_base_inputs,
    build_alpha_train_predict_inputs,
    build_current_features_dataframe,
    build_factor_snapshot,
    build_factor_snapshots,
    build_ml_train_predict_inputs,
    build_predictive_training_dataframe,
    build_statistical_train_predict_inputs,
    calculate_benchmark_forward_return,
    calculate_forward_return_for_tickers,
)

# ---------------------------------------------------------------------
# Main alpha interface
# ---------------------------------------------------------------------

from src.analytics.predictive_models.alpha_models import (
    FINAL_ALPHA_COLUMN,
    STATISTICAL_ALPHA_COLUMN,
    add_current_date_to_training_boundaries,
    calculate_alpha_expected_returns,
    select_top_alpha_tickers,
)

# ---------------------------------------------------------------------
# Statistical expected-return models
# ---------------------------------------------------------------------

from src.analytics.predictive_models.statistical_models import (
    StatisticalExpectedReturnModel,
    predict_statistical_expected_returns,
    train_and_predict_statistical_expected_returns,
    train_statistical_expected_return_model,
)

# ---------------------------------------------------------------------
# Experimental machine-learning models
# ---------------------------------------------------------------------

from src.analytics.predictive_models.machine_learning_models import (
    MACHINE_LEARNING_OUTPUT_COLUMN,
    MachineLearningExpectedReturnModel,
    predict_machine_learning_expected_returns,
    train_and_predict_machine_learning_expected_returns,
    train_machine_learning_expected_return_model,
)

# ---------------------------------------------------------------------
# Experimental combined stack
# ---------------------------------------------------------------------

from src.analytics.predictive_models.combined import (
    COMBINED_OUTPUT_COLUMN,
    CombinedExpectedReturnModel,
    predict_combined_expected_returns,
    train_and_predict_combined_expected_returns,
    train_combined_expected_return_model,
)


__all__ = [
    # Constants
    "PREDICTIVE_RESULTS_DIR",
    "DEFAULT_TARGET_COLUMN",
    "DEFAULT_DATE_COLUMN",
    "STATISTICAL_FEATURE_COLUMNS",
    "ML_FEATURE_COLUMNS",
    "STATISTICAL_ALPHA_COLUMN",
    "FINAL_ALPHA_COLUMN",
    "MACHINE_LEARNING_OUTPUT_COLUMN",
    "COMBINED_OUTPUT_COLUMN",

    # Data construction
    "build_factor_snapshot",
    "build_factor_snapshots",
    "build_predictive_training_dataframe",
    "build_current_features_dataframe",
    "build_statistical_train_predict_inputs",
    "build_ml_train_predict_inputs",
    "build_alpha_train_predict_inputs",
    "build_alpha_model_base_inputs",
    "calculate_forward_return_for_tickers",
    "calculate_benchmark_forward_return",
    "add_forward_excess_returns",

    # Main alpha interface
    "add_current_date_to_training_boundaries",
    "calculate_alpha_expected_returns",
    "select_top_alpha_tickers",

    # Statistical models
    "StatisticalExpectedReturnModel",
    "train_statistical_expected_return_model",
    "predict_statistical_expected_returns",
    "train_and_predict_statistical_expected_returns",

    # Experimental ML models
    "MachineLearningExpectedReturnModel",
    "train_machine_learning_expected_return_model",
    "predict_machine_learning_expected_returns",
    "train_and_predict_machine_learning_expected_returns",

    # Experimental combined model
    "CombinedExpectedReturnModel",
    "train_combined_expected_return_model",
    "predict_combined_expected_returns",
    "train_and_predict_combined_expected_returns",
]