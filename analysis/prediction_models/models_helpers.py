import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from xgboost import XGBClassifier

sys.path.insert(0, '..')

from clustering.config import (
    
    HOUSEHOLD_BINS,
    HOUSEHOLD_LABELS,
    HS_COLS,
    OBESITY_BMI_THRESHOLD,
    DIABETES_UNLIKELY_VALUE,
    AGE_BINS,
    AGE_LABELS,
)

from config_models import (
    DATE_COLS,
    CATEGORICAL_COLS,
    MEASURE_LIMITS,
    MEASURES_COLS,
    MLTC_COLS,
    UNDERSERVED_COLS,
    COPD_HSU_COLS,
    DUMMY_MEASURE_PARAMS,
    SUBGROUP_COLS,
)
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
)

def build_predictor_features(df):
    """
    Build predictor features for WP4 prediction models.Primary-care diagnosis only
    """

    out = pd.DataFrame({"patient_id": df["patient_id"]}, index=df.index)

    dates_df = {
        col: pd.to_datetime(df[col], errors="coerce")
        for col in DATE_COLS
    }

    index_date = dates_df["index_date"]

    # Age (Should be no missings)
    age = np.floor(
        (index_date - dates_df["birth_date"]).dt.days / 365.25
    )

    out["age"] = age
    # Age bands
    out["age_band"] = pd.cut(
    age,
    bins=AGE_BINS,
    labels=AGE_LABELS,
    right=False
).astype("object")
    
    # Household size
    hs_numeric = pd.to_numeric(df["household_size"], errors="coerce") # Remove this one ? 

    out["cat_household_size"] = pd.cut(
        hs_numeric,
        bins=HOUSEHOLD_BINS,
        labels=HOUSEHOLD_LABELS,
        right=True,
        include_lowest=True,
    ).astype("object")

    out.loc[
        hs_numeric.isna() | (hs_numeric <= 0),
        "cat_household_size"
    ] = "unknown"

    #  categorical predictors
    derived_cols = {"cat_household_size"}
    for col in CATEGORICAL_COLS:
        if col not in derived_cols:
            out[col] = df[col].astype("object")

    #  clinical measures
    for col in MEASURES_COLS:
        out[col] = pd.to_numeric(df[col], errors="coerce")

    # Primary-care MLTCs
    out["copd"] = dates_df["tmp_copd_date_primary"].notna().astype(int)

    out["hypertension"] = dates_df["hypertension_date_primary"].notna().astype(int)

    out["af"] = dates_df["af_date_primary"].notna().astype(int)

    out["ihd"] = dates_df["ihd_date_primary"].notna().astype(int)

    out["ckd"] = dates_df["ckd_date_primary"].notna().astype(int)

    # Diabetes
    out["has_diabetes"] = ((df["cat_diabetes"] != DIABETES_UNLIKELY_VALUE) & (df["cat_diabetes"].notna())).astype(int)

    # Obesity: primary-care code OR BMI >= 30 
    obesity_from_code = dates_df["obesity_primary_date"].notna()

    bmi_numeric = pd.to_numeric(df["bmi_value"], errors="coerce")
    bmi_lower, bmi_upper = MEASURE_LIMITS["bmi_value"]

    obesity_from_bmi = (
        (bmi_numeric >= OBESITY_BMI_THRESHOLD) & 
        (bmi_numeric >= bmi_lower) & 
        (bmi_numeric <= bmi_upper)
    )

    out["obesity"] = (obesity_from_code | obesity_from_bmi).astype(int)

    # Medication/treatment flags
    out["bp_treatment"] = (
        dates_df["last_hypertension_date_med"].notna().astype(int)
    )

    out["diabetes_treatment"] = (
        dates_df["last_diabetes_medication_date"].notna().astype(int)
    )

    # Multi-morbidity Keep both for now ? 
    out["mltc_count"] = out[MLTC_COLS].sum(axis=1)
    out["has_mltc"] = (out["mltc_count"] >= 2).astype(int)

    # Under-served groups
    for col in UNDERSERVED_COLS:
        out[col] = (
            pd.to_numeric(df[col], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    out["n_underserved"] = out[UNDERSERVED_COLS].sum(axis=1)
    out["any_underserved"] = (
    out["n_underserved"] >= 1
    ).astype(int)

    # Review indicators
    out["asthma_review"] = dates_df["asthma_review_date"].notna().astype(int)
    out["copd_review"] = dates_df["copd_review_date"].notna().astype(int)
    out["med_review"] = dates_df["med_review_date"].notna().astype(int)

    # Pre-index healthcare utilisation
    for col in HS_COLS:
        out[col] = (
                pd.to_numeric(df[col], errors="coerce")
                .fillna(0)
            )

    # COPD-specific utilisation
    for col in COPD_HSU_COLS:
        out[col] = (
            pd.to_numeric(df[col], errors="coerce")
            .fillna(0)
            
        )

    out = out.drop(columns=["has_diabetes"])

    return out


def clean_measure_values(df):
    """
    Clean unplausible measurement values.
    """

    out = df.copy()


    # Swap systolic and diastolic BP if diastolic > systolic
    swap_bp = (
        out["sysbp_value"].notna()
        & out["diasbp_value"].notna()
        & (out["diasbp_value"] > out["sysbp_value"])
    )

    out.loc[swap_bp, ["sysbp_value", "diasbp_value"]] = (
        out.loc[swap_bp, ["diasbp_value", "sysbp_value"]].to_numpy()
    )

    for col, limits in MEASURE_LIMITS.items():

        lower, upper = limits

        out.loc[
            (out[col] < lower) | (out[col] > upper),
            col
        ] = np.nan

    invalid_bp = (
        out["sysbp_value"].notna()
        & out["diasbp_value"].notna()
        & (out["diasbp_value"] == out["sysbp_value"])
    )

    out.loc[
        invalid_bp,
        ["sysbp_value", "diasbp_value"]
    ] = np.nan

    return out

def is_binary_column(s):
    """
    check if a column is binary"""

    if s.dtype in ['object', 'category']:
        return False
    
    numeric_values = pd.to_numeric(s, errors='coerce')
    unique_values = set(numeric_values.dropna().unique())
    
    # Check if all values are 0 or 1 
    return len(unique_values) > 0 and all(v in (0, 1) for v in unique_values)

def fill_dummy_measure_values(df, missing_prop=0.2, seed=42):
    """ Fill measures values with plausible values + noise + random missing values.
      Otherwise, they are removed from the dataset. """
    
    rng = np.random.default_rng(seed)
    out = df.copy()

    

    for col, params in DUMMY_MEASURE_PARAMS.items():
        

        mean, sd, lower, upper = params

        values = rng.normal(mean, sd, len(out))
        values = np.clip(values, lower, upper)

        missing_mask = rng.random(len(out)) < missing_prop
        values[missing_mask] = np.nan

        out[col] = values

    
    invalid_bp = (
        out["sysbp_value"].notna()
        & out["diasbp_value"].notna()
        & (out["diasbp_value"] >= out["sysbp_value"])
    )

    out.loc[invalid_bp, "diasbp_value"] = (
        out.loc[invalid_bp, "sysbp_value"]
        - rng.uniform(20, 60, invalid_bp.sum())
    )

    out["diasbp_value"] = out["diasbp_value"].clip(lower=20, upper=200)

    return out

def get_model_specs(y_train, random_state=42):
    """
    Define model specifications (based on Charlottes code)
    
    """

    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    model_specs = {
        "lr": { # lr doesn't run without imputation, so we add imputer
            "search_type": "grid", # as it is fast 
            "n_iter": None,
            "model": Pipeline([
                ("imputer", SimpleImputer(
                    strategy="median",
                    add_indicator=True
                )),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(
                    max_iter=10000,
                    class_weight="balanced",
                    random_state=random_state
                ))
            ]),
            "params": [
                {
                    "model__C": [0.1, 1, 10],
                    "model__penalty": ["l2"],
                    "model__solver": ["saga"],
                },
                {
                    "model__C": [0.1, 1, 10],
                    "model__penalty": ["elasticnet"],
                    "model__solver": ["saga"],
                    "model__l1_ratio": [0.5],
                    
                },
            ],
        },

        "rf": {
            "search_type": "random",
            "n_iter": 25,
            "model": RandomForestClassifier(
                random_state=random_state
               
            ),
            "params": {
                "n_estimators": [50, 100, 150],
                "max_depth": [10, 20, 30, 40],
                "max_features": ["sqrt", "log2"],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
                "criterion": ["gini", "entropy", "log_loss"],
                "class_weight": ["balanced", "balanced_subsample"],
            },
        },

        "hgb": {
            "search_type": "random",
            "n_iter": 20,
            "model": HistGradientBoostingClassifier(
                random_state=random_state
            ),
            "params": {
                "max_iter": [100, 200, 300, 400],
                "max_depth": [2, 3, 5],
                "learning_rate": [0.1, 0.01, 0.001],
            },
        },

        "xgb": {
            "search_type": "random",
            "n_iter": 25,
            "model": XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=random_state,
                missing=np.nan
            ),
            "params": {
                "n_estimators": [100, 200, 300, 400],
                "max_depth": [2, 3, 5],
                "learning_rate": [0.1, 0.01, 0.001],
                "gamma": [0, 0.1, 0.2],
                "subsample": [0.2, 0.5, 0.7],
                "colsample_bytree": [0.2, 0.5, 0.7],
                "scale_pos_weight": [scale_pos_weight],
            },
        },
    }

    return model_specs

