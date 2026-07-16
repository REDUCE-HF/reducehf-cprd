
<!-- README.md is generated from README.Rmd. 
Please edit that file and rerun in R `rmarkdown::render('README.Rmd')` or run `just render` in a Terminal -->

# diabetes-algo

This is the code and configuration for `diabetes-algo`, which is an R
reusable action for the OpenSAFELY framework.

The action:

  - Loads and double-checks 21 input variables
  - Runs the diabetes adjudication algorithm (Figure 1 below) to define
    the following Diabetes types:
  - Gestational, Type 2, Type 1, Other, Unlikely (variable
    ‘cat\_diabetes’: GDM, T2DM, T1DM, DM\_other, DM\_unlikely)
  - Besides the categorical type variable, it provides the diagnosis
    date for each type. The default choice of diagnosis date sources for
    each type is:
  - gestationaldm\_date: First date from GDM clinical codes
  - t2dm\_date: First date from T1DM clinical codes, T2DM clinical
    codes, unspecific diabetes clinical codes, and diabetes medication
    codes
  - t1dm\_date: First date from T1DM clinical codes, T2DM clinical
    codes, unspecific diabetes clinical codes, and diabetes medication
    codes
  - otherdm\_date: First date from T1DM clinical codes, T2DM clinical
    codes, unspecific diabetes clinical codes, diabetes medication
    codes, and diabetes-specific procedure codes
  - Version 0.0.10 allows users to change the above-mentioned default
    choice of diagnosis date sources and define their own sources, see
    args gestationaldm\_date\_sources, t1dm\_date\_sources,
    t2dm\_date\_sources, otherdm\_date\_sources

## Usage

