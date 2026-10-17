"""Gerador de dados mock de um portfólio de projetos de uma mineradora fictícia.

Cria uma base SQLite realista (unidades, PMs, projetos, custos mensais, marcos,
riscos, mudanças e documentos de gate) e injeta problemas conhecidos em parte dos
projetos, gravando um *gabarito* para medir se a auditoria os detecta.

Uso:
    python -m pmo_copilot.data.generator            # gera com padrões
    python -m pmo_copilot.data.generator --n 500 --seed 7
"""
from __future__ import annotations

import argparse
import math
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from pmo_copilot import config, domain

# ---------------------------------------------------------------------------
# Cadastros fictícios
# ---------------------------------------------------------------------------
EMPRESA = "MineraSul S.A."

UNIDADES = [
    # sigla, nome, país, região, commodity, peso, áreas (para nomes de projetos)
    ("SAZ", "Complexo Serra Azul", "Brasil", "MG", "Minério de ferro", 0.20,
     ["Mina Pico Alto", "Mina Fazendão", "Usina 2", "Barragem B3", "Pátio de produtos"]),
    ("TPJ", "Complexo Tapajós", "Brasil", "PA", "Minério de ferro e cobre", 0.18,
     ["Mina N4", "Mina Cobre Sul", "Usina de concentração", "Barragem do Gelado", "Pilha de estéril PDE-7"]),
    ("ATL", "Porto e Pelotização Atlântico", "Brasil", "ES", "Pelotas / logística portuária", 0.13,
     ["Usina de pelotização 3", "Píer 2", "Virador de vagões VV-4", "Pátio de estocagem", "Subestação portuária"]),
    ("FCL", "Ferrovia Centro-Leste", "Brasil", "MG/ES", "Logística ferroviária", 0.10,
     ["Ramal Itabira", "Oficina de vagões", "Pátio Tubarão", "Trecho Km 340", "CCO ferroviário"]),
    ("AND", "Unidade Andina", "Chile", "Antofagasta", "Cobre", 0.13,
     ["Mina Los Cóndores", "Planta de flotação", "Tranque de relaves", "Planta dessalinizadora", "Lixiviação SX-EW"]),
    ("BOR", "Mina Boreal", "Canadá", "Ontário", "Níquel", 0.09,
     ["Shaft 3", "Concentrador", "Smelter", "Rampa subterrânea", "Planta de pasta"]),
    ("ZAM", "Complexo Zambeze", "Moçambique", "Tete", "Carvão metalúrgico", 0.07,
     ["Mina Chipanga", "Planta de beneficiamento", "Corredor logístico Nacala", "Barragem de rejeitos Z1", "Oficina de frota"]),
    ("COR", "Corporativo", "Brasil", "RJ", "Serviços corporativos", 0.10,
     ["Sede", "Centro de Operações Integradas", "Data center", "Supply chain", "Finanças"]),
]

# Peso de cada tipo de projeto por unidade
PESOS_TIPO = {
    "default": {"Sustaining": 0.50, "Growth": 0.09, "HSE / Compliance": 0.20, "Descarbonização": 0.11, "Digital / TI": 0.10},
    "COR": {"Sustaining": 0.05, "Growth": 0.0, "HSE / Compliance": 0.05, "Descarbonização": 0.10, "Digital / TI": 0.80},
    "FCL": {"Sustaining": 0.60, "Growth": 0.10, "HSE / Compliance": 0.12, "Descarbonização": 0.10, "Digital / TI": 0.08},
}

# Fase do projeto por tipo (Growth tem mais estudos FEL)
PESOS_FASE = {
    "Sustaining":       [0.06, 0.06, 0.08, 0.54, 0.10, 0.16],
    "Growth":           [0.22, 0.22, 0.18, 0.28, 0.05, 0.05],
    "HSE / Compliance": [0.08, 0.10, 0.12, 0.50, 0.08, 0.12],
    "Descarbonização":  [0.20, 0.18, 0.14, 0.34, 0.06, 0.08],
    "Digital / TI":     [0.08, 0.08, 0.10, 0.52, 0.08, 0.14],
}

# CAPEX total (USD): mediana, sigma lognormal, mínimo, máximo
CAPEX_TIPO = {
    "Sustaining": (6e6, 0.9, 0.5e6, 60e6),
    "Growth": (380e6, 0.8, 40e6, 3_000e6),
    "HSE / Compliance": (35e6, 1.0, 2e6, 600e6),
    "Descarbonização": (70e6, 0.9, 5e6, 900e6),
    "Digital / TI": (4e6, 0.8, 0.4e6, 50e6),
}

