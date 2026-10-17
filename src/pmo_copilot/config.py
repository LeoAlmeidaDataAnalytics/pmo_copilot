"""Configurações centrais: caminhos, variáveis de ambiente e LLM."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# Raiz do repositório (…/src/pmo_copilot/config.py -> sobe 3 níveis)
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
DB_PATH = DATA_DIR / "portfolio.db"
GABARITO_PATH = DATA_DIR / "gabarito.csv"

load_dotenv(ENV_PATH)

# Data de corte dos dados (fechamento do último mês)
DATA_CORTE = date(2026, 9, 30)

DEFAULT_MODEL = "gemini-3.8-flash"


def get_gemini_api_key() -> str | None:
    chave = os.getenv("GEMINI_API_KEY", "").strip()
    return chave or None


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def build_llm(api_key: str | None = None, temperature: float = 0.3):
    """Cria o LLM Gemini do CrewAI. Import tardio para não pesar o dashboard."""
    from crewai import LLM

    chave = api_key or get_gemini_api_key()
    if not chave:
        raise ValueError(
            "GEMINI_API_KEY não encontrada. Defina no arquivo .env ou informe na interface."
        )
    return LLM(model=f"gemini/{get_model_name()}", api_key=chave, temperature=temperature)