The input variables/arguments/options to the action are specified using
the flags style (i.e., `--argname=argvalue`). Below, you find a detailed
description of each input variable including examples for codelists to
use when defining these variables in the OpenSAFELY dataset definition.
IMPORTANT: The used codelists here are just examples. Users have to
double-check these. Important is to adhere to the specified source
(primary or secondary care) where these codelists should come from.
Copy-paste the argument names into your yaml and map them to your input
variable names. An example of a dataset definition that defines each 21
input variables, find
[here](https://github.com/alainamstutz/diabetes-algo/blob/main/analysis/dataset_definition.py).

    Usage: diabetes-algo:[version] [options]
    
    
    Options:
    --df_input=FILENAME.CSV
    Input dataset. csv, csv.gz, rds, arrow, or a feather file. Assumed to be within
    the directory 'output' [default input.csv]
    
    --remove_helper=TRUE/FALSE
    Logical, indicating whether all helper variables (tmp_ and step_) are removed
    [default TRUE]
    
    --birth_date=YYYY-MM-DD
    Birth date [default birth_date]
    
    --ethnicity_cat=ETHNICITY_VARNAME
    Ethnicity, in 6 categories, coded as follows: White, Mixed, Asian, Black,
    Other, Unknown. Guidance: https://pubmed.ncbi.nlm.nih.gov/38987774/ [default
    ethnicity_cat]
    
    --t1dm_date=YYYY-MM-DD
    First type 1 DM diagnosis date, from both primary (e.g.
    https://www.opencodelists.org/codelist/user/hjforbes/type-1-diabetes/674fbd7a/)
    and secondary (e.g.
    https://www.opencodelists.org/codelist/user/alainamstutz/type-1-diabetes-secondary-care/5eab6d93/)
    care [default t1dm_date]
    
    --tmp_t1dm_primarycare_date=YYYY-MM-DD
    First type 1 DM diagnosis date, from primary care only [default
    tmp_t1dm_primarycare_date]
    
    --tmp_t1dm_count_num=T1DM_COUNT_VARNAME
    Count of all recorded Type 1 DM diagnosis codes, from both primary and
    secondary care [default tmp_t1dm_count_num]
    
    --t2dm_date=YYYY-MM-DD
    First type 2 DM diagnosis date, from both primary (e.g.
    https://www.opencodelists.org/codelist/user/hjforbes/type-2-diabetes/3530d710/)
    and secondary (e.g.
    https://www.opencodelists.org/codelist/user/alainamstutz/type-2-diabetes-secondary-care/77bae0c8/)
    care [default t2dm_date]
    
    --tmp_t2dm_primarycare_date=YYYY-MM-DD
    First type 2 DM diagnosis date, from primary care only [default
    tmp_t2dm_primarycare_date]
    
    --tmp_t2dm_count_num=T2DM_COUNT_VARNAME
    Count of all recorded Type 2 DM diagnosis codes, from both primary and
    secondary care [default tmp_t2dm_count_num]
    
    --otherdm_date=YYYY-MM-DD
    First other/unspecified DM diagnosis date, from primary care (e.g.
    https://www.opencodelists.org/codelist/user/hjforbes/other-or-nonspecific-diabetes/0311f0a6/)
    only [default otherdm_date]
    
    --tmp_otherdm_count_num=OTHERDM_COUNT_VARNAME
    Count of all recorded other/unspecified DM diagnosis codes, from primary care
    only [default tmp_otherdm_count_num]
    
    --gestationaldm_date=YYYY-MM-DD
    First gestational DM diagnosis date, from both primary (e.g.
    https://www.opencodelists.org/codelist/user/hjforbes/gestational-diabetes/1ed423d1/)
    and secondary (e.g.
    https://www.opencodelists.org/codelist/user/alainamstutz/gestational-diabetes-icd10-bristol/474e7a09/)
    care [default gestationaldm_date]
    
    --tmp_poccdm_date=YYYY-MM-DD
    First Non-diagnostic DM code date, from primary care (e.g.
    https://www.opencodelists.org/codelist/user/hjforbes/nondiagnostic-diabetes-codes/50f30a3b/)
    only [default tmp_poccdm_date]
    
    --tmp_poccdm_primarycare_count_num=NON_DIAG_DM_CODE_COUNT_VARNAME
    Count of all recorded Non-diagnostic DM codes, from primary care only [default
    tmp_poccdm_primarycare_count_num]
    
    --tmp_max_hba1c_mmol_mol_num=MAX_HBA1C_VARNAME
    Maximum HbA1c value recorded in query period, in mmol/mol (e.g.
    https://www.opencodelists.org/codelist/opensafely/glycated-haemoglobin-hba1c-tests-numerical-value/5134e926/)
    from primary care only [default tmp_max_hba1c_mmol_mol_num]
    
    --tmp_max_hba1c_date=YYYY-MM-DD
    First maximum HbA1c value date, from primary care only [default
    tmp_max_hba1c_date]
    
    --tmp_insulin_dmd_date=YYYY-MM-DD
    First insulin drug date variable, from primary care (e.g.
    https://www.opencodelists.org/codelist/opensafely/insulin-medication/2020-04-26/)
    only [default tmp_insulin_dmd_date]
    
    --tmp_antidiabetic_drugs_dmd_date=YYYY-MM-DD
    First antidiabetic drug (any, except insulin) date, from primary care (e.g.
    https://www.opencodelists.org/codelist/opensafely/antidiabetic-drugs/2020-07-16/)
    only [default tmp_antidiabetic_drugs_dmd_date]
    
    --tmp_nonmetform_drugs_dmd_date=YYYY-MM-DD
    First antidiabetic drug (any, except insulin and metformin) date, from primary
    care (e.g.
    https://www.opencodelists.org/codelist/user/alainamstutz/non-metformin-oral-antidiabetic/0641be78/)
    only [default tmp_nonmetform_drugs_dmd_date]
    
    --tmp_diabetes_medication_date=YYYY-MM-DD
    First antidiabetic drug date, i.e. minimum of tmp_insulin_dmd_date and
    tmp_antidiabetic_drugs_dmd_date [default tmp_diabetes_medication_date]
    
    --tmp_first_diabetes_diag_date=YYYY-MM-DD
    First diabetes diagnosis date variable, i.e. minimum of t1dm_date, t2dm_date,
    otherdm_date, gestationaldm_date, tmp_poccdm_date,
    tmp_nonmetform_drugs_dmd_date, and tmp_diabetes_medication_date [default
    tmp_first_diabetes_diag_date]
    
    --gestationaldm_date_sources=DIAGNOSIS_DATE_SOURCES
    Choose which dates are the source to define the baseline date for Gestational
    DM (minimum of these). Options: t2dm_date, t1dm_date, gestationaldm_date,
    otherdm_date, tmp_diabetes_medication_date, tmp_max_hba1c_date (If >= 47.5
    mmol/mol, see step 7), tmp_poccdm_date (If > 5 process codes, see step 7)
    [default gestationaldm_date]
    
    --t1dm_date_sources=DIAGNOSIS_DATE_SOURCES
    Choose which dates are the source to define the baseline date for Type 1 DM
    (minimum of these). Options: t2dm_date, t1dm_date, gestationaldm_date,
    otherdm_date, tmp_diabetes_medication_date, tmp_max_hba1c_date (If >= 47.5
    mmol/mol, see step 7), tmp_poccdm_date (If > 5 process codes, see step 7)
    [default t2dm_date,t1dm_date,otherdm_date,tmp_diabetes_medication_date]
    
    --t2dm_date_sources=DIAGNOSIS_DATE_SOURCES
    Choose which dates are the source to define the baseline date for Type 2 DM
    (minimum of these). Options: t2dm_date, t1dm_date, gestationaldm_date,
    otherdm_date, tmp_diabetes_medication_date, tmp_max_hba1c_date (If >= 47.5
    mmol/mol, see step 7), tmp_poccdm_date (If > 5 process codes, see step 7)
    [default t2dm_date,t1dm_date,otherdm_date,tmp_diabetes_medication_date]
    
    --otherdm_date_sources=DIAGNOSIS_DATE_SOURCES
    Choose which dates are the source to define the baseline date for Other DM
    (minimum of these). Options: t2dm_date, t1dm_date, gestationaldm_date,
    otherdm_date, tmp_diabetes_medication_date, tmp_max_hba1c_date (If >= 47.5
    mmol/mol, see step 7), tmp_poccdm_date (If > 5 process codes, see step 7)
    [default
    t2dm_date,t1dm_date,otherdm_date,tmp_diabetes_medication_date,tmp_max_hba1c_date,tmp_poccdm_date]
    
    --df_output=FILENAME.CSV.GZ
    Output dataset. csv.gz or rds file. This is assumed to be added to the
    directory 'output' [default data_processed.csv.gz]
    
    --config=
    Config parsed from the YAML
    
    -h, --help
    Show this help message and exit

## Diabetes Adjudication Algorithm Flowchart

<div class="figure">

<img src="diabetes-algo_fig.png" alt="Flowchart of the Diabetes adjudication algorithm" width="720" />

<p class="caption">

Figure 1.

</p>

</div>

This action can be specified in the `project.yaml` with its options at
their default values as follows, where you should replace `[version]`
with the latest tag from
[here](https://github.com/opensafely-actions/diabetes-algo/tags), e.g.,
`v0.0.1`. Note that no space is allowed between `diabetes-algo:` and
`[version]`. This action can be run specifying input arguments as
follows (in YAML “\>” indicates to treat the subsequent nested lines as
a single line).

``` yaml
generate_dataset:
    run: ehrql:v1 generate-dataset analysis/dataset_definition.py --output output/input.arrow
    outputs:
      highly_sensitive:
        dataset: output/input.arrow

diabetes_algo:
  run: >
    diabetes-algo:[version]
      --birth_date=your_dob_date_variable
      --tmp_t1dm_primarycare_date=your_t1dm_from_primcare_date_variable
      --tmp_max_hba1c_mmol_mol_num=your_max_hba1c_num_variable
      --## more arguments
      --df_output=data_processed.csv.gz #or data_processed.rds
  needs:
  - generate_dataset
  outputs:
    highly_sensitive:
      csv.gz: output/data_processed.csv.gz #or data_processed.rds
```

Alternatively, the input arguments can also be specified using a
`config:` key in the YAML as follows. Input arguments specified in the
config overwrite those specified at the command line.

``` yaml
generate_dataset:
    run: ehrql:v1 generate-dataset analysis/dataset_definition.py --output output/input.arrow
    outputs:
      highly_sensitive:
        dataset: output/input.arrow

diabetes_algo_via_config:
  run: diabetes-algo:[version]
  config:
      df_input: input.arrow
      birth_date: your_dob_date_variable
      tmp_t1dm_primarycare_date: your_t1dm_from_primcare_date_variable
      ## more arguments
      df_output: data_processed.csv.gz #or data_processed.rds
  needs:
  - generate_dataset
  outputs:
    highly_sensitive:
      csv.gz: output/data_processed.csv.gz #or data_processed.rds
```

For more information about reusable actions see
[here](https://docs.opensafely.org/actions-reusable/).

# About the OpenSAFELY framework

The OpenSAFELY framework is a Trusted Research Environment (TRE) for
electronic health records research in the NHS, with a focus on public
accountability and research quality.

Read more at [OpenSAFELY.org](https://opensafely.org).

# Licences

As standard, research projects have a MIT license.