# Duração da implantação em meses (min, max)
DURACAO_TIPO = {
    "Sustaining": (8, 24),
    "Growth": (24, 60),
    "HSE / Compliance": (12, 42),
    "Descarbonização": (16, 44),
    "Digital / TI": (8, 20),
}

# Percentual do CAPEX gasto em cada fase de estudo
CUSTO_ESTUDO = {"FEL 1": (0.004, 0.01), "FEL 2": (0.01, 0.025), "FEL 3": (0.025, 0.05)}

NOMES_PROJETO = {
    "Sustaining": [
        "Substituição do britador primário — {area}",
        "Substituição da correia transportadora TC-{n} — {area}",
        "Renovação da frota de caminhões fora de estrada — {area}",
        "Reforma da empilhadeira-recuperadora ER-{n} — {area}",
        "Revitalização das bombas de polpa — {area}",
        "Ampliação da subestação 138 kV — {area}",
        "Troca do revestimento do moinho de bolas — {area}",
        "Substituição das peneiras vibratórias — {area}",
        "Sistema de despoeiramento — {area}",
        "Recuperação estrutural de prédios industriais — {area}",
        "Renovação de vagões e locomotivas (lote {n}) — {area}",
        "Adequação do sistema de combate a incêndio — {area}",
        "Reforma do espessador de rejeitos — {area}",
    ],
    "Growth": [
        "Expansão da {area} para +{n} Mtpa",
        "Projeto {codinome} — nova frente de lavra",
        "Nova planta de concentração — {area}",
        "Duplicação do trecho ferroviário — {area}",
        "Projeto {codinome} — abertura de nova cava",
        "Aumento de capacidade de embarque — {area}",
        "Projeto {codinome} — desgargalamento da usina",
    ],
    "HSE / Compliance": [
        "Descaracterização da barragem — {area}",
        "Reforço da barragem a jusante — {area}",
        "Sistema de monitoramento geotécnico — {area}",
        "Disposição de rejeito a seco (filtragem) — {area}",
        "Sistema de alerta de emergência (PAEBM) — {area}",
        "Adequação de máquinas à NR-12 — {area}",
        "Tratamento de efluentes industriais — {area}",
        "Controle de emissões atmosféricas — {area}",
    ],
    "Descarbonização": [
        "Eletrificação da frota de mina — {area}",
        "Parque solar de {n}0 MWp — {area}",
        "Substituição de óleo combustível por gás natural — {area}",
        "Piloto de caminhões elétricos autônomos — {area}",
        "Briquete verde — {area}",
        "Recuperação de calor residual — {area}",
        "Contrato PPA de energia eólica — {area}",
    ],
    "Digital / TI": [
        "Manutenção preditiva com IoT — {area}",
        "Gêmeo digital da usina — {area}",
        "Migração SAP S/4HANA — onda {n}",
        "Despacho inteligente de frota — {area}",
        "Cibersegurança de automação (OT) — {area}",
        "Visão computacional para segurança — {area}",
        "Plataforma de dados e analytics — onda {n}",
    ],
}
CODINOMES = ["Aurora", "Jaguar", "Quartzo", "Serra Nova", "Horizonte", "Atlas", "Tucano", "Andes II",
             "Boreal Deep", "Ipê", "Mandacaru", "Cóndor", "Titan", "Magnetita", "Safira", "Itacolomi"]

PROGRAMAS = {
    "SAZ": ["Programa Serra Azul 2030", "Programa de Descaracterização de Barragens MG"],
    "TPJ": ["Programa Tapajós +40 Mtpa", "Programa Cobre Norte"],
    "ATL": ["Programa Pelotização Verde", "Programa Capacidade Portuária"],
    "FCL": ["Programa Ferrovia Eficiente"],
    "AND": ["Programa Cobre Andes 2029", "Programa Água Dessalinizada"],
    "BOR": ["Programa Boreal Deep"],
    "ZAM": ["Programa Corredor Nacala"],
    "COR": ["Programa Transformação Digital", "Programa Net Zero 2050"],
}

PRIMEIROS_NOMES = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Henrique", "Isabela",
                   "João", "Karina", "Lucas", "Mariana", "Nicolas", "Olívia", "Paulo", "Renata", "Rafael",
                   "Sofia", "Thiago", "Valéria", "Vinícius", "Camila", "Rodrigo", "Patrícia", "Marcelo",
                   "Fernanda", "Gustavo", "Juliana", "André", "Beatriz", "Leonardo", "Larissa", "Matheus"]
