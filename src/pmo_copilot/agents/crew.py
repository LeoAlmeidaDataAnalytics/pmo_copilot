"""Equipe de agentes CrewAI (PMO Copilot) para auditoria e governança de portfólio."""
from __future__ import annotations

from crewai import Agent, Crew, Process, Task

from pmo_copilot import config, prompts
from pmo_copilot.agents import tools


def _agente(papel: str, llm, ferramentas: list) -> Agent:
    """Cria um agente cujo backstory é o system prompt composto em `prompts.py`."""
    return Agent(
        role=prompts.role(papel),
        goal=prompts.goal(papel),
        backstory=prompts.montar_system_prompt(papel),
        tools=ferramentas,
        llm=llm,
        verbose=True,
    )


def montar_equipe_pmo(api_key: str | None = None) -> Crew:
    """Configura e retorna a Crew de 4 agentes do PMO Copilot com LLM Gemini."""
    llm = config.build_llm(api_key=api_key)

    controller = _agente(
        prompts.CONTROLLER, llm,
        [tools.obter_kpis_portfolio, tools.obter_resumo_por_unidade, tools.listar_projetos_criticos],
    )
    auditor = _agente(
        prompts.AUDITOR, llm,
        [tools.listar_projetos_criticos, tools.consultar_projeto, tools.filtrar_projetos],
    )
    especialista_riscos = _agente(
        prompts.RISCOS, llm,
        [tools.listar_riscos_criticos, tools.consultar_pm, tools.obter_resumo_por_unidade],
    )
    gerente = _agente(
        prompts.GERENTE, llm,
        [tools.obter_kpis_portfolio, tools.obter_resumo_por_unidade],
    )

    regras_dados = (
        "REGRAS OBRIGATÓRIAS:\n"
        "- Use SOMENTE dados retornados pelas ferramentas. Nunca invente projetos, códigos, nomes de PM ou valores.\n"
        "- Cite projetos exclusivamente pelo código exato retornado. "
        "Se uma ferramenta falhar ou não trouxer o dado, diga que o dado não está disponível.\n"
        "- Não faça nenhum cálculo: cite os números exatamente como as ferramentas os devolvem.\n"
    )

    tarefa_financeira = Task(
        description=(
            "Consulte os KPIs consolidados, o resumo por unidade e os projetos críticos. Elabore o diagnóstico "
            "FINANCEIRO E DE EVM: CPI e SPI globais e por complexo (explique o que significam), EAC projetado versus "
            "orçamento, projetos com maior risco de estouro e contingência quase esgotada, e quais complexos concentram "
            "a maior exposição.\n\n" + regras_dados
        ),
        expected_output="Diagnóstico financeiro e de EVM didático, baseado apenas nos dados das ferramentas, com projetos citados pelo código real.",
        agent=controller,
    )

    tarefa_governanca = Task(
        description=(
            "Consulte os projetos críticos e, quando necessário, a ficha de projetos específicos. Elabore o diagnóstico "
            "de GOVERNANÇA E STAGE-GATE: projetos em implantação sem baseline aprovada, documentos obrigatórios de gate "
            "pendentes, marcos críticos atrasados, projetos zumbis e demais regras violadas, citando regra, severidade "
            "e evidência.\n\n" + regras_dados
        ),
        expected_output="Diagnóstico de governança com achados por projeto (código, regra, severidade, evidência), sem dados inventados.",
        agent=auditor,
    )

    tarefa_riscos = Task(
        description=(
            "Consulte os riscos críticos e altos abertos (com e sem dono/plano) e, quando necessário, a carteira de PMs. "
            "Elabore o diagnóstico de RISCOS E CAPACIDADE: riscos severos sem responsável ou sem plano de resposta, "
            "unidades mais expostas e PMs com carteira acima do limite, com foco em processo e carga de trabalho.\n\n"
            + regras_dados
        ),
        expected_output="Diagnóstico de riscos e capacidade de PMs, citando códigos reais e sem dados inventados.",
        agent=especialista_riscos,
    )

    tarefa_relatorio = Task(
        description=(
            "Com base nos três diagnósticos recebidos (financeiro, governança e riscos), redija a ANÁLISE EXECUTIVA em "
            "prosa do relatório mensal de saúde do portfólio de projetos de capital. Não acrescente fatos novos.\n\n"
            + regras_dados +
            "- NÃO crie tabelas de projetos nem repita os indicadores consolidados: o sistema os anexa automaticamente.\n"
            "\nEstrutura (use exatamente estes títulos em Markdown, nível ##):\n"
            "## Sumário Executivo — leitura geral do semáforo e principais mensagens\n"
            "## Análise Financeira e EVM — CPI/SPI, EAC, contingência e unidades mais expostas\n"
            "## Governança e Riscos — baselines, stage-gate, marcos e riscos sem dono ou sem plano\n"
            "## Recomendações para o Comitê de Investimentos — plano de ação para os próximos 30 dias, "
            "com responsável sugerido (cargo, não nome de pessoa inventado)\n\n"
            "Seja objetivo, didático e profissional; explique brevemente cada métrica citada."
        ),
        expected_output=(
            "Análise executiva em Markdown com as 4 seções pedidas, sem tabelas de projetos e sem dados inventados."
        ),
        agent=gerente,
        context=[tarefa_financeira, tarefa_governanca, tarefa_riscos],
    )

    crew = Crew(
        agents=[controller, auditor, especialista_riscos, gerente],
        tasks=[tarefa_financeira, tarefa_governanca, tarefa_riscos, tarefa_relatorio],
        process=Process.sequential,
        verbose=True,
        max_rpm=4,  # Respeita o limite do plano gratuito do Gemini (5 RPM)
    )

    return crew
