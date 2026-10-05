"""
ehrQL backend for CPRD Aurum data.

Maps ehrql.tables.tpp tables to the CPRD data specification.

Run from the reducehf/ directory so Python can find this module.

Table mapping summary:
    patients                → CPRD Patient (yob+mob → date_of_birth, cprd_ddate → date_of_death)
    practice_registrations  → CPRD Patient + Practice (regstartdate/regenddate, region → practice_stp)
    clinical_events         → CPRD Observation + MedicalDictionary (snomedctconceptid as snomedct_code)
    clinical_events_ranges  → CPRD Observation (range columns all NULL)
    medications             → CPRD DrugIssue + ProductDictionary (dmdid as dmd_code)
    ons_deaths              → empty (not available in CPRD)
    apcs                    → hes_hospital + hes_diagnosis + hes_procedure + hes_criticalcare
    addresses               → patient_imdcomposite + patient_urbanrural
    emergency_care_         → hesae_attendance + hesae_diagnosis
      attendances
    ethnicity_from_sus      → hesae_attendance.ethnos (most common code per patient)
    household_memberships   → empty (not available in CPRD)
      _2020
"""

import ehrql.tables.core
from ehrql.backends.base import QueryTable, SQLBackend
from ehrql.query_engines.sqlite import SQLiteQueryEngine


def _cprd_date(col):
    """Convert a dd/mm/YYYY column to ISO date string, returning NULL for empty values."""
    return (
        f"CASE WHEN {col} IS NULL OR {col} = '' THEN NULL "
        f"ELSE SUBSTR({col}, 7, 4) || '-' || SUBSTR({col}, 4, 2) || '-' || SUBSTR({col}, 1, 2) "
        f"END"
    )