def safe_divide(numerator, denominator):
    

    if denominator == 0:
        return np.nan

    return numerator / denominator

def calculate_accuracy(observed, predicted):
    """
    Calculates classification performance from observed and predicted classes.

    """

    observed = np.asarray(observed)
    predicted = np.asarray(predicted)

    observed_positives = observed == 1
    observed_negatives = observed == 0
    predicted_positives = predicted == 1
    predicted_negatives = predicted == 0

    tp = np.sum(predicted_positives & observed_positives)
    fp = np.sum(predicted_positives & observed_negatives)
    tn = np.sum(predicted_negatives & observed_negatives)
    fn = np.sum(predicted_negatives & observed_positives)

    accuracy = np.mean(predicted == observed)

    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)

    sensitivity = recall
    specificity = safe_divide(tn, tn + fp)

    if np.isnan(precision) or np.isnan(recall) or (precision + recall == 0):
        f1 = np.nan
    else:
        f1 = 2 * precision * recall / (precision + recall)

    positive_likelihood = safe_divide(
        sensitivity,
        1 - specificity
    )

    negative_likelihood = safe_divide(
        1 - sensitivity,
        specificity
    )

    negative_predictive_value = safe_divide(tn, tn + fn)

    results = {
        "observed_positive_rate": np.mean(observed_positives),
        "observed_negative_rate": np.mean(observed_negatives),
        "predicted_positive_rate": np.mean(predicted_positives),
        "predicted_negative_rate": np.mean(predicted_negatives),
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "positive_likelihood": positive_likelihood,
        "negative_likelihood": negative_likelihood,
        "false_positive_rate": 1 - specificity,
        "false_negative_rate": 1 - sensitivity,
        "true_positive_rate": sensitivity,
        "true_negative_rate": specificity,
        "positive_predictive_value": precision,
        "negative_predictive_value": negative_predictive_value,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
    }

    return results

