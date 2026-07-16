"""
Python translation of fn_diabetes_algorithm.R (diabetes-algo v0.0.13).

Applies a stepwise algorithm to classify patients into diabetes categories:
  DM unlikely, DM_other, T2DM, T1DM, GDM
and assigns the corresponding incident diagnosis date.
"""

import pandas as pd
import numpy as np


def fn_diabetes_algorithm(data, column_mapping, diagnosis_date_sources=None):

    if diagnosis_date_sources is None:
        diagnosis_date_sources = {
            'gestationaldm': ['gestationaldm_date'],
            't1dm': ['t2dm_date', 't1dm_date', 'otherdm_date', 'tmp_diabetes_medication_date'],
            't2dm': ['t2dm_date', 't1dm_date', 'otherdm_date', 'tmp_diabetes_medication_date'],
            'otherdm': ['t2dm_date', 't1dm_date', 'otherdm_date', 'tmp_diabetes_medication_date',
                        'tmp_max_hba1c_date', 'tmp_poccdm_date'],
        }

    valid_sources = [
        't2dm_date', 't1dm_date', 'otherdm_date', 'gestationaldm_date',
        'tmp_diabetes_medication_date', 'tmp_max_hba1c_date', 'tmp_poccdm_date',
    ]
    for dm_type in ['gestationaldm', 't1dm', 't2dm', 'otherdm']:
        invalid = set(diagnosis_date_sources[dm_type]) - set(valid_sources)
        if invalid:
            raise ValueError(f"Invalid date sources for {dm_type}: {', '.join(invalid)}")

    data = data.copy()

    # ── Step 0: helper variables ──────────────────────────────────────────────

    birth_date    = pd.to_datetime(data['birth_date'], format='%Y-%m-%d', errors='coerce')
    first_diag    = pd.to_datetime(data['tmp_first_diabetes_diag_date'], format='%Y-%m-%d', errors='coerce')
    hba1c_num     = pd.to_numeric(data['tmp_max_hba1c_mmol_mol_num'], errors='coerce')
    hba1c_date    = pd.to_datetime(data['tmp_max_hba1c_date'], format='%Y-%m-%d', errors='coerce')
    poccdm_count  = pd.to_numeric(data['tmp_poccdm_primarycare_count_num'], errors='coerce').fillna(0)
    poccdm_date   = pd.to_datetime(data['tmp_poccdm_date'], format='%Y-%m-%d', errors='coerce')

    data['tmp_birth_year_num']           = birth_date.dt.year
    data['tmp_first_diabetes_diag_year'] = first_diag.dt.year.astype('Int64')
    data['tmp_age_1st_diag']             = data['tmp_first_diabetes_diag_year'] - data['tmp_birth_year_num']
    data.loc[data['tmp_age_1st_diag'] < 0, 'tmp_age_1st_diag'] = pd.NA

    age       = data['tmp_age_1st_diag']
    ethnicity = data['ethnicity_cat']
    data['tmp_age_under_35_30_1st_diag'] = np.where(
        pd.notna(age) & (
            ((age < 35) & ethnicity.isin(['White', 'Mixed', 'Other'])) | (age < 30)
        ),
        'Yes', 'No',
    )

    # HbA1c date only counts when >= 47.5 mmol/mol
    data['tmp_hba1c_date_step7'] = pd.NaT
    mask = pd.notna(hba1c_num) & (hba1c_num >= 47.5)
    data.loc[mask, 'tmp_hba1c_date_step7'] = hba1c_date[mask]

    # POCC date only counts when >= 5 codes
    data['tmp_over5_pocc_step7'] = pd.NaT
    mask = poccdm_count >= 5
    data.loc[mask, 'tmp_over5_pocc_step7'] = poccdm_date[mask]

    # Parse key date/count columns used in the steps
    gest_date    = pd.to_datetime(data['gestationaldm_date'], format='%Y-%m-%d', errors='coerce')
    t1dm_date    = pd.to_datetime(data['t1dm_date'],          format='%Y-%m-%d', errors='coerce')
    t2dm_date    = pd.to_datetime(data['t2dm_date'],          format='%Y-%m-%d', errors='coerce')
    otherdm_date = pd.to_datetime(data['otherdm_date'],       format='%Y-%m-%d', errors='coerce')
    nonmetform   = pd.to_datetime(data['tmp_nonmetform_drugs_dmd_date'], format='%Y-%m-%d', errors='coerce')
    diab_med     = pd.to_datetime(data['tmp_diabetes_medication_date'],  format='%Y-%m-%d', errors='coerce')
    t1dm_pc      = pd.to_datetime(data['tmp_t1dm_primarycare_date'],     format='%Y-%m-%d', errors='coerce')
    t2dm_pc      = pd.to_datetime(data['tmp_t2dm_primarycare_date'],     format='%Y-%m-%d', errors='coerce')
    t1dm_count   = pd.to_numeric(data['tmp_t1dm_count_num'], errors='coerce').fillna(0)
    t2dm_count   = pd.to_numeric(data['tmp_t2dm_count_num'], errors='coerce').fillna(0)

    # ── Steps 1 – 7 ──────────────────────────────────────────────────────────

    # Step 1: gestational DM code present?
    data['step_1'] = np.where(pd.notna(gest_date), 'Yes', 'No')

    # Step 1a: T1/T2 codes also present? (denominator: step_1 == Yes)
    in1 = data['step_1'] == 'Yes'
    data['step_1a'] = np.where(
        in1 & (pd.notna(t1dm_date) | pd.notna(t2dm_date)), 'Yes',
        np.where(in1, 'No', None),
    )

    # Step 2: non-metformin oral antidiabetic? (denominator: step_1==No OR step_1a==Yes)
    in2 = (data['step_1'] == 'No') | (data['step_1a'] == 'Yes')
    data['step_2'] = np.where(
        in2 & pd.notna(nonmetform), 'Yes',
        np.where(in2, 'No', None),
    )

    # Step 3: T1DM code without T2DM? (denominator: step_2==No)
    in3 = data['step_2'] == 'No'
    data['step_3'] = np.where(
        in3 & pd.notna(t1dm_date) & pd.isna(t2dm_date), 'Yes',
        np.where(in3, 'No', None),
    )

    # Step 4: T2DM code without T1DM? (denominator: step_3==No)
    in4 = data['step_3'] == 'No'
    data['step_4'] = np.where(
        in4 & pd.notna(t2dm_date) & pd.isna(t1dm_date), 'Yes',
        np.where(in4, 'No', None),
    )

    # Step 5: young at first diagnosis? (denominator: step_4==No)
    in5 = data['step_4'] == 'No'
    data['step_5'] = np.where(
        in5 & (data['tmp_age_under_35_30_1st_diag'] == 'Yes'), 'Yes',
        np.where(in5, 'No', None),
    )

    # Step 6: both T1DM and T2DM codes? (denominator: step_5==No)
    in6 = data['step_5'] == 'No'
    data['step_6'] = np.where(
        in6 & pd.notna(t1dm_date) & pd.notna(t2dm_date), 'Yes',
        np.where(in6 & (pd.isna(t1dm_date) | pd.isna(t2dm_date)), 'No', None),
    )

    # Step 6a: primary care shows T1DM only? (denominator: step_6==Yes)
    in6a = data['step_6'] == 'Yes'
    data['step_6a'] = np.where(
        in6a & pd.notna(t1dm_pc) & pd.isna(t2dm_pc), 'Yes',
        np.where(in6a, 'No', None),
    )

    # Step 6b: primary care shows T2DM only? (denominator: step_6a==No)
    in6b = data['step_6a'] == 'No'
    data['step_6b'] = np.where(
        in6b & pd.isna(t1dm_pc) & pd.notna(t2dm_pc), 'Yes',
        np.where(in6b, 'No', None),
    )

    # Step 6c: T1DM count > T2DM count? (denominator: step_6b==No)
    in6c = data['step_6b'] == 'No'
    data['step_6c'] = np.where(
        in6c & (t1dm_count > t2dm_count), 'Yes',
        np.where(in6c, 'No', None),
    )

    # Step 6d: T2DM count > T1DM count? (denominator: step_6c==No)
    in6d = data['step_6c'] == 'No'
    data['step_6d'] = np.where(
        in6d & (t2dm_count > t1dm_count), 'Yes',
        np.where(in6d, 'No', None),
    )

    # Step 6e: T2DM date more recent than T1DM date? (denominator: step_6d==No)
    in6e = data['step_6d'] == 'No'
    data['step_6e'] = np.where(
        in6e & (t2dm_date > t1dm_date), 'Yes',
        np.where(in6e & (t2dm_date <= t1dm_date), 'No', None),
    )

    # Step 7: any other valid DM evidence? (denominator: step_6==No)
    in7 = data['step_6'] == 'No'
    any_evidence = (
        pd.notna(diab_med) |
        (hba1c_num >= 47.5) |
        (poccdm_count >= 5)
    )
    data['step_7'] = np.where(
        in7 & any_evidence, 'Yes',
        np.where(in7, 'No', None),
    )

    # ── Final classification ──────────────────────────────────────────────────

    s = data

    dm_unlikely = (
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='No') &
         (s['step_5']=='No') & (s['step_6']=='No') & (s['step_7']=='No')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='No') &
         (s['step_4']=='No') & (s['step_5']=='No') & (s['step_6']=='No') & (s['step_7']=='No'))
    )
    dm_other = (
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='No') &
         (s['step_5']=='No') & (s['step_6']=='No') & (s['step_7']=='Yes')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='No') &
         (s['step_4']=='No') & (s['step_5']=='No') & (s['step_6']=='No') & (s['step_7']=='Yes'))
    )
    t2dm = (
        ((s['step_1']=='No') & (s['step_2']=='Yes')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='Yes')) |
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='Yes')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='Yes')) |
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='No') &
         (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='No') & (s['step_6b']=='Yes')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='No') &
         (s['step_4']=='No') & (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='No') & (s['step_6b']=='Yes')) |
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='No') &
         (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='No') & (s['step_6b']=='No') &
         (s['step_6c']=='No') & (s['step_6d']=='Yes')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='No') &
         (s['step_4']=='No') & (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='No') &
         (s['step_6b']=='No') & (s['step_6c']=='No') & (s['step_6d']=='Yes')) |
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='No') &
         (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='No') & (s['step_6b']=='No') &
         (s['step_6c']=='No') & (s['step_6d']=='No') & (s['step_6e']=='Yes')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='No') &
         (s['step_4']=='No') & (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='No') &
         (s['step_6b']=='No') & (s['step_6c']=='No') & (s['step_6d']=='No') & (s['step_6e']=='Yes'))
    )
    t1dm = (
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='Yes')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='Yes')) |
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='No') & (s['step_5']=='Yes')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='No') &
         (s['step_4']=='No') & (s['step_5']=='Yes')) |
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='No') &
         (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='Yes')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='No') &
         (s['step_4']=='No') & (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='Yes')) |
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='No') &
         (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='No') & (s['step_6b']=='No') & (s['step_6c']=='Yes')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='No') &
         (s['step_4']=='No') & (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='No') &
         (s['step_6b']=='No') & (s['step_6c']=='Yes')) |
        ((s['step_1']=='No') & (s['step_2']=='No') & (s['step_3']=='No') & (s['step_4']=='No') &
         (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='No') & (s['step_6b']=='No') &
         (s['step_6c']=='No') & (s['step_6d']=='No') & (s['step_6e']=='No')) |
        ((s['step_1']=='Yes') & (s['step_1a']=='Yes') & (s['step_2']=='No') & (s['step_3']=='No') &
         (s['step_4']=='No') & (s['step_5']=='No') & (s['step_6']=='Yes') & (s['step_6a']=='No') &
         (s['step_6b']=='No') & (s['step_6c']=='No') & (s['step_6d']=='No') & (s['step_6e']=='No'))
    )
    gdm = (s['step_1'] == 'Yes') & (s['step_1a'] == 'No')

    data['cat_diabetes'] = np.select(
        [dm_unlikely, dm_other, t2dm, t1dm, gdm],
        ['DM unlikely', 'DM_other', 'T2DM', 'T1DM', 'GDM'],
        default=None,
    )
    data['cat_diabetes'] = data['cat_diabetes'].fillna('DM_unlikely')

    # ── Incident diagnosis date assignment ────────────────────────────────────
    # Build date column map using ORIGINAL parsed values (before any overwriting)
    date_col_map = {
        't2dm_date':                    t2dm_date,
        't1dm_date':                    t1dm_date,
        'gestationaldm_date':           gest_date,
        'otherdm_date':                 otherdm_date,
        'tmp_diabetes_medication_date': diab_med,
        'tmp_max_hba1c_date':           pd.to_datetime(data['tmp_hba1c_date_step7'], errors='coerce'),
        'tmp_poccdm_date':              pd.to_datetime(data['tmp_over5_pocc_step7'],  errors='coerce'),
    }

    def calc_min_date(dm_type):
        sources   = diagnosis_date_sources[dm_type]
        available = [date_col_map[s] for s in sources if s in date_col_map]
        if not available:
            return pd.Series(pd.NaT, index=data.index)
        return pd.concat(available, axis=1).min(axis=1)

    gdm_min    = calc_min_date('gestationaldm')
    t2dm_min   = calc_min_date('t2dm')
    t1dm_min   = calc_min_date('t1dm')
    otherdm_min = calc_min_date('otherdm')

    data['gestationaldm_date'] = gdm_min.where(data['cat_diabetes'] == 'GDM',     other=pd.NaT)
    data['t2dm_date']          = t2dm_min.where(data['cat_diabetes'] == 'T2DM',   other=pd.NaT)
    data['t1dm_date']          = t1dm_min.where(data['cat_diabetes'] == 'T1DM',   other=pd.NaT)
    data['otherdm_date']       = otherdm_min.where(data['cat_diabetes'] == 'DM_other', other=pd.NaT)

    return data
