# numpy for random seed - and set random seed
#import numpy as np 
#np.random.seed(209109) # random seed

#######################################################################################
# IMPORT
#######################################################################################
## Import ehrQL functions
from ehrql import (
    create_dataset,
    minimum_of,
    case,
    when
)

## Import TPP tables
from ehrql.tables.tpp import (
    clinical_events,
    patients,
    ethnicity_from_sus
)

## Import all codelists from codelists.py
from codelists import *

## Import the variable helper functions 
from variable_helper_functions import *

#######################################################################################
# DEFINE or IMPORT the index date
#######################################################################################
index_date = "2024-12-10"

#######################################################################################
# INITIALISE the dataset and set the dummy dataset size
#######################################################################################
dataset = create_dataset()
dataset.configure_dummy_data(population_size=5000)
dataset.define_population(patients.exists_for_patient())

#######################################################################################
# DEFINE necessary variables to build algo
#######################################################################################
## See https://github.com/opensafely/post-covid-diabetes/blob/main/analysis/common_variables.py

## Demographics
dataset.birth_date = patients.date_of_birth

# Ethnicity in 6 categories
ethnicity_snomed = (
    clinical_events.where(clinical_events.snomedct_code.is_in(ethnicity_codes))
    .sort_by(clinical_events.date)
    .last_for_patient()
    .snomedct_code.to_category(ethnicity_codes)
)

ethnicity_sus = ethnicity_from_sus.code

dataset.ethnicity_cat = case(
  when((ethnicity_snomed == "1") | ((ethnicity_snomed.is_null()) & (ethnicity_sus.is_in(["A", "B", "C"])))).then("White"),
  when((ethnicity_snomed == "2") | ((ethnicity_snomed.is_null()) & (ethnicity_sus.is_in(["D", "E", "F", "G"])))).then("Mixed"),
  when((ethnicity_snomed == "3") | ((ethnicity_snomed.is_null()) & (ethnicity_sus.is_in(["H", "J", "K", "L"])))).then("Asian"),
  when((ethnicity_snomed == "4") | ((ethnicity_snomed.is_null()) & (ethnicity_sus.is_in(["M", "N", "P"])))).then("Black"),
  when((ethnicity_snomed == "5") | ((ethnicity_snomed.is_null()) & (ethnicity_sus.is_in(["R", "S"])))).then("Other"),
  otherwise="Unknown", 
)


## Type 1 Diabetes 
# First date from primary+secondary, but also primary care date separately for diabetes algo
dataset.tmp_t1dm_primarycare_date = first_matching_event_clinical_ctv3_before(diabetes_type1_ctv3, index_date).date
dataset.t1dm_date = minimum_of(
    (first_matching_event_clinical_ctv3_before(diabetes_type1_ctv3, index_date).date),
    (first_matching_event_apc_before(diabetes_type1_icd10, index_date).admission_date)
)
# Count codes (individually and together, for diabetes algo)
tmp_t1dm_primarycare_count = count_matching_event_clinical_ctv3_before(diabetes_type1_ctv3, index_date)
tmp_t1dm_hes_count = count_matching_event_apc_before(diabetes_type1_icd10, index_date)
dataset.tmp_t1dm_count_num = tmp_t1dm_primarycare_count + tmp_t1dm_hes_count

## Type 2 Diabetes
# First date from primary+secondary, but also primary care date separately for diabetes algo)
dataset.tmp_t2dm_primarycare_date = first_matching_event_clinical_ctv3_before(diabetes_type2_ctv3, index_date).date
dataset.t2dm_date = minimum_of(
    (first_matching_event_clinical_ctv3_before(diabetes_type2_ctv3, index_date).date),
    (first_matching_event_apc_before(diabetes_type2_icd10, index_date).admission_date)
)
# Count codes (individually and together, for diabetes algo)
tmp_t2dm_primarycare_count = count_matching_event_clinical_ctv3_before(diabetes_type2_ctv3, index_date)
tmp_t2dm_hes_count = count_matching_event_apc_before(diabetes_type2_icd10, index_date)
dataset.tmp_t2dm_count_num = tmp_t2dm_primarycare_count + tmp_t2dm_hes_count

## Diabetes unspecified/other
# First date
dataset.otherdm_date = first_matching_event_clinical_ctv3_before(diabetes_other_ctv3, index_date).date
# Count codes
dataset.tmp_otherdm_count_num = count_matching_event_clinical_ctv3_before(diabetes_other_ctv3, index_date)

## Gestational diabetes
# First date from primary+secondary
dataset.gestationaldm_date = minimum_of(
    (first_matching_event_clinical_ctv3_before(diabetes_gestational_ctv3, index_date).date),
    (first_matching_event_apc_before(diabetes_gestational_icd10, index_date).admission_date)
)

## Diabetes diagnostic codes
# First date
dataset.tmp_poccdm_date = first_matching_event_clinical_ctv3_before(diabetes_diagnostic_ctv3, index_date).date
# Count codes
dataset.tmp_poccdm_primarycare_count_num = count_matching_event_clinical_ctv3_before(diabetes_diagnostic_ctv3, index_date)

### Other variables needed to define diabetes
## HbA1c
# Maximum HbA1c measure (in the same period)
dataset.tmp_max_hba1c_mmol_mol_num = (
  clinical_events.where(
    clinical_events.snomedct_code.is_in(hba1c_snomed))
    .where(clinical_events.date.is_on_or_before(index_date))
    .numeric_value.maximum_for_patient()
)
# Date of first maximum HbA1c measure
dataset.tmp_max_hba1c_date = ( 
  clinical_events.where(
    clinical_events.snomedct_code.is_in(hba1c_snomed))
    .where(clinical_events.date.is_on_or_before(index_date)) # this line of code probably not needed again
    .where(clinical_events.numeric_value == dataset.tmp_max_hba1c_mmol_mol_num)
    .sort_by(clinical_events.date)
    .first_for_patient() 
    .date
)

## Diabetes drugs
# First dates
dataset.tmp_insulin_dmd_date = first_matching_med_dmd_before(insulin_dmd, index_date).date
dataset.tmp_antidiabetic_drugs_dmd_date = first_matching_med_dmd_before(antidiabetic_drugs_dmd, index_date).date
dataset.tmp_nonmetform_drugs_dmd_date = first_matching_med_dmd_before(non_metformin_dmd, index_date).date

# Identify first date (in same period) that any diabetes medication was prescribed
dataset.tmp_diabetes_medication_date = minimum_of(dataset.tmp_insulin_dmd_date, dataset.tmp_antidiabetic_drugs_dmd_date)

# Identify first date (in same period) that any diabetes diagnosis codes were recorded
dataset.tmp_first_diabetes_diag_date = minimum_of(
  dataset.t1dm_date, 
  dataset.t2dm_date,
  dataset.otherdm_date,
  dataset.gestationaldm_date,
  dataset.tmp_poccdm_date,
  dataset.tmp_diabetes_medication_date,
  dataset.tmp_nonmetform_drugs_dmd_date
)