class CPRDBackend(SQLBackend):
    display_name = "CPRD Aurum (Synthetic)"
    query_engine_class = SQLiteQueryEngine
    patient_join_column = "patient_id"
    implements = [ehrql.tables.core]

    # ------------------------------------------------------------------
    # Core tables (validated against ehrql.tables.core)
    # ------------------------------------------------------------------

    patients = QueryTable(f"""
        SELECT
            CAST(patid AS INTEGER) AS patient_id,
            CAST(yob AS TEXT) || '-' || PRINTF('%02d', CAST(mob AS INTEGER)) || '-01'
                AS date_of_birth,
            CASE CAST(gender AS INTEGER)
                WHEN 1 THEN 'male'
                WHEN 2 THEN 'female'
                ELSE 'unknown'
            END AS sex,
            {_cprd_date('cprd_ddate')} AS date_of_death
        FROM Patient
        WHERE acceptable = 1
    """)

    practice_registrations = QueryTable(f"""
        SELECT
            CAST(p.patid AS INTEGER) AS patient_id,
            {_cprd_date('p.regstartdate')} AS start_date,
            {_cprd_date('p.regenddate')} AS end_date,
            CAST(p.pracid AS INTEGER) AS practice_pseudo_id,
            CAST(pr.region AS TEXT) AS practice_stp,
            NULL AS practice_nuts1_region_name,
            NULL AS practice_systmone_go_live_date
        FROM Patient p
        LEFT JOIN Practice pr ON p.pracid = pr.pracid
    """)

    clinical_events = QueryTable(f"""
        SELECT
            CAST(o.patid AS INTEGER) AS patient_id,
            {_cprd_date('o.obsdate')} AS date,
            CAST(md.snomedctconceptid AS TEXT) AS snomedct_code,
            NULL AS ctv3_code,
            CAST(o.value AS REAL) AS numeric_value,
            CAST(o.consid AS INTEGER) AS consultation_id,
            CAST(o.staffid AS INTEGER) AS staffid,
            CAST(s.jobcatid AS INTEGER) AS jobcatid
        FROM Observation o
        LEFT JOIN MedicalDictionary md ON o.medcodeid = md.medcodeid
        LEFT JOIN Staff s ON o.staffid = s.staffid AND o.pracid = s.pracid
    """)

    medications = QueryTable(f"""
        SELECT
            CAST(di.patid AS INTEGER) AS patient_id,
            {_cprd_date('di.issuedate')} AS date,
            CAST(pd.dmdid AS TEXT) AS dmd_code
        FROM DrugIssue di
        LEFT JOIN ProductDictionary pd ON di.prodcodeid = pd.prodcodeid
    """)

    # ONS death data is not linked in CPRD — return empty table.
    ons_deaths = QueryTable("""
        SELECT
            CAST(patid AS INTEGER) AS patient_id,
            NULL AS date,
            NULL AS underlying_cause_of_death,
            NULL AS cause_of_death_01,
            NULL AS cause_of_death_02,
            NULL AS cause_of_death_03,
            NULL AS cause_of_death_04,
            NULL AS cause_of_death_05,
            NULL AS cause_of_death_06,
            NULL AS cause_of_death_07,
            NULL AS cause_of_death_08,
            NULL AS cause_of_death_09,
            NULL AS cause_of_death_10,
            NULL AS cause_of_death_11,
            NULL AS cause_of_death_12,
            NULL AS cause_of_death_13,
            NULL AS cause_of_death_14,
            NULL AS cause_of_death_15,
            NULL AS place
        FROM Patient
        WHERE 1 = 0
    """)

    # ------------------------------------------------------------------
    # TPP-specific tables (not validated, but used by REDUCE-HF queries)
    # ------------------------------------------------------------------

    # clinical_events_ranges: same source as clinical_events; range columns are
    # not recorded in CPRD so they are returned as NULL.
    clinical_events_ranges = QueryTable(f"""
        SELECT
            CAST(o.patid AS INTEGER) AS patient_id,
            {_cprd_date('o.obsdate')} AS date,
            CAST(md.snomedctconceptid AS TEXT) AS snomedct_code,
            NULL AS ctv3_code,
            CAST(o.value AS REAL) AS numeric_value,
            CAST(o.consid AS INTEGER) AS consultation_id,
            CAST(o.numrangelow AS REAL) AS lower_bound,
            CAST(o.numrangehigh AS REAL) AS upper_bound,
            NULL AS comparator,
            CAST(o.staffid AS INTEGER) AS staffid,
            CAST(s.jobcatid AS INTEGER) AS jobcatid
        FROM Observation o
        LEFT JOIN MedicalDictionary md ON o.medcodeid = md.medcodeid
        LEFT JOIN Staff s ON o.staffid = s.staffid AND o.pracid = s.pracid
    """)

    # HES Admitted Patient Care: hospital + diagnosis + procedure + critical care tables.
    # all_diagnoses is formatted as ||code1 ,code2 ,code3|| to match the TPP convention.
    apcs = QueryTable(f"""
        SELECT
            CAST(h.patid AS INTEGER) AS patient_id,
            CAST(h.epikey AS INTEGER) AS apcs_ident,
            {_cprd_date('h.admidate')} AS admission_date,
            {_cprd_date('h.discharged')} AS discharge_date,
            NULL AS discharge_destination,
            CAST(h.dismeth AS TEXT) AS discharge_method,
            NULL AS spell_core_hrg_sus,
            CAST(h.admimeth AS TEXT) AS admission_method,
            h.diag_01 AS primary_diagnosis,
            NULL AS secondary_diagnosis,
            '||' || COALESCE(diag.all_diagnoses, h.diag_01) || '||' AS all_diagnoses,
            '||' || COALESCE(proc.all_procedures, '') || '||' AS all_procedures,
            CAST(COALESCE(cc.cclev2days, 0) AS INTEGER) AS days_in_critical_care,
            CAST(h.classpat AS TEXT) AS patient_classification
        FROM hes_hospital h
        LEFT JOIN (
            SELECT epikey, GROUP_CONCAT(ICD, ' ,') AS all_diagnoses
            FROM hes_diagnosis
            GROUP BY epikey
        ) diag ON h.epikey = diag.epikey
        LEFT JOIN (
            SELECT epikey, GROUP_CONCAT(OPCS, ',') AS all_procedures
            FROM hes_procedure
            GROUP BY epikey
        ) proc ON h.epikey = proc.epikey
        LEFT JOIN (
            SELECT epikey, SUM(CAST(cclev2days AS INTEGER)) AS cclev2days
            FROM hes_criticalcare
            GROUP BY epikey
        ) cc ON h.epikey = cc.epikey
    """)

    # Addresses: derived from small-area IMD and urban/rural tables.
    # imd_rounded is approximated from the IMD decile (1=most deprived → 0,
    # 10=least deprived → 32800), rounded to the nearest 100 as required.
    # rural_urban_classification: 1=Urban → 3 (Urban city and town),
    #                              2=Rural → 7 (Rural village and dispersed).
    addresses = QueryTable(f"""
        SELECT
            CAST(i.patid AS INTEGER) AS patient_id,
            CAST(i.patid AS INTEGER) AS address_id,
            {_cprd_date('p.regstartdate')} AS start_date,
            {_cprd_date('p.regenddate')} AS end_date,
            0 AS address_type,
            CASE CAST(u.e2011_urbanrural AS INTEGER)
                WHEN 1 THEN 3
                WHEN 2 THEN 7
                ELSE NULL
            END AS rural_urban_classification,
            CAST((CAST(i.e2019_imd_10 AS INTEGER) - 1) * 32800 / 9 / 100 AS INTEGER) * 100
                AS imd_rounded,
            NULL AS msoa_code,
            0 AS has_postcode,
            0 AS care_home_is_potential_match,
            NULL AS care_home_requires_nursing,
            NULL AS care_home_does_not_require_nursing
        FROM patient_imdcomposite i
        JOIN Patient p ON i.patid = p.patid AND i.pracid = p.pracid
        LEFT JOIN patient_urbanrural u ON i.patid = u.patid AND i.pracid = u.pracid
    """)

    # Ethnicity derived from gen_ethnicity in the HES APC patient table.
    # gen_ethnicity category labels are mapped to NHS single-letter ethnicity codes.
    ethnicity_from_sus = QueryTable("""
        SELECT
            CAST(patid AS INTEGER) AS patient_id,
            CASE gen_ethnicity
                WHEN 'White'            THEN 'A'
                WHEN 'Mixed'            THEN 'D'
                WHEN 'Indian'           THEN 'H'
                WHEN 'Pakistani'        THEN 'J'
                WHEN 'Bangladeshi'      THEN 'K'
                WHEN 'Other_Asian'      THEN 'L'
                WHEN 'Black_Caribbean'  THEN 'M'
                WHEN 'Black_African'    THEN 'N'
                WHEN 'Black_Other'      THEN 'P'
                WHEN 'Chinese'          THEN 'R'
                WHEN 'Other'            THEN 'S'
                ELSE NULL
            END AS code
        FROM hes_patient
        WHERE gen_ethnicity IS NOT NULL
            AND gen_ethnicity != ''
            AND gen_ethnicity != 'Unknown'
    """)

    # Household membership is not available in CPRD — return empty table.
    household_memberships_2020 = QueryTable("""
        SELECT
            CAST(patid AS INTEGER) AS patient_id,
            NULL AS household_pseudo_id,
            NULL AS household_size
        FROM Patient
        WHERE 1 = 0
    """)

    # HES A&E emergency care attendances.
    # Diagnoses are pivoted from hesae_diagnosis (up to 3 per attendance in
    # the synthetic data); columns diagnosis_04 through diagnosis_24 are NULL.
    emergency_care_attendances = QueryTable(f"""
        SELECT
            CAST(a.patid AS INTEGER) AS patient_id,
            CAST(a.aekey AS INTEGER) AS id,
            {_cprd_date('a.arrivaldate')} AS arrival_date,
            NULL AS discharge_destination,
            MAX(CASE WHEN d.diag_order = 1 THEN d.diag END) AS diagnosis_01,
            MAX(CASE WHEN d.diag_order = 2 THEN d.diag END) AS diagnosis_02,
            MAX(CASE WHEN d.diag_order = 3 THEN d.diag END) AS diagnosis_03,
            NULL AS diagnosis_04,
            NULL AS diagnosis_05,
            NULL AS diagnosis_06,
            NULL AS diagnosis_07,
            NULL AS diagnosis_08,
            NULL AS diagnosis_09,
            NULL AS diagnosis_10,
            NULL AS diagnosis_11,
            NULL AS diagnosis_12,
            NULL AS diagnosis_13,
            NULL AS diagnosis_14,
            NULL AS diagnosis_15,
            NULL AS diagnosis_16,
            NULL AS diagnosis_17,
            NULL AS diagnosis_18,
            NULL AS diagnosis_19,
            NULL AS diagnosis_20,
            NULL AS diagnosis_21,
            NULL AS diagnosis_22,
            NULL AS diagnosis_23,
            NULL AS diagnosis_24
        FROM hesae_attendance a
        LEFT JOIN hesae_diagnosis d ON a.aekey = d.aekey
        GROUP BY a.aekey
    """)
