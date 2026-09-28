from govhub.ingestion import registry


def _write(tmp_path, name, text):
    (tmp_path / name).write_text(text)


def test_load_configs_filtra_por_tipo_e_modo(tmp_path):
    _write(tmp_path, "a.yaml", "source_name: a\ntype: api\n")
    _write(tmp_path, "b.yaml", "source_name: b\ntype: pdf\nextraction_mode: semantic\n")
    _write(tmp_path, "c.yaml", "source_name: c\ntype: pdf\nextraction_mode: structural\n")

    assert [c["source_name"] for c in registry.load_configs(tmp_path)] == ["a", "b", "c"]
    assert [c["source_name"] for c in registry.load_configs(tmp_path, types=("api",))] == ["a"]
    semantic = registry.load_configs(tmp_path, types=("pdf",), extraction_mode="semantic")
    assert [c["source_name"] for c in semantic] == ["b"]


def test_load_configs_ignora_malformados_e_registra_arquivo(tmp_path):
    _write(tmp_path, "ok.yaml", "source_name: ok\n")
    _write(tmp_path, "lista.yaml", "- 1\n- 2\n")
    _write(tmp_path, "quebrado.yaml", "source_name: [\n")

    configs = registry.load_configs(tmp_path)
    assert len(configs) == 1
    assert configs[0][registry.CONFIG_FILE_KEY] == "ok.yaml"


def test_target_table_usa_source_name_normalizado_por_padrao():
    assert registry.target_table({"source_name": "SIAFI-Empenhos 2024"}) == "siafi_empenhos_2024"


def test_target_table_explicito_tem_prioridade():
    cfg = {"source_name": "siafi_empenhos", "target_table": "Notas_Empenho"}
    assert registry.target_table(cfg) == "notas_empenho"


def test_silver_dataset_padrao_e_explicito():
    assert registry.silver_dataset({"source_name": "ibge"}) == "silver://ibge"
    cfg = {"source_name": "ibge", "silver_dataset": "silver://outro"}
    assert registry.silver_dataset(cfg) == "silver://outro"
