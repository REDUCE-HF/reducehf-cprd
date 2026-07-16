FROM --platform=linux/amd64 continuumio/miniconda3

RUN apt-get update && apt-get install -y make && rm -rf /var/lib/apt/lists/*

RUN conda update -n base -c defaults conda -y

COPY environment-linux.yaml /tmp/environment-linux.yaml

RUN conda env create -f /tmp/environment-linux.yaml && \
    conda clean -afy

WORKDIR /workspace
