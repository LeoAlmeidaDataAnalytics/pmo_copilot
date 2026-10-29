"""Módulo de Observabilidade e Health Check Determinístico (RFC / Kubernetes Probes).

Implementa verificações de Liveness, Readiness e Deep Health Check do sistema:
1. Liveness Probe (`check_liveness`): Verifica se o processo Python/servidor está vivo e responsivo.
2. Readiness / Deep Health Check (`check_system_health`): Avalia todas as dependências críticas:
   - Banco de Dados Relacional SQLite (`data/portfolio.db`): conectividade, integridade das 10 tabelas e latência.
   - Motor Determinístico de EVM & Compliance (`metrics.py`, `compliance.py`): sanidade matemática e catálogo de 16 regras.
   - Conectividade da API Gemini / LLM (`GEMINI_API_KEY` + ping opcional de rede na API Google GenAI).
   - Sistema de Arquivos (`data/` e `reports/`): permissões de leitura/escrita e gabarito oficial.

Segue o padrão de resposta estruturada RFC draft-inadarei-api-health-check (`pass`, `warn`, `fail`)
mapeado para status executivos (`healthy`, `degraded`, `unhealthy`) e códigos HTTP (`200 OK` vs `503 Service Unavailable`).
"""
from __future__ import annotations

import os
import platform
import sqlite3
import time
import urllib.error
import urllib.request
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import numpy as np

from pmo_copilot import __version__, config, domain
from pmo_copilot.analytics import metrics
from pmo_copilot.data import repository

# Momento de inicialização do processo para cálculo de Uptime
PROCESS_START_TIME = time.monotonic()
PROCESS_STARTED_AT_ISO = datetime.now(timezone.utc).isoformat()

ComponentStatus = Literal["healthy", "degraded", "unhealthy"]
RfcStatus = Literal["pass", "warn", "fail"]

STATUS_TO_RFC: dict[ComponentStatus, RfcStatus] = {
    "healthy": "pass",
    "degraded": "warn",
    "unhealthy": "fail",
}


@dataclass
class ComponentHealth:
    """Resultado do diagnóstico de um componente individual da arquitetura."""

    name: str
    status: ComponentStatus
    latency_ms: float
    message: str
    details: dict = field(default_factory=dict)

    @property
    def rfc_status(self) -> RfcStatus:
        return STATUS_TO_RFC[self.status]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["rfc_status"] = self.rfc_status
        return d


@dataclass
class SystemHealthReport:
    """Relatório consolidado de saúde do sistema (Readiness & Deep Health)."""

    status: ComponentStatus
    http_status_code: int
    version: str
    service: str
    timestamp: str
    uptime_seconds: float
    total_latency_ms: float
    components: dict[str, ComponentHealth]

    @property
    def rfc_status(self) -> RfcStatus:
        return STATUS_TO_RFC[self.status]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "rfc_status": self.rfc_status,
            "http_status_code": self.http_status_code,
            "service": self.service,
            "version": self.version,
            "timestamp": self.timestamp,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "started_at": PROCESS_STARTED_AT_ISO,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "environment": {
                "python_version": platform.python_version(),
                "platform": platform.system(),
                "model_configured": config.get_model_name(),
            },
            "checks": {k: v.to_dict() for k, v in self.components.items()},
        }


def get_uptime_seconds() -> float:
    """Retorna o tempo de atividade (uptime) do processo em segundos."""
    return max(0.0, time.monotonic() - PROCESS_START_TIME)


def check_liveness() -> dict:
    """Liveness Probe (`/health/live`): Rápido e leve, atesta apenas que o processo está ativo."""
    return {
        "status": "healthy",
        "rfc_status": "pass",
        "http_status_code": 200,
        "service": "pmo-copilot-minerasul",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(get_uptime_seconds(), 2),
    }


