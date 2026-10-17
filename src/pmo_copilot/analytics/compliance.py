"""Motor de auditoria do PMO: aplica as regras de conformidade e calcula o semáforo.

Cada achado (issue) informa projeto, regra, severidade e um detalhe legível.
O semáforo de cada projeto segue:
    🔴 Vermelho  — algum achado Crítico ou 2+ achados Altos
    🟡 Amarelo   — algum achado Alto ou 2+ achados Médios
    🟢 Verde     — demais casos
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from pmo_copilot import domain
from pmo_copilot.data.repository import Portfolio

COLUNAS_ACHADOS = ["projeto_id", "codigo", "projeto", "unidade", "pm", "fase", "regra", "titulo",
                   "severidade", "categoria", "detalhe"]


def _usd(v: float) -> str:
    v = float(v)
    if abs(v) >= 1e9:
        return f"US$ {v / 1e9:,.2f} bi"
    if abs(v) >= 1e6:
        return f"US$ {v / 1e6:,.1f} mi"
    return f"US$ {v / 1e3:,.0f} mil"


def _achado(proj: pd.Series, regra: str, detalhe: str, severidade: str | None = None) -> dict:
    r = domain.REGRAS[regra]
    return dict(projeto_id=int(proj.id), codigo=proj.codigo, projeto=proj.nome, unidade=proj.unidade,
                pm=proj.pm, fase=proj.fase, regra=regra, titulo=r.titulo,
                severidade=severidade or r.severidade, categoria=r.categoria, detalhe=detalhe)


def auditar(port: Portfolio, metricas: pd.DataFrame) -> pd.DataFrame:
    """Executa todas as regras e retorna um DataFrame de achados."""
    corte: date = port.data_corte
    achados: list[dict] = []
    m = metricas.set_index("id", drop=False)

    implantacao = m[m.fase.isin(domain.FASES_IMPLANTACAO)]
    ativos = m[m.ativo]
    evm_confiavel = implantacao[implantacao.meses_com_dados >= domain.MESES_MINIMOS_EVM]

    # ----------------------------------------------------------- financeiro
    for _, p in evm_confiavel.iterrows():
        if p.cpi < domain.LIMITE_CPI_ALTO:
            sev = "Crítico" if p.cpi < domain.LIMITE_CPI_CRITICO else "Alto"
            achados.append(_achado(p, "CPI_BAIXO",
                                   f"CPI {p.cpi:.2f}: para cada US$ 1,00 gasto entregou US$ {p.cpi:.2f}. "
                                   f"EAC {_usd(p.eac)} vs BAC {_usd(p.orcamento_base)}.", sev))
        if p.spi < domain.LIMITE_SPI_ALTO:
            sev = "Crítico" if p.spi < domain.LIMITE_SPI_CRITICO else "Alto"
            achados.append(_achado(p, "SPI_BAIXO",
                                   f"SPI {p.spi:.2f}: avanço físico {p.avanco_fisico:.0%} vs planejado "
                                   f"{p.avanco_planejado:.0%}.", sev))

    for _, p in implantacao.iterrows():
        if p.contingencia_restante < 0:
            achados.append(_achado(p, "EAC_ESTOURO",
                                   f"Custo final previsto {_usd(p.eac_total)} supera o orçamento total "
                                   f"{_usd(p.orcamento_total)} em {_usd(-p.variacao_vs_orcamento_total)}."))
        if (p.contingencia > 0 and p.contingencia_restante_pct < domain.LIMITE_CONTINGENCIA_RESTANTE
                and p.avanco_fisico < domain.LIMITE_AVANCO_CONTINGENCIA):
            achados.append(_achado(p, "CONTINGENCIA",
                                   f"Restam {max(p.contingencia_restante_pct, 0):.0%} da contingência "
                                   f"({_usd(max(p.contingencia_restante, 0))}) com apenas {p.avanco_fisico:.0%} "
                                   f"de avanço físico."))
        if p.opex_pct > domain.LIMITE_OPEX_PCT:
            achados.append(_achado(p, "OPEX_EM_CAPEX",
                                   f"{p.opex_pct:.1%} do realizado ({_usd(p.ac_opex)}) classificado como OPEX."))

    for _, p in m[m.fase == "Encerrado"].iterrows():
        if p.comprometido_a_pagar > 1_000:
            achados.append(_achado(p, "COMPROMETIDO_ABERTO",
                                   f"{_usd(p.comprometido_a_pagar)} em pedidos/contratos não liquidados."))

    # ----------------------------------------------------------- governança
    for _, p in implantacao[implantacao.baseline_aprovada == 0].iterrows():
        achados.append(_achado(p, "SEM_BASELINE", f"Projeto em {p.fase} sem baseline aprovada."))

    docs = port.documentos_gate
    faltando = docs[docs.status != "Aprovado"].groupby("projeto_id")["documento"].apply(list)
    for pid, lista in faltando.items():
        if pid in m.index and m.loc[pid, "fase"] != "Encerrado":
            achados.append(_achado(m.loc[pid], "DOC_GATE_AUSENTE", "Não entregue: " + "; ".join(lista)))

    for _, p in ativos.iterrows():
        if p.dias_desde_report > domain.LIMITE_REPORT_DIAS:
            sev = "Alto" if p.dias_desde_report > domain.LIMITE_REPORT_DIAS_ALTO else "Médio"
            achados.append(_achado(p, "REPORT_ATRASADO",
                                   f"Último status report em {p.data_ultimo_report} ({p.dias_desde_report} dias).",
                                   sev))
        if p.mudanca_pendente_max_dias > domain.LIMITE_MUDANCA_PENDENTE_DIAS:
            achados.append(_achado(p, "MUDANCA_PENDENTE",
                                   f"Change request aguardando decisão há {p.mudanca_pendente_max_dias} dias "
                                   f"({_usd(p.mudancas_pendentes_valor)} pendentes)."))

    for _, p in m[(m.fase == "Execução") & (m.meses_sem_gasto >= domain.MESES_ZUMBI)].iterrows():
        achados.append(_achado(p, "ZUMBI", f"Sem lançamentos há {int(p.meses_sem_gasto)} meses, "
                                           f"avanço parado em {p.avanco_fisico:.0%}."))

    # ----------------------------------------------------------- prazo
    for _, p in m[(m.fase == "Execução") & (m.dias_apos_fim_baseline > 0)].iterrows():
        achados.append(_achado(p, "PRAZO_VENCIDO", f"Baseline terminou em {p.data_fim_baseline} "
                                                   f"({p.dias_apos_fim_baseline} dias atrás); avanço "
                                                   f"{p.avanco_fisico:.0%}."))

    mc = port.marcos
    limite_marco = (corte - timedelta(days=domain.LIMITE_MARCO_ATRASO_DIAS)).isoformat()
    atrasados = mc[(mc.critico == 1) & mc.data_real.isna() & (mc.data_planejada < limite_marco)]
    for pid, grp in atrasados.groupby("projeto_id"):
        if pid in m.index and m.loc[pid, "ativo"]:
            desc = "; ".join(f"{r.nome} (previsto {r.data_planejada})" for r in grp.itertuples())
            achados.append(_achado(m.loc[pid], "MARCO_ATRASADO", desc))

    # ----------------------------------------------------------- riscos
    rk = port.riscos
    rk_alto = rk[(rk.status == "Aberto") & rk.nivel.isin(["Alto", "Crítico"])]
    for regra, mascara in (("RISCO_SEM_DONO", rk_alto.responsavel.isna()),
                           ("RISCO_SEM_PLANO", rk_alto.responsavel.notna() & rk_alto.plano_resposta.isna())):
        for pid, grp in rk_alto[mascara].groupby("projeto_id"):
            if pid in m.index and m.loc[pid, "ativo"]:
                desc = "; ".join(f"{r.titulo} [{r.nivel}]" for r in grp.itertuples())
                achados.append(_achado(m.loc[pid], regra, desc))

    # PM sobrecarregado (achado atribuído a cada projeto ativo do PM? não — um por PM, no maior projeto)
    carga = ativos.groupby("pm_id").size()
    for pm_id, qtd in carga[carga > domain.LIMITE_PROJETOS_POR_PM].items():
        maior = ativos[ativos.pm_id == pm_id].sort_values("orcamento_total").iloc[-1]
        achados.append(_achado(maior, "PM_SOBRECARREGADO",
                               f"{maior.pm} responde por {qtd} projetos ativos (limite "
                               f"{domain.LIMITE_PROJETOS_POR_PM})."))

    df = pd.DataFrame(achados, columns=COLUNAS_ACHADOS)
    ordem = {s: i for i, s in enumerate(domain.SEVERIDADES)}
    return df.sort_values(["severidade", "codigo"], key=lambda s: s.map(ordem) if s.name == "severidade" else s,
                          ignore_index=True)


def semaforo(metricas: pd.DataFrame, achados: pd.DataFrame) -> pd.DataFrame:
    """Adiciona colunas de saúde (semáforo, pontuação e contagens) às métricas."""
    cont = achados.pivot_table(index="projeto_id", columns="severidade", values="regra",
                               aggfunc="count", fill_value=0)
    for s in domain.SEVERIDADES:
        if s not in cont.columns:
            cont[s] = 0
    m = metricas.merge(cont[domain.SEVERIDADES], left_on="id", right_index=True, how="left")
    for s in domain.SEVERIDADES:
        m[s] = m[s].fillna(0).astype(int)
    m = m.rename(columns={"Crítico": "n_critico", "Alto": "n_alto", "Médio": "n_medio"})
    m["pontuacao_risco"] = 3 * m.n_critico + 2 * m.n_alto + m.n_medio
    m["saude"] = np.select(
        [(m.n_critico > 0) | (m.n_alto >= 2), (m.n_alto > 0) | (m.n_medio >= 2)],
        ["🔴 Vermelho", "🟡 Amarelo"], default="🟢 Verde")
    regras = achados.groupby("projeto_id")["regra"].apply(lambda s: ", ".join(sorted(set(s))))
    m["achados"] = m.id.map(regras).fillna("")
    return m


def avaliar_gabarito(achados: pd.DataFrame, gabarito: pd.DataFrame) -> dict:
    """Compara achados com os problemas injetados no mock.

    Recall: dos problemas plantados, quantos a auditoria detectou.
    Achados extras: achados de regras 'injetáveis' em projetos sem o problema plantado. Nem todo
    extra é erro — o mock pode gerar o problema por acaso (ex.: SPI baixo "natural") —, mas serve
    para vigiar excesso de alarmes.
    """
    if gabarito.empty:
        return dict(total=0, detectados=0, recall=float("nan"), por_regra=pd.DataFrame(),
                    nao_detectados=gabarito, extras=pd.DataFrame(), precisao=float("nan"))
    detect = set(zip(achados.codigo, achados.regra))
    g = gabarito.copy()
    g["detectado"] = [(c, p) in detect for c, p in zip(g.codigo, g.problema)]
    por_regra = g.groupby("problema")["detectado"].agg(injetados="count", detectados="sum").reset_index()
    por_regra["recall"] = por_regra.detectados / por_regra.injetados

    plantados = set(zip(g.codigo, g.problema))
    regras_inj = set(g.problema)
    rel = achados[achados.regra.isin(regras_inj)]
    extras = rel[[(c, r) not in plantados for c, r in zip(rel.codigo, rel.regra)]]
    extras_por_regra = extras.groupby("regra").size().rename("extras")
    por_regra = por_regra.merge(extras_por_regra, left_on="problema", right_index=True, how="left")
    por_regra["extras"] = por_regra["extras"].fillna(0).astype(int)
    precisao = len(rel[[(c, r) in plantados for c, r in zip(rel.codigo, rel.regra)]]) / len(rel) if len(rel) else float("nan")
    return dict(total=len(g), detectados=int(g.detectado.sum()), recall=float(g.detectado.mean()),
                por_regra=por_regra, nao_detectados=g[~g.detectado], extras=extras, precisao=float(precisao))
