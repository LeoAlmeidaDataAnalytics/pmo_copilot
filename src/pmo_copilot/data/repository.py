"""Acesso à base SQLite do portfólio."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from pmo_copilot import config

TABELAS = ["unidades", "programas", "pms", "projetos", "custos_mensais", "mudancas", "marcos",
           "riscos", "documentos_gate", "metadados"]


@dataclass
class Portfolio:
    """Todas as tabelas do portfólio carregadas em memória."""
    unidades: pd.DataFrame
    programas: pd.DataFrame
    pms: pd.DataFrame
    projetos: pd.DataFrame
    custos_mensais: pd.DataFrame
    mudancas: pd.DataFrame
    marcos: pd.DataFrame
    riscos: pd.DataFrame
    documentos_gate: pd.DataFrame
    metadados: pd.DataFrame

    @property
    def data_corte(self) -> date:
        valor = self.metadados.set_index("chave").loc["data_corte", "valor"]
        return date.fromisoformat(valor)

    @property
    def empresa(self) -> str:
        return self.metadados.set_index("chave").loc["empresa", "valor"]


def garantir_base(db_path: Path = config.DB_PATH) -> None:
    """Gera a base mock caso ela ainda não exista."""
    if not db_path.exists():
        from pmo_copilot.data.generator import gerar_portfolio, salvar
        salvar(gerar_portfolio(), db_path=db_path)


def carregar_portfolio(db_path: Path = config.DB_PATH) -> Portfolio:
    garantir_base(db_path)
    with sqlite3.connect(db_path) as conn:
        dfs = {t: pd.read_sql_query(f"SELECT * FROM {t}", conn) for t in TABELAS}
    return Portfolio(**dfs)


def carregar_gabarito(path: Path = config.GABARITO_PATH) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["codigo", "problema"])
