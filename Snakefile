import os

# Derive absolute paths from this Snakefile's location so it can be invoked
# from any working directory (e.g. snakemake --snakefile reducehf/Snakefile).
_here          = os.path.dirname(os.path.abspath(workflow.snakefile))
EHRQL_PROJECT  = os.path.normpath(os.path.join(_here, "ehrql"))
SYNTHETIC_DB   = os.path.normpath(os.path.join(_here, "..", "synthetic_cprd_sqlite.db"))
DIABETES_ALGO  = os.path.normpath(os.path.join(_here, "diabetes-algo"))
_ABS_OUTPUT    = os.path.join(_here, "output")
BACKEND        = "cprd_backend_sqlite.CPRDBackend"

# One time-dependent dataset per cohort year
COHORT_YEARS = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]

# ── Database source ───────────────────────────────────────────────────────────
# Default: generate and use the local synthetic SQLite database.
# To use a different database pass its DSN on the command line:
#   snakemake --config dsn=sqlite:////absolute/path/to/other.db
# Any SQLAlchemy DSN accepted by CPRDBackend works (e.g. mssql+pyodbc://...).
# When a custom DSN is supplied the generate_synthetic_db rule is skipped.
_custom_dsn = config.get("dsn", None)
DSN         = _custom_dsn if _custom_dsn else f"sqlite:////{SYNTHETIC_DB}"
_db_input   = [] if _custom_dsn else [SYNTHETIC_DB]

# ── Shell fragments ───────────────────────────────────────────────────────────
_ENV   = "PYTHONPATH=. SQLITE_TMPDIR=output TMPDIR=output EHRQL_MAX_JOIN_COUNT=32 UV_PROJECT_ENVIRONMENT=/tmp/ehrql-venv"
_EHRQL = f"uv run --project {EHRQL_PROJECT} python -m ehrql generate-dataset"
_BKND  = f"--backend {BACKEND} --dsn '{DSN}'"

# Column renames needed because REDUCE-HF uses ctv3 suffix; diabetes-algo expects primarycare
_CTXV3 = (
    " --tmp_t1dm_primarycare_date tmp_t1dm_ctv3_date"
    " --tmp_t2dm_primarycare_date tmp_t2dm_ctv3_date"
    " --tmp_poccdm_primarycare_count_num tmp_poccdm_ctv3_count_num"
)
_RSCRIPT = (
    f"cd {DIABETES_ALGO} && Rscript analysis/data_process.R"
    f" --input_dir ../output --output_dir ../output"
    " --birth_date dob --ethnicity_cat ethnicity_cat"
    + _CTXV3
)

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


rule generate_dataset_consort:
    input:  _db_input
    output: "output/dataset_consort.csv"
    params: script="analysis/dataset_definition/dataset_definition_consort.py"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND


rule generate_dataset_wp1_common:
    input:  _db_input
    output: "output/tmp_dataset_wp1_common.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp1_common.py"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND


rule generate_dataset_wp1_time_dep:
    input:  _db_input
    output: "output/dataset_wp1_{year}.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp1_time_dep.py"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND
        + " -- --cohort_index_date {wildcards.year}-02-01"


rule generate_dataset_wp2_1:
    input:  _db_input
    output: "output/tmp_dataset_wp2_1.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp2_1.py"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND


rule generate_dataset_wp2_2:
    input:  _db_input
    output: "output/tmp_dataset_wp2_2.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp2_2.py"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND


rule generate_dataset_wp3:
    input:  _db_input
    output: "output/tmp_dataset_wp3.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp3.py"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND


rule generate_dataset_wp4:
    input:  _db_input
    output: "output/tmp_dataset_wp4.csv"
    params: script="analysis/dataset_definition/dataset_definition_wp4.py"
    shell:
        _ENV + " " + _EHRQL + " {params.script} --output {output} " + _BKND


rule diabetes_algo_wp1:
    input:  "output/tmp_dataset_wp1_common.csv"
    output: "output/dataset_wp1_common.csv"
    shell:
        _RSCRIPT + " --df_input tmp_dataset_wp1_common.csv --df_output dataset_wp1_common.csv"


rule diabetes_algo_wp2_1:
    input:  "output/tmp_dataset_wp2_1.csv"
    output: "output/dataset_wp2_1.csv"
    shell:
        _RSCRIPT + " --df_input tmp_dataset_wp2_1.csv --df_output dataset_wp2_1.csv"


rule diabetes_algo_wp2_2:
    input:  "output/tmp_dataset_wp2_2.csv"
    output: "output/dataset_wp2_2.csv"
    shell:
        _RSCRIPT + " --df_input tmp_dataset_wp2_2.csv --df_output dataset_wp2_2.csv"


rule diabetes_algo_wp3:
    input:  "output/tmp_dataset_wp3.csv"
    output: "output/dataset_wp3.csv"
    shell:
        _RSCRIPT + " --df_input tmp_dataset_wp3.csv --df_output dataset_wp3.csv"


rule diabetes_algo_wp4:
    input:  "output/tmp_dataset_wp4.csv"
    output: "output/dataset_wp4.csv"
    shell:
        _RSCRIPT + " --df_input tmp_dataset_wp4.csv --df_output dataset_wp4.csv"