NOMES_LOCAIS = {
    "Chile": ["Javiera", "Matías", "Catalina", "Sebastián", "Francisca", "Benjamín", "Constanza", "Ignacio"],
    "Canadá": ["Emily", "Liam", "Olivia", "Noah", "Charlotte", "Ethan", "Chloe", "Mason"],
    "Moçambique": ["Amélia", "Celso", "Graça", "Edson", "Lurdes", "Hélder", "Neusa", "Abílio"],
}
SOBRENOMES = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Rodrigues", "Almeida",
              "Nascimento", "Carvalho", "Gomes", "Martins", "Araújo", "Ribeiro", "Barbosa", "Rocha", "Dias",
              "Moreira", "Teixeira", "Cardoso", "Mendes", "Freitas", "Castro"]
SOBRENOMES_LOCAIS = {
    "Chile": ["González", "Muñoz", "Rojas", "Díaz", "Soto", "Contreras", "Fuentes", "Valenzuela"],
    "Canadá": ["Smith", "Tremblay", "Brown", "Wilson", "MacDonald", "Gagnon", "Taylor", "Roy"],
    "Moçambique": ["Machava", "Cossa", "Sitoe", "Mondlane", "Nhantumbo", "Macuácua", "Chissano", "Tembe"],
}
CERTIFICACOES = ["PMP", "PMP", "IPMA-C", "PRINCE2", "Sem certificação", "Sem certificação"]

RISCOS = [
    ("Licenciamento", "Atraso na emissão da licença de instalação"),
    ("Licenciamento", "Condicionantes ambientais adicionais exigidas pelo órgão"),
    ("Comunidades", "Paralisação por manifestação de comunidades vizinhas"),
    ("Comunidades", "Disputa fundiária na faixa de servidão"),
    ("Geotecnia", "Condições geotécnicas piores que as sondagens indicaram"),
    ("Geotecnia", "Instabilidade de taludes durante escavação"),
    ("Suprimentos", "Atraso na entrega de equipamentos importados"),
    ("Suprimentos", "Fornecedor único para equipamento crítico"),
    ("Mercado", "Variação cambial sobre equipamentos cotados em moeda estrangeira"),
    ("Mercado", "Inflação de aço e cobre acima do previsto"),
    ("Clima", "Período chuvoso acima da média impactando terraplenagem"),
    ("Segurança", "Acidente grave durante montagem eletromecânica"),
    ("Segurança", "Interferência com a operação em andamento"),
    ("Contratual", "Pleito (claim) da construtora por escopo adicional"),
    ("Contratual", "Baixa produtividade da empreiteira de montagem"),
    ("Engenharia", "Revisões tardias de projeto de engenharia"),
    ("Engenharia", "Integração com sistemas legados de automação"),
    ("Recursos", "Falta de mão de obra qualificada na região"),
    ("Tecnologia", "Tecnologia sem histórico em escala industrial"),
    ("Regulatório", "Mudança na norma de segurança de barragens"),
]
PLANOS_RISCO = [
    "Antecipar protocolo e reuniões técnicas com o órgão licenciador",
    "Contratar fornecedor alternativo qualificado",
    "Hedge cambial para pedidos acima de US$ 5 mi",
    "Programa de relacionamento e investimento social com a comunidade",
    "Campanha adicional de sondagens e revisão do projeto geotécnico",
    "Plano de contingência para período chuvoso e resequenciamento",
    "Reforço da equipe de fiscalização de SSMA em campo",
    "Cláusulas contratuais de performance e acompanhamento semanal",
    "Teste piloto antes da implantação em escala",
]

MUDANCAS = [
    "Inclusão de escopo de automação adicional",
    "Readequação do projeto de fundações",
    "Atualização cambial de pacote de equipamentos",
    "Exigência de condicionante ambiental",
    "Aditivo contratual de montagem",
    "Revisão de layout por interferência operacional",
    "Antecipação de compra de itens de longo prazo",
    "Mudança de especificação de material",
]

MARCOS_EXECUCAO = [
    ("Mobilização do canteiro", 0.04, False),
    ("Engenharia de detalhamento concluída", 0.30, True),
    ("Equipamentos críticos entregues no site", 0.55, True),
    ("Obras civis concluídas", 0.70, False),
    ("Montagem eletromecânica concluída", 0.88, True),
    ("Início do comissionamento", 0.95, True),
    ("Aceite operacional", 1.00, True),
]
MARCOS_ESTUDO = [
    ("Kick-off do estudo", 0.0, False),
    ("Relatório intermediário", 0.5, False),
    ("Entrega do relatório final", 0.95, True),
    ("Gate review", 1.05, True),
]

