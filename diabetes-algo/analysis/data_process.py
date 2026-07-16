"""
Python equivalent of data_process.R (diabetes-algo v0.0.13).

Reads a CSV dataset, applies the diabetes classification algorithm, and writes
the result back as CSV. Accepts the same command-line arguments as the R script.
"""

import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "functions"))
from fn_diabetes_algorithm import fn_diabetes_algorithm

print("diabetes-algo version: v0.0.13 (Python)")

# ── Argument parsing ──────────────────────────────────────────────────────────
print("Import libraries")

parser = argparse.ArgumentParser(usage="diabetes-algo:[version] [options]")
parser.add_argument("--df_input",  default="input.csv")
parser.add_argument("--df_output", default="data_processed.csv")
parser.add_argument("--input_dir",  default="output")
parser.add_argument("--output_dir", default="output")
parser.add_argument("--remove_helper", type=lambda x: x.lower() == "true", default=True)
parser.add_argument("--birth_date",     default="birth_date")
parser.add_argument("--ethnicity_cat",  default="ethnicity_cat")
parser.add_argument("--t1dm_date",      default="t1dm_date")
parser.add_argument("--tmp_t1dm_primarycare_date", default="tmp_t1dm_primarycare_date")
parser.add_argument("--tmp_t1dm_count_num",         default="tmp_t1dm_count_num")
parser.add_argument("--t2dm_date",      default="t2dm_date")
parser.add_argument("--tmp_t2dm_primarycare_date", default="tmp_t2dm_primarycare_date")
parser.add_argument("--tmp_t2dm_count_num",         default="tmp_t2dm_count_num")
parser.add_argument("--otherdm_date",   default="otherdm_date")
parser.add_argument("--tmp_otherdm_count_num",      default="tmp_otherdm_count_num")
parser.add_argument("--gestationaldm_date",         default="gestationaldm_date")
parser.add_argument("--tmp_poccdm_date",            default="tmp_poccdm_date")
parser.add_argument("--tmp_poccdm_primarycare_count_num", default="tmp_poccdm_primarycare_count_num")
parser.add_argument("--tmp_max_hba1c_mmol_mol_num", default="tmp_max_hba1c_mmol_mol_num")
parser.add_argument("--tmp_max_hba1c_date",         default="tmp_max_hba1c_date")
parser.add_argument("--tmp_insulin_dmd_date",       default="tmp_insulin_dmd_date")
parser.add_argument("--tmp_antidiabetic_drugs_dmd_date", default="tmp_antidiabetic_drugs_dmd_date")
parser.add_argument("--tmp_nonmetform_drugs_dmd_date",   default="tmp_nonmetform_drugs_dmd_date")
parser.add_argument("--tmp_diabetes_medication_date",    default="tmp_diabetes_medication_date")
parser.add_argument("--tmp_first_diabetes_diag_date",    default="tmp_first_diabetes_diag_date")
parser.add_argument("--gestationaldm_date_sources",
                    default="gestationaldm_date")
parser.add_argument("--t1dm_date_sources",
                    default="t2dm_date,t1dm_date,otherdm_date,tmp_diabetes_medication_date")
parser.add_argument("--t2dm_date_sources",
                    default="t2dm_date,t1dm_date,otherdm_date,tmp_diabetes_medication_date")
parser.add_argument("--otherdm_date_sources",
                    default="t2dm_date,t1dm_date,otherdm_date,tmp_diabetes_medication_date,tmp_max_hba1c_date,tmp_poccdm_date")
parser.add_argument("--config", default="")

opt = parser.parse_args()

# Apply JSON config overrides if provided
if opt.config:
    overrides = json.loads(opt.config)
    for k, v in overrides.items():
        if hasattr(opt, k):
            setattr(opt, k, v)

# ── Load data ─────────────────────────────────────────────────────────────────
print("Load data")
input_path = os.path.join(opt.input_dir, opt.df_input)
if opt.df_input.endswith(".csv.gz") or opt.df_input.endswith(".csv"):
    data = pd.read_csv(input_path, dtype=str, keep_default_na=False, na_values=[""])
elif opt.df_input.endswith(".rds") or opt.df_input.endswith(".feather") or opt.df_input.endswith(".arrow"):
    raise NotImplementedError(f"Input format not supported: {opt.df_input}. Use CSV.")
else:
    raise ValueError(f"Unrecognised input format: {opt.df_input}")

print(data.describe(include="all"))

# ── Column mapping ────────────────────────────────────────────────────────────
print("Map user variable names")
column_mapping = {
    "birth_date":                        opt.birth_date,
    "ethnicity_cat":                     opt.ethnicity_cat,
    "tmp_t1dm_primarycare_date":         opt.tmp_t1dm_primarycare_date,
    "t1dm_date":                         opt.t1dm_date,
    "tmp_t1dm_count_num":                opt.tmp_t1dm_count_num,
    "tmp_t2dm_primarycare_date":         opt.tmp_t2dm_primarycare_date,
    "t2dm_date":                         opt.t2dm_date,
    "tmp_t2dm_count_num":                opt.tmp_t2dm_count_num,
    "otherdm_date":                      opt.otherdm_date,
    "tmp_otherdm_count_num":             opt.tmp_otherdm_count_num,
    "gestationaldm_date":                opt.gestationaldm_date,
    "tmp_poccdm_date":                   opt.tmp_poccdm_date,
    "tmp_poccdm_primarycare_count_num":  opt.tmp_poccdm_primarycare_count_num,
    "tmp_max_hba1c_mmol_mol_num":        opt.tmp_max_hba1c_mmol_mol_num,
    "tmp_max_hba1c_date":                opt.tmp_max_hba1c_date,
    "tmp_insulin_dmd_date":              opt.tmp_insulin_dmd_date,
    "tmp_antidiabetic_drugs_dmd_date":   opt.tmp_antidiabetic_drugs_dmd_date,
    "tmp_nonmetform_drugs_dmd_date":     opt.tmp_nonmetform_drugs_dmd_date,
    "tmp_diabetes_medication_date":      opt.tmp_diabetes_medication_date,
    "tmp_first_diabetes_diag_date":      opt.tmp_first_diabetes_diag_date,
}

