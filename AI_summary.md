# REDUCE-HF on CPRD

This repository is a fork of [REDUCE-HF/reducehf](https://github.com/REDUCE-HF/reducehf), the REDUCE-HF study code written for [OpenSAFELY](https://www.opensafely.org). It adds a small set of files that allow the same study code to be run against [CPRD Aurum](https://www.cprd.com) data, outside the OpenSAFELY platform.

The aim is to keep the study logic identical in both settings. The dataset definitions, codelists and analysis code are shared with the upstream repository; only the parts that OpenSAFELY normally provides (the mapping to the underlying database, the pipeline runner and the software environment) are replaced.

> **Status:** work in progress. The pipeline has so far been run against synthetic CPRD data only. See [Limitations](#limitations).

## Contents

- [How this differs from OpenSAFELY](#how-this-differs-from-opensafely)
- [What has been added](#what-has-been-added)
- [How it works](#how-it-works)
- [Running the pipeline](#running-the-pipeline)
- [Configuration](#configuration)
- [Limitations](#limitations)

## How this differs from OpenSAFELY

On OpenSAFELY, a study is a set of ehrQL dataset definitions plus a `project.yaml` describing the actions to run. The platform supplies everything else. To run the study elsewhere, each of those platform-provided pieces needs an equivalent:

| Piece | On OpenSAFELY | In this repository |
| --- | --- | --- |
| Source data | TPP SystmOne records in the OpenSAFELY-TPP database | CPRD Aurum with linked HES, deprivation and rurality data |
| Mapping from ehrQL tables to the database | ehrQL's built-in TPP backend | `cprd_backend_sqlite.py` |
| Pipeline definition and runner | `project.yaml`, run by the OpenSAFELY job runner | `Snakefile`, run by Snakemake |
| ehrQL runtime | The `ehrql` Docker image | `ehrql/`, run through `uv` |
| Diabetes algorithm | The `diabetes-algo` reusable action | `diabetes-algo/`, run through `Rscript` |
| Software environment | OpenSAFELY Docker images | `docker/` |

Because ehrQL separates *what* a study asks for (the dataset definition) from *where* the data lives (the backend), the dataset definitions in `analysis/dataset_definition/` do not need to change. They still refer to tables such as `patients`, `clinical_events` and `apcs`; the CPRD backend supplies those tables from CPRD's own schema.

## What has been added

| Path | Purpose |
| --- | --- |
| `cprd_backend_sqlite.py` | ehrQL backend that maps the ehrQL tables used by REDUCE-HF onto CPRD Aurum tables |
| `Snakefile` | Pipeline rules: one per dataset, plus the diabetes algorithm post-processing steps |
| `common.smk` | Paths, settings and shell command fragments used by the rules |
| `config.yaml` | User-editable settings (backend, cohort years, database location, runtime options) |
| `ehrql/` | The ehrQL project used to run `generate-dataset` |
| `diabetes-algo/` | The diabetes algorithm R code, run locally in place of the OpenSAFELY reusable action |
| `docker/` | Container definition providing Snakemake, uv, Python and R |

Everything else comes from the upstream repository. `project.yaml` is retained for reference but is not used here.

## How it works

### 1. The CPRD backend

`cprd_backend_sqlite.py` defines `CPRDBackend`, an ehrQL backend in which each ehrQL table is a SQL query over the CPRD tables. It also converts CPRD conventions to the ones ehrQL expects, for example `dd/mm/YYYY` text dates to ISO dates, and year and month of birth to a date of birth on the first of the month.

| ehrQL table | CPRD source | Notes |
| --- | --- | --- |
| `patients` | `Patient` | Restricted to `acceptable = 1`; date of death from `cprd_ddate` |
| `practice_registrations` | `Patient`, `Practice` | Practice region is returned as `practice_stp` |
| `clinical_events` | `Observation`, `MedicalDictionary`, `Staff` | SNOMED CT codes from `snomedctconceptid`; `ctv3_code` is NULL |
| `clinical_events_ranges` | `Observation`, `MedicalDictionary`, `Staff` | Reference ranges from `numrangelow` / `numrangehigh`; `comparator` is NULL |
| `medications` | `DrugIssue`, `ProductDictionary` | dm+d codes from `dmdid` |
| `apcs` | `hes_hospital`, `hes_diagnosis`, `hes_procedure`, `hes_criticalcare` | `all_diagnoses` formatted to match the TPP convention |
| `emergency_care_attendances` | `hesae_attendance`, `hesae_diagnosis` | First three diagnoses only; the rest are NULL |
| `addresses` | `patient_imdcomposite`, `patient_urbanrural`, `Patient` | IMD and rural/urban values are approximations (see [Limitations](#limitations)) |
| `ethnicity_from_sus` | `hes_patient` | `gen_ethnicity` mapped to NHS single-letter codes |
| `ons_deaths` | none | Empty table |
| `household_memberships_2020` | none | Empty table |

### 2. The Snakemake pipeline

The `Snakefile` plays the role of `project.yaml`. It has two groups of rules:

1. **Dataset generation.** Each `generate_dataset_*` rule runs `ehrql generate-dataset` on one dataset definition, using `CPRDBackend` and the configured database. The time-dependent WP1 dataset is generated once per cohort year, with the index date passed to the dataset definition as an argument.
2. **Diabetes algorithm.** Each `diabetes_algo_*` rule runs `diabetes-algo/analysis/data_process.R` on a `tmp_dataset_*.csv` file and writes the final `dataset_*.csv`. REDUCE-HF names its primary care diabetes variables with a `ctv3` suffix, whereas the algorithm expects `primarycare`, so the rule passes the column names explicitly.

Snakemake works out the order from the input and output files, runs independent jobs in parallel, and skips anything already up to date.

The pipeline produces:

```
output/dataset_consort.csv
output/dataset_wp1_common.csv
output/dataset_wp1_<year>.csv      (one per cohort year)
output/dataset_wp2_1.csv
output/dataset_wp2_2.csv
output/dataset_wp3.csv
output/dataset_wp4.csv
```

Files named `output/tmp_dataset_*.csv` are intermediate ehrQL outputs awaiting the diabetes algorithm.

### 3. The Docker environment

The `docker/` folder defines a container with the tools the pipeline needs (Snakemake, uv, Python and R), so that it runs the same way on any machine. The image is built for `linux/amd64`.

## Running the pipeline

### Prerequisites

- Docker, **or** a local installation of Snakemake, [uv](https://docs.astral.sh/uv/), and R with the packages required by `diabetes-algo`
- A CPRD database in the layout the backend expects. By default the pipeline looks for a synthetic SQLite database in the root of this repository, one level above this repository.
- Network access the first time ehrQL runs, so that uv can install its dependencies

### With Docker

see [docker/README.md](https://github.com/REDUCE-HF/reducehf-cprd/tree/main/docker/README.md)

## Configuration

Settings that are likely to change live in `config.yaml`. Any of them can be overridden for a single run with `--config key=value`.

| Setting | Meaning | Default |
| --- | --- | --- |
| `dsn` | Database connection string. `null` uses the synthetic SQLite database | `null` |
| `backend` | ehrQL backend class, as `module.ClassName` | `cprd_backend_sqlite.CPRDBackend` |
| `cohort_years` | Years for which a time-dependent WP1 dataset is generated | 2019 to 2025 |
| `cohort_index_month_day` | Month and day of the index date within each cohort year | `02-01` |
| `tmp_dir` | Directory for temporary files | `output` |
| `max_join_count` | Maximum number of tables ehrQL joins in a single query | `32` |
| `venv_dir` | Where uv creates the ehrQL virtual environment | `/tmp/ehrql-venv` |

## Limitations

**Not all OpenSAFELY data has a CPRD equivalent.** These differences affect any variable built on the tables concerned:

- `ons_deaths` is empty, so cause of death is unavailable. Date of death is available from `patients.date_of_death`.
- `household_memberships_2020` is empty.
- `clinical_events.ctv3_code` is always NULL, so only SNOMED CT codelists will match.
- `addresses.imd_rounded` is approximated from the IMD decile rather than taken from the IMD rank.
- `addresses.rural_urban_classification` is collapsed to two values (urban or rural).
- Ethnicity from `ethnicity_from_sus` is derived from the HES `gen_ethnicity` category, which is coarser than the SUS ethnicity codes.
- Date of birth is the first day of the month of birth.
- Several columns with no CPRD source are returned as NULL (for example `practice_nuts1_region_name`, `msoa_code`, and discharge destination).

