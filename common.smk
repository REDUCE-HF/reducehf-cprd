import os

# ── Paths ─────────────────────────────────────────────────────────────────────
# Derive absolute paths from the Snakefile's location so the workflow can be
# invoked from any working directory (e.g. snakemake --snakefile reducehf/Snakefile).

_here         = os.path.dirname(os.path.abspath(workflow.snakefile))

EHRQL_DIR = os.path.normpath(os.path.join(_here, "ehrql"))
SYNTHETIC_DB  = os.path.normpath(os.path.join(_here, "synthetic_cprd_sqlite.db"))
DIABETES_ALGO_DIR = os.path.normpath(os.path.join(_here, "diabetes-algo"))
_ABS_OUTPUT   = os.path.join(_here, "output")

# ── Settings ──────────────────────────────────────────────────────────────────
# User-editable values live in config.yaml, next to the Snakefile.
# Anything passed with --config on the command line overrides the file.

configfile: os.path.join(_here, "config.yaml")

BACKEND = config["backend"]

# One time-dependent dataset per cohort year
COHORT_YEARS    = config["cohort_years"]
INDEX_MONTH_DAY = config["cohort_index_month_day"]

# ── Database source ───────────────────────────────────────────────────────────
# Default: generate and use the local synthetic SQLite database.
# To use a different database pass its DSN on the command line:
#   snakemake --config dsn=sqlite:////absolute/path/to/other.db
# Any SQLAlchemy DSN accepted by CPRDBackend works (e.g. mssql+pyodbc://...).

_custom_dsn = config.get("dsn")
DSN         = _custom_dsn if _custom_dsn else f"sqlite:////{SYNTHETIC_DB}"
_db_input   = [] if _custom_dsn else [SYNTHETIC_DB]

# ── Shell fragments ───────────────────────────────────────────────────────────
_ENV = (
    f"PYTHONPATH=. SQLITE_TMPDIR={config['tmp_dir']} TMPDIR={config['tmp_dir']}"
    f" EHRQL_MAX_JOIN_COUNT={config['max_join_count']}"
    f" UV_PROJECT_ENVIRONMENT={config['venv_dir']}"
)
_EHRQL = f"uv run --project {EHRQL_DIR} python -m ehrql generate-dataset"
_BKND  = f"--backend {BACKEND} --dsn '{DSN}'"
_LOG = " > {log} 2>&1"

# Column renames needed because REDUCE-HF uses ctv3 suffix; diabetes-algo expects primarycare
_CTXV3 = (
    " --tmp_t1dm_primarycare_date tmp_t1dm_ctv3_date"
    " --tmp_t2dm_primarycare_date tmp_t2dm_ctv3_date"
    " --tmp_poccdm_primarycare_count_num tmp_poccdm_ctv3_count_num"
)
_DIABETES_ALGO = (
    f"cd {DIABETES_ALGO_DIR} && Rscript analysis/data_process.R"
    f" --input_dir ../output --output_dir ../output"
    " --birth_date dob --ethnicity_cat ethnicity_cat"
    + _CTXV3
)