GRUPOS_EXCLUSIVOS = [{"CPI_BAIXO", "CONTINGENCIA"}, {"SPI_BAIXO", "ZUMBI", "PRAZO_VENCIDO"}]


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def curva_s(x: np.ndarray | float) -> np.ndarray:
    """Curva S de avanço (smoothstep): 0→1 para x em [0, 1]."""
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def _resolver_ritmo(x_corte: float, spi_alvo: float) -> float:
    """Encontra o ritmo r tal que S(x*r)/S(min(x,1)) == spi_alvo (bisseção)."""
    base = float(curva_s(min(x_corte, 1.0)))
    lo, hi = 0.05, 3.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if float(curva_s(x_corte * mid)) / base < spi_alvo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


@dataclass
class Contexto:
    rng: np.random.Generator
    corte: date
    pms_por_unidade: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    seq_codigo: dict[str, int] = field(default_factory=dict)
    nomes_usados: set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Geração
# ---------------------------------------------------------------------------
def _nome_pessoa(rng: np.random.Generator, pais: str) -> str:
    if pais in NOMES_LOCAIS and rng.random() < 0.7:
        return f"{rng.choice(NOMES_LOCAIS[pais])} {rng.choice(SOBRENOMES_LOCAIS[pais])}"
    return f"{rng.choice(PRIMEIROS_NOMES)} {rng.choice(SOBRENOMES)}"


def _gerar_cadastros(ctx: Contexto, n_projetos: int):
    rng = ctx.rng
    unidades, programas, pms = [], [], []
    for uid, (sigla, nome, pais, regiao, commodity, peso, _areas) in enumerate(UNIDADES, start=1):
        unidades.append(dict(id=uid, sigla=sigla, nome=nome, pais=pais, regiao=regiao, commodity=commodity))
        for prog in PROGRAMAS[sigla]:
            programas.append(dict(id=len(programas) + 1, nome=prog, unidade_id=uid))
        n_pms = max(3, round(n_projetos * peso / 5.5))
        ctx.pms_por_unidade[sigla] = []
        nomes_unidade: set[str] = set()
        while len(ctx.pms_por_unidade[sigla]) < n_pms:
            nome_pm = _nome_pessoa(rng, pais)
            if nome_pm in nomes_unidade:
                continue
            nomes_unidade.add(nome_pm)
            pid = len(pms) + 1
            email = nome_pm.lower().replace(" ", ".")
            for a, b in zip("áàâãéêíóôõúçñ", "aaaaeeiooouc n".replace(" ", "")):
                email = email.replace(a, b)
            pms.append(dict(id=pid, nome=nome_pm, email=f"{email}@minerasul.com", unidade_id=uid,
                            certificacao=str(rng.choice(CERTIFICACOES))))
            ctx.pms_por_unidade[sigla].append((pid, nome_pm))
    return unidades, programas, pms


def _sortear_problemas(rng: np.random.Generator, fase: str, taxa: float) -> list[str]:
    if rng.random() >= taxa:
        return []
    candidatos = [p for p, fases in domain.PROBLEMAS_INJETAVEIS.items() if fase in fases]
    if not candidatos:
        return []
    qtd = 1 if rng.random() < 0.7 else 2
    escolhidos: list[str] = []
    for p in rng.permutation(candidatos):
        if len(escolhidos) >= qtd:
            break
        if any(p in g and escolhidos and any(e in g for e in escolhidos) for g in GRUPOS_EXCLUSIVOS):
            continue
        escolhidos.append(str(p))
    return escolhidos


def _nome_projeto(ctx: Contexto, tipo: str, areas: list[str]) -> str:
    rng = ctx.rng
    for _ in range(50):
        nome = str(rng.choice(NOMES_PROJETO[tipo])).format(
            area=rng.choice(areas), n=int(rng.integers(2, 9)), codinome=rng.choice(CODINOMES))
        if nome not in ctx.nomes_usados:
            ctx.nomes_usados.add(nome)
            return nome
    nome = f"{nome} (fase {int(rng.integers(2, 5))})"
    ctx.nomes_usados.add(nome)
    return nome


