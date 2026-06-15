# Pipeline — Separação por Projeto

O **YAML é o único ponto onde a fonte é associada a um projeto** (`dbt_packages.name`).
A ingestão não conhece "projeto" — ela só grava em `silver.<source_name>`.
O `transformation_dag_factory.py` lê todos os YAMLs, agrupa por `dbt_packages.name`,
e gera um DAG dbt por projeto.

```mermaid
flowchart LR
    subgraph CFG["configs/  —  ponto de separação por projeto"]
        direction TB
        Y1["bacen_scr.yaml"]
        Y2["bacen_cambio.yaml"]
        Y3["minc_convenios.yaml"]
    end

    subgraph ING["Ingestion  —  1 DAG por fonte"]
        direction TB
        D1["ingest_csv_bacen_scr"]
        D2["ingest_csv_bacen_cambio"]
        D3["ingest_csv_minc_convenios"]
    end

    subgraph BRZ["Bronze  —  MinIO"]
        direction TB
        B1[("bronze/bacen_scr")]
        B2[("bronze/bacen_cambio")]
        B3[("bronze/minc_convenios")]
    end

    subgraph SLV["Silver  —  PostgreSQL"]
        direction TB
        S1[("silver.bacen_scr")]
        S2[("silver.bacen_cambio")]
        S3[("silver.minc_convenios")]
    end

    subgraph TRF["Transformation  —  1 DAG por projeto"]
        direction TB
        T1["transform_bacen"]
        T2["transform_minc"]
    end

    subgraph DBT["dbt packages"]
        direction TB
        P1["dbt/bacen/"]
        P2["dbt/minc/"]
    end

    %% data flow
    Y1 --> D1 --> B1 --> S1
    Y2 --> D2 --> B2 --> S2
    Y3 --> D3 --> B3 --> S3

    %% project grouping via dbt_packages.name
    Y1 & Y2 -- "name: bacen" --> T1
    Y3 -- "name: minc" --> T2

    %% dataset triggers
    S1 & S2 -. "Dataset trigger" .-> T1
    S3 -. "Dataset trigger" .-> T2

    T1 --> P1
    T2 --> P2

    classDef yamlNode fill:#fef9c3,stroke:#ca8a04,color:#78350f
    classDef dagNode fill:#eff6ff,stroke:#3b82f6,color:#1e40af
    classDef storageNode fill:#f0fdf4,stroke:#16a34a,color:#14532d
    classDef transformNode fill:#faf5ff,stroke:#7c3aed,color:#4c1d95
    classDef dbtNode fill:#ecfdf5,stroke:#059669,color:#064e3b

    class Y1,Y2,Y3 yamlNode
    class D1,D2,D3 dagNode
    class B1,B2,B3,S1,S2,S3 storageNode
    class T1,T2 transformNode
    class P1,P2 dbtNode

    style CFG fill:#fefce8,stroke:#eab308,color:#713f12
    style ING fill:#eff6ff,stroke:#93c5fd,color:#1e3a8a
    style BRZ fill:#fdf2f8,stroke:#f0abfc,color:#701a75
    style SLV fill:#f0fdf4,stroke:#86efac,color:#14532d
    style TRF fill:#faf5ff,stroke:#c4b5fd,color:#3b0764
    style DBT fill:#ecfdf5,stroke:#6ee7b7,color:#064e3b
```
