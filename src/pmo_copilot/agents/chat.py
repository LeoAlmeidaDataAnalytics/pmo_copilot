"""Módulo de Chat Interativo do PMO Copilot.

Permite que gerentes, diretores e analistas façam perguntas em linguagem natural
sobre o portfólio de projetos, respondendo sempre com dados exatos das ferramentas determinísticas.
"""
from __future__ import annotations

from crewai import Agent, Crew, Process, Task

from pmo_copilot import config
from pmo_copilot.agents import tools


def criar_agente_chat(api_key: str | None = None) -> Agent:
    """Cria o agente conversacional especialista em portfólio."""
    llm = config.build_llm(api_key=api_key, temperature=0.2)

    return Agent(
        role="Assistente Interativo de Gestão de Portfólio (PMO Copilot)",
        goal="Responder dúvidas e consultas sobre o portfólio de projetos da MineraSul S.A. com precisão absoluta.",
        backstory=(
            "Você é o assistente virtual do PMO Corporativo da MineraSul S.A. "
            "Você tem acesso direto a ferramentas de consulta ao banco de dados do portfólio de projetos (>300 projetos, US$ 14.5 Bi). "
            "Você NUNCA inventa dados ou projetos: sempre executa a ferramenta adequada para obter fatos, números e status reais. "
            "Suas respostas são claras, diretas, estruturadas e práticas para tomada de decisão executiva."
        ),
        tools=[
            tools.obter_kpis_portfolio,
            tools.obter_resumo_por_unidade,
            tools.listar_projetos_criticos,
            tools.filtrar_projetos,
            tools.consultar_projeto,
            tools.listar_riscos_criticos,
            tools.consultar_pm,
        ],
        llm=llm,
        verbose=True,
    )


def responder_pergunta(pergunta: str, historico: list[dict] | None = None, api_key: str | None = None) -> str:
    """Processa uma pergunta do usuário (com contexto de histórico) e retorna a resposta fundamentada."""
    agente = criar_agente_chat(api_key=api_key)

    contexto_historico = ""
    if historico:
        # Pega as últimas 3 interações para manter o contexto sem estourar tokens
        ultimas = historico[-4:]
        linhas = []
        for msg in ultimas:
            papel = "Usuário" if msg.get("role") == "user" else "Assistente"
            linhas.append(f"{papel}: {msg.get('content', '')}")
        contexto_historico = "\nHistórico recente da conversa:\n" + "\n".join(linhas) + "\n---\n"

    instrucao = (
        f"{contexto_historico}"
        f"Pergunta atual do usuário: \"{pergunta}\"\n\n"
        "INSTRUÇÕES OBRIGATÓRIAS:\n"
        "1. Identifique qual ferramenta é necessária para responder (ex: filtrar_projetos, consultar_projeto, listar_riscos_criticos, etc.).\n"
        "2. Execute a ferramenta e use EXCLUSIVAMENTE os dados retornados.\n"
        "3. Se perguntarem sobre um projeto pelo código ou nome, use consultar_projeto ou filtrar_projetos.\n"
        "4. Apresente os dados em formato amigável (bullet points, tabelas curtas em Markdown ou destaques).\n"
        "5. Se nenhuma informação for encontrada, informe claramente que não foram localizados registros com os critérios informados."
    )

    tarefa = Task(
        description=instrucao,
        expected_output="Resposta clara, objetiva e estruturada em Markdown, fundamentada exclusivamente nos dados das ferramentas.",
        agent=agente,
    )

    crew = Crew(
        agents=[agente],
        tasks=[tarefa],
        process=Process.sequential,
        verbose=False,
    )

    resultado = crew.kickoff()
    return getattr(resultado, "raw", str(resultado))
