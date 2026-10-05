# Constants, paths and shell fragments are defined in common.smk.
# User-editable settings (project specific) are in config.yaml.
include: "common.smk"

# Constrain {year} wildcard to 4 digits to avoid ambiguous matching
wildcard_constraints:
    year = r"\d{4}"

rule all:
    input:
        "output/dataset_consort.csv",
        "output/dataset_wp1_common.csv",
        expand("output/dataset_wp1_{year}.csv", year=COHORT_YEARS),
        "output/dataset_wp2_1.csv",
        "output/dataset_wp2_2.csv",
        "output/dataset_wp3.csv",
        "output/dataset_wp4.csv",

# ── ehrQL dataset generation ──────────────────────────────────────────────────

rule generate_dataset_consort:
    input:  _db_input
    output: "output/dataset_consort.csv"
    params: script="analysis/dataset_definition/dataset_definition_consort.py"
    log:    "logs/generate_dataset_consort.log"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND + _LOG

rule generate_dataset_wp1_common:
    input:  _db_input
    output: "output/tmp_dataset_wp1_common.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp1_common.py"
    log:    "logs/generate_dataset_wp1_common.log"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND + _LOG

rule generate_dataset_wp1_time_dep:
    input:  _db_input
    output: "output/dataset_wp1_{year}.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp1_time_dep.py"
    log:    "logs/generate_dataset_wp1_{year}.log"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND
        + " -- --cohort_index_date {wildcards.year}-" + INDEX_MONTH_DAY + _LOG

rule generate_dataset_wp2_1:
    input:  _db_input
    output: "output/tmp_dataset_wp2_1.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp2_1.py"
    log:    "logs/generate_dataset_wp2_1.log"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND + _LOG

rule generate_dataset_wp2_2:
    input:  _db_input
    output: "output/tmp_dataset_wp2_2.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp2_2.py"
    log:    "logs/generate_dataset_wp2_2.log"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND + _LOG

rule generate_dataset_wp3:
    input:  _db_input
    output: "output/tmp_dataset_wp3.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp3.py"
    log:    "logs/generate_dataset_wp3.log"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND + _LOG

rule generate_dataset_wp4:
    input:  _db_input
    output: "output/tmp_dataset_wp4.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp4.py"
    log:    "logs/generate_dataset_wp4.log"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND + _LOG

# ── Diabetes algorithm post-processing (R) ────────────────────────────────────

rule diabetes_algo_wp1:
    input:  "output/tmp_dataset_wp1_common.csv"
    output: "output/dataset_wp1_common.csv"
    shell:
        _DIABETES_ALGO + " --df_input tmp_dataset_wp1_common.csv --df_output dataset_wp1_common.csv"

rule diabetes_algo_wp2_1:
    input:  "output/tmp_dataset_wp2_1.csv"
    output: "output/dataset_wp2_1.csv"
    shell:
        _DIABETES_ALGO + " --df_input tmp_dataset_wp2_1.csv --df_output dataset_wp2_1.csv"

rule diabetes_algo_wp2_2:
    input:  "output/tmp_dataset_wp2_2.csv"
    output: "output/dataset_wp2_2.csv"
    shell:
        _DIABETES_ALGO + " --df_input tmp_dataset_wp2_2.csv --df_output dataset_wp2_2.csv"

rule diabetes_algo_wp3:
    input:  "output/tmp_dataset_wp3.csv"
    output: "output/dataset_wp3.csv"
    shell:
        _DIABETES_ALGO + " --df_input tmp_dataset_wp3.csv --df_output dataset_wp3.csv"

rule diabetes_algo_wp4:
    input:  "output/tmp_dataset_wp4.csv"
    output: "output/dataset_wp4.csv"
    shell:
        _DIABETES_ALGO + " --df_input tmp_dataset_wp4.csv --df_output dataset_wp4.csv"
