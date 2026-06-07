"""
Known semantic groups for Brazilian federal budget domain.
Used to boost candidate key scores when column names match known patterns.
"""

DOMAIN_SEMANTIC_GROUPS = {
    "empenho": [
        "nr_empenho", "num_empenho", "numero_empenho", "empenho",
        "cd_empenho", "cod_empenho", "ne", "nota_empenho",
    ],
    "convenio": [
        "nr_convenio", "num_convenio", "numero_convenio", "convenio",
        "cd_convenio", "cod_convenio",
    ],
    "orgao": [
        "cd_orgao", "cod_orgao", "codigo_orgao", "orgao",
        "nr_orgao", "id_orgao", "sg_orgao",
    ],
    "unidade_orcamentaria": [
        "cd_uo", "cod_uo", "unidade_orcamentaria", "uo",
        "cd_unidade", "cod_unidade",
    ],
    "programa": [
        "cd_programa", "cod_programa", "codigo_programa", "programa",
        "nr_programa",
    ],
    "acao": [
        "cd_acao", "cod_acao", "codigo_acao", "acao",
        "nr_acao",
    ],
    "funcao": [
        "cd_funcao", "cod_funcao", "codigo_funcao", "funcao",
    ],
    "subfuncao": [
        "cd_subfuncao", "cod_subfuncao", "subfuncao",
    ],
    "fonte_recurso": [
        "cd_fonte", "cod_fonte", "fonte_recurso", "fonte",
        "cd_fonte_recurso",
    ],
    "natureza_despesa": [
        "cd_natureza", "cod_natureza", "natureza_despesa",
        "nd", "elemento_despesa", "cd_elemento",
    ],
    "instrumento": [
        "nr_instrumento", "num_instrumento", "instrumento",
        "cd_instrumento", "id_instrumento",
    ],
    "nota_credito": [
        "nr_nc", "nota_credito", "nc", "num_nc", "cd_nc",
    ],
    "exercicio": [
        "exercicio", "ano_exercicio", "ano", "cd_ano",
        "nr_exercicio", "ds_ano",
    ],
    "cpf_cnpj": [
        "cpf", "cnpj", "cpf_cnpj", "nr_cpf", "nr_cnpj",
        "documento", "nr_documento",
    ],
    "municipio": [
        "cd_municipio", "cod_municipio", "municipio", "ibge",
        "cd_ibge", "codigo_ibge",
    ],
    "uf": [
        "uf", "sg_uf", "cd_uf", "estado",
    ],
}

DOMAIN_KEY_PATTERNS = {
    "empenho": r"^\d{4}NE\d{6}$",
    "convenio": r"^\d{6}/\d{4}$",
    "cpf": r"^\d{3}\.\d{3}\.\d{3}-\d{2}$",
    "cnpj": r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$",
    "orgao": r"^\d{5}$",
    "uo": r"^\d{5}$",
    "exercicio": r"^\d{4}$",
}
