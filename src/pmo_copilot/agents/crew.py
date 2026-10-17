"""Equipe de agentes CrewAI (PMO Copilot) para auditoria e governança de portfólio."""
from __future__ import annotations

from crewai import Agent, Crew, Process, Task

from pmo_copilot import config
from pmo_copilot.agents import tools


def montar_equipe_pmo(api_key: str | None = None) -> Crew:
    """Configura e retorna a Crew de agentes do PMO Copilot com LLM Gemini."""
    llm = config.build_llm(api_key=api_key)

    # 1. Agente Especialista Integrado de Auditoria, EVM e Riscos
    auditor_senior = Agent(
        role="Auditor Sênior de Portfólio, CAPEX e Riscos",
        goal="Diagnosticar a saúde financeira (EVM), conformidade de stage-gate e matriz de riscos do portfólio.",
        backstory=(
            "Você é um engenheiro sênior com 20 anos de experiência em gestão de megaprojetos de mineração. "
            "Você analisa conjuntamente desvios de CPI/SPI, estouro de orçamento (EAC), queima prematura de contingência, "
            "documentos de stage-gate ausentes, marcos atrasados e riscos críticos sem dono. "
            "Você se baseia estritamente nos fatos e números das ferramentas determinísticas, sem inventar cálculos."
        ),
        tools=[tools.obter_kpis_portfolio, tools.listar_projetos_criticos, tools.obter_resumo_por_unidade],
        llm=llm,
        verbose=True,
    )

    # 2. Líder do PMO / Redator Executivo
    lider_pmo = Agent(
        role="Gerente Geral do PMO Corporativo",
        goal="Consolidar os diagnósticos técnicos em um Relatório Executivo Direcionado à Diretoria e Comitê de Investimentos.",
        backstory=(
            "Você lidera o PMO da multinacional de mineração e se reporta diretamente ao CFO e Diretoria Executiva. "
            "Você traduz os desvios de CAPEX e governança em decisões estratégicas de negócio claras e planos de ação práticos."
        ),
        tools=[tools.obter_kpis_portfolio, tools.obter_resumo_por_unidade],
        llm=llm,
        verbose=True,
    )

    tarefa_diagnostico = Task(
        description=(
            "1. Consulte os KPIs consolidados do portfólio, o resumo por unidade e os projetos mais críticos.\n"
            "2. Elabore um diagnóstico técnico completo cobrindo:\n"
            "   - Desempenho de Custo e Prazo (EVM): CPI e SPI globais, EAC projetado e maiores riscos de estouro de CAPEX.\n"
            "   - Governança e Stage-Gate: projetos em execução sem baseline aprovada, documentos mandatórios pendentes e marcos críticos atrasados.\n"
            "   - Riscos Severos: riscos de nível Crítico/Alto sem responsável definido ou sem plano de contingência.\n"
            "3. Destaque quais complexos mineradores concentram as maiores vulnerabilidades.\n\n"
            "REGRAS: use somente dados retornados pelas ferramentas; cite projetos apenas pelo código exato "
            "retornado; se uma ferramenta falhar, informe que o dado não está disponível em vez de inventar."
        ),
        expected_output="Diagnóstico técnico aprofundado baseado apenas nos dados das ferramentas, com projetos citados pelo código real.",
        agent=auditor_senior,
    )

    regras_dados = (
        "REGRAS OBRIGATÓRIAS:\n"
        "- Use SOMENTE dados retornados pelas ferramentas. Nunca invente projetos, códigos, nomes de PM ou valores.\n"
        "- Cite projetos exclusivamente pelo código exato retornado (ex.: 'SAZ-2025-059'). "
        "Se uma ferramenta falhar ou não trouxer o dado, diga que o dado não está disponível.\n"
        "- NÃO crie tabelas de projetos nem repita os indicadores consolidados: o sistema os anexa automaticamente.\n"
    )

    tarefa_relatorio = Task(
        description=(
            "Com base no diagnóstico técnico gerado, redija a ANÁLISE EXECUTIVA em prosa do relatório mensal de "
            "saúde do portfólio de projetos de capital da MineraSul S.A.\n\n"
            + regras_dados +
            "\nEstrutura (use exatamente estes títulos em Markdown, nível ##):\n"
            "## Sumário Executivo — leitura geral do semáforo e principais mensagens\n"
            "## Análise Financeira e EVM — CPI/SPI, EAC, contingência e unidades mais expostas\n"
            "## Governança e Riscos — baselines, stage-gate, marcos e riscos sem dono ou sem plano\n"
            "## Recomendações para o Comitê de Investimentos — plano de ação para os próximos 30 dias, "
            "com responsável sugerido (cargo, não nome de pessoa inventado)\n\n"
            "Seja objetivo e profissional."
        ),
        expected_output=(
            "Análise executiva em Markdown com as 4 seções pedidas, sem tabelas de projetos e sem dados inventados."
        ),
        agent=lider_pmo,
    )

    crew = Crew(
        agents=[auditor_senior, lider_pmo],
        tasks=[tarefa_diagnostico, tarefa_relatorio],
        process=Process.sequential,
        verbose=True,
        max_rpm=4,  # Respeita o limite do plano gratuito do Gemini (5 RPM)
    )

    return crew
