"""Testes do relatório (tabelas determinísticas e validação anti-invenção) e das ferramentas dos agentes."""
from __future__ import annotations

import json

import pytest

from pmo_copilot import reporting
from pmo_copilot.analytics import compliance, metrics
from pmo_copilot.data.generator import gerar_portfolio
from pmo_copilot.data.repository import Portfolio


@pytest.fixture(scope="module")
def dados():
    tabelas = gerar_portfolio(n_projetos=60, seed=7)
    port = Portfolio(**{k: v for k, v in tabelas.items() if k != "gabarito"})
    m = metrics.metricas_projetos(port)
    achados = compliance.auditar(port, m)
    return port, compliance.semaforo(m, achados), achados


def test_validador_detecta_codigo_inventado(dados):
    _, m, _ = dados
    real = m.codigo.iloc[0]
    texto = f"O projeto {real} está atrasado, assim como o PRJ-SA-004 e o XYZ-2099-999."
    v = reporting.validar_texto(texto, m)
    assert not v["ok"]
    assert real not in v["inventados"]
    assert "XYZ-2099-999" in v["inventados"]
    assert "PRJ-SA-004" in v["inventados"]


def test_validador_aceita_codigos_reais(dados):
    _, m, _ = dados
    texto = "Atenção a " + ", ".join(m.codigo.head(3))
    assert reporting.validar_texto(texto, m)["ok"]


def test_relatorio_montado_contem_numeros_do_sistema(dados):
    port, m, achados = dados
    texto, val = reporting.montar_relatorio("## Sumário Executivo\nTudo sob controle.", port, m, achados)
    assert val["ok"]
    assert f"{len(m)} (" in texto  # total de projetos calculado pelo sistema
    assert "Anexo A" in texto and "Anexo B" in texto
    # todo projeto da tabela crítica existe na base
    assert set(reporting.REGEX_CODIGO.findall(texto)) <= set(m.codigo)


def test_relatorio_avisa_quando_ia_inventa(dados):
    port, m, achados = dados
    texto, val = reporting.montar_relatorio("O projeto PRJ-SA-004 está crítico.", port, m, achados)
    assert not val["ok"]
    assert "Aviso de validação" in texto


def test_ferramentas_dos_agentes_retornam_json_valido():
    """Regressão: listar_projetos_criticos quebrava com UnboundLocalError (import de numpy)."""
    from pmo_copilot.agents import tools

    for nome in ("obter_kpis_portfolio", "listar_projetos_criticos", "obter_resumo_por_unidade"):
        json.loads(getattr(tools, nome).func())
    criticos = json.loads(tools.listar_projetos_criticos.func())
    assert criticos, "deveria haver projetos vermelhos na base padrão"
    ficha = json.loads(tools.consultar_projeto.func(criticos[0]["codigo"]))
    assert ficha["codigo"] == criticos[0]["codigo"]
    assert "erro" in json.loads(tools.consultar_projeto.func("NAO-0000-000"))
