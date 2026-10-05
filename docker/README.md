# Executing snakemake pipeline on MAC-OS / Windows

The snakemake pipeline extracts datasets from a CPRD database using the `dataset_definition*.py` scripts written in ehrql.

It has only been tested on linux, so for now we can run these scripts through a docker container.

Build the container (on windows, use WSL or GitBash terminal):

```bash
cd /Path/to/this/repo/docker
docker build -t reducehf .
```

This creates a docker container (named reducehf) running linux, installs conda in the container, and creates the reducehf conda environment (for packages installed, see [environment-linux.yaml](https://github.com/REDUCE-HF/reducehf-cprd/blob/main/docker/environment-linux.yaml))

In the terminal, you can activate the container as an interactive session using:

```bash
docker run -it -v /Path/to/this/repo/:/workspace reducehf
```

Once the container is running, activate the conda environment and execute the snakemake pipeline:

```bash
conda activate reducehf
snakemake --cores 2
```

n.b you can use more/less cores depending on what you have available.

**Notes**

- the Snakefile currently takes 'synthetic_cprd_sqlite.db' as an input database. This database was created for developing the data extraction pipeline. To create a local version of this database, see <https://github.com/CharlotteJames/synthetic-cprd>. The snakefile looks for the database in the parent directory of this repo.

