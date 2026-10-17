"""Métricas financeiras e de valor agregado (EVM) por projeto — 100% determinístico.

Glossário:
    BAC  Budget at Completion      orçamento base (sem contingência)
    PV   Planned Value             valor planejado acumulado até a data de corte
    EV   Earned Value              valor do trabalho efetivamente realizado
    AC   Actual Cost               custo realizado acumulado
    CPI  EV / AC                   < 1 → gastando mais do que entrega
    SPI  EV / PV                   < 1 → atrasado
    EAC  AC + (BAC − EV) / CPI     custo final previsto
    VAC  BAC − EAC                 variação no término (negativo = estouro)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pmo_copilot import domain
from pmo_copilot.data.repository import Portfolio


def _div(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, a / b, np.nan)


def calcular_evm(bac, pv, ev, ac, encerrado=None) -> dict[str, np.ndarray]:
    """Fórmulas EVM vetorizadas (aceita escalares ou arrays)."""
    bac, pv, ev, ac = (np.asarray(v, dtype=float) for v in (bac, pv, ev, ac))
    cpi = _div(ev, ac)
    spi = _div(ev, pv)
    cpi_seguro = np.where(np.isnan(cpi) | (cpi <= 0), 1.0, cpi)
    eac = ac + np.maximum(bac - ev, 0) / cpi_seguro
    if encerrado is not None:
        eac = np.where(np.asarray(encerrado, dtype=bool), ac, eac)
    return dict(cpi=cpi, spi=spi, eac=eac, vac=bac - eac, etc=eac - ac,
                avanco_fisico=_div(ev, bac), avanco_planejado=_div(pv, bac))


def _meses_sem_gasto(custos: pd.DataFrame) -> pd.Series:
    """Quantidade de meses consecutivos (até o último mês) sem custo realizado."""
    def contar(serie: pd.Series) -> int:
        n = 0
        for v in serie.to_numpy()[::-1]:
            if v > 0:
                break
            n += 1
        return n
    return custos.sort_values("mes").groupby("projeto_id")["ac"].apply(contar)


def metricas_projetos(port: Portfolio) -> pd.DataFrame:
    """Uma linha por projeto com cadastro + métricas financeiras, EVM e governança."""
    corte = pd.Timestamp(port.data_corte)
    p = port.projetos.copy()

    # Cadastros
    p = p.merge(port.unidades[["id", "sigla", "nome", "pais"]].rename(
        columns={"id": "unidade_id", "nome": "unidade"}), on="unidade_id", how="left")
    p = p.merge(port.programas[["id", "nome"]].rename(columns={"id": "programa_id", "nome": "programa"}),
                on="programa_id", how="left")
    p = p.merge(port.pms[["id", "nome"]].rename(columns={"id": "pm_id", "nome": "pm"}), on="pm_id", how="left")

    # Custos acumulados
    c = port.custos_mensais
    soma = c.groupby("projeto_id").agg(pv=("pv", "sum"), ev=("ev", "sum"), ac=("ac", "sum"),
                                       ac_opex=("ac_opex", "sum"), meses_com_dados=("mes", "count"))
    ultimo = c.sort_values("mes").groupby("projeto_id").tail(1).set_index("projeto_id")
    soma["comprometido"] = ultimo["comprometido_acum"]
    soma["meses_sem_gasto"] = _meses_sem_gasto(c)
    p = p.merge(soma, left_on="id", right_index=True, how="left")
    for col in ("pv", "ev", "ac", "ac_opex", "comprometido", "meses_com_dados", "meses_sem_gasto"):
        p[col] = p[col].fillna(0)

    # Mudanças
    m = port.mudancas
    aprov = m[m.status == "Aprovada"].groupby("projeto_id")["impacto_custo"].sum()
    pend = m[m.status == "Pendente"].copy()
    pend["dias"] = (corte - pd.to_datetime(pend.data_solicitacao)).dt.days
    p["mudancas_aprovadas"] = p.id.map(aprov).fillna(0.0)
    p["mudancas_pendentes_valor"] = p.id.map(pend.groupby("projeto_id")["impacto_custo"].sum()).fillna(0.0)
    p["mudanca_pendente_max_dias"] = p.id.map(pend.groupby("projeto_id")["dias"].max()).fillna(0).astype(int)

    # EVM
    evm = calcular_evm(p.orcamento_base, p.pv, p.ev, p.ac, encerrado=p.fase == "Encerrado")
    for k, v in evm.items():
        p[k] = v

    p["orcamento_total"] = p.orcamento_base + p.contingencia
    p["saldo_orcamento"] = p.orcamento_total - p.ac
    p["saldo_a_comprometer"] = p.orcamento_total - p.comprometido
    p["comprometido_a_pagar"] = p.comprometido - p.ac
    p["estouro_previsto"] = np.maximum(p.eac - p.orcamento_base, 0)
    p["contingencia_consumida"] = p.estouro_previsto + p.mudancas_aprovadas
    p["contingencia_restante"] = p.contingencia - p.contingencia_consumida
    p["contingencia_restante_pct"] = _div(p.contingencia_restante, p.contingencia)
    p["eac_total"] = p.eac + p.mudancas_aprovadas
    p["variacao_vs_orcamento_total"] = p.orcamento_total - p.eac_total
    p["opex_pct"] = _div(p.ac_opex, p.ac)

    # Prazos / governança
    p["dias_desde_report"] = (corte - pd.to_datetime(p.data_ultimo_report)).dt.days
    p["dias_apos_fim_baseline"] = (corte - pd.to_datetime(p.data_fim_baseline)).dt.days
    p["atraso_previsto_dias"] = (pd.to_datetime(p.data_fim_prevista) - pd.to_datetime(p.data_fim_baseline)).dt.days
    p["ativo"] = p.fase.isin(domain.FASES_ATIVAS)
    return p


def resumo_portfolio(metricas: pd.DataFrame, por: str | None = None) -> pd.DataFrame:
    """Agrega o portfólio (opcionalmente por uma coluna: 'unidade', 'tipo', 'fase', 'programa')."""
    cols = ["orcamento_base", "contingencia", "orcamento_total", "pv", "ev", "ac", "comprometido",
            "eac_total", "mudancas_aprovadas", "contingencia_restante"]
    grupo = metricas.groupby(por) if por else metricas.assign(_todos="Portfólio").groupby("_todos")
    r = grupo[cols].sum()
    r.insert(0, "projetos", grupo.size())
    r["cpi"] = _div(r.ev, r.ac)
    r["spi"] = _div(r.ev, r.pv)
    r["saldo_a_comprometer"] = r.orcamento_total - r.comprometido
    r["variacao_vs_orcamento_total"] = r.orcamento_total - r.eac_total
    r["pct_realizado"] = _div(r.ac, r.orcamento_total)
    return r.reset_index().rename(columns={"_todos": "escopo"})


def curva_s_projeto(port: Portfolio, projeto_id: int) -> pd.DataFrame:
    """Série mensal acumulada de PV, EV, AC e comprometido para um projeto."""
    c = port.custos_mensais[port.custos_mensais.projeto_id == projeto_id].sort_values("mes").copy()
    for col in ("pv", "ev", "ac"):
        c[f"{col}_acum"] = c[col].cumsum()
    c["mes"] = pd.to_datetime(c["mes"])
    return c[["mes", "pv_acum", "ev_acum", "ac_acum", "comprometido_acum", "pv", "ac"]]


def curva_s_portfolio(port: Portfolio, projeto_ids: list[int] | None = None) -> pd.DataFrame:
    c = port.custos_mensais
    if projeto_ids is not None:
        c = c[c.projeto_id.isin(projeto_ids)]
    g = c.groupby("mes")[["pv", "ev", "ac"]].sum().sort_index().cumsum().reset_index()
    g = g.rename(columns={"pv": "pv_acum", "ev": "ev_acum", "ac": "ac_acum"})
    g["mes"] = pd.to_datetime(g["mes"])
    return g
