"""Montagem e validação do relatório executivo.

Princípio: **números e tabelas vêm do Python; a IA escreve apenas a análise em prosa.**
Depois de gerado, o texto da IA é validado contra a base (códigos de projeto citados
precisam existir).
"""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from pmo_copilot.analytics import metrics

REGEX_CODIGO = re.compile(r"\b[A-Z]{3}-\d{4}-\d{3}\b")
# Padrões típicos de códigos inventados pelo modelo (ex.: PRJ-SA-004)
REGEX_CODIGO_SUSPEITO = re.compile(r"\b[A-Z]{2,4}-[A-Z]{2,3}-\d{2,4}\b")


def usd(v: float) -> str:
    v = float(v)
    if abs(v) >= 1e9:
        return f"US$ {v / 1e9:,.2f} bi"
    if abs(v) >= 1e6:
        return f"US$ {v / 1e6:,.1f} mi"
    return f"US$ {v / 1e3:,.0f} mil"


def _md_tabela(df: pd.DataFrame) -> str:
    cab = "| " + " | ".join(df.columns) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    linhas = ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([cab, sep, *linhas])


def _fmt_idx(v) -> str:
    return "n/d" if pd.isna(v) else f"{v:.2f}"


def bloco_indicadores(m: pd.DataFrame, data_corte, empresa: str) -> str:
    r = metrics.resumo_portfolio(m).iloc[0]
    saude = m["saude"].value_counts()
    ativos = int(m["ativo"].sum())
    n = len(m)
    linhas = [
        f"# Relatório Executivo de Saúde do Portfólio — {empresa}",
        f"**Data de corte:** {data_corte.strftime('%d/%m/%Y')} · **Moeda:** USD",
        "",
        "## Indicadores consolidados (calculados pelo sistema)",
        "",
        _md_tabela(pd.DataFrame([
            ("Projetos no portfólio", f"{n} ({ativos} ativos, {n - ativos} encerrados)"),
            ("Orçamento total (base + contingência)", usd(r.orcamento_total)),
            ("Realizado (AC)", f"{usd(r.ac)} ({r.pct_realizado:.0%} do orçamento)"),
            ("Comprometido", usd(r.comprometido)),
            ("Saldo a comprometer", usd(r.saldo_a_comprometer)),
            ("EAC projetado (com mudanças aprovadas)", usd(r.eac_total)),
            ("CPI / SPI do portfólio", f"{_fmt_idx(r.cpi)} / {_fmt_idx(r.spi)}"),
            ("Semáforo", f"🔴 {saude.get('🔴 Vermelho', 0)} · 🟡 {saude.get('🟡 Amarelo', 0)} · "
                         f"🟢 {saude.get('🟢 Verde', 0)}"),
        ], columns=["Indicador", "Valor"])),
        "",
    ]
    return "\n".join(linhas)


def tabela_projetos_criticos(m: pd.DataFrame, achados: pd.DataFrame, n: int = 15) -> str:
    top = m[m["saude"] == "🔴 Vermelho"].sort_values(["pontuacao_risco", "orcamento_total"],
                                                      ascending=[False, False]).head(n)
    if top.empty:
        return "_Nenhum projeto em estado vermelho._"
    regras = achados.groupby("codigo")["regra"].apply(lambda s: ", ".join(sorted(set(s))))
    df = pd.DataFrame({
        "Código": top.codigo, "Projeto": top.nome, "Unidade": top.unidade, "PM": top.pm,
        "Fase": top.fase, "Orçamento": top.orcamento_total.map(usd),
        "CPI": top.cpi.map(_fmt_idx), "SPI": top.spi.map(_fmt_idx),
        "Regras violadas": top.codigo.map(regras).fillna(""),
    })
    return _md_tabela(df)


def tabela_unidades(m: pd.DataFrame) -> str:
    r = metrics.resumo_portfolio(m, por="unidade").sort_values("orcamento_total", ascending=False)
    sem = m.groupby(["unidade", "saude"]).size().unstack(fill_value=0)
    for c in ("🔴 Vermelho", "🟡 Amarelo", "🟢 Verde"):
        if c not in sem.columns:
            sem[c] = 0
    df = pd.DataFrame({
        "Unidade": r.unidade, "Projetos": r.projetos, "Orçamento": r.orcamento_total.map(usd),
        "Realizado": r.ac.map(usd), "CPI": r.cpi.map(_fmt_idx), "SPI": r.spi.map(_fmt_idx),
        "🔴": r.unidade.map(sem["🔴 Vermelho"]), "🟡": r.unidade.map(sem["🟡 Amarelo"]),
        "🟢": r.unidade.map(sem["🟢 Verde"]),
    })
    return _md_tabela(df)


def validar_texto(texto: str, m: pd.DataFrame) -> dict:
    """Confere se o texto da IA cita apenas projetos que existem na base."""
    validos = set(m["codigo"])
    citados = set(REGEX_CODIGO.findall(texto))
    inventados = sorted(citados - validos)
    suspeitos = sorted(set(REGEX_CODIGO_SUSPEITO.findall(texto)) - validos - citados)
    return dict(citados=sorted(citados), inventados=inventados + suspeitos,
                ok=not inventados and not suspeitos)


def montar_relatorio(narrativa: str, port, m: pd.DataFrame, achados: pd.DataFrame) -> tuple[str, dict]:
    """Junta as partes numéricas (Python) com a análise da IA e valida o resultado."""
    validacao = validar_texto(narrativa, m)
    partes = [
        bloco_indicadores(m, port.data_corte, port.empresa),
        narrativa.strip(),
        "",
        "## Anexo A — Projetos em estado crítico 🔴 (dados da base)",
        "",
        tabela_projetos_criticos(m, achados),
        "",
        "## Anexo B — Desempenho por unidade (dados da base)",
        "",
        tabela_unidades(m),
        "",
    ]
    if not validacao["ok"]:
        partes += [
            "> ⚠️ **Aviso de validação:** a análise acima cita códigos que não existem na base: "
            + ", ".join(f"`{c}`" for c in validacao["inventados"])
            + ". Desconsidere essas referências e gere o relatório novamente.",
            "",
        ]
    partes.append(f"_Gerado em {datetime.now():%d/%m/%Y %H:%M}. Números e tabelas calculados pelo sistema; "
                  "texto analítico gerado por IA._")
    return "\n".join(partes), validacao
