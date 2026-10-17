"""Testes unitários dos cálculos determinísticos de EVM e métricas financeiras."""
from __future__ import annotations

import numpy as np
import pytest

from pmo_copilot.analytics import metrics
from pmo_copilot.data.generator import gerar_portfolio
from pmo_copilot.data.repository import Portfolio


def test_calcular_evm_basico():
    bac = 100.0
    pv = 50.0
    ev = 40.0
    ac = 50.0

    res = metrics.calcular_evm(bac, pv, ev, ac, encerrado=False)

    # CPI = 40 / 50 = 0.8
    assert np.isclose(res["cpi"], 0.8)
    # SPI = 40 / 50 = 0.8
    assert np.isclose(res["spi"], 0.8)
    # EAC = AC + (BAC - EV) / CPI = 50 + (100 - 40) / 0.8 = 50 + 75 = 125
    assert np.isclose(res["eac"], 125.0)
    # VAC = BAC - EAC = 100 - 125 = -25
    assert np.isclose(res["vac"], -25.0)


def test_calcular_evm_encerrado():
    bac = 200.0
    pv = 200.0
    ev = 200.0
    ac = 180.0

    res = metrics.calcular_evm(bac, pv, ev, ac, encerrado=True)

    assert np.isclose(res["cpi"], 200 / 180)
    assert np.isclose(res["eac"], 180.0)  # Projeto encerrado trava o EAC no AC final


def test_metricas_portfolio_consistencia():
    # Gera um portfólio reduzido para teste rápido
    tabelas = gerar_portfolio(n_projetos=20, seed=123)
    port = Portfolio(**{k: v for k, v in tabelas.items() if k != "gabarito"})

    m = metrics.metricas_projetos(port)

    assert len(m) == 20
    assert (m["orcamento_total"] == m["orcamento_base"] + m["contingencia"]).all()
    assert (m["saldo_orcamento"] == m["orcamento_total"] - m["ac"]).all()
    assert (m["contingencia_consumida"] >= 0).all()
