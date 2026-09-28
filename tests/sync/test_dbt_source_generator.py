import yaml

from govhub.sync import dbt_source_generator as gen


def _registry(tmp_path, **files):
    configs = tmp_path / "configs"
    configs.mkdir()
    for name, text in files.items():
        (configs / f"{name}.yaml").write_text(text)
    models = tmp_path / "models"
    (models / "bronze").mkdir(parents=True)
    return configs, models


def test_source_tables_por_tipo():
    assert gen.source_tables({"source_name": "IBGE UFs", "type": "api"}) == ["ibge_ufs"]
    assert gen.source_tables({"source_name": "x", "target_table": "y", "type": "csv"}) == ["y"]
    dump = {"source_name": "d", "type": "dump", "tables": ["Tab_A", "tab_b"]}
    assert gen.source_tables(dump) == ["tab_a", "tab_b"]
    assert gen.source_tables({"source_name": "d", "type": "dump"}) == []


def test_build_bronze_model_incremental_por_lote():
    sql = gen.build_bronze_model("ibge_municipios", "ibge.yaml")
    assert sql.startswith(f"-- {gen.MARKER} a partir de ibge.yaml")
    assert "source('registry', 'ibge_municipios')" in sql
    assert "incremental_strategy='delete+insert'" in sql
    assert "unique_key='_silver_table'" in sql
    assert "{% if is_incremental() %}" in sql and "{{ this }}" in sql


def test_generate_escreve_sources_e_models(tmp_path):
    configs, models = _registry(
        tmp_path,
        a="source_name: ibge_municipios\ntype: api\n",
        b="source_name: ibge_estados\ntype: api\ntarget_table: ibge_ufs\n",
    )
    files = gen.generate(configs, models)
    out = models / "bronze" / "_generated"
    assert {f.name for f in files} == {"ibge_municipios.sql", "ibge_ufs.sql", "_sources.yml"}

    doc = yaml.safe_load((out / "_sources.yml").read_text())
    source = doc["sources"][0]
    assert source["name"] == "registry" and source["schema"] == "silver"
    assert [t["name"] for t in source["tables"]] == ["ibge_municipios", "ibge_ufs"]


def test_generate_e_idempotente(tmp_path):
    configs, models = _registry(tmp_path, a="source_name: t1\ntype: csv\n")
    gen.generate(configs, models)
    antes = {p.name: p.read_text() for p in (models / "bronze" / "_generated").iterdir()}
    gen.generate(configs, models)
    depois = {p.name: p.read_text() for p in (models / "bronze" / "_generated").iterdir()}
    assert antes == depois


def test_generate_remove_gerados_de_fontes_retiradas(tmp_path):
    configs, models = _registry(tmp_path, a="source_name: t1\ntype: csv\n",
                                b="source_name: t2\ntype: csv\n")
    gen.generate(configs, models)
    (configs / "b.yaml").unlink()
    gen.generate(configs, models)
    out = models / "bronze" / "_generated"
    assert sorted(p.name for p in out.iterdir()) == ["_sources.yml", "t1.sql"]


def test_generate_nao_toca_em_arquivo_manual(tmp_path):
    configs, models = _registry(tmp_path, a="source_name: t1\ntype: csv\n")
    out = models / "bronze" / "_generated"
    out.mkdir()
    manual = out / "t1.sql"
    manual.write_text("select 1 -- escrito à mão\n")
    extra = out / "notas.yml"
    extra.write_text("version: 2\n")

    gen.generate(configs, models)
    assert manual.read_text() == "select 1 -- escrito à mão\n"
    assert extra.exists()


def test_generate_pula_fonte_com_model_manual_de_mesmo_nome(tmp_path):
    configs, models = _registry(tmp_path, a="source_name: siafi_notas_empenho\ntype: api\n",
                                b="source_name: nova\ntype: api\n")
    (models / "bronze" / "siafi_notas_empenho.sql").write_text("select 1\n")
    files = gen.generate(configs, models)
    assert {f.name for f in files} == {"nova.sql", "_sources.yml"}


def test_models_gerados_no_repo_estao_atualizados(tmp_path):
    """dbt/models/bronze/_generated deve refletir airflow/configs (rode `make dbt-generate`)."""
    import shutil
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    models = tmp_path / "models"
    shutil.copytree(root / "dbt" / "models", models)
    shutil.rmtree(models / "bronze" / gen.GENERATED_DIRNAME)
    gen.generate(root / "airflow" / "configs", models)

    gerado = models / "bronze" / gen.GENERATED_DIRNAME
    esperado = {p.name: p.read_text() for p in gerado.iterdir()}
    atual = {p.name: p.read_text()
             for p in (root / "dbt" / "models" / "bronze" / gen.GENERATED_DIRNAME).iterdir()}
    assert atual == esperado, "rode `make dbt-generate` e commite o resultado"
