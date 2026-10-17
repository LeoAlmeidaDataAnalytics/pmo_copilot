"""Ferramentas determinísticas para os agentes CrewAI consultarem o portfólio.

Garante que os agentes consumam números exatos pré-calculados em Python,
evitando qualquer cálculo manual ou alucinação aritmética pelo LLM.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from crewai.tools import tool

from pmo_copilot.analytics import compliance, metrics
from pmo_copilot.data import repository


def _num(v, casas: int = 2):
    """Arredonda um número; devolve None se for NaN (JSON válido)."""
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), casas)


def _carregar_dados():
    port = repository.carregar_portfolio()
    m = metrics.metricas_projetos(port)
    achados = compliance.auditar(port, m)
    m_saude = compliance.semaforo(m, achados)
    return port, m_saude, achados


@tool("Obter KPIs Gerais do Portfólio")
def obter_kpis_portfolio() -> str:
    """Retorna os indicadores consolidados de todo o portfólio de projetos (CAPEX em USD, EVM e Saúde)."""
    port, m, achados = _carregar_dados()
    resumo = metrics.resumo_portfolio(m).iloc[0]

    cont_saude = m["saude"].value_counts().to_dict()

    dados = {
        "empresa": port.empresa,
        "data_corte": str(port.data_corte),
        "total_projetos": int(resumo["projetos"]),
        "distribuicao_saude": {
            "vermelho_critico": int(cont_saude.get("🔴 Vermelho", 0)),
            "amarelo_alerta": int(cont_saude.get("🟡 Amarelo", 0)),
            "verde_regular": int(cont_saude.get("🟢 Verde", 0)),
        },
        "financeiro_usd": {
            "orcamento_total_com_contingencia": f"US$ {resumo['orcamento_total']:,.2f}",
            "realizado_ac": f"US$ {resumo['ac']:,.2f}",
            "comprometido_total": f"US$ {resumo['comprometido']:,.2f}",
            "saldo_a_comprometer": f"US$ {resumo['saldo_a_comprometer']:,.2f}",
            "eac_projetado_total": f"US$ {resumo['eac_total']:,.2f}",
            "variacao_prevista_vs_orcamento": f"US$ {resumo['variacao_vs_orcamento_total']:,.2f}",
        },
        "desempenho_global_evm": {
            "cpi_portfolio": round(float(resumo["cpi"]), 3),
            "spi_portfolio": round(float(resumo["spi"]), 3),
        },
        "total_achados_auditoria": {
            "criticos": int((achados["severidade"] == "Crítico").sum()),
            "altos": int((achados["severidade"] == "Alto").sum()),
            "medios": int((achados["severidade"] == "Médio").sum()),
        },
    }
    return json.dumps(dados, ensure_ascii=False, indent=2)


@tool("Listar Projetos Críticos do Portfólio")
def listar_projetos_criticos(limite: int = 15) -> str:
    """Retorna os N projetos mais críticos (maior pontuação de risco e piores desvios de CPI/SPI)."""
    _, m, achados = _carregar_dados()

    vermelhos = m[m["saude"] == "🔴 Vermelho"].sort_values(
        by=["pontuacao_risco", "orcamento_total"], ascending=[False, False]
    ).head(limite)

    resultado = []
    for _, p in vermelhos.iterrows():
        p_achados = achados[achados["codigo"] == p["codigo"]][["severidade", "regra", "detalhe"]].to_dict(orient="records")
        resultado.append({
            "codigo": p["codigo"],
            "nome": p["nome"],
            "unidade": p["unidade"],
            "tipo": p["tipo"],
            "fase": p["fase"],
            "pm": p["pm"],
            "orcamento_total_usd": f"US$ {p['orcamento_total']:,.2f}",
            "realizado_usd": f"US$ {p['ac']:,.2f}",
            "cpi": _num(p["cpi"]),
            "spi": _num(p["spi"]),
            "contingencia_restante_pct": f"{p['contingencia_restante_pct']:.1%}",
            "pontuacao_risco": int(p["pontuacao_risco"]),
            "achados_auditoria": p_achados,
        })

    return json.dumps(resultado, ensure_ascii=False, indent=2)


@tool("Obter Resumo por Unidade de Negócio")
def obter_resumo_por_unidade() -> str:
    """Retorna consolidação financeira e quantidade de projetos críticos por complexo/unidade mineradora."""
    _, m, _ = _carregar_dados()
    por_u = metrics.resumo_portfolio(m, por="unidade")

    saude_u = m.groupby(["unidade", "saude"]).size().unstack(fill_value=0)

    resultado = []
    for _, row in por_u.iterrows():
        u_nome = row["unidade"]
        v = int(saude_u.loc[u_nome, "🔴 Vermelho"]) if "🔴 Vermelho" in saude_u.columns and u_nome in saude_u.index else 0
        a = int(saude_u.loc[u_nome, "🟡 Amarelo"]) if "🟡 Amarelo" in saude_u.columns and u_nome in saude_u.index else 0
        g = int(saude_u.loc[u_nome, "🟢 Verde"]) if "🟢 Verde" in saude_u.columns and u_nome in saude_u.index else 0

        resultado.append({
            "unidade": u_nome,
            "projetos": int(row["projetos"]),
            "orcamento_total_usd": f"US$ {row['orcamento_total']:,.2f}",
            "realizado_usd": f"US$ {row['ac']:,.2f}",
            "cpi": _num(row["cpi"]),
            "spi": _num(row["spi"]),
            "saude": {"criticos_vermelho": v, "atencao_amarelo": a, "regular_verde": g},
        })

    return json.dumps(resultado, ensure_ascii=False, indent=2)


@tool("Consultar Ficha Detalhada de um Projeto")
def consultar_projeto(codigo: str) -> str:
    """Retorna o raio-X completo de um projeto específico pelo seu código (ex: 'SAZ-2024-001')."""
    port, m, achados = _carregar_dados()
    p_row = m[m["codigo"] == codigo]
    if p_row.empty:
        return json.dumps({"erro": f"Projeto com código '{codigo}' não encontrado."}, ensure_ascii=False)

    p = p_row.iloc[0]
    pid = int(p["id"])

    # Riscos abertos
    riscos = port.riscos[(port.riscos["projeto_id"] == pid) & (port.riscos["status"] == "Aberto")][
        ["titulo", "nivel", "responsavel", "plano_resposta"]
    ].to_dict(orient="records")

    # Marcos
    marcos = port.marcos[port.marcos["projeto_id"] == pid][
        ["nome", "data_planejada", "data_real", "critico"]
    ].to_dict(orient="records")

    # Documentos
    docs = port.documentos_gate[port.documentos_gate["projeto_id"] == pid][
        ["documento", "status"]
    ].to_dict(orient="records")

    # Achados
    p_achados = achados[achados["codigo"] == codigo][["severidade", "regra", "titulo", "detalhe"]].to_dict(orient="records")

    ficha = {
        "codigo": p["codigo"],
        "nome": p["nome"],
        "unidade": p["unidade"],
        "tipo": p["tipo"],
        "fase": p["fase"],
        "pm": p["pm"],
        "saude": p["saude"],
        "orcamento": {
            "orcamento_base": f"US$ {p['orcamento_base']:,.2f}",
            "contingencia_original": f"US$ {p['contingencia']:,.2f}",
            "contingencia_restante": f"US$ {p['contingencia_restante']:,.2f} ({p['contingencia_restante_pct']:.1%})",
            "realizado_ac": f"US$ {p['ac']:,.2f}",
            "comprometido": f"US$ {p['comprometido']:,.2f}",
            "eac_estimado": f"US$ {p['eac_total']:,.2f}",
        },
        "evm": {
            "cpi": _num(p["cpi"]),
            "spi": _num(p["spi"]),
            "avanco_fisico": f"{p['avanco_fisico']:.1%}",
            "avanco_planejado": f"{p['avanco_planejado']:.1%}",
        },
        "achados_auditoria": p_achados,
        "marcos": marcos,
        "riscos_criticos_altos": [r for r in riscos if r["nivel"] in ("Crítico", "Alto")],
        "documentos_gate": docs,
    }
    return json.dumps(ficha, ensure_ascii=False, indent=2)


@tool("Filtrar e Buscar Projetos")
def filtrar_projetos(
    termo: str = "",
    unidade: str = "",
    tipo: str = "",
    fase: str = "",
    saude: str = "",
    cpi_max: float = 0.0,
    spi_max: float = 0.0,
    pm: str = "",
    limite: int = 15,
) -> str:
    """Busca e filtra projetos por diversos critérios combinados (unidade, tipo, fase, saúde, CPI, SPI, PM ou termo no nome)."""
    _, m, achados = _carregar_dados()
    df = m.copy()

    if termo:
        termo_l = termo.lower()
        df = df[df["nome"].str.lower().str.contains(termo_l) | df["codigo"].str.lower().str.contains(termo_l)]
    if unidade:
        df = df[df["unidade"].str.lower().str.contains(unidade.lower())]
    if tipo:
        df = df[df["tipo"].str.lower().str.contains(tipo.lower())]
    if fase:
        df = df[df["fase"].str.lower().str.contains(fase.lower())]
    if saude:
        df = df[df["saude"].str.contains(saude)]
    if cpi_max > 0:
        df = df[df["cpi"] <= cpi_max]
    if spi_max > 0:
        df = df[df["spi"] <= spi_max]
    if pm:
        df = df[df["pm"].str.lower().str.contains(pm.lower())]

    total_encontrados = len(df)
    df = df.head(limite)

    resultado = []
    for _, p in df.iterrows():
        resultado.append({
            "codigo": p["codigo"],
            "nome": p["nome"],
            "unidade": p["unidade"],
            "tipo": p["tipo"],
            "fase": p["fase"],
            "pm": p["pm"],
            "saude": p["saude"],
            "orcamento_total_usd": f"US$ {p['orcamento_total']:,.0f}",
            "cpi": _num(p["cpi"]),
            "spi": _num(p["spi"]),
            "avanco_fisico": f"{p['avanco_fisico']:.1%}",
            "achados": p["achados"],
        })

    resposta = {
        "total_encontrados": total_encontrados,
        "limite_retornado": limite,
        "projetos": resultado,
    }
    return json.dumps(resposta, ensure_ascii=False, indent=2)


@tool("Listar Riscos Críticos do Portfólio")
def listar_riscos_criticos(
    unidade: str = "",
    apenas_sem_dono: bool = False,
    apenas_sem_plano: bool = False,
    limite: int = 20,
) -> str:
    """Retorna os riscos de nível Crítico ou Alto abertos, com opções de filtrar por unidade, sem responsável ou sem plano."""
    port, m, _ = _carregar_dados()
    rk = port.riscos[(port.riscos["status"] == "Aberto") & port.riscos["nivel"].isin(["Crítico", "Alto"])].copy()
    rk = rk.merge(m[["id", "codigo", "nome", "unidade", "pm"]].rename(columns={"nome": "projeto_nome"}), left_on="projeto_id", right_on="id")

    if unidade:
        rk = rk[rk["unidade"].str.lower().str.contains(unidade.lower())]
    if apenas_sem_dono:
        rk = rk[rk["responsavel"].isna()]
    if apenas_sem_plano:
        rk = rk[rk["plano_resposta"].isna()]

    total = len(rk)
    rk = rk.head(limite)

    resultado = []
    for _, r in rk.iterrows():
        resultado.append({
            "codigo_projeto": r["codigo"],
            "projeto": r["projeto_nome"],
            "unidade": r["unidade"],
            "categoria": r["categoria"],
            "titulo": r["titulo"],
            "nivel": r["nivel"],
            "responsavel": r["responsavel"] if pd.notna(r["responsavel"]) else "SEM RESPONSÁVEL (ALERTA)",
            "plano_resposta": r["plano_resposta"] if pd.notna(r["plano_resposta"]) else "SEM PLANO (ALERTA)",
        })

    return json.dumps({"total_encontrados": total, "riscos": resultado}, ensure_ascii=False, indent=2)


@tool("Consultar Desempenho de um Gerente de Projetos (PM)")
def consultar_pm(nome_pm: str) -> str:
    """Retorna o histórico, número de projetos, sobrecarga e indicadores dos projetos liderados por um PM específico."""
    _, m, _ = _carregar_dados()
    pms_encontrados = m[m["pm"].str.lower().str.contains(nome_pm.lower())]
    if pms_encontrados.empty:
        return json.dumps({"erro": f"Nenhum Gerente de Projeto (PM) encontrado com o nome '{nome_pm}'."}, ensure_ascii=False)

    nome_exato = pms_encontrados.iloc[0]["pm"]
    proj_pm = m[m["pm"] == nome_exato]

    cont_saude = proj_pm["saude"].value_counts().to_dict()

    projetos_lista = []
    for _, p in proj_pm.iterrows():
        projetos_lista.append({
            "codigo": p["codigo"],
            "nome": p["nome"],
            "unidade": p["unidade"],
            "fase": p["fase"],
            "saude": p["saude"],
            "cpi": _num(p["cpi"]),
            "spi": _num(p["spi"]),
            "orcamento_total_usd": f"US$ {p['orcamento_total']:,.0f}",
        })

    resposta = {
        "pm": nome_exato,
        "total_projetos": len(proj_pm),
        "projetos_ativos": int(proj_pm["ativo"].sum()),
        "sobrecarregado": len(proj_pm[proj_pm["ativo"]]) > 6,
        "saude_projetos": cont_saude,
        "projetos": projetos_lista,
    }
    return json.dumps(resposta, ensure_ascii=False, indent=2)

