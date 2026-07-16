################################################################################
# A custom made function to extract the data from a feather file and format variables
################################################################################
fn_extract_data <- function(input_filename) {
  data_extract <- arrow::read_feather(here::here("output", input_filename))

  data_extract <- data_extract %>%
    mutate(across(c(contains("_date")),
                  ~ floor_date(as.Date(., format="%Y-%m-%d"), unit = "days")), # rounding down the date to the nearest day
           across(contains('birth_year'),
                   ~ format(as.Date(.), "%Y")), # specifically for birth_year, then pass it onto _num to reformat birth_year_num
           across(contains('_num'), ~ as.numeric(.)),
           across(contains('_cat'), ~ as.factor(.)),
           across(contains('_bin'), ~ as.logical(.))
           )
}