def _gerar_projeto(ctx: Contexto, pid: int, unidade: dict, areas: list[str], programas_unidade: list[dict],
                   taxa_problemas: float) -> dict:
    rng, corte = ctx.rng, ctx.corte
    mes_corte = date(corte.year, corte.month, 1)
    sigla = unidade["sigla"]

    pesos_t = PESOS_TIPO.get(sigla, PESOS_TIPO["default"])
    tipo = str(rng.choice(list(pesos_t), p=np.array(list(pesos_t.values())) / sum(pesos_t.values())))
    fase = str(rng.choice(domain.FASES, p=PESOS_FASE[tipo]))
    problemas = _sortear_problemas(rng, fase, taxa_problemas)

    med, sig, lo, hi = CAPEX_TIPO[tipo]
    capex = float(np.clip(rng.lognormal(math.log(med), sig), lo, hi))
    capex = round(capex, -4)

    # PM (distribuição desigual: alguns PMs acumulam muitos projetos)
    pms_u = ctx.pms_por_unidade[sigla]
    pesos_pm = 1 / np.arange(1, len(pms_u) + 1) ** 0.6
    pm_id, pm_nome = pms_u[int(rng.choice(len(pms_u), p=pesos_pm / pesos_pm.sum()))]

    programa_id = None
    if programas_unidade and (tipo in ("Growth", "Descarbonização", "Digital / TI") and rng.random() < 0.6
                              or rng.random() < 0.08):
        programa_id = int(rng.choice([p["id"] for p in programas_unidade]))

    # ------------------------------------------------------------------ prazos
    em_estudo = fase in domain.FASES_ESTUDO
    if em_estudo:
        duracao = int(rng.integers(4, 13))
        decorrido = max(1, round(duracao * rng.uniform(0.15, 0.9)))
        lo_pct, hi_pct = CUSTO_ESTUDO[fase]
        bac = round(capex * rng.uniform(lo_pct, hi_pct), -3)
        contingencia_pct = 0.10
    else:
        dmin, dmax = DURACAO_TIPO[tipo]
        duracao = int(rng.integers(dmin, dmax + 1))
        if fase == "Execução":
            if "PRAZO_VENCIDO" in problemas:
                decorrido = duracao + int(rng.integers(2, 10))
            elif "CONTINGENCIA" in problemas:
                decorrido = max(6, round(duracao * rng.uniform(0.25, 0.5)))
            else:
                decorrido = max(2, round(duracao * rng.uniform(0.08, 0.9)))
            if {"CPI_BAIXO", "SPI_BAIXO", "ZUMBI"} & set(problemas):
                decorrido = max(decorrido, domain.MESES_MINIMOS_EVM + domain.MESES_ZUMBI + 2)
                duracao = max(duracao, round(decorrido / 0.85))
            if "CONTINGENCIA" in problemas:
                # avanço ≈ curva S(decorrido/duracao): mantém < 50% para o cenário ser coerente
                duracao = max(duracao, math.ceil(decorrido / 0.5))
        elif fase == "Comissionamento":
            decorrido = duracao + int(rng.integers(0, 3))
        else:  # Encerrado
            decorrido = duracao
        bac = capex
        contingencia_pct = rng.uniform(0.10, 0.15)

    if fase == "Encerrado":
        mes_fim = add_months(mes_corte, -int(rng.integers(1, 13)))
        inicio = add_months(mes_fim, -(duracao - 1))
        n_meses = duracao
    else:
        inicio = add_months(mes_corte, -(decorrido - 1))
        n_meses = decorrido
    fim_baseline = add_months(inicio, duracao) - timedelta(days=1)

    contingencia = round(bac * contingencia_pct, -3)

    # ------------------------------------------------------------- desempenho
    cpi_alvo = float(np.clip(rng.normal(1.0, 0.03), 0.95, 1.08))
    spi_alvo = float(np.clip(rng.normal(0.985, 0.03), 0.93, 1.05))
    if "CPI_BAIXO" in problemas:
        cpi_alvo = rng.uniform(0.70, 0.85)
    if "CONTINGENCIA" in problemas:
        cpi_alvo = rng.uniform(0.98, 1.03)
    if "SPI_BAIXO" in problemas:
        spi_alvo = rng.uniform(0.66, 0.85)
    if "PRAZO_VENCIDO" in problemas:
        spi_alvo = rng.uniform(0.86, 0.95)
    if fase == "Comissionamento":
        spi_alvo = min(spi_alvo, rng.uniform(0.95, 0.99))
    if fase == "Encerrado":
        spi_alvo = 1.0

    k = np.arange(1, n_meses + 1)
    x = k / duracao
    pv_acum = bac * curva_s(x)
    ritmo = _resolver_ritmo(x[-1], spi_alvo)
    ev_acum = bac * curva_s(x * ritmo)
    rampa = np.minimum(1.0, k / 5)
    cpi_k = 1 - (1 - cpi_alvo) * rampa
    ac_acum = ev_acum / cpi_k * (1 + rng.normal(0, 0.006, n_meses))
    ac_acum = np.maximum.accumulate(np.maximum(ac_acum, 0))
    if fase == "Encerrado":
        ev_acum[-1] = bac

    if "ZUMBI" in problemas:
        z = int(rng.integers(domain.MESES_ZUMBI, domain.MESES_ZUMBI + 5))
        z = min(z, n_meses - 2)
        ev_acum[-z:] = ev_acum[-z - 1]
        ac_acum[-z:] = ac_acum[-z - 1]

    # Comprometido: realizado + parte do saldo já contratado (POs/contratos)
    gama = rng.uniform(0.25, 0.55)
    restante = np.maximum(bac - ev_acum, 0) / cpi_k
    comp_acum = np.maximum.accumulate(ac_acum + gama * restante * np.minimum(1, k / 3))
    if fase == "Encerrado":
        comp_acum = np.minimum(comp_acum, ac_acum[-1])
        comp_acum[-1] = ac_acum[-1]
        if "COMPROMETIDO_ABERTO" in problemas:
            comp_acum[-1] = ac_acum[-1] + bac * rng.uniform(0.015, 0.05)
    comp_acum = np.maximum(comp_acum, ac_acum)

    pv_m = np.diff(pv_acum, prepend=0.0)
    ev_m = np.diff(ev_acum, prepend=0.0)
    ac_m = np.diff(ac_acum, prepend=0.0)
    opex_pct = rng.uniform(0.04, 0.12) if "OPEX_EM_CAPEX" in problemas else 0.0
    custos = [
        dict(projeto_id=pid, mes=_iso(add_months(inicio, i)), pv=round(pv_m[i], 2), ev=round(ev_m[i], 2),
             ac=round(ac_m[i], 2), ac_opex=round(ac_m[i] * opex_pct, 2), comprometido_acum=round(comp_acum[i], 2))
        for i in range(n_meses)
    ]

    # EAC medido (igual ao que a auditoria vai calcular)
    ev_t, ac_t = float(ev_acum[-1]), float(ac_acum[-1])
    cpi_med = ev_t / ac_t if ac_t > 0 else 1.0
    eac = ac_t if fase == "Encerrado" else ac_t + (bac - ev_t) / cpi_med
    estouro = max(0.0, eac - bac)

    # --------------------------------------------------------------- mudanças
    mudancas = []
    n_mud = int(rng.integers(0, 4)) if not em_estudo else int(rng.integers(0, 2))
    teto_aprovado = contingencia * 0.15
    aprovado_total = 0.0
    for _ in range(n_mud):
        status = str(rng.choice(["Aprovada", "Aprovada", "Rejeitada", "Pendente"]))
        valor = round(min(bac * rng.uniform(0.003, 0.02), max(teto_aprovado - aprovado_total, 0)), -3)
        dias_atras = int(rng.integers(5, max(6, n_meses * 30)))
        data_sol = corte - timedelta(days=dias_atras)
        if status == "Pendente":
            data_sol = corte - timedelta(days=int(rng.integers(3, 45)))
        if status == "Aprovada":
            if valor <= 0:
                status = "Rejeitada"
            else:
                aprovado_total += valor
        mudancas.append(dict(projeto_id=pid, titulo=str(rng.choice(MUDANCAS)), impacto_custo=valor,
                             impacto_prazo_dias=int(rng.integers(0, 90)), status=status,
                             data_solicitacao=_iso(data_sol),
                             data_decisao=None if status == "Pendente" else _iso(
                                 min(corte, data_sol + timedelta(days=int(rng.integers(7, 40)))))))
    if "CONTINGENCIA" in problemas:
        consumo_alvo = contingencia * rng.uniform(0.82, 0.95)
        valor = round(max(consumo_alvo - estouro - aprovado_total, contingencia * 0.3), -3)
        mudancas.append(dict(projeto_id=pid, titulo="Aditivo de escopo — reforço estrutural e pleito da montadora",
                             impacto_custo=valor, impacto_prazo_dias=int(rng.integers(30, 120)), status="Aprovada",
                             data_solicitacao=_iso(corte - timedelta(days=int(rng.integers(40, 120)))),
                             data_decisao=_iso(corte - timedelta(days=int(rng.integers(5, 30))))))
    if "MUDANCA_PENDENTE" in problemas:
        mudancas.append(dict(projeto_id=pid, titulo=str(rng.choice(MUDANCAS)),
                             impacto_custo=round(bac * rng.uniform(0.01, 0.06), -3),
                             impacto_prazo_dias=int(rng.integers(15, 150)), status="Pendente",
                             data_solicitacao=_iso(corte - timedelta(days=int(rng.integers(65, 220)))),
                             data_decisao=None))

    # ------------------------------------------------------------------ marcos
    marcos = []
    modelo = MARCOS_ESTUDO if em_estudo else MARCOS_EXECUCAO
    for nome_m, frac, critico in modelo:
        planejada = inicio + timedelta(days=round(frac * duracao * 30.4))
        real = None
        if planejada < corte - timedelta(days=domain.LIMITE_MARCO_ATRASO_DIAS) or fase == "Encerrado":
            real = min(corte, planejada + timedelta(days=int(rng.integers(0, 40))))
        elif planejada <= corte and rng.random() < 0.5:
            real = min(corte, planejada + timedelta(days=int(rng.integers(0, 20))))
        marcos.append(dict(projeto_id=pid, nome=nome_m, data_planejada=_iso(planejada), data_real=_iso(real),
                           critico=int(critico)))
    if "MARCO_ATRASADO" in problemas:
        alvo = next((m for m in marcos if m["critico"] and m["data_real"] is None), None) \
            or [m for m in marcos if m["critico"]][1]
        alvo["data_planejada"] = _iso(corte - timedelta(days=int(rng.integers(70, 200))))
        alvo["data_real"] = None

    # ------------------------------------------------------------------ riscos
    riscos = []
    n_riscos = int(rng.integers(2, 6)) + (3 if tipo == "Growth" else 0)
    for idx in rng.choice(len(RISCOS), size=min(n_riscos, len(RISCOS)), replace=False):
        cat, titulo = RISCOS[int(idx)]
        prob, imp = int(rng.integers(1, 6)), int(rng.integers(1, 6))
        nivel = domain.nivel_risco(prob, imp)
        status = "Aberto" if (fase != "Encerrado" and rng.random() < 0.8) else "Fechado"
        responsavel = pm_nome if rng.random() < 0.4 else _nome_pessoa(rng, unidade["pais"])
        plano = str(rng.choice(PLANOS_RISCO)) if nivel in ("Alto", "Crítico") or rng.random() < 0.7 else None
        riscos.append(dict(projeto_id=pid, categoria=cat, titulo=titulo, probabilidade=prob, impacto=imp,
                           nivel=nivel, responsavel=responsavel, plano_resposta=plano, status=status))
    for prob_inj in ("RISCO_SEM_DONO", "RISCO_SEM_PLANO"):
        if prob_inj in problemas:
            cat, titulo = RISCOS[int(rng.integers(len(RISCOS)))]
            prob, imp = int(rng.integers(3, 6)), int(rng.integers(4, 6))
            riscos.append(dict(projeto_id=pid, categoria=cat, titulo=titulo, probabilidade=prob, impacto=imp,
                               nivel=domain.nivel_risco(prob, imp),
                               responsavel=None if prob_inj == "RISCO_SEM_DONO" else pm_nome,
                               plano_resposta=None, status="Aberto"))

    # ------------------------------------------------------------- documentos
    docs_obrig = domain.documentos_obrigatorios(fase, tipo)
    faltantes: set[str] = set()
    if "DOC_GATE_AUSENTE" in problemas and docs_obrig:
        qtd = min(len(docs_obrig), int(rng.integers(1, 3)))
        faltantes = {str(d) for d in rng.choice(docs_obrig, size=qtd, replace=False)}
    documentos = [dict(projeto_id=pid, documento=d, status="Não entregue" if d in faltantes else "Aprovado")
                  for d in docs_obrig]

    # ----------------------------------------------------------------- report
    if fase == "Encerrado":
        ultimo_report = add_months(inicio, n_meses) + timedelta(days=int(rng.integers(5, 25)))
    elif "REPORT_ATRASADO" in problemas:
        ultimo_report = corte - timedelta(days=int(rng.integers(45, 160)))
    else:
        ultimo_report = corte - timedelta(days=int(rng.integers(0, 28)))

    ano = inicio.year
    ctx.seq_codigo[sigla] = ctx.seq_codigo.get(sigla, 0) + 1
    codigo = f"{sigla}-{ano}-{ctx.seq_codigo[sigla]:03d}"

    projeto = dict(
        id=pid, codigo=codigo, nome=_nome_projeto(ctx, tipo, areas), unidade_id=unidade["id"],
        programa_id=programa_id, tipo=tipo, fase=fase, pm_id=pm_id,
        status="Encerrado" if fase == "Encerrado" else "Ativo",
        classe_estimativa=domain.CLASSE_ESTIMATIVA[fase],
        capex_estimado=capex, orcamento_base=bac, contingencia=contingencia,
        baseline_aprovada=int(not em_estudo and "SEM_BASELINE" not in problemas),
        data_inicio=_iso(inicio), data_fim_baseline=_iso(fim_baseline),
        data_fim_prevista=_iso(add_months(inicio, max(duracao, math.ceil(duracao / max(ritmo, 0.3)))) - timedelta(days=1)),
        data_ultimo_report=_iso(min(ultimo_report, corte)),
        prioridade_estrategica=int(rng.choice([1, 2, 3, 4, 5], p=[0.1, 0.2, 0.35, 0.2, 0.15])),
    )
    return dict(projeto=projeto, custos=custos, mudancas=mudancas, marcos=marcos, riscos=riscos,
                documentos=documentos, problemas=[(codigo, p) for p in problemas])


