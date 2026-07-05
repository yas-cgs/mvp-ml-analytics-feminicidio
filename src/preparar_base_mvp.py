#!/usr/bin/env python3
"""Prepara a base anonimizada do MVP de Machine Learning.

A unidade de analise e um registro de processo em primeiro grau (G1).
O alvo indica se houve decisao judicial substantiva em ate 730 dias do
ajuizamento, usando os codigos de movimento 219, 220 e 221, ja empregados
nas analises exploratorias do projeto.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


CODIGOS_DECISAO_SUBSTANTIVA = {219, 220, 221}
PRAZO_DIAS = 730

COLUNAS_PUBLICAS = [
    "tribunal",
    "classe_codigo",
    "sistema_nome",
    "formato_nome",
    "ano_ajuizamento",
    "mes_ajuizamento",
    "orgao_julgador_municipio_ibge",
    "quantidade_assuntos",
    "assunto_homicidio_qualificado",
    "assunto_violencia_domestica_mulher",
    "assunto_crime_tentado",
    "assunto_ameaca",
    "assunto_homicidio_simples",
    "assunto_arma",
    "assunto_medida_protetiva",
    "decisao_substantiva_ate_730d",
]

COLUNAS_PROIBIDAS_BASE_PUBLICA = {
    "numeroProcesso",
    "numero_processo",
    "id",
    "id_instancia",
    "orgaoJulgador_nome",
    "orgao_julgador_nome",
    "dataHoraUltimaAtualizacao",
    "@timestamp",
    "data_extracao",
    "data_primeira_decisao",
    "dias_ate_decisao",
    "dias_acompanhamento",
    "codigo_primeira_decisao",
    "nome_primeira_decisao",
    "resultado_judicial",
}


def parse_data_utc(serie: pd.Series) -> pd.Series:
    """Converte datas heterogeneas da API para timestamps sem timezone."""
    return pd.to_datetime(serie, errors="coerce", utc=True).dt.tz_localize(None)


def carregar_assuntos(valor: Any) -> list[dict[str, Any]]:
    if pd.isna(valor):
        return []
    if isinstance(valor, list):
        return [item for item in valor if isinstance(item, dict)]
    try:
        dados = json.loads(valor)
    except (TypeError, json.JSONDecodeError):
        return []
    return [item for item in dados if isinstance(item, dict)]


def codigos_assuntos(valor: Any) -> set[int]:
    codigos: set[int] = set()
    for assunto in carregar_assuntos(valor):
        try:
            codigos.add(int(assunto.get("codigo")))
        except (TypeError, ValueError):
            continue
    return codigos


def nomes_assuntos(valor: Any) -> str:
    nomes = []
    for assunto in carregar_assuntos(valor):
        nome = str(assunto.get("nome") or "").strip().casefold()
        if nome:
            nomes.append(nome)
    return " | ".join(nomes)


def preparar_processos(processos: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    processos_g1 = processos.loc[processos["grau"].eq("G1")].copy()
    processos_g1["data_ajuizamento"] = parse_data_utc(processos_g1["dataAjuizamento"])
    processos_g1["data_ultima_atualizacao"] = parse_data_utc(
        processos_g1["dataHoraUltimaAtualizacao"]
    )

    registros_g1_antes = len(processos_g1)
    processos_g1 = processos_g1.dropna(subset=["numeroProcesso", "data_ajuizamento"])
    registros_g1_com_data_valida = len(processos_g1)
    processos_g1 = processos_g1.sort_values(
        ["numeroProcesso", "data_ajuizamento", "data_ultima_atualizacao"]
    )
    processos_unicos = processos_g1.drop_duplicates("numeroProcesso", keep="first").copy()
    ultima_atualizacao = processos_g1.groupby("numeroProcesso")["data_ultima_atualizacao"].max()
    processos_unicos["data_ultima_atualizacao"] = processos_unicos["numeroProcesso"].map(
        ultima_atualizacao
    )

    processos_unicos["ano_ajuizamento"] = processos_unicos["data_ajuizamento"].dt.year
    processos_unicos["mes_ajuizamento"] = processos_unicos["data_ajuizamento"].dt.month
    processos_unicos["orgao_julgador_municipio_ibge"] = processos_unicos[
        "orgaoJulgador_codigoMunicipioIBGE"
    ].astype("Int64")

    assuntos_codigos = processos_unicos["assuntos"].apply(codigos_assuntos)
    assuntos_nomes = processos_unicos["assuntos"].apply(nomes_assuntos)
    processos_unicos["quantidade_assuntos"] = assuntos_codigos.apply(len)
    processos_unicos["assunto_homicidio_qualificado"] = assuntos_codigos.apply(
        lambda codigos: int(3372 in codigos)
    )
    processos_unicos["assunto_violencia_domestica_mulher"] = assuntos_codigos.apply(
        lambda codigos: int(bool({10948, 10949, 5560, 12194} & codigos))
    )
    processos_unicos["assunto_crime_tentado"] = assuntos_codigos.apply(
        lambda codigos: int(5555 in codigos)
    )
    processos_unicos["assunto_ameaca"] = assuntos_codigos.apply(lambda codigos: int(3402 in codigos))
    processos_unicos["assunto_homicidio_simples"] = assuntos_codigos.apply(
        lambda codigos: int(3370 in codigos)
    )
    processos_unicos["assunto_arma"] = assuntos_nomes.str.contains(
        "arma|sistema nacional de armas", regex=True
    ).astype(int)
    processos_unicos["assunto_medida_protetiva"] = assuntos_nomes.str.contains(
        "medida protetiva", regex=False
    ).astype(int)

    diagnostico = {
        "registros_g1_antes_filtro_data": int(registros_g1_antes),
        "registros_g1_descartados_por_data_ajuizamento_invalida": int(
            registros_g1_antes - registros_g1_com_data_valida
        ),
        "registros_g1_antes_deduplicacao": int(registros_g1_com_data_valida),
        "processos_g1_unicos": int(len(processos_unicos)),
        "duplicidades_removidas_por_numeroProcesso": int(
            registros_g1_com_data_valida - len(processos_unicos)
        ),
    }
    return processos_unicos, diagnostico


def primeira_decisao_substantiva(
    movimentos: pd.DataFrame, processos: pd.DataFrame
) -> pd.DataFrame:
    processos_aux = processos[["numeroProcesso", "data_ajuizamento"]].copy()
    movimentos_decisao = movimentos.loc[
        movimentos["codigo"].isin(CODIGOS_DECISAO_SUBSTANTIVA),
        ["numeroProcesso", "codigo", "nome", "dataHora"],
    ].copy()
    movimentos_decisao["data_primeira_decisao"] = parse_data_utc(movimentos_decisao["dataHora"])
    movimentos_decisao = movimentos_decisao.merge(processos_aux, on="numeroProcesso", how="inner")
    movimentos_decisao["dias_ate_decisao"] = (
        movimentos_decisao["data_primeira_decisao"] - movimentos_decisao["data_ajuizamento"]
    ).dt.total_seconds() / 86400
    movimentos_decisao = movimentos_decisao.loc[
        movimentos_decisao["data_primeira_decisao"].notna()
        & movimentos_decisao["dias_ate_decisao"].ge(0)
    ].copy()

    return (
        movimentos_decisao.sort_values(["numeroProcesso", "data_primeira_decisao", "codigo"])
        .drop_duplicates("numeroProcesso", keep="first")
        .rename(columns={"codigo": "codigo_primeira_decisao", "nome": "nome_primeira_decisao"})
    )


def criar_alvo(processos: pd.DataFrame, decisoes: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    base = processos.merge(
        decisoes[
            [
                "numeroProcesso",
                "data_primeira_decisao",
                "dias_ate_decisao",
                "codigo_primeira_decisao",
            ]
        ],
        on="numeroProcesso",
        how="left",
    )
    base["dias_acompanhamento"] = (
        base["data_ultima_atualizacao"] - base["data_ajuizamento"]
    ).dt.total_seconds() / 86400

    base["decisao_substantiva_ate_730d"] = pd.NA
    base.loc[base["dias_ate_decisao"].le(PRAZO_DIAS), "decisao_substantiva_ate_730d"] = 1
    base.loc[base["dias_ate_decisao"].gt(PRAZO_DIAS), "decisao_substantiva_ate_730d"] = 0
    base.loc[
        base["dias_ate_decisao"].isna() & base["dias_acompanhamento"].ge(PRAZO_DIAS),
        "decisao_substantiva_ate_730d",
    ] = 0

    censurados = base["decisao_substantiva_ate_730d"].isna()
    modelagem = base.loc[~censurados].copy()
    modelagem["decisao_substantiva_ate_730d"] = modelagem[
        "decisao_substantiva_ate_730d"
    ].astype(int)

    diagnostico = {
        "processos_com_decisao_substantiva": int(base["dias_ate_decisao"].notna().sum()),
        "processos_censurados_excluidos": int(censurados.sum()),
        "registros_modelagem": int(len(modelagem)),
        "classe_0": int((modelagem["decisao_substantiva_ate_730d"] == 0).sum()),
        "classe_1": int((modelagem["decisao_substantiva_ate_730d"] == 1).sum()),
    }
    return modelagem, diagnostico


def validar_base_publica(base: pd.DataFrame) -> None:
    proibidas_presentes = sorted(COLUNAS_PROIBIDAS_BASE_PUBLICA & set(base.columns))
    if proibidas_presentes:
        raise ValueError(f"Colunas proibidas na base publica: {proibidas_presentes}")
    if base["decisao_substantiva_ate_730d"].isna().any():
        raise ValueError("A base de modelagem nao pode conter alvo ausente.")
    valores_alvo = set(base["decisao_substantiva_ate_730d"].unique())
    if valores_alvo != {0, 1}:
        raise ValueError(f"Alvo deve conter exatamente as classes 0 e 1; obtido {valores_alvo}.")


def gerar_base(caminho_processos: Path, caminho_movimentos: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    processos = pd.read_parquet(caminho_processos)
    movimentos = pd.read_parquet(
        caminho_movimentos, columns=["numeroProcesso", "codigo", "nome", "dataHora"]
    )

    processos_unicos, diag_processos = preparar_processos(processos)
    decisoes = primeira_decisao_substantiva(movimentos, processos_unicos)
    modelagem, diag_alvo = criar_alvo(processos_unicos, decisoes)

    base_publica = modelagem[COLUNAS_PUBLICAS].copy()
    validar_base_publica(base_publica)

    diagnostico = {
        "codigos_decisao_substantiva": sorted(CODIGOS_DECISAO_SUBSTANTIVA),
        "prazo_dias": PRAZO_DIAS,
        **diag_processos,
        **diag_alvo,
        "colunas_publicas": COLUNAS_PUBLICAS,
    }
    return base_publica, diagnostico


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--processos",
        type=Path,
        default=Path("Data/processos.parquet"),
        help="Caminho do Parquet de processos original.",
    )
    parser.add_argument(
        "--movimentos",
        type=Path,
        default=Path("Data/movimentos.parquet"),
        help="Caminho do Parquet de movimentos original.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("data/mvp/base_modelagem.csv.gz"),
        help="Caminho da base publica compactada.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/mvp/base_modelagem_metadata.json"),
        help="Caminho do arquivo de diagnostico da preparacao.",
    )
    args = parser.parse_args()

    base_publica, diagnostico = gerar_base(args.processos, args.movimentos)

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    base_publica.to_csv(args.saida, index=False, compression="gzip")
    args.metadata.write_text(json.dumps(diagnostico, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(diagnostico, ensure_ascii=False, indent=2))
    print(f"Base salva em: {args.saida} ({args.saida.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
