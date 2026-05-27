"""Gera CSVs sintéticos para testar a skill analisar-tabela."""
import csv, random, os
from pathlib import Path

random.seed(42)
OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

ORGAOS = ["26000", "20000", "52000", "36000", "44000"]
UOS    = ["260001", "200002", "520003", "360004", "440005"]
ANOS   = ["2023", "2024"]
ACOES  = ["20RV", "20TP", "8282", "0181", "2004"]
FONTES = ["0100", "0112", "0250"]
NDs    = ["339039", "449051", "339030", "449052", "339014"]


def ne(orgao, ano, seq):
    return f"{ano}NE{seq:06d}"


def cnpj():
    d = [random.randint(0, 9) for _ in range(14)]
    return f"{d[0]:02d}.{d[1]:03d}.{d[2]:03d}/{d[3]:04d}-{d[4]:02d}".replace(
        ".", ""
    ).replace("/", "").replace("-", "")


# ── Tabela 1: Empenhos (bem formada, chave óbvia) ──────────────────────────
rows_a = []
for i in range(200):
    orgao = random.choice(ORGAOS)
    ano   = random.choice(ANOS)
    rows_a.append({
        "nr_empenho":   ne(orgao, ano, i + 1),
        "cd_orgao":     orgao,
        "cd_uo":        random.choice(UOS),
        "exercicio":    ano,
        "cd_acao":      random.choice(ACOES),
        "cd_fonte":     random.choice(FONTES),
        "cd_natureza":  random.choice(NDs),
        "vl_empenho":   f"{random.uniform(1000, 9_000_000):.2f}".replace(".", ","),
        "ds_historico": f"Empenho referente ao contrato nº {random.randint(1,999)}/2024",
    })

with open(OUT / "empenhos.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows_a[0].keys(), delimiter=";")
    w.writeheader(); w.writerows(rows_a)

# ── Tabela 2: Transferências (encoding latin-1, colunas com nomes genéricos) ──
rows_b = []
municipios = [f"{random.randint(1000000,9999999)}" for _ in range(20)]
for i in range(150):
    rows_b.append({
        "campo_1":      f"CONV{random.randint(100000,999999)}/2024",
        "campo_2":      random.choice(["SP","RJ","MG","BA","RS","GO"]),
        "campo_3":      random.choice(municipios),
        "campo_4":      cnpj(),
        "campo_5":      f"{random.uniform(50000, 5_000_000):.2f}".replace(".", ","),
        "campo_6":      random.choice(["FIRMADO","ENCERRADO","EM EXECUÇÃO"]),
        "campo_7":      f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
    })

with open(OUT / "transferencias_latin1.csv", "w", newline="", encoding="latin-1") as f:
    w = csv.DictWriter(f, fieldnames=rows_b[0].keys(), delimiter=";")
    w.writeheader(); w.writerows(rows_b)

# ── Tabela 3: Mista — chave composta, coluna de valor ambígua ──────────────
from itertools import product as iproduct
all_combos = list(iproduct(ORGAOS, ACOES, FONTES))  # 125 combos
random.shuffle(all_combos)
rows_c = []
for orgao, acao, fonte in all_combos[:100]:
    rows_c.append({
        "CO_ORGAO":     orgao,
        "CO_ACAO":      acao,
        "CO_FONTE":     fonte,
        "NO_PROGRAMA":  f"Programa {random.randint(1,20):04d}",
        "VL_DOTACAO":   f"{random.uniform(100000, 50_000_000):.2f}".replace(".", ","),
        "VL_EMPENHADO": f"{random.uniform(10000, 40_000_000):.2f}".replace(".", ","),
        "PC_EXEC":      f"{random.uniform(10,100):.1f}",
    })

with open(OUT / "dotacao_acao.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows_c[0].keys(), delimiter=";")
    w.writeheader(); w.writerows(rows_c)

print("Dados gerados em:", OUT)
for p in OUT.iterdir():
    print(f"  {p.name}: {sum(1 for _ in p.open())-1} linhas")
