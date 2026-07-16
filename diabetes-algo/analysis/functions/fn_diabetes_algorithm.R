fn_diabetes_algorithm <- function(data, column_mapping, diagnosis_date_sources = NULL) {

  # Set default date sources if not provided
  if (is.null(diagnosis_date_sources)) {
    diagnosis_date_sources <- list(
      gestationaldm = c("gestationaldm_date"),
      t1dm = c("t2dm_date", "t1dm_date", "otherdm_date", "tmp_diabetes_medication_date"),
      t2dm = c("t2dm_date", "t1dm_date", "otherdm_date", "tmp_diabetes_medication_date"),
      otherdm = c("t2dm_date", "t1dm_date", "otherdm_date", "tmp_diabetes_medication_date",
                  "tmp_max_hba1c_date", "tmp_poccdm_date")
    )
  }

  # Validate date sources
  valid_sources <- c("t2dm_date", "t1dm_date", "otherdm_date", "gestationaldm_date",
                     "tmp_diabetes_medication_date", "tmp_max_hba1c_date", "tmp_poccdm_date")
  for (dm_type in c("gestationaldm", "t1dm", "t2dm", "otherdm")) {
    invalid <- setdiff(diagnosis_date_sources[[dm_type]], valid_sources)
    if (length(invalid) > 0) {
      stop(paste0("Invalid date sources for ", dm_type, ": ", paste(invalid, collapse = ", ")))
    }
  }

  data <- data %>%
    rename(
      birth_date = all_of(column_mapping$birth_date),
      ethnicity_cat = all_of(column_mapping$ethnicity_cat),
      tmp_t1dm_primarycare_date = all_of(column_mapping$tmp_t1dm_primarycare_date),
      t1dm_date = all_of(column_mapping$t1dm_date),
      tmp_t1dm_count_num = all_of(column_mapping$tmp_t1dm_count_num),
      tmp_t2dm_primarycare_date = all_of(column_mapping$tmp_t2dm_primarycare_date),
      t2dm_date = all_of(column_mapping$t2dm_date),
      tmp_t2dm_count_num = all_of(column_mapping$tmp_t2dm_count_num),
      otherdm_date = all_of(column_mapping$otherdm_date),
      tmp_otherdm_count_num = all_of(column_mapping$tmp_otherdm_count_num),
      gestationaldm_date = all_of(column_mapping$gestationaldm_date),
      tmp_poccdm_date = all_of(column_mapping$tmp_poccdm_date),
      tmp_poccdm_primarycare_count_num = all_of(column_mapping$tmp_poccdm_primarycare_count_num),
      tmp_max_hba1c_mmol_mol_num = all_of(column_mapping$tmp_max_hba1c_mmol_mol_num),
      tmp_max_hba1c_date = all_of(column_mapping$tmp_max_hba1c_date),
      tmp_insulin_dmd_date = all_of(column_mapping$tmp_insulin_dmd_date),
      tmp_antidiabetic_drugs_dmd_date = all_of(column_mapping$tmp_antidiabetic_drugs_dmd_date),
      tmp_nonmetform_drugs_dmd_date = all_of(column_mapping$tmp_nonmetform_drugs_dmd_date),
      tmp_diabetes_medication_date = all_of(column_mapping$tmp_diabetes_medication_date),
      tmp_first_diabetes_diag_date = all_of(column_mapping$tmp_first_diabetes_diag_date)
      )

  data <- data %>%
    mutate(
    ## --- Step 0: Temporary helper variables ---
      tmp_birth_year_num = as.numeric(format(as.Date(birth_date, format = "%Y-%m-%d"), "%Y")),
      tmp_first_diabetes_diag_year = as.integer(format(tmp_first_diabetes_diag_date, "%Y")), # includes many diagnosis possibilities: t2dm_date, t1dm_date, otherdm_date, gestationaldm_date, tmp_elig_date_poccdm, tmp_elig_date_diabetes_medication, tmp_nonmetform_drugs_dmd_date
      tmp_age_1st_diag = tmp_first_diabetes_diag_year - tmp_birth_year_num,
      tmp_age_1st_diag = replace(tmp_age_1st_diag, which(tmp_age_1st_diag < 0), NA),
      tmp_age_under_35_30_1st_diag = case_when(!is.na(tmp_age_1st_diag)
                                               & ((tmp_age_1st_diag < 35 & (ethnicity_cat %in% c("White", "Mixed", "Other")))
                                                  | (tmp_age_1st_diag < 30)) ~ "Yes",
                                               TRUE ~ "No"), # prevents any NA: Those with DM but not fulfilling the condition OR those without DM at all -> "No"
      tmp_hba1c_date_step7 = case_when(!is.na(tmp_max_hba1c_mmol_mol_num) & tmp_max_hba1c_mmol_mol_num >= 47.5 ~ tmp_max_hba1c_date,
                                       TRUE ~ as.Date(NA)),
      tmp_over5_pocc_step7 = case_when(!is.na(tmp_poccdm_primarycare_count_num) & tmp_poccdm_primarycare_count_num >= 5 ~ tmp_poccdm_date,
                                       TRUE ~ as.Date(NA))) %>%

    ## --- Step 1: Any gestational diabetes code?
    mutate(step_1 = case_when(!is.na(gestationaldm_date) ~ "Yes",
                              TRUE ~ "No")
           ) %>%

    ## --- Step 1a: Any T1/T2 diagnostic codes besides gestational diabetes present? Denominator: Those with step 1 == Yes
    mutate(step_1a = case_when(step_1 == "Yes" & (!is.na(t1dm_date) | !is.na(t2dm_date)) ~ "Yes",
                              step_1 == "Yes" ~ "No", # everyone else with Yes to step 1 - but first condition not true
                              TRUE ~ NA_character_) # NA will only be fulfilled for people not part of denominator
           ) %>%

    ## --- Step 2: Any non-metformin oral antidiabetic drug prescription? Denominator: Step 1 == No or Step 1a == Yes
    mutate(step_2 = case_when((step_1 == "No" | step_1a == "Yes") & !is.na(tmp_nonmetform_drugs_dmd_date) ~ "Yes",
                              step_1 == "No" | step_1a == "Yes" ~ "No",
                              TRUE ~ NA_character_) # NA will only be fulfilled for people not part of denominator
           ) %>%

    ## --- Step 3: Any type 1 DM diagnostic code in the absence of any type 2 DM diagnostic code? Denominator: Step 2 == No
    mutate(step_3 = case_when(step_2 == "No" & !is.na(t1dm_date) & is.na(t2dm_date) ~ "Yes",
                              step_2 == "No" ~ "No",
                              TRUE ~ NA_character_) # NA will only be fulfilled for people not part of denominator
           ) %>%

    ## --- Step 4: Any type 2 DM diagnostic code in the absence of any type 1 DM diagnostic code? Denominator: Step 3 == No
    mutate(step_4 = case_when(step_3 == "No" & !is.na(t2dm_date) & is.na(t1dm_date) ~ "Yes",
                              step_3 == "No" ~ "No",
                              TRUE ~ NA_character_) # NA will only be fulfilled for people not part of denominator
           ) %>%

    ## --- Step 5. Aged <35yrs (or <30 yrs for SAs and AFCS) at first diagnostic code? Denominator: Step 4 == No
    mutate(step_5 = case_when(step_4 == "No" & tmp_age_under_35_30_1st_diag == "Yes" ~ "Yes", # tmp_age_under_35_30_1st_diag includes many diagnostic codes, see Step 0 above (incl. gestational DM, but excluded in Step 1)
                              step_4 == "No" & tmp_age_under_35_30_1st_diag == "No" ~ "No", # tmp_age_under_35_30_1st_diag cannot be NA (see above)
                              TRUE ~ NA_character_) # NA will only be fulfilled if not part of denominator
           ) %>%

    ## --- Step 6. Both, type 1 DM diagnostic codes and type 2 DM diagnostic codes present? Denominator: Step 5 == No
    mutate(step_6 = case_when(step_5 == "No" & !is.na(t1dm_date) & !is.na(t2dm_date) ~ "Yes",
                              step_5 == "No" & (is.na(t1dm_date) | is.na(t2dm_date)) ~ "No",
                              TRUE ~ NA_character_) # NA will only be fulfilled if not part of denominator
           ) %>%

    ## --- Step 6a. In primary care, only type 1 DM diagnostic codes reported? Denominator: Step 6 == Yes
    mutate(step_6a = case_when(step_6 == "Yes" & !is.na(tmp_t1dm_primarycare_date) & is.na(tmp_t2dm_primarycare_date) ~ "Yes",
                               step_6 == "Yes" ~ "No",
                               TRUE ~ NA_character_) # NA will only be fulfilled if not part of denominator
           ) %>%

    ## --- Step 6b. In primary care, only type 2 DM diagnostic codes reported? Denominator: Step 6a == No
    mutate(step_6b = case_when(step_6a == "No" & is.na(tmp_t1dm_primarycare_date) & !is.na(tmp_t2dm_primarycare_date) ~ "Yes",
                               step_6a == "No" ~ "No",
                               TRUE ~ NA_character_) # NA will only be fulfilled if not part of denominator
           ) %>%

    ## --- Step 6c. Number of type 1 DM diagnostic codes > number of type 2 DM diagnostic codes? Denominator: Step 6b == No
    mutate(step_6c = case_when(step_6b == "No" & tmp_t1dm_count_num > tmp_t2dm_count_num ~ "Yes", # count variables cannot be NA, see ehrQL documentation for count_for_patient(): "Note this will be 0 rather than NULL if the patient has no rows at all in the frame." https://docs.opensafely.org/ehrql/reference/language/#PatientFrame.count_for_patient
                               step_6b == "No" ~ "No",
                               TRUE ~ NA_character_) # NA will only be fulfilled if not part of denominator
           ) %>%

    ## --- Step 6d. Number of type 2 DM diagnostic codes > number of type 1 DM diagnostic codes? Denominator: Step 6c == No
    mutate(step_6d = case_when(step_6c == "No" & tmp_t2dm_count_num > tmp_t1dm_count_num ~ "Yes", # count variables cannot be NA, see ehrQL documentation for count_for_patient(): "Note this will be 0 rather than NULL if the patient has no rows at all in the frame." https://docs.opensafely.org/ehrql/reference/language/#PatientFrame.count_for_patient
                               step_6c == "No" ~ "No",
                               TRUE ~ NA_character_) # NA will only be fulfilled if not part of denominator
    ) %>%

    ## --- Step 6e. Type 2 DM diagnostic code is more recent than type 1 DM diagnostic code? Denominator: Step 6d == No
    mutate(step_6e = case_when(step_6d == "No" & t2dm_date > t1dm_date ~ "Yes",
                               step_6d == "No" & t2dm_date <= t1dm_date ~ "No", # I think the second part of this condition can be removed, since all that end up here have a t2dm_date and t1dm_date (step 6)? Currently Type 1 overrules Type 2 in case they have exactly the same date (extreme edge case), which I think is reasonable. If we remove the second part, the same will apply by default.
                               TRUE ~ NA_character_) # NA will only be fulfilled if not part of denominator
    ) %>%

    ## --- Step 7. Diabetes medication or >5 DM process of care codes or HbA1c >= 6.5 (47.5 mmol/mol)? Denominator: Step 6 == No
    mutate(step_7 = case_when(step_6 == "No" # this includes only people with both missing t1dm_date & t2dm_date (otherwise fished out further above)
                              & ((!is.na(tmp_diabetes_medication_date)) |
                                   (tmp_max_hba1c_mmol_mol_num >= 47.5) |
                                   (tmp_poccdm_primarycare_count_num >= 5)) ~ "Yes", # any other valid evidence for a diabetes, i.e. "unspecified Diabetes"?
                              step_6 == "No" ~ "No", # => Diabetes unlikely
                              TRUE ~ NA_character_) # NA will only be fulfilled if not part of denominator.
    ) %>%


    ## --- Final Diabetes Classification ---
    mutate(
      cat_diabetes = case_when(

        # DM unlikely conditions
        (step_1 == "No" & step_2 == "No" & step_3 == "No" & step_4 == "No" &
           step_5 == "No" & step_6 == "No" & step_7 == "No") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "No" & step_4 == "No" &
             step_5 == "No" & step_6 == "No" & step_7 == "No") ~ "DM unlikely",

        # DM other conditions
        (step_1 == "No" & step_2 == "No" & step_3 == "No" & step_4 == "No" &
           step_5 == "No" & step_6 == "No" & step_7 == "Yes") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "No" & step_4 == "No" &
             step_5 == "No" & step_6 == "No" & step_7 == "Yes") ~ "DM_other",

        # T2DM conditions
        (step_1 == "No" & step_2 == "Yes") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "Yes") |
          (step_1 == "No" & step_2 == "No" & step_3 == "No" & step_4 == "Yes") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "No" & step_4 == "Yes") |
          (step_1 == "No" & step_2 == "No" & step_3 == "No" & step_4 == "No" &
             step_5 == "No" & step_6 == "Yes" & step_6a == "No" & step_6b == "Yes") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "No" & step_4 == "No" &
             step_5 == "No" & step_6 == "Yes" & step_6a == "No" & step_6b == "Yes") |
          (step_1 == "No" & step_2 == "No" & step_3 == "No" & step_4 == "No" &
             step_5 == "No" & step_6 == "Yes" & step_6a == "No" & step_6b == "No" & step_6c == "No" & step_6d == "Yes") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "No" & step_4 == "No" &
             step_5 == "No" & step_6 == "Yes" & step_6a == "No" & step_6b == "No" & step_6c == "No" & step_6d == "Yes") |
          (step_1 == "No" & step_2 == "No" & step_3 == "No" & step_4 == "No" &
             step_5 == "No" & step_6 == "Yes" & step_6a == "No" & step_6b == "No" & step_6c == "No" & step_6d == "No" & step_6e == "Yes") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "No" & step_4 == "No" &
             step_5 == "No" & step_6 == "Yes" & step_6a == "No" & step_6b == "No" & step_6c == "No" & step_6d == "No" & step_6e == "Yes") ~ "T2DM",

        # T1DM conditions
        (step_1 == "No" & step_2 == "No" & step_3 == "Yes") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "Yes") |
          (step_1 == "No" & step_2 == "No" & step_3 == "No" & step_4 == "No" & step_5 == "Yes") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "No" & step_4 == "No" & step_5 == "Yes") |
          (step_1 == "No" & step_2 == "No" & step_3 == "No" & step_4 == "No" & step_5 == "No" & step_6 == "Yes" & step_6a == "Yes") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "No" & step_4 == "No" & step_5 == "No" & step_6 == "Yes" & step_6a == "Yes") |
          (step_1 == "No" & step_2 == "No" & step_3 == "No" & step_4 == "No" & step_5 == "No" & step_6 == "Yes" & step_6a == "No" & step_6b == "No" & step_6c == "Yes") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "No" & step_4 == "No" & step_5 == "No" & step_6 == "Yes" & step_6a == "No" & step_6b == "No" & step_6c == "Yes") |
          (step_1 == "No" & step_2 == "No" & step_3 == "No" & step_4 == "No" & step_5 == "No" & step_6 == "Yes" & step_6a == "No" & step_6b == "No" & step_6c == "No" & step_6d == "No" & step_6e == "No") |
          (step_1 == "Yes" & step_1a == "Yes" & step_2 == "No" & step_3 == "No" & step_4 == "No" & step_5 == "No" & step_6 == "Yes" & step_6a == "No" & step_6b == "No" & step_6c == "No" & step_6d == "No" & step_6e == "No") ~ "T1DM",

        # Gestational Diabetes (GDM)
        step_1 == "Yes" & step_1a == "No" ~ "GDM",

        # Default case (for any other conditions)
        TRUE ~ NA_character_
      )
    ) %>%
    mutate(across(cat_diabetes, ~replace_na(., "DM_unlikely"))) %>%


    ## --- Assignment of the diagnosis date ---
    # Define the incident diabetes date variables ("diagnosis date") for each diabetes type category (user-customizable)

    {
      # Helper function to calculate minimum date from user-specified sources
      calc_min_date <- function(dm_type, data_cols) {
        sources <- diagnosis_date_sources[[dm_type]]
        date_cols <- intersect(sources, names(data_cols))
        if (length(date_cols) == 0) {
          return(as.Date(NA))
        }
        do.call(pmin, c(data_cols[date_cols], na.rm = TRUE))
      }

      mutate(.,
             # GDM (user-customizable)
             gestationaldm_date = as_date(case_when(
               cat_diabetes == "GDM" ~ calc_min_date("gestationaldm",
                                                     list(t2dm_date = t2dm_date,
                                                          t1dm_date = t1dm_date,
                                                          gestationaldm_date = gestationaldm_date,
                                                          otherdm_date = otherdm_date,
                                                          tmp_diabetes_medication_date = tmp_diabetes_medication_date,
                                                          tmp_max_hba1c_date = tmp_hba1c_date_step7, # takes the user input date variable, but is slightly modified above
                                                          tmp_poccdm_date = tmp_over5_pocc_step7)), # takes the user input date variable, but is slightly modified above
               TRUE ~ as.Date(NA))),

             # T2DM (user-customizable)
             t2dm_date = as_date(case_when(
               cat_diabetes == "T2DM" ~ calc_min_date("t2dm",
                                                      list(t2dm_date = t2dm_date,
                                                           t1dm_date = t1dm_date,
                                                           gestationaldm_date = gestationaldm_date,
                                                           otherdm_date = otherdm_date,
                                                           tmp_diabetes_medication_date = tmp_diabetes_medication_date,
                                                           tmp_max_hba1c_date = tmp_hba1c_date_step7,
                                                           tmp_poccdm_date = tmp_over5_pocc_step7)),
               TRUE ~ as.Date(NA))),

             # T1DM (user-customizable)
             t1dm_date = as_date(case_when(
               cat_diabetes == "T1DM" ~ calc_min_date("t1dm",
                                                      list(t2dm_date = t2dm_date,
                                                           t1dm_date = t1dm_date,
                                                           gestationaldm_date = gestationaldm_date,
                                                           otherdm_date = otherdm_date,
                                                           tmp_diabetes_medication_date = tmp_diabetes_medication_date,
                                                           tmp_max_hba1c_date = tmp_hba1c_date_step7,
                                                           tmp_poccdm_date = tmp_over5_pocc_step7)),
               TRUE ~ as.Date(NA))),

             # OTHER (user-customizable)
             otherdm_date = as_date(case_when(
               cat_diabetes == "DM_other" ~ calc_min_date("otherdm",
                                                          list(t2dm_date = t2dm_date,
                                                               t1dm_date = t1dm_date,
                                                               gestationaldm_date = gestationaldm_date,
                                                               otherdm_date = otherdm_date,
                                                               tmp_diabetes_medication_date = tmp_diabetes_medication_date,
                                                               tmp_max_hba1c_date = tmp_hba1c_date_step7,
                                                               tmp_poccdm_date = tmp_over5_pocc_step7)),
               TRUE ~ as.Date(NA)))
      )
    }

  return(data)
}
