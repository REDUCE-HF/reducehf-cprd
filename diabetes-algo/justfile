render:
    docker run --platform linux/amd64 --rm -v "/$PWD:/workspace" ghcr.io/opensafely-core/r:v2 -e "rmarkdown::render('README.Rmd')"
test:
    opensafely run run_all -f
test-1:
    opensafely run generate_dataset data_process -f
test-2:
    opensafely run generate_dataset_2 data_process_2 -f
test-3:
    opensafely run generate_dataset_3 data_process_3 -f
test-4:
    opensafely run generate_dataset_4 data_process_4 -f
