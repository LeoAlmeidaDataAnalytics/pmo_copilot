"""Testes do módulo de Chat Interativo do PMO Copilot."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from crewai import LLM

from pmo_copilot.agents import chat


def test_criar_agente_chat():
    llm_valido = LLM(model="gemini/gemini-3.8-flash", api_key="fake-key-test")
    with patch("pmo_copilot.config.build_llm", return_value=llm_valido):
        agente = chat.criar_agente_chat(api_key="fake-key-test")

        assert agente.role == "Assistente Interativo de Gestão de Portfólio (PMO Copilot)"
        # Confere se todas as ferramentas determinísticas necessárias foram atribuídas ao agente
        nomes_tools = [getattr(t, "name", str(t)) for t in agente.tools]
        assert "Obter KPIs Gerais do Portfólio" in nomes_tools
        assert "Filtrar e Buscar Projetos" in nomes_tools
        assert "Consultar Ficha Detalhada de um Projeto" in nomes_tools
        assert "Listar Riscos Críticos do Portfólio" in nomes_tools
        assert "Consultar Desempenho de um Gerente de Projetos (PM)" in nomes_tools


def test_responder_pergunta_orquestracao():
    mock_kickoff = MagicMock()
    mock_kickoff.raw = "Aqui estão os projetos com SPI < 0.9 em Tapajós: TPJ-2025-059 e TPJ-2025-054."

    llm_valido = LLM(model="gemini/gemini-3.8-flash", api_key="fake-key-test")
    with patch("pmo_copilot.config.build_llm", return_value=llm_valido), \
         patch("crewai.Crew.kickoff", return_value=mock_kickoff):

        resposta = chat.responder_pergunta(
            pergunta="Quais projetos de Tapajós estão atrasados?",
            historico=[{"role": "user", "content": "Olá"}],
            api_key="fake-key-test",
        )

        assert "TPJ-2025-059" in resposta