print("Double-check if all required variables are present in user data")
missing = set(column_mapping.values()) - set(data.columns)
if missing:
    sys.exit(f"The following columns are missing in the data: {', '.join(sorted(missing))}")

print("Extract core data and patient_id")
# dict.fromkeys preserves order while removing any duplicate column references
cols_needed = list(dict.fromkeys(["patient_id"] + list(column_mapping.values())))
core = data[cols_needed].copy()
# Drop any duplicate columns that may exist in the CSV
core = core.loc[:, ~core.columns.duplicated(keep="first")]

# ── Parse diagnosis date sources ──────────────────────────────────────────────
diagnosis_date_sources = {
    "gestationaldm": opt.gestationaldm_date_sources.split(","),
    "t1dm":          opt.t1dm_date_sources.split(","),
    "t2dm":          opt.t2dm_date_sources.split(","),
    "otherdm":       opt.otherdm_date_sources.split(","),
}

# ── Validation ────────────────────────────────────────────────────────────────
print("Check the date variables")
import re as _re
_date_pat = _re.compile(r'^\d{4}-\d{2}-\d{2}$')
date_cols = [c for c in core.columns if c.endswith("_date")]
for i, col in enumerate(core.columns):
    if not col.endswith("_date"):
        continue
    series   = core.iloc[:, i]
    non_null = series.replace("", pd.NA).dropna().astype(str)
    bad      = non_null[~non_null.str.match(_date_pat)]
    if not bad.empty:
        sys.exit(f"Column '{col}' contains invalid dates: {bad.unique()[:5]}")
print("validation passed: all date values are coded as dates in the format %Y-%m-%d")

print("Check the numeric variables")
num_cols = [c for c in core.columns if c.endswith("_num")]
for i, col in enumerate(core.columns):
    if not col.endswith("_num"):
        continue
    series   = core.iloc[:, i]
    non_null = series.replace("", pd.NA).dropna()
    bad      = non_null[pd.to_numeric(non_null, errors="coerce").isna()]
    if not bad.empty:
        sys.exit(f"Column '{col}' contains invalid numeric values: {bad.unique()[:5]}")
print("validation passed: all numeric values are coded as numeric")

print("Check the ethnicity variable")
valid_eth  = {"White", "Mixed", "Asian", "Black", "Unknown", "Other"}
eth_col    = column_mapping["ethnicity_cat"]
bad_eth    = core[eth_col][~core[eth_col].isin(valid_eth) | core[eth_col].isna()]
if not bad_eth.empty:
    sys.exit(
        f"'ethnicity_cat' contains invalid values: {bad_eth.unique()[:5]}. "
        f"Valid values: {', '.join(sorted(valid_eth))}. NA not allowed."
    )
print("'ethnicity_cat' validation passed")

# ── Reformat ──────────────────────────────────────────────────────────────────
print("Reformat the imported core variables")
for col in date_cols:
    core[col] = pd.to_datetime(core[col].replace("", pd.NA), format="%Y-%m-%d", errors="coerce")
for col in num_cols:
    core[col] = pd.to_numeric(core[col].replace("", pd.NA), errors="coerce")

# ── Rename user columns to standardised names before calling algorithm ─────────
print("DEBUG core columns:", sorted(core.columns.tolist()))
rename_map = {v: k for k, v in column_mapping.items() if v != k and v in core.columns}
print("DEBUG rename_map:", rename_map)
core = core.rename(columns=rename_map)
print("DEBUG core columns after rename:", sorted(core.columns.tolist()))

# ── Run algorithm ─────────────────────────────────────────────────────────────
print("Apply the diabetes algorithm")
core = fn_diabetes_algorithm(core, column_mapping, diagnosis_date_sources)

# ── Remove helper columns ─────────────────────────────────────────────────────
if opt.remove_helper:
    print("Remove helper variables")
    drop = [c for c in core.columns if "tmp" in c or "step" in c]
    core = core.drop(columns=drop)

# ── Merge back to original data ───────────────────────────────────────────────
non_core = data.drop(columns=[c for c in column_mapping.values() if c in data.columns])
data_processed = non_core.merge(core, on="patient_id", how="left")

# ── Save output ───────────────────────────────────────────────────────────────
print("Save output")
output_path = os.path.join(opt.output_dir, opt.df_output)
data_processed.to_csv(output_path, index=False, na_rep="", date_format="%Y-%m-%d")
print(f"Written to {output_path}")
