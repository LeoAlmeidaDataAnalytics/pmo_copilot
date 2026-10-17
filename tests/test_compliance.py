"""Testes de conformidade e auditoria de regras de PMO contra o gabarito mock."""
from __future__ import annotations

import pytest

from pmo_copilot.analytics import compliance, metrics
from pmo_copilot.data.generator import gerar_portfolio
from pmo_copilot.data.repository import Portfolio


def test_auditoria_e_recall_gabarito():
    # Gera 50 projetos com semente conhecida
    tabelas = gerar_portfolio(n_projetos=50, seed=999, taxa_problemas=0.3)
    gabarito = tabelas["gabarito"]
    port = Portfolio(**{k: v for k, v in tabelas.items() if k != "gabarito"})

    m = metrics.metricas_projetos(port)
    achados = compliance.auditar(port, m)
    m_saude = compliance.semaforo(m, achados)

    # Verifica se os semáforos são coerentes
    assert set(m_saude["saude"].unique()).issubset({"🔴 Vermelho", "🟡 Amarelo", "🟢 Verde"})

    # Avalia a taxa de detecção contra o gabarito sintético
    resultado = compliance.avaliar_gabarito(achados, gabarito)

    assert resultado["total"] > 0
    # O motor de regras deve detectar mais de 80% dos problemas injetados
    assert resultado["recall"] >= 0.80, f"Recall abaixo do esperado: {resultado['recall']:.1%}"


def test_regras_catalogo():
    from pmo_copilot import domain

    assert len(domain.REGRAS) >= 15
    for cod, r in domain.REGRAS.items():
        assert r.severidade in domain.SEVERIDADES
        assert r.categoria in ["Financeiro", "Prazo", "Governança", "Riscos"]


def test_recall_base_padrao_e_total():
    """Na base padrão (350 projetos, seed 42), todo problema plantado deve ser detectado."""
    tabelas = gerar_portfolio(n_projetos=350, seed=42)
    port = Portfolio(**{k: v for k, v in tabelas.items() if k != "gabarito"})
    achados = compliance.auditar(port, metrics.metricas_projetos(port))
    r = compliance.avaliar_gabarito(achados, tabelas["gabarito"])
    assert r["recall"] == 1.0, f"Não detectados:\n{r['nao_detectados']}"