def tune_model(model_name,model,params,search_type,X_train,y_train,cv,scoring="roc_auc", n_iter=None,
    random_state=42
):
    """ tune hyperparameters using grid search or random search """ 

    if search_type == "grid":
        search = GridSearchCV(
            estimator=model,
            param_grid=params,
            scoring=scoring,
            cv=cv,
            n_jobs=-1,
            verbose=1,
            refit=True,
            return_train_score=True
        )

    elif search_type == "random":
        search = RandomizedSearchCV(
            estimator=model,
            param_distributions=params,
            n_iter=n_iter,
            scoring=scoring,
            cv=cv,
            n_jobs=-1,
            verbose=1,
            refit=True,
            random_state=random_state,
            return_train_score=True
        )

    
    search.fit(X_train, y_train)

    print(f"{model_name}: best CV {scoring} = {search.best_score_:.4f}")
    print(f"{model_name}: best params = {search.best_params_}")

    return search

def evaluate_prediction_metrics(y_true, y_prob, threshold):
    """
    Evaluate model performance using predicted probabilities and a decision threshold.
    """

    y_pred = (y_prob >= threshold).astype(int)

    performance = calculate_accuracy(
        observed=y_true,
        predicted=y_pred
    )

    performance["auc"] = roc_auc_score(y_true, y_prob)
    performance["auc_pr"] = average_precision_score(y_true, y_prob)
    performance["brier"] = brier_score_loss(y_true, y_prob)
    performance["threshold"] = threshold
    performance["observed_event_rate"] = np.mean(y_true)
    performance["mean_predicted_risk"] = np.mean(y_prob)

    return performance



def find_threshold(probabilities, true_rate):
    """
    Find classification threshold so the predicted positive rate
    approximately equals the true positive rate.

    """

    probabilities = np.asarray(probabilities)

    threshold = np.quantile(
        probabilities,
        1 - true_rate
    )

    return float(threshold)


def evaluate_fitted_model(model, X, y, X_val, y_val, threshold=None):
    """
    Evaluate one fitted model.

    """

    # Tune threshold on training data
    y_prob_train = model.predict_proba(X)[:, 1]

    if threshold is None:
        threshold = find_threshold(
            probabilities=y_prob_train,
            true_rate=np.mean(y)
        )

    # Evaluate on val data
    y_prob = model.predict_proba(X_val)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    performance = evaluate_prediction_metrics(
        y_true=y_val,
        y_prob=y_prob,
        threshold=threshold
    )

    return y_pred, y_prob, performance, model

def evaluate_tuned_models(results,X_train,y_train,X_test,y_test,patient_ids,threshold=None
):
    """
    Evaluate tuned models 
    """

    performance_rows = []

    prediction_df = pd.DataFrame({
        "patient_id": patient_ids.reset_index(drop=True),
        "hf_outcome": y_test.reset_index(drop=True),
    })

    for model_name, search in results.items():
        print(f"Evaluating {model_name}")

        model = search.best_estimator_

        y_pred, y_prob, performance, _ = evaluate_fitted_model(
            model=model,
            X=X_train,
            y=y_train,
            X_val=X_test,
            y_val=y_test,
            threshold=threshold
        )

        prediction_df[f"{model_name}_prob"] = y_prob
        prediction_df[f"{model_name}_pred"] = y_pred

        performance["model"] = model_name
        performance["best_cv_score"] = search.best_score_
        performance_rows.append(performance)
        performance["threshold_method"] = (
    "event_rate_train" if threshold is None else "fixed"
)

    performance_df = pd.DataFrame(performance_rows)

    return performance_df, prediction_df


