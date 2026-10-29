"""Testes unitários do módulo de Health Check e Observabilidade (`health.py`)."""
from __future__ import annotations

from pathlib import Path

from pmo_copilot import health
from pmo_copilot.data.generator import gerar_portfolio, salvar


def test_liveness_probe():
    res = health.check_liveness()
    assert res["status"] == "healthy"
    assert res["rfc_status"] == "pass"
    assert res["http_status_code"] == 200
    assert res["service"] == "pmo-copilot-minerasul"
    assert res["uptime_seconds"] >= 0.0


def test_deterministic_engine_probe():
    comp = health.check_deterministic_engine()
    assert comp.status == "healthy"
    assert comp.rfc_status == "pass"
    assert comp.details["evm_self_test"] == "passed"
    assert comp.details["rules_catalog_count"] >= 16


def test_database_probe_missing_file(tmp_path: Path):
    fake_db = tmp_path / "inexistente.db"
    comp = health.check_database(db_path=fake_db)
    assert comp.status == "unhealthy"
    assert comp.rfc_status == "fail"
    assert comp.details["exists"] is False


def test_system_health_aggregation(tmp_path: Path):
    # Cria um banco SQLite temporário válido para testar agregação completa
    db_temp = tmp_path / "test_portfolio.db"
    tabelas = gerar_portfolio(n_projetos=15, seed=77)
    salvar(tabelas, db_path=db_temp, gabarito_path=tmp_path / "gabarito.csv")

    # 1. Com chave de API simulada (sem bater na rede externa) -> healthy (HTTP 200)
    report_ok = health.check_system_health(
        verify_gemini_network=False,
        api_key="AIzaSyFakeKeyForHealthUnitTest123456",
        db_path=db_temp,
    )
    assert report_ok.status == "healthy"
    assert report_ok.rfc_status == "pass"
    assert report_ok.http_status_code == 200
    payload = report_ok.to_dict()
    assert "checks" in payload
    assert payload["checks"]["database"]["status"] == "healthy"
    assert payload["checks"]["deterministic_engine"]["status"] == "healthy"
    assert payload["checks"]["gemini_api"]["status"] == "healthy"
    # Garante que a chave de API nunca vaza em texto aberto no payload de health
    assert "AIzaSyFakeKeyForHealthUnitTest123456" not in str(payload)

    # 2. Com banco de dados ausente -> unhealthy (HTTP 503)
    report_fail = health.check_system_health(
        verify_gemini_network=False,
        api_key="AIzaSyFakeKeyForHealthUnitTest123456",
        db_path=tmp_path / "missing.db",
    )
    assert report_fail.status == "unhealthy"
    assert report_fail.rfc_status == "fail"
    assert report_fail.http_status_code == 503