def check_database(db_path: Path = config.DB_PATH) -> ComponentHealth:
    """Verifica conectividade SQLite, existência das 10 tabelas obrigatórias e volume de projetos."""
    t0 = time.perf_counter()
    if not db_path.exists():
        latency = (time.perf_counter() - t0) * 1000
        return ComponentHealth(
            name="Banco de Dados SQLite (Portfólio)",
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Arquivo de banco não encontrado em {db_path.name}",
            details={"db_path": str(db_path), "exists": False},
        )

    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=3.0) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()

            # Verifica se todas as tabelas do domínio existem
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabelas_existentes = {row[0] for row in cur.fetchall()}
            tabelas_faltantes = [t for t in repository.TABELAS if t not in tabelas_existentes]

            if tabelas_faltantes:
                latency = (time.perf_counter() - t0) * 1000
                return ComponentHealth(
                    name="Banco de Dados SQLite (Portfólio)",
                    status="unhealthy",
                    latency_ms=round(latency, 2),
                    message=f"Tabelas obrigatórias ausentes: {', '.join(tabelas_faltantes)}",
                    details={"missing_tables": tabelas_faltantes},
                )

            cur.execute("SELECT COUNT(*) FROM projetos")
            n_projetos = int(cur.fetchone()[0])

            cur.execute("SELECT COUNT(*) FROM riscos WHERE status = 'Aberto'")
            n_riscos_abertos = int(cur.fetchone()[0])

            cur.execute("SELECT valor FROM metadados WHERE chave = 'data_corte'")
            row_corte = cur.fetchone()
            data_corte = row_corte[0] if row_corte else "N/A"

        latency = (time.perf_counter() - t0) * 1000
        db_size_mb = round(db_path.stat().st_size / (1024 * 1024), 2)

        if n_projetos == 0:
            return ComponentHealth(
                name="Banco de Dados SQLite (Portfólio)",
                status="degraded",
                latency_ms=round(latency, 2),
                message="Banco conectado, porém tabela de projetos está vazia.",
                details={"projects_count": 0, "size_mb": db_size_mb},
            )

        return ComponentHealth(
            name="Banco de Dados SQLite (Portfólio)",
            status="healthy",
            latency_ms=round(latency, 2),
            message=f"Operacional ({n_projetos} projetos, corte {data_corte})",
            details={
                "projects_count": n_projetos,
                "open_risks_count": n_riscos_abertos,
                "tables_verified": len(repository.TABELAS),
                "data_corte": data_corte,
                "size_mb": db_size_mb,
            },
        )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ComponentHealth(
            name="Banco de Dados SQLite (Portfólio)",
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Falha na conexão/consulta SQLite: {exc}",
            details={"error": str(exc)},
        )


def check_deterministic_engine() -> ComponentHealth:
    """Executa self-test rápido no motor determinístico de EVM (`metrics.py`) e catálogo de regras (`domain.py`)."""
    t0 = time.perf_counter()
    try:
        # Teste determinístico de sanidade: BAC=100, PV=50, EV=40, AC=50 -> CPI=0.8, SPI=0.8, EAC=125, VAC=-25
        evm_res = metrics.calcular_evm(bac=100.0, pv=50.0, ev=40.0, ac=50.0, encerrado=False)
        math_ok = (
            bool(np.isclose(evm_res["cpi"], 0.8))
            and bool(np.isclose(evm_res["spi"], 0.8))
            and bool(np.isclose(evm_res["eac"], 125.0))
            and bool(np.isclose(evm_res["vac"], -25.0))
        )
        n_regras = len(domain.REGRAS)
        fases_ok = len(domain.FASES) >= 5

        latency = (time.perf_counter() - t0) * 1000
        if not math_ok or n_regras < 16 or not fases_ok:
            return ComponentHealth(
                name="Motor Determinístico EVM & Stage-Gate",
                status="unhealthy",
                latency_ms=round(latency, 2),
                message="Falha de integridade no autoteste de fórmulas EVM ou catálogo de regras.",
                details={"math_ok": math_ok, "rules_count": n_regras, "fases_ok": fases_ok},
            )

        return ComponentHealth(
            name="Motor Determinístico EVM & Stage-Gate",
            status="healthy",
            latency_ms=round(latency, 2),
            message=f"Autoteste EVM 100% íntegro ({n_regras} regras ativas)",
            details={
                "evm_self_test": "passed",
                "rules_catalog_count": n_regras,
                "fel_gates_count": len(domain.FASES),
            },
        )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ComponentHealth(
            name="Motor Determinístico EVM & Stage-Gate",
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Erro no motor determinístico: {exc}",
            details={"error": str(exc)},
        )


