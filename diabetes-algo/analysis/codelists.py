#######################################################################################
# IMPORT
#######################################################################################
from ehrql import codelist_from_csv

#######################################################################################
# Codelists
#######################################################################################
## Ethnicity
ethnicity_codes = codelist_from_csv(
    "codelists/opensafely-ethnicity-snomed-0removed.csv",
    column="snomedcode",
    category_column="Grouping_6",
)

## DIABETES
# T1DM
diabetes_type1_ctv3 = codelist_from_csv("codelists/user-hjforbes-type-1-diabetes.csv",column="code")
diabetes_type1_icd10 = codelist_from_csv("codelists/user-alainamstutz-type-1-diabetes-secondary-care.csv",column="code")
# T2DM
diabetes_type2_ctv3 = codelist_from_csv("codelists/user-hjforbes-type-2-diabetes.csv",column="code")
diabetes_type2_icd10 = codelist_from_csv("codelists/user-alainamstutz-type-2-diabetes-secondary-care.csv",column="code")
# Other or non-specific diabetes
diabetes_other_ctv3 = codelist_from_csv("codelists/user-hjforbes-other-or-nonspecific-diabetes.csv",column="code")
# Gestational diabetes
diabetes_gestational_ctv3 = codelist_from_csv("codelists/user-hjforbes-gestational-diabetes.csv",column="code")
diabetes_gestational_icd10 = codelist_from_csv("codelists/user-alainamstutz-gestational-diabetes-icd10-bristol.csv",column="code")
# Non-diagnostic diabetes codes
diabetes_diagnostic_ctv3 = codelist_from_csv("codelists/user-hjforbes-nondiagnostic-diabetes-codes.csv",column="code")
# HbA1c
hba1c_snomed = codelist_from_csv("codelists/opensafely-glycated-haemoglobin-hba1c-tests-numerical-value.csv",column="code")
# Antidiabetic drugs
insulin_dmd = codelist_from_csv("codelists/opensafely-insulin-medication.csv",column="id")
antidiabetic_drugs_dmd = codelist_from_csv("codelists/opensafely-antidiabetic-drugs.csv",column="id")
non_metformin_dmd = codelist_from_csv("codelists/user-alainamstutz-non-metformin-oral-antidiabetic.csv",column="code")