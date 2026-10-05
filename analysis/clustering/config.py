#!/usr/bin/env python3
"""
Shared clustering configuration: paths, feature names, and common constants.
"""

import os
import sys
import numpy as np
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
# -------------------
# OpenSafely disclosure threshold
# -------------------

from sdc_helpers import DISCLOSURE_THRESHOLD
# -------------------
# Paths
# -------------------
# Project root directory (3 levels up from this file: analysis/clustering/config.py -> reducehf/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Real data directories
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output/clustering/")

# File names (same for both real and synthetic)
RAW_FILE = "clustering_raw.csv.gz"
SCALED_FILE = "clustering_scaled.csv.gz"


# Real data paths
RAW_PATH = os.path.join(OUTPUT_DIR, RAW_FILE)
SCALED_PATH = os.path.join(OUTPUT_DIR, SCALED_FILE)

# Input data path (for real data)
INPUT_DATA_PATH = os.path.join(PROJECT_ROOT, "output/dataset_wp3.csv.gz")

# All other paths use OUTPUT_DIR (which switches automatically)
FEATURE_NAMES_PATH = os.path.join(OUTPUT_DIR, "clustering_features.txt")
D_GOWER_PATH = os.path.join(OUTPUT_DIR, "D_gower.csv.gz")
X_PCA_PATH = os.path.join(OUTPUT_DIR, "X_pca.csv.gz")
OPTIMAL_K_RESULTS_PATH = os.path.join(OUTPUT_DIR, "optimal_k_results.csv")
OPTIMAL_K_SUMMARY_PATH = os.path.join(OUTPUT_DIR, "optimal_k_summary.csv")
OPTICS_TUNING_RESULTS_PATH = os.path.join(OUTPUT_DIR, "optics_tuning_results.csv")
VALIDATION_RESULTS_PATH = os.path.join(OUTPUT_DIR, "validation_results.csv")
VISUALIZATION_SUMMARY_PATH = os.path.join(OUTPUT_DIR, "visualization_summary.csv")

# path to variance of means table
VARIANCE_OF_MEANS_PATH = os.path.join(OUTPUT_DIR, "variance_of_means.csv")
# path to membership features (non-encoded)
MEMBERSHIP_PATH = os.path.join(OUTPUT_DIR, "membership_features.csv.gz")
# path to one-hot encoded membership features
ENCODED_MEMBERSHIP_PATH = os.path.join(OUTPUT_DIR, "membership_features_encoded.csv.gz")
# step 09 OVR outputs
#OVR_GRIDSEARCH_CV_RESULTS_PATH = os.path.join(OUTPUT_DIR, "ovr_gridsearch_cv_results.csv")
OVR_FEATURE_IMPORTANCE_ALL_PATH = os.path.join(OUTPUT_DIR, "ovr_feature_importance_all.csv")
# Plots directory
PLOTS_DIR = os.path.join(OUTPUT_DIR, "plots")

def labels_path(config_name: str) -> str:
    return os.path.join(OUTPUT_DIR, f"labels_{config_name}.csv.gz")


def umap_path(config_name: str) -> str:
    return os.path.join(PLOTS_DIR, f"umap_{config_name}.png")


def heatmap_path(config_name: str) -> str:
    return os.path.join(PLOTS_DIR, f"heatmap_{config_name}.png")


# -------------------
# Column types
# -------------------

HS_COLS = [
    "ed_attendances_pre_0_3m",
    "ed_attendances_pre_3_6m",
    "ed_attendances_pre_6_9m",
    "ed_attendances_pre_9_12m",
    "primary_care_attendances_pre_0_3m",
    "primary_care_attendances_pre_3_6m",
    "primary_care_attendances_pre_6_9m",
    "primary_care_attendances_pre_9_12m",
    "hospital_admissions_pre_0_3m",
    "hospital_admissions_pre_3_6m",
    "hospital_admissions_pre_6_9m",
    "hospital_admissions_pre_9_12m",
    "prescriptions_pre_0_3m",
    "prescriptions_pre_3_6m",
    "prescriptions_pre_6_9m",
    "prescriptions_pre_9_12m",
]

REVIEW_COLS = [
    "asthma_review_date",
    "copd_review_date",
    "med_review_date",
]

# -------------------
# Membership features configuration (for build_membership_features)
# -------------------
# Date columns to parse from raw data
MEMBERSHIP_DATE_COLS = [
    "patient_index_date", "birth_date",
    "first_copd_date", "tmp_copd_date_primary", "tmp_copd_date_sus",
    "hypertension_date_primary", "hypertension_date_sus", "hypertension_date_med",
    "af_date_primary", "af_date_sus",
    "ihd_date_primary", "ihd_date_sus",
    "ckd_date_primary", "ckd_date_sus",
    "obesity_primary_date", "obesity_sus_date",
    "bmi_date",
    "learndis",
    "hf_diagnosis_primary_date", "hf_diagnosis_emerg_date", 
    "hf_diagnosis_ec_date", "hf_diagnosis_apc_date", "hf_diagnosis_date"
]

# Age binning configuration
AGE_BINS = [0, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 120]
AGE_LABELS = ['<45', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', 
              '75-79', '80-84', '85-89', '90-94', '95-99', '100+']

# Household size binning configuration
HOUSEHOLD_BINS = [0, 1, 2, np.inf]
HOUSEHOLD_LABELS = ["1", "2", ">=3"]

# Categorical columns to preserve as-is
CATEGORICAL_COLS = ["sex", "ethnicity_cat", "imd_quintile", "region", 
                    "rural_urban", "cat_diabetes", "smoking","cat_household_size"]

# Date-based conditions: map condition name to its date columns
DATE_BASED_CONDITIONS = {
    "copd": ["first_copd_date", "tmp_copd_date_primary", "tmp_copd_date_sus"],
    "hypertension": ["hypertension_date_primary", "hypertension_date_sus", "hypertension_date_med"],
    "af": ["af_date_primary", "af_date_sus"],
    "ihd": ["ihd_date_primary", "ihd_date_sus"],
    "ckd": ["ckd_date_primary", "ckd_date_sus"],
    "learndis": ["learndis"],
}

# Obesity date columns
OBESITY_DATE_COLS = ["obesity_primary_date", "obesity_sus_date"]

# Obesity BMI threshold
OBESITY_BMI_THRESHOLD = 30

# Long-term condition columns (for multi-morbidity calculation)
LTC_COLS = ["copd_preexisting", "copd_new", "hypertension_preexisting", "hypertension_new", 
            "obesity", "af_preexisting", "af_new", "ihd_preexisting", "ihd_new", 
            "ckd_preexisting", "ckd_new", "has_diabetes"]

# Under-served populations columns
UNDERSERVED_COLS = ["carehome_at_index", "housebound", "smi", "homeless", 
                    "substance_abuse", "migrant", "non_english_speaking"]

# Time window for defining pre-existing vs new conditions (in days)
CONDITION_TIME_WINDOW_DAYS = 365

# Diabetes definition
DIABETES_UNLIKELY_VALUE = "DM unlikely"

# Diagnosis location columns
DIAGNOSIS_PRIMARY_COL = "hf_diagnosis_primary_date"
DIAGNOSIS_HOSPITAL_COLS = ["hf_diagnosis_emerg_date", "hf_diagnosis_ec_date", "hf_diagnosis_apc_date"]
