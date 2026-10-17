"""Vocabulário do domínio: fases, tipos de projeto e regras de conformidade do PMO.

Este módulo é compartilhado pelo gerador de dados mock (que injeta problemas)
e pelo motor de auditoria (que precisa detectá-los).
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Fases do ciclo de vida (stage-gate FEL)
# ---------------------------------------------------------------------------
FASES = ["FEL 1", "FEL 2", "FEL 3", "Execução", "Comissionamento", "Encerrado"]
FASES_ESTUDO = ["FEL 1", "FEL 2", "FEL 3"]
FASES_IMPLANTACAO = ["Execução", "Comissionamento"]
FASES_ATIVAS = FASES_ESTUDO + FASES_IMPLANTACAO

CLASSE_ESTIMATIVA = {
    "FEL 1": "Classe 5 (±50%)",
    "FEL 2": "Classe 4 (±30%)",
    "FEL 3": "Classe 3 (±10–15%)",
    "Execução": "Controle (baseline)",
    "Comissionamento": "Controle (baseline)",
    "Encerrado": "Realizado",
}

TIPOS_PROJETO = ["Sustaining", "Growth", "HSE / Compliance", "Descarbonização", "Digital / TI"]
# Tipos que exigem licenciamento ambiental para implantação
TIPOS_LICENCIADOS = {"Growth", "HSE / Compliance", "Descarbonização"}

# Documentos obrigatórios (cumulativos) por fase atual do projeto
_DOCS_FEL2 = ["Business case preliminar", "Estudo de alternativas (FEL 1)"]
_DOCS_FEL3 = _DOCS_FEL2 + ["Estudo conceitual (FEL 2)", "Estimativa Classe 4"]
_DOCS_EXEC = _DOCS_FEL3 + [
    "Projeto básico (FEL 3)",
    "Estimativa Classe 3",
    "Cronograma baseline",
    "Plano de gestão de riscos",
    "Aprovação do Comitê de Investimentos",
]
DOCS_LICENCIAMENTO = {
    "FEL 3": ["Plano de licenciamento ambiental"],
    "Execução": ["Plano de licenciamento ambiental", "Licença de instalação (LI)"],
}


def documentos_obrigatorios(fase: str, tipo: str) -> list[str]:
    """Lista de documentos que o projeto precisa ter aprovados na fase atual."""
    base = {
        "FEL 1": [],
        "FEL 2": _DOCS_FEL2,
        "FEL 3": _DOCS_FEL3,
        "Execução": _DOCS_EXEC,
        "Comissionamento": _DOCS_EXEC + ["Plano de comissionamento"],
        "Encerrado": _DOCS_EXEC
        + ["Plano de comissionamento", "Termo de aceite operacional", "Relatório de lições aprendidas"],
    }[fase]
    docs = list(base)
    if tipo in TIPOS_LICENCIADOS:
        chave = "Execução" if fase in ("Execução", "Comissionamento", "Encerrado") else fase
        docs += DOCS_LICENCIAMENTO.get(chave, [])
    return docs


# ---------------------------------------------------------------------------
# Níveis de risco (matriz probabilidade x impacto 5x5)
# ---------------------------------------------------------------------------
def nivel_risco(probabilidade: int, impacto: int) -> str:
    score = probabilidade * impacto
    if score >= 15:
        return "Crítico"
    if score >= 10:
        return "Alto"
    if score >= 5:
        return "Médio"
    return "Baixo"


# ---------------------------------------------------------------------------
# Limites usados pelas regras
# ---------------------------------------------------------------------------
LIMITE_CPI_ALTO = 0.90
LIMITE_CPI_CRITICO = 0.80
LIMITE_SPI_ALTO = 0.90
LIMITE_SPI_CRITICO = 0.80
LIMITE_CONTINGENCIA_RESTANTE = 0.25   # < 25% da contingência restante…
LIMITE_AVANCO_CONTINGENCIA = 0.60     # …com menos de 60% de avanço físico
LIMITE_REPORT_DIAS = 40
LIMITE_REPORT_DIAS_ALTO = 90
LIMITE_MARCO_ATRASO_DIAS = 60
LIMITE_MUDANCA_PENDENTE_DIAS = 60
LIMITE_OPEX_PCT = 0.02
MESES_ZUMBI = 4
LIMITE_PROJETOS_POR_PM = 6
MESES_MINIMOS_EVM = 6  # CPI/SPI só são confiáveis após alguns meses de execução

# ---------------------------------------------------------------------------
# Regras de conformidade
# ---------------------------------------------------------------------------
SEVERIDADES = ["Crítico", "Alto", "Médio"]
PESO_SEVERIDADE = {"Crítico": 3, "Alto": 2, "Médio": 1}


@dataclass(frozen=True)
class Regra:
    codigo: str
    titulo: str
    severidade: str          # severidade padrão (algumas regras escalam)
    categoria: str           # Financeiro | Prazo | Governança | Riscos
    descricao: str


REGRAS: dict[str, Regra] = {
    r.codigo: r
    for r in [
        Regra("CPI_BAIXO", "Desempenho de custo abaixo do limite", "Alto", "Financeiro",
              f"CPI < {LIMITE_CPI_ALTO} (crítico se < {LIMITE_CPI_CRITICO}): o projeto gasta mais do que entrega."),
        Regra("SPI_BAIXO", "Desempenho de prazo abaixo do limite", "Alto", "Prazo",
              f"SPI < {LIMITE_SPI_ALTO} (crítico se < {LIMITE_SPI_CRITICO}): o projeto está atrasado."),
        Regra("EAC_ESTOURO", "Custo final previsto acima do orçamento total", "Crítico", "Financeiro",
              "EAC (BAC/CPI) excede orçamento base + contingência."),
        Regra("CONTINGENCIA", "Contingência quase esgotada", "Alto", "Financeiro",
              f"Menos de {LIMITE_CONTINGENCIA_RESTANTE:.0%} da contingência restante com avanço físico "
              f"< {LIMITE_AVANCO_CONTINGENCIA:.0%}."),
        Regra("OPEX_EM_CAPEX", "Gastos de natureza OPEX no projeto", "Médio", "Financeiro",
              f"Mais de {LIMITE_OPEX_PCT:.0%} do realizado classificado como OPEX em projeto de capital."),
        Regra("COMPROMETIDO_ABERTO", "Projeto encerrado com compromissos em aberto", "Médio", "Financeiro",
              "Pedidos/contratos não liquidados em projeto já encerrado."),
        Regra("SEM_BASELINE", "Projeto em implantação sem baseline aprovada", "Crítico", "Governança",
              "Execução/comissionamento sem linha de base de custo e prazo aprovada."),
        Regra("DOC_GATE_AUSENTE", "Documento obrigatório de gate ausente", "Alto", "Governança",
              "Documentação exigida pela metodologia stage-gate não foi entregue."),
        Regra("REPORT_ATRASADO", "Status report atrasado", "Médio", "Governança",
              f"Último status report há mais de {LIMITE_REPORT_DIAS} dias (alto se > {LIMITE_REPORT_DIAS_ALTO})."),
        Regra("MUDANCA_PENDENTE", "Solicitação de mudança parada", "Médio", "Governança",
              f"Change request pendente de decisão há mais de {LIMITE_MUDANCA_PENDENTE_DIAS} dias."),
        Regra("ZUMBI", "Projeto zumbi", "Alto", "Governança",
              f"Projeto em execução sem nenhum gasto nos últimos {MESES_ZUMBI} meses."),
        Regra("PRAZO_VENCIDO", "Prazo da baseline vencido", "Alto", "Prazo",
              "Data de término da baseline já passou e o projeto continua em execução."),
        Regra("MARCO_ATRASADO", "Marco crítico atrasado", "Médio", "Prazo",
              f"Marco não concluído com mais de {LIMITE_MARCO_ATRASO_DIAS} dias de atraso."),
        Regra("RISCO_SEM_DONO", "Risco alto/crítico sem responsável", "Alto", "Riscos",
              "Risco aberto de nível Alto ou Crítico sem responsável definido."),
        Regra("RISCO_SEM_PLANO", "Risco alto/crítico sem plano de resposta", "Médio", "Riscos",
              "Risco aberto de nível Alto ou Crítico sem plano de resposta."),
        Regra("PM_SOBRECARREGADO", "PM sobrecarregado", "Médio", "Governança",
              f"PM responsável por mais de {LIMITE_PROJETOS_POR_PM} projetos ativos."),
    ]
}

# Problemas que o gerador injeta e as fases em que fazem sentido
PROBLEMAS_INJETAVEIS: dict[str, list[str]] = {
    "CPI_BAIXO": FASES_IMPLANTACAO,
    "SPI_BAIXO": ["Execução"],
    "CONTINGENCIA": ["Execução"],
    "SEM_BASELINE": ["Execução"],
    "RISCO_SEM_DONO": FASES_ATIVAS,
    "RISCO_SEM_PLANO": FASES_ATIVAS,
    "REPORT_ATRASADO": FASES_ATIVAS,
    "DOC_GATE_AUSENTE": ["FEL 2", "FEL 3", "Execução", "Comissionamento"],
    "MARCO_ATRASADO": ["Execução"],
    "ZUMBI": ["Execução"],
    "OPEX_EM_CAPEX": FASES_IMPLANTACAO,
    "MUDANCA_PENDENTE": FASES_ATIVAS,
    "PRAZO_VENCIDO": ["Execução"],
    "COMPROMETIDO_ABERTO": ["Encerrado"],
}
