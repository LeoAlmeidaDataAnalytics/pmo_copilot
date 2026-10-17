"""Interface de linha de comando para execução do PMO Copilot."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from pmo_copilot import config, reporting
from pmo_copilot.agents.crew import montar_equipe_pmo
from pmo_copilot.analytics import compliance, metrics
from pmo_copilot.data import repository


def gerar_relatorio_executivo(api_key: str | None = None) -> Path:
    """Executa a Crew, monta o relatório (números em Python + análise da IA) e salva em Markdown."""
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("🚀 Iniciando PMO Copilot — Equipe de Agentes de Governança e Portfólio...")
    crew = montar_equipe_pmo(api_key=api_key)
    resultado = crew.kickoff()
    narrativa = getattr(resultado, "raw", str(resultado))

    port = repository.carregar_portfolio()
    m = metrics.metricas_projetos(port)
    achados = compliance.auditar(port, m)
    m = compliance.semaforo(m, achados)
    conteudo, validacao = reporting.montar_relatorio(narrativa, port, m, achados)

    carimbo = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    arquivo_saida = config.REPORTS_DIR / f"relatorio_executivo_pmo_{carimbo}.md"
    arquivo_saida.write_text(conteudo, encoding="utf-8")

    print(f"\n✅ Relatório executivo salvo com sucesso em: {arquivo_saida}")
    if validacao["ok"]:
        print(f"🔎 Validação OK: {len(validacao['citados'])} códigos de projeto citados, todos existem na base.")
    else:
        print(f"⚠️  Validação: a IA citou códigos inexistentes: {', '.join(validacao['inventados'])}")
    return arquivo_saida


def main():
    parser = argparse.ArgumentParser(description="PMO Copilot — Gerador de Relatório Executivo de Portfólio.")
    parser.add_argument("--key", type=str, default=None, help="Chave GEMINI_API_KEY (opcional, senão usa .env)")
    args = parser.parse_args()

    gerar_relatorio_executivo(api_key=args.key)


if __name__ == "__main__":
    main()