def gerar_portfolio(n_projetos: int = 340, seed: int = 42, taxa_problemas: float = 0.27,
                    corte: date = config.DATA_CORTE) -> dict[str, pd.DataFrame]:
    """Gera todas as tabelas do portfólio em memória."""
    ctx = Contexto(rng=np.random.default_rng(seed), corte=corte)
    unidades, programas, pms = _gerar_cadastros(ctx, n_projetos)

    pesos_u = np.array([u[5] for u in UNIDADES])
    acumulado: dict[str, list] = {k: [] for k in ("projetos", "custos_mensais", "mudancas", "marcos",
                                                   "riscos", "documentos_gate", "gabarito")}
    for pid in range(1, n_projetos + 1):
        idx_u = int(ctx.rng.choice(len(UNIDADES), p=pesos_u / pesos_u.sum()))
        unidade = unidades[idx_u]
        progs = [p for p in programas if p["unidade_id"] == unidade["id"]]
        r = _gerar_projeto(ctx, pid, unidade, UNIDADES[idx_u][6], progs, taxa_problemas)
        acumulado["projetos"].append(r["projeto"])
        acumulado["custos_mensais"] += r["custos"]
        acumulado["mudancas"] += r["mudancas"]
        acumulado["marcos"] += r["marcos"]
        acumulado["riscos"] += r["riscos"]
        acumulado["documentos_gate"] += r["documentos"]
        acumulado["gabarito"] += [dict(codigo=c, problema=p) for c, p in r["problemas"]]

    tabelas = {"unidades": pd.DataFrame(unidades), "programas": pd.DataFrame(programas), "pms": pd.DataFrame(pms)}
    tabelas.update({k: pd.DataFrame(v) for k, v in acumulado.items()})
    for nome in ("mudancas", "marcos", "riscos"):
        tabelas[nome].insert(0, "id", range(1, len(tabelas[nome]) + 1))
    tabelas["metadados"] = pd.DataFrame([
        dict(chave="empresa", valor=EMPRESA),
        dict(chave="data_corte", valor=corte.isoformat()),
        dict(chave="moeda", valor="USD"),
        dict(chave="seed", valor=str(seed)),
        dict(chave="n_projetos", valor=str(n_projetos)),
    ])
    return tabelas