def check_gemini_api(verify_network: bool = False, api_key: str | None = None, timeout: float = 3.5) -> ComponentHealth:
    """Verifica a configuração da chave Gemini e, opcionalmente, testa a conectividade real com a API Google GenAI."""
    t0 = time.perf_counter()
    chave = (api_key or config.get_gemini_api_key() or "").strip()
    modelo = config.get_model_name()

    if not chave:
        latency = (time.perf_counter() - t0) * 1000
        return ComponentHealth(
            name="API Google Gemini & Agentes CrewAI",
            status="degraded",
            latency_ms=round(latency, 2),
            message="GEMINI_API_KEY ausente (Dashboard analítico ativo; Chat/CrewAI em espera)",
            details={
                "api_key_configured": False,
                "model": modelo,
                "network_verified": False,
            },
        )

    # Mascaramento seguro da chave (ex: AIza...9xYz)
    key_masked = f"{chave[:4]}...{chave[-4:]}" if len(chave) > 8 else "****"

    if not verify_network:
        latency = (time.perf_counter() - t0) * 1000
        return ComponentHealth(
            name="API Google Gemini & Agentes CrewAI",
            status="healthy",
            latency_ms=round(latency, 2),
            message=f"Chave configurada ({modelo} pronto)",
            details={
                "api_key_configured": True,
                "api_key_masked": key_masked,
                "model": modelo,
                "network_verified": False,
            },
        )

    # Ping leve na API Google Generative Language (listagem de modelos / metadados sem gastar tokens de geração)
    url = f"https://generativelanguage.googleapis.com/v1beta/models?pageSize=1&key={chave}"
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            http_code = resp.getcode()
            payload = json.loads(resp.read().decode("utf-8"))
        latency = (time.perf_counter() - t0) * 1000
        if http_code == 200 and "models" in payload:
            return ComponentHealth(
                name="API Google Gemini & Agentes CrewAI",
                status="healthy",
                latency_ms=round(latency, 2),
                message=f"Conectado à API Google GenAI ({round(latency)} ms)",
                details={
                    "api_key_configured": True,
                    "api_key_masked": key_masked,
                    "model": modelo,
                    "network_verified": True,
                    "endpoint_http_status": http_code,
                },
            )
        return ComponentHealth(
            name="API Google Gemini & Agentes CrewAI",
            status="degraded",
            latency_ms=round(latency, 2),
            message=f"Resposta inesperada da API Gemini (HTTP {http_code})",
            details={
                "api_key_configured": True,
                "model": modelo,
                "network_verified": True,
                "endpoint_http_status": http_code,
            },
        )
    except urllib.error.HTTPError as http_err:
        latency = (time.perf_counter() - t0) * 1000
        motivo = "Chave de API inválida ou sem permissão" if http_err.code in (400, 401, 403) else f"HTTP {http_err.code}"
        return ComponentHealth(
            name="API Google Gemini & Agentes CrewAI",
            status="degraded",
            latency_ms=round(latency, 2),
            message=f"Falha na autenticação/chamada Gemini ({motivo})",
            details={
                "api_key_configured": True,
                "api_key_masked": key_masked,
                "model": modelo,
                "network_verified": True,
                "endpoint_http_status": http_err.code,
            },
        )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ComponentHealth(
            name="API Google Gemini & Agentes CrewAI",
            status="degraded",
            latency_ms=round(latency, 2),
            message=f"Sem alcance de rede para API Gemini ({type(exc).__name__})",
            details={
                "api_key_configured": True,
                "api_key_masked": key_masked,
                "model": modelo,
                "network_verified": True,
                "error": str(exc),
            },
        )


def check_filesystem() -> ComponentHealth:
    """Verifica diretórios de dados (`data/`), relatórios (`reports/`) e gabarito de auditoria."""
    t0 = time.perf_counter()
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        data_writable = os.access(config.DATA_DIR, os.W_OK)
        reports_writable = os.access(config.REPORTS_DIR, os.W_OK)
        gabarito_exists = config.GABARITO_PATH.exists()
        saved_reports = len(list(config.REPORTS_DIR.glob("*.md")))

        latency = (time.perf_counter() - t0) * 1000
        if not data_writable or not reports_writable:
            return ComponentHealth(
                name="Storage & Diretórios (I/O)",
                status="degraded",
                latency_ms=round(latency, 2),
                message="Permissão de escrita restrita em data/ ou reports/",
                details={
                    "data_writable": data_writable,
                    "reports_writable": reports_writable,
                    "gabarito_exists": gabarito_exists,
                },
            )

        return ComponentHealth(
            name="Storage & Diretórios (I/O)",
            status="healthy",
            latency_ms=round(latency, 2),
            message=f"Leitura/Escrita OK ({saved_reports} relatórios salvos)",
            details={
                "data_writable": data_writable,
                "reports_writable": reports_writable,
                "gabarito_exists": gabarito_exists,
                "saved_reports_count": saved_reports,
            },
        )
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000
        return ComponentHealth(
            name="Storage & Diretórios (I/O)",
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Erro de I/O no sistema de arquivos: {exc}",
            details={"error": str(exc)},
        )


def check_system_health(
    verify_gemini_network: bool = False,
    api_key: str | None = None,
    db_path: Path = config.DB_PATH,
) -> SystemHealthReport:
    """Executa a bateria completa de verificações de saúde (Readiness + Deep Health Check).

    Regras de agregação de status:
    - Se qualquer componente essencial (`database`, `engine`, `filesystem`) estiver `unhealthy` -> `unhealthy` (HTTP 503).
    - Se todos estiverem `healthy` -> `healthy` (HTTP 200).
    - Se houver algum `degraded` (ex: chave da API Gemini ainda não preenchida, mas DB e motor EVM 100% funcionais) -> `degraded` (HTTP 200).
    """
    t0 = time.perf_counter()

    comp_db = check_database(db_path=db_path)
    comp_engine = check_deterministic_engine()
    comp_api = check_gemini_api(verify_network=verify_gemini_network, api_key=api_key)
    comp_fs = check_filesystem()

    components = {
        "database": comp_db,
        "deterministic_engine": comp_engine,
        "gemini_api": comp_api,
        "filesystem": comp_fs,
    }

    statuses = [c.status for c in components.values()]
    if "unhealthy" in statuses:
        overall_status: ComponentStatus = "unhealthy"
        http_code = 503
    elif "degraded" in statuses:
        overall_status = "degraded"
        http_code = 200
    else:
        overall_status = "healthy"
        http_code = 200

    total_latency = (time.perf_counter() - t0) * 1000

    return SystemHealthReport(
        status=overall_status,
        http_status_code=http_code,
        version=__version__,
        service="pmo-copilot-minerasul",
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=get_uptime_seconds(),
        total_latency_ms=round(total_latency, 2),
        components=components,
    )
