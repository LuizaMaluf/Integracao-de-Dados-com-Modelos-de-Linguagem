FROM apache/airflow:2.9.2

# libgs: backend do camelot (fallback do parser estrutural de PDF).
# libgl1/libglib2.0-0: o opencv, importado pelo unstructured (parser semântico), exige.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ghostscript libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
# Ponto de montagem do volume do DuckDB (Silver Zone): se não existir na imagem,
# o Docker cria como root e o usuário airflow não consegue gravar.
RUN mkdir -p /opt/airflow/data && chown airflow:root /opt/airflow/data
USER airflow

# Lock gerado por `make airflow-lock`: versões fixas evitam o backtracking do pip.
# apache-airflow fixado junto para o pip nunca trocar a versão da imagem.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir "apache-airflow==2.9.2" -r /tmp/requirements.txt