def salvar(tabelas: dict[str, pd.DataFrame], db_path: Path = config.DB_PATH,
           gabarito_path: Path = config.GABARITO_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        for nome, df in tabelas.items():
            if nome == "gabarito":
                continue
            df.to_sql(nome, conn, index=False)
        conn.execute("CREATE INDEX idx_custos_projeto ON custos_mensais(projeto_id)")
    tabelas["gabarito"].to_csv(gabarito_path, index=False)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Gera a base mock do portfólio de projetos.")
    parser.add_argument("--n", type=int, default=340, help="quantidade de projetos (padrão: 340)")
    parser.add_argument("--seed", type=int, default=42, help="semente aleatória (padrão: 42)")
    parser.add_argument("--taxa-problemas", type=float, default=0.27,
                        help="fração de projetos com problemas injetados (padrão: 0.27)")
    args = parser.parse_args(argv)

    tabelas = gerar_portfolio(args.n, args.seed, args.taxa_problemas)
    salvar(tabelas)
    p = tabelas["projetos"]
    print(f"✔ {EMPRESA}: {len(p)} projetos gerados em {config.DB_PATH}")
    print(f"  Orçamento total (base + contingência): US$ {(p.orcamento_base + p.contingencia).sum() / 1e9:,.2f} bi")
    print(f"  Problemas injetados: {len(tabelas['gabarito'])} em {tabelas['gabarito'].codigo.nunique()} projetos "
          f"(gabarito em {config.GABARITO_PATH})")
    for nome, df in tabelas.items():
        print(f"  - {nome:<16} {len(df):>7,} linhas")


if __name__ == "__main__":
    main()
