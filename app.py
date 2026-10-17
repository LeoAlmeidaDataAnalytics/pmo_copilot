"""Dashboard Interativo Executivo Streamlit — PMO Copilot (MineraSul S.A.).

Interface de alta governança AI-First para gestão de portfólio de projetos de capital (CAPEX) em mineração,
com Assistente de IA no topo, cross-filtering dinâmico (estilo PowerBI) entre gráficos e analytics 100% determinístico.
"""
from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pmo_copilot import config, domain
from pmo_copilot.analytics import compliance, metrics
from pmo_copilot.data import repository
from pmo_copilot.data.generator import gerar_portfolio, salvar

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA & ESTILIZAÇÃO EXECUTIVA (DEEP SLATE DARK MODE)
# ==============================================================================
st.set_page_config(
    page_title="PMO Copilot | MineraSul S.A.",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Refinamento geral de containers e cards com borda nativa */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.78) 0%, rgba(15, 23, 42, 0.92) 100%) !important;
        border: 1px solid rgba(51, 65, 85, 0.85) !important;
        border-radius: 14px !important;
        box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.35), inset 0 1px 0 0 rgba(255, 255, 255, 0.05) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(96, 165, 250, 0.45) !important;
    }

    /* Métricas nativas com visual C-Level */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.92) 0%, rgba(15, 23, 42, 0.96) 100%) !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25) !important;
    }
    div[data-testid="stMetricValue"] {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.025em !important;
        color: #F8FAFC !important;
    }
    div[data-testid="stMetricLabel"] {
        font-weight: 500 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.05em !important;
    }

    /* Barra minimalista de contexto no topo */
    .top-context-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        padding: 6px 4px 14px 4px;
        border-bottom: 1px solid rgba(51, 65, 85, 0.45);
        margin-bottom: 10px;
    }
    .top-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 14px;
        font-weight: 600;
        color: #CBD5E1;
    }
    .exec-pill-bar {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }
    .exec-pill {
        background: rgba(30, 41, 59, 0.65);
        border: 1px solid rgba(51, 65, 85, 0.8);
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 11.5px;
        font-weight: 500;
        color: #CBD5E1;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }

    /* Gemini Web Hero & Greeting */
    .gemini-web-wrap {
        text-align: center;
        padding: 22px 12px 14px 12px;
        max-width: 780px;
        margin: 0 auto;
    }
    .gemini-greeting {
        font-size: 34px;
        font-weight: 700;
        letter-spacing: -0.03em;
        line-height: 1.2;
        margin-bottom: 6px;
        background: linear-gradient(90deg, #60A5FA 0%, #A855F7 48%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-block;
    }
    .gemini-sub {
        font-size: 18px;
        font-weight: 400;
        color: #94A3B8;
        letter-spacing: -0.01em;
        margin-top: 2px;
    }

    /* Estilização da barra de digitar estilo Gemini Web (Pill Input) */
    div[data-testid="stChatInput"] {
        max-width: 820px !important;
        margin: 6px auto 10px auto !important;
    }
    div[data-testid="stChatInput"] > div {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 9999px !important;
        padding: 6px 14px !important;
        box-shadow: 0 10px 30px -6px rgba(0, 0, 0, 0.45) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-testid="stChatInput"] > div:focus-within {
        border-color: #60A5FA !important;
        box-shadow: 0 10px 32px -4px rgba(59, 130, 246, 0.28) !important;
    }

    /* Chips de sugestão abaixo da barra de digitar */
    .gemini-chips-row button {
        background-color: rgba(30, 41, 59, 0.65) !important;
        border: 1px solid rgba(51, 65, 85, 0.85) !important;
        border-radius: 9999px !important;
        color: #CBD5E1 !important;
        font-size: 12.5px !important;
        font-weight: 500 !important;
        padding: 6px 14px !important;
        transition: all 0.18s ease !important;
    }
    .gemini-chips-row button:hover {
        background-color: rgba(51, 65, 85, 0.65) !important;
        border-color: #60A5FA !important;
        color: #F8FAFC !important;
    }

    /* Barra de Cross-Filter Estilo PowerBI */
    .powerbi-bar {
        background: linear-gradient(90deg, rgba(59, 130, 246, 0.18) 0%, rgba(30, 41, 59, 0.85) 100%);
        border: 1px solid rgba(96, 165, 250, 0.5);
        border-radius: 12px;
        padding: 10px 16px;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
    }
    .powerbi-chip {
        background: rgba(59, 130, 246, 0.25);
        border: 1px solid #60A5FA;
        color: #F8FAFC;
        border-radius: 999px;
        padding: 3px 11px;
        font-size: 12px;
        font-weight: 600;
    }

    /* Cards Customizados de Auditoria */
    .metric-card {
        background-color: #1E293B !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        border: 1px solid #334155 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3) !important;
        margin-bottom: 10px !important;
        transition: all 0.2s ease-in-out !important;
        color: #F1F5F9 !important;
    }
    .metric-card:hover {
        border-color: #60A5FA !important;
        box-shadow: 0 6px 12px -2px rgba(96, 165, 250, 0.2) !important;
    }

    /* Badges de Semáforo tipo Pill */
    .badge-red {
        background-color: rgba(239, 68, 68, 0.18) !important;
        color: #FCA5A5 !important;
        border: 1px solid rgba(239, 68, 68, 0.45) !important;
        padding: 3px 10px !important;
        border-radius: 9999px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 0.03em !important;
        text-transform: uppercase !important;
    }
    .badge-yellow {
        background-color: rgba(245, 158, 11, 0.18) !important;
        color: #FCD34D !important;
        border: 1px solid rgba(245, 158, 11, 0.45) !important;
        padding: 3px 10px !important;
        border-radius: 9999px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 0.03em !important;
        text-transform: uppercase !important;
    }
    .badge-green {
        background-color: rgba(16, 185, 129, 0.18) !important;
        color: #6EE7B7 !important;
        border: 1px solid rgba(16, 185, 129, 0.45) !important;
        padding: 3px 10px !important;
        border-radius: 9999px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 0.03em !important;
        text-transform: uppercase !important;
    }

    /* Estilização moderna para Abas (Tabs) */
    button[data-baseweb="tab"] {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 18px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# FUNÇÕES UTILITÁRIAS DE FORMATAÇÃO, TEMA E CROSS-FILTERING (ESTILO POWERBI)
# ==============================================================================
CORES_SAUDE = {
    "🔴 Vermelho": "#EF4444",
    "🟡 Amarelo": "#F59E0B",
    "🟢 Verde": "#10B981",
}
CORES_SEVERIDADE = {
    "Crítico": "#EF4444",
    "Alto": "#F59E0B",
    "Médio": "#3B82F6",
    "Baixo": "#10B981",
}


def formatar_usd(v: float) -> str:
    """Formata valores em dólares americanos de forma executiva."""
    if pd.isna(v):
        return "US$ 0"
    sinal = "-" if v < 0 else ""
    v_abs = abs(float(v))
    if v_abs >= 1e9:
        return f"{sinal}US$ {v_abs / 1e9:,.2f} bi"
    if v_abs >= 1e6:
        return f"{sinal}US$ {v_abs / 1e6:,.1f} mi"
    return f"{sinal}US$ {v_abs / 1e3:,.0f} mil"


def aplicar_tema_plotly(fig: go.Figure, height: int = 335, show_legend: bool = True) -> go.Figure:
    """Padroniza todos os gráficos Plotly no tema escuro executivo obrigatório."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#F1F5F9", size=12),
        height=height,
        margin=dict(t=26, b=14, l=12, r=12),
        showlegend=show_legend,
        clickmode="event+select",
        hoverlabel=dict(
            bgcolor="#0F172A",
            bordercolor="#334155",
            font=dict(family="Inter, sans-serif", size=12, color="#F8FAFC"),
        ),
    )
    fig.update_xaxes(
        gridcolor="rgba(51, 65, 85, 0.35)",
        zerolinecolor="#334155",
        tickfont=dict(family="Inter", color="#94A3B8"),
    )
    fig.update_yaxes(
        gridcolor="rgba(51, 65, 85, 0.35)",
        zerolinecolor="#334155",
        tickfont=dict(family="Inter", color="#94A3B8"),
    )
    return fig


def _pontos_plotly(key: str) -> list[dict]:
    """Extrai com segurança a lista de pontos selecionados de um gráfico Plotly no session_state."""
    st_val = st.session_state.get(key)
    if not st_val:
        return []
    if isinstance(st_val, dict):
        return st_val.get("selection", {}).get("points", [])
    if hasattr(st_val, "selection") and isinstance(st_val.selection, dict):
        return st_val.selection.get("points", [])
    if hasattr(st_val, "selection") and hasattr(st_val.selection, "points"):
        return list(st_val.selection.points)
    return []


def extrair_cross_filters(
    unidades_validas: set[str],
    fases_validas: set[str],
    tipos_validos: set[str],
    saudes_validas: set[str],
    codigos_validos: set[str],
    categorias_validas: set[str],
    regras_validas: set[str],
) -> dict[str, set]:
    """Lê as seleções ativas de todos os gráficos interativos para aplicar cross-filtering estilo PowerBI."""
    cf: dict[str, set] = {
        "unidade": set(),
        "saude": set(),
        "fase": set(),
        "tipo": set(),
        "codigo": set(),
        "categoria": set(),
        "regra": set(),
    }
    rev = st.session_state.get("cf_rev", 0)

    # 1. Gráfico de barras por Complexo (x = unidade)
    for pt in _pontos_plotly(f"chart_complexo_{rev}"):
        x_val = pt.get("x")
        if x_val in unidades_validas:
            cf["unidade"].add(x_val)

    # 2. Gráfico de Distribuição (Semáforo / Funil FEL / Por Tipo)
    for pt in _pontos_plotly(f"chart_dist_{rev}"):
        cd = pt.get("customdata")
        val = cd[0] if isinstance(cd, (list, tuple)) and cd else (pt.get("label") or pt.get("y") or pt.get("x"))
        if val in saudes_validas:
            cf["saude"].add(val)
        elif val in fases_validas:
            cf["fase"].add(val)
        elif val in tipos_validos:
            cf["tipo"].add(val)

    # 3. Matriz de Quadrantes EVM (CPI x SPI) — seleciona 1 ou mais projetos (bolhas ou lasso/box)
    for pt in _pontos_plotly(f"chart_quad_{rev}"):
        cd = pt.get("customdata")
        cod = cd[0] if isinstance(cd, (list, tuple)) and cd else pt.get("hovertext")
        if cod in codigos_validos:
            cf["codigo"].add(cod)

    # 4. Auditoria: Violações por Categoria
    for pt in _pontos_plotly(f"chart_audit_cat_{rev}"):
        y_val = pt.get("y")
        if y_val in categorias_validas:
            cf["categoria"].add(y_val)

    # 5. Auditoria: Ranking de Regras
    for pt in _pontos_plotly(f"chart_audit_reg_{rev}"):
        y_val = pt.get("y")
        if y_val in regras_validas:
            cf["regra"].add(y_val)

    return cf


@st.cache_data(show_spinner=False)
def carregar_dados_completos():
    repository.garantir_base()
    port = repository.carregar_portfolio()
    m = metrics.metricas_projetos(port)
    achados = compliance.auditar(port, m)
    m_saude = compliance.semaforo(m, achados)
    gabarito = repository.carregar_gabarito()
    avaliacao_gabarito = compliance.avaliar_gabarito(achados, gabarito)
    return port, m_saude, achados, avaliacao_gabarito


port, df_projetos, df_achados, eval_gab = carregar_dados_completos()

if "cf_rev" not in st.session_state:
    st.session_state["cf_rev"] = 0

# ==============================================================================
# BARRA LATERAL (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.title("⛏️ PMO Copilot")
    st.caption(f"**{port.empresa}** — Inteligência de Capital")

    chave_configurada = bool(config.get_gemini_api_key())
    if chave_configurada:
        modelo_nome = config.get_model_name()
        st.markdown(
            f"""
            <div style="
                display: flex;
                align-items: center;
                gap: 14px;
                background: linear-gradient(135deg, rgba(26, 115, 232, 0.14) 0%, rgba(155, 114, 207, 0.20) 50%, rgba(217, 101, 112, 0.14) 100%);
                border: 1px solid rgba(155, 114, 207, 0.38);
                padding: 12px 16px;
                border-radius: 14px;
                margin-top: 6px;
                margin-bottom: 16px;
                box-shadow: 0 4px 18px -2px rgba(155, 114, 207, 0.22);
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 44px;
                    height: 44px;
                    border-radius: 12px;
                    background: rgba(255, 255, 255, 0.06);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    flex-shrink: 0;
                ">
                    <svg width="32" height="32" viewBox="0 0 48 48" fill="none" style="filter: drop-shadow(0 2px 6px rgba(155, 114, 207, 0.65));">
                        <path d="M24 2C24 14.15 14.15 24 2 24C14.15 24 24 33.85 24 46C24 33.85 33.85 24 46 24C33.85 24 24 14.15 24 2Z" fill="url(#gemini_grad_hero)"/>
                        <defs>
                            <linearGradient id="gemini_grad_hero" x1="2" y1="2" x2="46" y2="46" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#4285F4"/>
                                <stop offset="0.45" stop-color="#9B72CF"/>
                                <stop offset="0.85" stop-color="#D96570"/>
                                <stop offset="1" stop-color="#FBBC05"/>
                            </linearGradient>
                        </defs>
                    </svg>
                </div>
                <div style="display: flex; flex-direction: column; justify-content: center;">
                    <span style="font-size: 14px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.01em; line-height: 1.2;">Google Gemini</span>
                    <div style="display: flex; align-items: center; gap: 6px; margin-top: 3px;">
                        <span style="width: 7px; height: 7px; border-radius: 50%; background: #10B981; box-shadow: 0 0 8px #10B981; display: inline-block;"></span>
                        <span style="font-size: 11px; font-weight: 500; color: #CBD5E1;">{modelo_nome}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("⚠️ Chave Gemini não configurada no `.env`")
        api_key_input = st.text_input(
            "Inserir Chave Gemini",
            type="password",
            help="Insira a chave da API do Gemini para habilitar os agentes.",
        )
        if api_key_input:
            os.environ["GEMINI_API_KEY"] = api_key_input.strip()

    with st.container(border=True):
        st.markdown("##### :material/tune: Filtros Globais")

        unidades_opcoes = ["Todas"] + sorted(df_projetos["unidade"].dropna().unique().tolist())
        unidade_sel = st.selectbox("Complexo / Unidade:", unidades_opcoes)

        tipos_opcoes = ["Todos"] + sorted(df_projetos["tipo"].dropna().unique().tolist())
        tipo_sel = st.selectbox("Tipo de Investimento:", tipos_opcoes)

        fases_opcoes = ["Todas"] + domain.FASES
        fase_sel = st.selectbox("Fase Stage-Gate (FEL):", fases_opcoes)

        saude_opcoes = ["Todas", "🔴 Vermelho", "🟡 Amarelo", "🟢 Verde"]
        saude_sel = st.selectbox("Saúde / Semáforo:", saude_opcoes)

        busca_termo = st.text_input(
            "Busca rápida (Código, Nome ou PM):",
            placeholder="Ex: MNS-001, Barragem, Ana...",
        )

    with st.expander("⚙️ Gerar Novos Dados Sintéticos"):
        st.caption("Simule um novo portfólio mock com falhas determinísticas injetadas.")
        n_proj = st.number_input("Qtd Projetos", min_value=100, max_value=1000, value=350, step=50)
        seed_in = st.number_input("Semente (Seed)", min_value=1, max_value=9999, value=42)
        if st.button("Regenerar Base Mock", width="stretch"):
            with st.spinner("Gerando dados sintéticos..."):
                tabelas = gerar_portfolio(n_projetos=int(n_proj), seed=int(seed_in))
                salvar(tabelas)
                st.cache_data.clear()
                st.session_state["cf_rev"] += 1
                st.success("Base mock regenerada!")
                st.rerun()

# ==============================================================================
# 1. APLICAÇÃO DOS FILTROS DA BARRA LATERAL (BASE)
# ==============================================================================
df_base = df_projetos.copy()
if unidade_sel != "Todas":
    df_base = df_base[df_base["unidade"] == unidade_sel]
if tipo_sel != "Todos":
    df_base = df_base[df_base["tipo"] == tipo_sel]
if fase_sel != "Todas":
    df_base = df_base[df_base["fase"] == fase_sel]
if saude_sel != "Todas":
    df_base = df_base[df_base["saude"] == saude_sel]
if busca_termo.strip():
    termo = busca_termo.strip().lower()
    mascara_busca = (
        df_base["codigo"].str.lower().str.contains(termo, na=False)
        | df_base["nome"].str.lower().str.contains(termo, na=False)
        | df_base["pm"].str.lower().str.contains(termo, na=False)
    )
    df_base = df_base[mascara_busca]

# ==============================================================================
# 2. CROSS-FILTERING DINÂMICO ENTRE GRÁFICOS (ESTILO POWERBI)
# ==============================================================================
cf_ativos = extrair_cross_filters(
    unidades_validas=set(df_projetos["unidade"].dropna().unique()),
    fases_validas=set(domain.FASES),
    tipos_validos=set(df_projetos["tipo"].dropna().unique()),
    saudes_validas={"🔴 Vermelho", "🟡 Amarelo", "🟢 Verde"},
    codigos_validos=set(df_projetos["codigo"].dropna().unique()),
    categorias_validas=set(df_achados["categoria"].dropna().unique()),
    regras_validas=set(df_achados["regra"].dropna().unique()),
)


def aplicar_mascara_cf(df_in: pd.DataFrame, ignorar: str | None = None) -> pd.DataFrame:
    """Filtra um DataFrame aplicando todos os cross-filters ativos exceto o próprio gráfico de origem."""
    out = df_in
    if ignorar != "unidade" and cf_ativos["unidade"]:
        out = out[out["unidade"].isin(cf_ativos["unidade"])]
    if ignorar != "dist":
        if cf_ativos["saude"]:
            out = out[out["saude"].isin(cf_ativos["saude"])]
        if cf_ativos["fase"]:
            out = out[out["fase"].isin(cf_ativos["fase"])]
        if cf_ativos["tipo"]:
            out = out[out["tipo"].isin(cf_ativos["tipo"])]
    if ignorar != "quad" and cf_ativos["codigo"]:
        out = out[out["codigo"].isin(cf_ativos["codigo"])]
    if ignorar != "audit_cat" and cf_ativos["categoria"]:
        cods_cat = set(df_achados[df_achados["categoria"].isin(cf_ativos["categoria"])]["codigo"])
        out = out[out["codigo"].isin(cods_cat)]
    if ignorar != "audit_reg" and cf_ativos["regra"]:
        cods_reg = set(df_achados[df_achados["regra"].isin(cf_ativos["regra"])]["codigo"])
        out = out[out["codigo"].isin(cods_reg)]
    return out


df_filtrado = aplicar_mascara_cf(df_base, ignorar=None)
codigos_filtrados = set(df_filtrado["codigo"])
achados_filtrados = df_achados[df_achados["codigo"].isin(codigos_filtrados)]
if cf_ativos["categoria"]:
    achados_filtrados = achados_filtrados[achados_filtrados["categoria"].isin(cf_ativos["categoria"])]
if cf_ativos["regra"]:
    achados_filtrados = achados_filtrados[achados_filtrados["regra"].isin(cf_ativos["regra"])]

tem_cross_filter = any(bool(v) for v in cf_ativos.values())

# ==============================================================================
# BARRA SUPERIOR MINIMALISTA + EXPERIÊNCIA GEMINI WEB NO TOPO
# ==============================================================================
n_vermelhos = int((df_filtrado["saude"] == "🔴 Vermelho").sum())
n_amarelos = int((df_filtrado["saude"] == "🟡 Amarelo").sum())
n_verdes = int((df_filtrado["saude"] == "🟢 Verde").sum())
escopo_label = unidade_sel if unidade_sel != "Todas" else "Portfólio Global"

st.markdown(
    f"""
    <div class="top-context-bar">
        <div class="top-brand">
            <span>⛏️ <strong>{port.empresa}</strong></span>
            <span style="color:#475569;">•</span>
            <span>PMO Copilot</span>
            <span style="color:#475569;">•</span>
            <span style="color:#94A3B8;font-weight:400;">{escopo_label}</span>
        </div>
        <div class="exec-pill-bar">
            <span class="exec-pill">📅 Corte: <strong style="color:#60A5FA;">{port.data_corte.strftime('%d/%m/%Y')}</strong></span>
            <span class="exec-pill">🔴 <strong style="color:#FCA5A5;">{n_vermelhos}</strong></span>
            <span class="exec-pill">🟡 <strong style="color:#FCD34D;">{n_amarelos}</strong></span>
            <span class="exec-pill">🟢 <strong style="color:#6EE7B7;">{n_verdes}</strong></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Inicializa histórico de conversa (vazio por padrão, igual ao Gemini Web)
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []

# Centraliza o bloco do Chat na página principal (estilo Gemini Web)
_, col_gemini, _ = st.columns([0.12, 0.76, 0.12])
with col_gemini:
    if not st.session_state["chat_messages"]:
        st.markdown(
            """
            <div class="gemini-web-wrap">
                <div class="gemini-greeting">✦ Olá, Executivo do PMO</div>
                <div class="gemini-sub">Como posso ajudar com o portfólio da MineraSul hoje?</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Mostra cabeçalho discreto da conversa + botão Nova Conversa
        c_top_chat1, c_top_chat2 = st.columns([3, 1], vertical_alignment="center")
        with c_top_chat1:
            st.caption("✦ **Gemini PMO Copilot** • Respostas baseadas nos cálculos determinísticos do portfólio")
        with c_top_chat2:
            with st.container(horizontal=True, horizontal_alignment="right"):
                if st.button(":material/edit_square: Nova conversa", key="btn_limpar_chat", type="tertiary"):
                    st.session_state["chat_messages"] = []
                    st.rerun()

    # Container onde as mensagens aparecem (acima da barra de digitar quando há conversa)
    mensagens_slot = st.container()

    # 1. BARRA DE DIGITAR (acima das sugestões, idêntico ao Gemini Web)
    prompt_digitado = st.chat_input("Peça ao Gemini PMO Copilot...")

    # 2. SUGESTÕES DE PERGUNTAS EMBAIXO DA BARRA DE DIGITAR
    st.markdown('<div class="gemini-chips-row">', unsafe_allow_html=True)
    chip1, chip2, chip3, chip4 = st.columns(4, gap="small")
    with chip1:
        if st.button("🚩 Tapajós com SPI < 0.9", width="stretch", key="chip_1"):
            st.session_state["pending_prompt"] = "Quais projetos do Complexo Tapajós estão com SPI abaixo de 0.9?"
    with chip2:
        if st.button("⚠️ Riscos críticos sem dono", width="stretch", key="chip_2"):
            st.session_state["pending_prompt"] = "Liste os riscos de nível Crítico ou Alto que ainda estão sem responsável definido."
    with chip3:
        if st.button("👤 PMs sobrecarregados", width="stretch", key="chip_3"):
            st.session_state["pending_prompt"] = "Existem gerentes de projetos (PMs) sobrecarregados com mais de 6 projetos ativos? Destaque a situação deles."
    with chip4:
        if st.button("💸 Maiores estouros de EAC", width="stretch", key="chip_4"):
            st.session_state["pending_prompt"] = "Quais são os 5 projetos com maior estouro previsto de orçamento total (EAC acima do orçamento total)?"
    st.markdown("</div>", unsafe_allow_html=True)

    # Resolve prompt vindo da barra de digitar ou de clique nas pílulas abaixo
    prompt_ativo = prompt_digitado
    if "pending_prompt" in st.session_state:
        prompt_ativo = st.session_state.pop("pending_prompt")

    if prompt_ativo:
        st.session_state["chat_messages"].append({"role": "user", "content": prompt_ativo})
        chave_chat = os.getenv("GEMINI_API_KEY", "").strip()
        if not chave_chat:
            st.session_state["chat_messages"].append(
                {
                    "role": "assistant",
                    "content": "❌ **GEMINI_API_KEY não configurada.** Insira sua chave na barra lateral esquerda para conversar com o assistente.",
                }
            )
        else:
            with mensagens_slot:
                for msg in st.session_state["chat_messages"]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                with st.chat_message("assistant"):
                    with st.spinner("Analisando dados determinísticos do portfólio..."):
                        try:
                            from pmo_copilot.agents.chat import responder_pergunta
                            resposta = responder_pergunta(
                                pergunta=prompt_ativo,
                                historico=st.session_state["chat_messages"][:-1],
                                api_key=chave_chat,
                            )
                        except Exception as e:
                            resposta = f"⚠️ Ocorreu um erro ao processar sua consulta: `{e}`"
            st.session_state["chat_messages"].append({"role": "assistant", "content": resposta})
            st.rerun()

    # Renderiza histórico quando já existe conversa ativa
    if st.session_state["chat_messages"]:
        with mensagens_slot:
            altura_hist = 320 if len(st.session_state["chat_messages"]) > 2 else None
            box_hist = st.container(height=altura_hist, border=False) if altura_hist else st.container(border=False)
            with box_hist:
                for msg in st.session_state["chat_messages"]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

st.space("small")


# ==============================================================================
# BARRA DE STATUS DO CROSS-FILTERING (ESTILO POWERBI)
# ==============================================================================
if tem_cross_filter:
    chips_html = []
    if cf_ativos["unidade"]:
        chips_html.append(f"<span class='powerbi-chip'>Complexo: {', '.join(sorted(cf_ativos['unidade']))}</span>")
    if cf_ativos["saude"]:
        chips_html.append(f"<span class='powerbi-chip'>Saúde: {', '.join(sorted(cf_ativos['saude']))}</span>")
    if cf_ativos["fase"]:
        chips_html.append(f"<span class='powerbi-chip'>Fase FEL: {', '.join(sorted(cf_ativos['fase']))}</span>")
    if cf_ativos["tipo"]:
        chips_html.append(f"<span class='powerbi-chip'>Tipo: {', '.join(sorted(cf_ativos['tipo']))}</span>")
    if cf_ativos["codigo"]:
        lista_cod = sorted(cf_ativos["codigo"])
        resumo_cod = ", ".join(lista_cod[:4]) + (f" (+{len(lista_cod) - 4})" if len(lista_cod) > 4 else "")
        chips_html.append(f"<span class='powerbi-chip'>Projetos: {resumo_cod}</span>")
    if cf_ativos["categoria"]:
        chips_html.append(f"<span class='powerbi-chip'>Categoria Auditoria: {', '.join(sorted(cf_ativos['categoria']))}</span>")
    if cf_ativos["regra"]:
        chips_html.append(f"<span class='powerbi-chip'>Regra: {', '.join(sorted(cf_ativos['regra']))}</span>")

    cf_bar_col1, cf_bar_col2 = st.columns([4.2, 1], vertical_alignment="center")
    with cf_bar_col1:
        st.markdown(
            f"<div class='powerbi-bar'>"
            f"<span style='font-size:12px;font-weight:700;color:#93C5FD;'>⚡ Cross-Filter Ativo nos Gráficos ({len(df_filtrado)} projetos exibidos):</span>"
            f"{''.join(chips_html)}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with cf_bar_col2:
        if st.button("🔄 Limpar Seleção dos Gráficos", width="stretch", type="primary"):
            st.session_state["cf_rev"] += 1
            st.rerun()
else:
    st.caption(
        "💡 **Interatividade PowerBI Ativa:** Clique em qualquer barra de complexo, fatia do semáforo, etapa do funil FEL ou bolha de projeto nos gráficos abaixo para filtrar todos os demais visuais instantaneamente."
    )

if df_filtrado.empty:
    st.warning("Nenhum projeto encontrado para a combinação atual de filtros. Clique em 'Limpar Seleção dos Gráficos' ou ajuste a barra lateral.")
    st.stop()

# ==============================================================================
# SEÇÃO 2 (ABAIXO DO CHAT): PAINÉIS ANALÍTICOS INTERATIVOS
# ==============================================================================
tab_visao, tab_semaforo, tab_auditoria, tab_copilot = st.tabs([
    "📊 Painel Executivo Interativo (PowerBI)",
    "🚦 Semáforo & Raio-X de Projetos",
    "🔍 Auditoria Stage-Gate & Matriz 5×5",
    "📑 Relatório Executivo Autônomo (CrewAI)",
])

rev = st.session_state["cf_rev"]

# ------------------------------------------------------------------------------
# ABA 1: PAINEL EXECUTIVO INTERATIVO (POWERBI CROSS-FILTERING)
# ------------------------------------------------------------------------------
with tab_visao:
    resumo_geral = metrics.resumo_portfolio(df_filtrado).iloc[0]
    ids_filtrados = df_filtrado["id"].tolist()
    curva_port = metrics.curva_s_portfolio(port, projeto_ids=ids_filtrados)

    # Séries históricas para Sparklines nos cards de KPI
    c_hist = port.custos_mensais[port.custos_mensais["projeto_id"].isin(ids_filtrados)]
    mensal_agg = c_hist.groupby("mes")[["pv", "ev", "ac"]].sum().sort_index()
    acum_agg = mensal_agg.cumsum()
    cpi_hist = (acum_agg["ev"] / acum_agg["ac"].replace(0, np.nan)).fillna(1.0).tail(12).tolist()
    spi_hist = (acum_agg["ev"] / acum_agg["pv"].replace(0, np.nan)).fillna(1.0).tail(12).tolist()
    ac_hist = mensal_agg["ac"].tail(12).tolist()
    ev_hist = mensal_agg["ev"].tail(12).tolist()

    pct_realizado = float(resumo_geral["pct_realizado"]) if pd.notna(resumo_geral["pct_realizado"]) else 0.0
    variacao_eac = float(resumo_geral["variacao_vs_orcamento_total"])
    cpi_val = float(resumo_geral["cpi"]) if pd.notna(resumo_geral["cpi"]) else 1.0
    spi_val = float(resumo_geral["spi"]) if pd.notna(resumo_geral["spi"]) else 1.0

    # Linha 1: 6 KPIs Executivos que reagem em tempo real ao clique nos gráficos
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric(
        "Portfólio Selecionado",
        f"{int(resumo_geral['projetos'])} proj.",
        delta=f"{n_vermelhos} em alerta crítico",
        delta_color="inverse" if n_vermelhos > 0 else "normal",
        help="Total de projetos sob o filtro/cross-filter atual e contagem de projetos no semáforo vermelho.",
    )
    kpi2.metric(
        "CAPEX Aprovado (USD)",
        formatar_usd(resumo_geral["orcamento_total"]),
        delta=f"Conting.: {formatar_usd(resumo_geral['contingencia'])}",
        delta_color="off",
        help="Orçamento Total = Baseline (BAC) + Contingência aprovada.",
    )
    kpi3.metric(
        "Realizado (AC)",
        formatar_usd(resumo_geral["ac"]),
        delta=f"{pct_realizado:.1%} do CAPEX",
        delta_color="off",
        chart_data=ac_hist if len(ac_hist) > 1 else None,
        chart_type="bar",
        help="Custo Realizado Acumulado (Actual Cost) e evolução de desembolso mensal nos últimos 12 meses.",
    )
    kpi4.metric(
        "EAC Projetado Final",
        formatar_usd(resumo_geral["eac_total"]),
        delta=f"{formatar_usd(variacao_eac)} vs Budget",
        delta_color="normal" if variacao_eac >= 0 else "inverse",
        chart_data=ev_hist if len(ev_hist) > 1 else None,
        chart_type="line",
        help="Estimate at Completion (EAC Total) comparado ao Orçamento Total aprovado.",
    )
    kpi5.metric(
        "CPI Consolidado",
        f"{cpi_val:.2f}",
        delta=f"{cpi_val - 1.0:+.2f} vs Meta (1.00)",
        delta_color="normal" if cpi_val >= 0.98 else "inverse",
        chart_data=cpi_hist if len(cpi_hist) > 1 else None,
        chart_type="line",
        help="Cost Performance Index (EV / AC). Acima de 1.0 indica eficiência de custo; abaixo de 1.0 indica estouro.",
    )
    kpi6.metric(
        "SPI Consolidado",
        f"{spi_val:.2f}",
        delta=f"{spi_val - 1.0:+.2f} vs Meta (1.00)",
        delta_color="normal" if spi_val >= 0.98 else "inverse",
        chart_data=spi_hist if len(spi_hist) > 1 else None,
        chart_type="line",
        help="Schedule Performance Index (EV / PV). Acima de 1.0 indica avanço adiantado; abaixo de 1.0 indica atraso.",
    )

    st.space("small")

    # Linha 2: Alocação por Complexo (Clicável) + Distribuição Semáforo/FEL/Tipo (Clicável)
    col_comp, col_direita = st.columns([1.35, 1.05])

    with col_comp:
        with st.container(border=True):
            b_hdr1, b_hdr2 = st.columns([1.3, 1])
            with b_hdr1:
                st.markdown("##### 🏛️ Alocação de Capital por Complexo (Clique para Filtrar)")
                st.caption("Clique em uma barra de Complexo para recalcular Curva S, KPIs e Quadrante EVM")
            with b_hdr2:
                modo_aloc = st.segmented_control(
                    "Modo de Alocação",
                    options=["Barras (Complexo)", "Treemap CAPEX"],
                    default="Barras (Complexo)",
                    label_visibility="collapsed",
                    key="seg_modo_aloc",
                )

            # Usa df filtrado pelos DEMAIS gráficos para permitir troca de barra sem esconder as outras
            df_para_complexo = aplicar_mascara_cf(df_base, ignorar="unidade")

            if modo_aloc == "Barras (Complexo)":
                por_u = metrics.resumo_portfolio(df_para_complexo, por="unidade").sort_values("orcamento_total", ascending=False)
                opacidades_u = [
                    1.0 if (not cf_ativos["unidade"] or u in cf_ativos["unidade"]) else 0.28
                    for u in por_u["unidade"]
                ]
                fig_bar = go.Figure(
                    data=[
                        go.Bar(
                            name="Orçamento Total",
                            x=por_u["unidade"],
                            y=por_u["orcamento_total"],
                            marker=dict(color="#3B82F6", opacity=opacidades_u),
                        ),
                        go.Bar(
                            name="Comprometido",
                            x=por_u["unidade"],
                            y=por_u["comprometido"],
                            marker=dict(color="#F59E0B", opacity=opacidades_u),
                        ),
                        go.Bar(
                            name="Realizado (AC)",
                            x=por_u["unidade"],
                            y=por_u["ac"],
                            marker=dict(color="#10B981", opacity=opacidades_u),
                        ),
                        go.Scatter(
                            name="EAC Projetado",
                            x=por_u["unidade"],
                            y=por_u["eac_total"],
                            mode="markers",
                            marker=dict(color="#EF4444", size=11, symbol="diamond", line=dict(width=1.5, color="#FFFFFF")),
                        ),
                    ]
                )
                aplicar_tema_plotly(fig_bar, height=340)
                fig_bar.update_layout(
                    barmode="group",
                    yaxis_title="USD",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(
                    fig_bar,
                    width="stretch",
                    key=f"chart_complexo_{rev}",
                    on_select="rerun",
                    selection_mode="points",
                )
            else:
                df_tree = df_filtrado.copy()
                df_tree["cpi_clip"] = df_tree["cpi"].fillna(1.0).clip(0.65, 1.25)
                fig_tree = px.treemap(
                    df_tree,
                    path=[px.Constant("MineraSul"), "unidade", "tipo", "codigo"],
                    values="orcamento_total",
                    color="cpi_clip",
                    color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"],
                    color_continuous_midpoint=1.0,
                    hover_data={"nome": True, "cpi": ":.2f", "spi": ":.2f", "saude": True, "cpi_clip": False},
                )
                aplicar_tema_plotly(fig_tree, height=340)
                fig_tree.update_layout(margin=dict(t=10, b=10, l=10, r=10), coloraxis_colorbar=dict(title="CPI"))
                st.plotly_chart(fig_tree, width="stretch")

    with col_direita:
        with st.container(border=True):
            d_hdr1, d_hdr2 = st.columns([1.15, 1])
            with d_hdr1:
                st.markdown("##### 🎯 Distribuição (Clique para Filtrar)")
                st.caption("Clique em Semáforo, Fase FEL ou Tipo")
            with d_hdr2:
                visao_dist = st.segmented_control(
                    "Visão de Distribuição",
                    options=["Semáforo", "Funil FEL", "Por Tipo"],
                    default="Semáforo",
                    label_visibility="collapsed",
                    key="seg_visao_dist",
                )

            df_para_dist = aplicar_mascara_cf(df_base, ignorar="dist")

            if visao_dist == "Semáforo":
                saude_counts = (
                    df_para_dist.groupby("saude", as_index=False)
                    .agg(Qtd=("id", "count"), CAPEX=("orcamento_total", "sum"))
                )
                fig_dist = px.pie(
                    saude_counts,
                    names="saude",
                    values="Qtd",
                    color="saude",
                    color_discrete_map=CORES_SAUDE,
                    hole=0.64,
                    custom_data=["saude", "CAPEX"],
                )
                pulls = [
                    0.08 if (cf_ativos["saude"] and s in cf_ativos["saude"]) else 0.0
                    for s in saude_counts["saude"]
                ]
                fig_dist.update_traces(
                    pull=pulls,
                    textinfo="percent+value",
                    textfont=dict(family="Inter", size=12, color="#F8FAFC"),
                    hovertemplate="<b>%{label}</b><br>Projetos: %{value} (%{percent})<br>CAPEX: US$ %{customdata[1]:,.0f}<br><i>Clique para filtrar</i><extra></extra>",
                )
                fig_dist.add_annotation(
                    text=f"<b>{len(df_filtrado)}</b><br><span style='font-size:11px;color:#94A3B8'>Ativos</span>",
                    x=0.5,
                    y=0.5,
                    font=dict(size=18, color="#F8FAFC", family="Inter"),
                    showarrow=False,
                )
                aplicar_tema_plotly(fig_dist, height=340)
                fig_dist.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.08, xanchor="center", x=0.5))
                st.plotly_chart(
                    fig_dist,
                    width="stretch",
                    key=f"chart_dist_{rev}",
                    on_select="rerun",
                    selection_mode="points",
                )

            elif visao_dist == "Funil FEL":
                df_fel = (
                    df_para_dist.groupby("fase", as_index=False)
                    .agg(projetos=("id", "count"), capex=("orcamento_total", "sum"))
                )
                ordem_fases = {f: i for i, f in enumerate(domain.FASES)}
                df_fel["ordem"] = df_fel["fase"].map(ordem_fases)
                df_fel = df_fel.sort_values("ordem")
                cores_f = [
                    "#3B82F6" if (not cf_ativos["fase"] or f in cf_ativos["fase"]) else "rgba(100, 116, 139, 0.35)"
                    for f in df_fel["fase"]
                ]
                fig_fel = go.Figure(
                    go.Funnel(
                        y=df_fel["fase"],
                        x=df_fel["projetos"],
                        textinfo="value+percent initial",
                        marker=dict(color=cores_f),
                        customdata=np.stack([df_fel["fase"], df_fel["capex"]], axis=-1),
                        hovertemplate="<b>%{y}</b><br>Projetos: %{x}<br>CAPEX: US$ %{customdata[1]:,.0f}<br><i>Clique para filtrar</i><extra></extra>",
                    )
                )
                aplicar_tema_plotly(fig_fel, height=340, show_legend=False)
                st.plotly_chart(
                    fig_fel,
                    width="stretch",
                    key=f"chart_dist_{rev}",
                    on_select="rerun",
                    selection_mode="points",
                )

            else:
                df_tipo = (
                    df_para_dist.groupby("tipo", as_index=False)
                    .agg(projetos=("id", "count"), capex=("orcamento_total", "sum"))
                    .sort_values("capex", ascending=True)
                )
                opac_t = [
                    1.0 if (not cf_ativos["tipo"] or t in cf_ativos["tipo"]) else 0.3
                    for t in df_tipo["tipo"]
                ]
                fig_tipo = go.Figure(
                    go.Bar(
                        x=df_tipo["capex"],
                        y=df_tipo["tipo"],
                        orientation="h",
                        text=df_tipo["capex"].apply(formatar_usd),
                        textposition="auto",
                        customdata=np.stack([df_tipo["tipo"], df_tipo["projetos"]], axis=-1),
                        marker=dict(
                            color=["#3B82F6", "#10B981", "#A855F7", "#F59E0B", "#06B6D4"][: len(df_tipo)],
                            opacity=opac_t,
                        ),
                        hovertemplate="<b>%{y}</b><br>CAPEX: US$ %{x:,.0f}<br>Projetos: %{customdata[1]}<br><i>Clique para filtrar</i><extra></extra>",
                    )
                )
                aplicar_tema_plotly(fig_tipo, height=340, show_legend=False)
                fig_tipo.update_layout(xaxis_title="CAPEX Total (USD)", yaxis_title="")
                st.plotly_chart(
                    fig_tipo,
                    width="stretch",
                    key=f"chart_dist_{rev}",
                    on_select="rerun",
                    selection_mode="points",
                )

    # Linha 3: Curva S Dinâmica (Reage a todos os cliques) + Matriz de Quadrantes EVM (Clicável e Lasso)
    col_curva, col_quad = st.columns([1.25, 1.15])

    with col_curva:
        with st.container(border=True):
            c_hdr1, c_hdr2 = st.columns([1.3, 1])
            with c_hdr1:
                st.markdown("##### 📈 Curva S & Desembolso do Escopo Selecionado")
                st.caption(f"Recalculada dinamicamente para os {len(df_filtrado)} projetos ativos no filtro")
            with c_hdr2:
                modo_curva = st.segmented_control(
                    "Modo da Curva S",
                    options=["Acumulado (Curva S)", "Desembolso Mensal", "Variações (CV & SV)"],
                    default="Acumulado (Curva S)",
                    label_visibility="collapsed",
                    key="seg_modo_curva",
                )

            fig_curva = go.Figure()
            if modo_curva == "Desembolso Mensal":
                m_serie = mensal_agg.reset_index()
                m_serie["mes"] = pd.to_datetime(m_serie["mes"])
                fig_curva.add_trace(
                    go.Bar(x=m_serie["mes"], y=m_serie["pv"], name="Planejado Mensal (PV)", marker_color="rgba(96, 165, 250, 0.55)")
                )
                fig_curva.add_trace(
                    go.Bar(x=m_serie["mes"], y=m_serie["ac"], name="Realizado Mensal (AC)", marker_color="#EF4444")
                )
                fig_curva.add_trace(
                    go.Scatter(
                        x=m_serie["mes"],
                        y=m_serie["ev"],
                        mode="lines+markers",
                        name="Valor Agregado (EV)",
                        line=dict(color="#10B981", width=2.5),
                    )
                )
                fig_curva.update_layout(barmode="group", yaxis_title="USD no Mês")
            elif modo_curva == "Variações (CV & SV)":
                curva_var = curva_port.copy()
                curva_var["cv"] = curva_var["ev_acum"] - curva_var["ac_acum"]
                curva_var["sv"] = curva_var["ev_acum"] - curva_var["pv_acum"]
                fig_curva.add_trace(
                    go.Scatter(
                        x=curva_var["mes"],
                        y=curva_var["cv"],
                        mode="lines",
                        name="Variação de Custo (CV = EV - AC)",
                        line=dict(color="#EF4444", width=2.5),
                        fill="tozeroy",
                        fillcolor="rgba(239, 68, 68, 0.12)",
                    )
                )
                fig_curva.add_trace(
                    go.Scatter(
                        x=curva_var["mes"],
                        y=curva_var["sv"],
                        mode="lines",
                        name="Variação de Prazo (SV = EV - PV)",
                        line=dict(color="#F59E0B", width=2.5),
                        fill="tozeroy",
                        fillcolor="rgba(245, 158, 11, 0.10)",
                    )
                )
                fig_curva.add_hline(y=0, line_dash="dash", line_color="#94A3B8", annotation_text="Linha de Equilíbrio (0)")
                fig_curva.update_layout(yaxis_title="Desvio Acumulado (USD)")
            else:
                fig_curva.add_trace(
                    go.Scatter(
                        x=curva_port["mes"],
                        y=curva_port["pv_acum"],
                        mode="lines",
                        name="Planejado (PV)",
                        line=dict(color="#60A5FA", width=2.5, dash="dot"),
                    )
                )
                fig_curva.add_trace(
                    go.Scatter(
                        x=curva_port["mes"],
                        y=curva_port["ev_acum"],
                        mode="lines",
                        name="Valor Agregado (EV)",
                        line=dict(color="#10B981", width=3),
                        fill="tozeroy",
                        fillcolor="rgba(16, 185, 129, 0.08)",
                    )
                )
                fig_curva.add_trace(
                    go.Scatter(
                        x=curva_port["mes"],
                        y=curva_port["ac_acum"],
                        mode="lines",
                        name="Custo Realizado (AC)",
                        line=dict(color="#EF4444", width=3),
                    )
                )
                fig_curva.update_layout(yaxis_title="USD Acumulado")

            aplicar_tema_plotly(fig_curva, height=345)
            fig_curva.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(
                    rangeslider=dict(visible=False),
                    rangeselector=dict(
                        bgcolor="#1E293B",
                        activecolor="#3B82F6",
                        font=dict(color="#F1F5F9", size=11),
                        buttons=list([
                            dict(count=6, label="6M", step="month", stepmode="backward"),
                            dict(count=1, label="1A", step="year", stepmode="backward"),
                            dict(count=2, label="2A", step="year", stepmode="backward"),
                            dict(step="all", label="Tudo"),
                        ]),
                    ),
                ),
            )
            st.plotly_chart(fig_curva, width="stretch")

    with col_quad:
        with st.container(border=True):
            st.markdown("##### 🎯 Quadrante EVM CPI × SPI (Clique ou Arraste para Filtrar)")
            st.caption("Selecione uma bolha ou use Box/Lasso no gráfico para isolar projetos na Curva S e KPIs")

            df_para_quad = aplicar_mascara_cf(df_base, ignorar="quad")
            df_evm = df_para_quad[df_para_quad["cpi"].notna() & df_para_quad["spi"].notna()].copy()
            if df_evm.empty:
                st.info("Sem projetos com métricas CPI/SPI calculadas no filtro atual.")
            else:
                df_evm["cpi_plot"] = df_evm["cpi"].clip(0.45, 1.45)
                df_evm["spi_plot"] = df_evm["spi"].clip(0.45, 1.45)
                df_evm["capex_mi"] = (df_evm["orcamento_total"] / 1e6).clip(lower=5.0)

                fig_quad = px.scatter(
                    df_evm,
                    x="spi_plot",
                    y="cpi_plot",
                    size="capex_mi",
                    color="saude",
                    color_discrete_map=CORES_SAUDE,
                    hover_name="codigo",
                    custom_data=["codigo", "nome", "unidade", "fase", "cpi", "spi", "orcamento_total"],
                    size_max=28,
                )
                fig_quad.update_traces(
                    hovertemplate=(
                        "<b>%{customdata[0]} — %{customdata[1]}</b><br>"
                        "Complexo: %{customdata[2]} | Fase: %{customdata[3]}<br>"
                        "CPI: %{customdata[4]:.2f} | SPI: %{customdata[5]:.2f}<br>"
                        "CAPEX: US$ %{customdata[6]:,.0f}<br><i>Clique ou arraste para filtrar</i><extra></extra>"
                    )
                )
                fig_quad.add_hline(y=1.0, line_dash="solid", line_color="rgba(148, 163, 184, 0.55)", line_width=1.5)
                fig_quad.add_vline(x=1.0, line_dash="solid", line_color="rgba(148, 163, 184, 0.55)", line_width=1.5)
                fig_quad.add_hline(y=domain.LIMITE_CPI_ALTO, line_dash="dot", line_color="rgba(239, 68, 68, 0.45)", line_width=1)
                fig_quad.add_vline(x=domain.LIMITE_SPI_ALTO, line_dash="dot", line_color="rgba(239, 68, 68, 0.45)", line_width=1)

                fig_quad.add_annotation(
                    x=0.52, y=0.52, text="⚠️ Estouro & Atraso", showarrow=False,
                    font=dict(size=10, color="#FCA5A5"), bgcolor="rgba(239,68,68,0.12)", borderpad=3,
                )
                fig_quad.add_annotation(
                    x=1.32, y=1.35, text="✅ Alta Performance", showarrow=False,
                    font=dict(size=10, color="#6EE7B7"), bgcolor="rgba(16,185,129,0.12)", borderpad=3,
                )
                aplicar_tema_plotly(fig_quad, height=345)
                fig_quad.update_layout(
                    xaxis_title="SPI — Desempenho de Prazo (EV / PV)",
                    yaxis_title="CPI — Eficiência de Custo (EV / AC)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
                )
                st.plotly_chart(
                    fig_quad,
                    width="stretch",
                    key=f"chart_quad_{rev}",
                    on_select="rerun",
                    selection_mode=("points", "box", "lasso"),
                )

# ------------------------------------------------------------------------------
# ABA 2: SEMÁFORO & PROJETOS CRÍTICOS (RAIO-X INTERATIVO)
# ------------------------------------------------------------------------------
with tab_semaforo:
    with st.container(border=True):
        top_c1, top_c2 = st.columns([1.5, 1])
        with top_c1:
            st.markdown("##### 🚦 Monitoramento de Projetos & Governança Individual")
            st.caption("Clique em qualquer linha da tabela para abrir automaticamente o Raio-X Executivo do projeto abaixo")
        with top_c2:
            ord_criterio = st.segmented_control(
                "Ordenar por:",
                options=["Score de Risco", "Maior CAPEX", "Pior CPI", "Maior Estouro EAC"],
                default="Score de Risco",
                label_visibility="collapsed",
                key="seg_ord_tabela",
            )

        cols_grid = [
            "saude", "codigo", "nome", "unidade", "tipo", "fase", "pm",
            "orcamento_total", "ac", "eac_total", "cpi", "spi", "avanco_fisico", "pontuacao_risco", "achados"
        ]
        df_tabela = df_filtrado[cols_grid].copy()

        if ord_criterio == "Maior CAPEX":
            df_tabela = df_tabela.sort_values(by=["orcamento_total", "pontuacao_risco"], ascending=[False, False])
        elif ord_criterio == "Pior CPI":
            df_tabela = df_tabela.sort_values(by=["cpi", "pontuacao_risco"], ascending=[True, False], na_position="last")
        elif ord_criterio == "Maior Estouro EAC":
            df_tabela["estouro"] = df_tabela["eac_total"] - df_tabela["orcamento_total"]
            df_tabela = df_tabela.sort_values(by="estouro", ascending=False).drop(columns=["estouro"])
        else:
            df_tabela = df_tabela.sort_values(by=["pontuacao_risco", "orcamento_total"], ascending=[False, False])

        df_tabela = df_tabela.reset_index(drop=True)

        evento_sel = st.dataframe(
            df_tabela,
            column_config={
                "saude": st.column_config.TextColumn("Saúde", width="small"),
                "codigo": st.column_config.TextColumn("Código", width="small"),
                "nome": st.column_config.TextColumn("Projeto", width="medium"),
                "unidade": st.column_config.TextColumn("Complexo", width="small"),
                "tipo": st.column_config.TextColumn("Tipo", width="small"),
                "fase": st.column_config.TextColumn("Stage-Gate", width="small"),
                "pm": st.column_config.TextColumn("Gerente (PM)", width="small"),
                "orcamento_total": st.column_config.NumberColumn("CAPEX Total (USD)", format="$%,.0f"),
                "ac": st.column_config.NumberColumn("Realizado (USD)", format="$%,.0f"),
                "eac_total": st.column_config.NumberColumn("EAC Previsto (USD)", format="$%,.0f"),
                "cpi": st.column_config.NumberColumn("CPI", format="%.2f"),
                "spi": st.column_config.NumberColumn("SPI", format="%.2f"),
                "avanco_fisico": st.column_config.ProgressColumn("Avanço Físico", min_value=0.0, max_value=1.0, format="%.0f%%"),
                "pontuacao_risco": st.column_config.NumberColumn("Score Risco", format="%d"),
                "achados": st.column_config.TextColumn("Regras Violadas", width="medium"),
            },
            height=300,
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )

    st.space("small")

    opcoes_proj = (df_tabela["codigo"] + " — " + df_tabela["nome"]).tolist()
    idx_padrao = 0
    if evento_sel and hasattr(evento_sel, "selection") and evento_sel.selection.rows:
        linha_clicada = evento_sel.selection.rows[0]
        if 0 <= linha_clicada < len(opcoes_proj):
            idx_padrao = linha_clicada

    with st.container(border=True):
        rx_hdr1, rx_hdr2 = st.columns([1.2, 1.8])
        with rx_hdr1:
            st.markdown("##### 🔬 Raio-X Executivo do Projeto")
            st.caption("Diagnóstico individual de EVM, decomposição orçamentária, auditoria e riscos")
        with rx_hdr2:
            proj_escolhido = st.selectbox(
                "Projeto em inspeção:",
                opcoes_proj,
                index=idx_padrao,
                label_visibility="collapsed",
            )

        cod_escolhido = proj_escolhido.split(" — ")[0]
        p_row = df_projetos[df_projetos["codigo"] == cod_escolhido].iloc[0]
        pid_escolhido = int(p_row["id"])

        col_rx1, col_rx2, col_rx3, col_rx4, col_rx5, col_rx6 = st.columns(6)
        col_rx1.metric("Status / Semáforo", p_row["saude"], delta=f"Fase: {p_row['fase']}", delta_color="off")
        col_rx2.metric(
            "CAPEX Total Aprovado",
            formatar_usd(p_row["orcamento_total"]),
            delta=f"BAC: {formatar_usd(p_row['orcamento_base'])}",
            delta_color="off",
        )
        var_proj = float(p_row["variacao_vs_orcamento_total"])
        col_rx3.metric(
            "EAC Estimado Final",
            formatar_usd(p_row["eac_total"]),
            delta=f"{formatar_usd(var_proj)} vs Total",
            delta_color="normal" if var_proj >= 0 else "inverse",
        )
        cont_pct = float(p_row["contingencia_restante_pct"]) if pd.notna(p_row["contingencia_restante_pct"]) else 0.0
        col_rx4.metric(
            "Contingência Restante",
            f"{cont_pct:.1%}",
            delta=formatar_usd(p_row["contingencia_restante"]),
            delta_color="normal" if p_row["contingencia_restante"] >= 0 else "inverse",
        )
        cpi_p = float(p_row["cpi"]) if pd.notna(p_row["cpi"]) else 1.0
        spi_p = float(p_row["spi"]) if pd.notna(p_row["spi"]) else 1.0
        col_rx5.metric(
            "Índices CPI / SPI",
            f"{cpi_p:.2f} / {spi_p:.2f}",
            delta=f"Avanço: {p_row['avanco_fisico']:.0%}",
            delta_color="off",
        )
        col_rx6.metric(
            "Gerente (PM)",
            p_row["pm"],
            delta=f"{p_row['unidade']}",
            delta_color="off",
        )

        col_left, col_mid, col_right = st.columns([1.25, 1.05, 1.1])

        with col_left:
            st.markdown("###### 📈 Curva S Individual (PV, EV, AC & Comprometido)")
            curva_p = metrics.curva_s_projeto(port, pid_escolhido)
            fig_p = go.Figure()
            fig_p.add_trace(
                go.Scatter(
                    x=curva_p["mes"], y=curva_p["pv_acum"], mode="lines+markers",
                    name="Planejado (PV)", line=dict(color="#60A5FA", dash="dot", width=2), marker=dict(size=5),
                )
            )
            fig_p.add_trace(
                go.Scatter(
                    x=curva_p["mes"], y=curva_p["ev_acum"], mode="lines+markers",
                    name="Agregado (EV)", line=dict(color="#10B981", width=2.5), marker=dict(size=5),
                )
            )
            fig_p.add_trace(
                go.Scatter(
                    x=curva_p["mes"], y=curva_p["ac_acum"], mode="lines+markers",
                    name="Realizado (AC)", line=dict(color="#EF4444", width=2.5), marker=dict(size=5),
                )
            )
            fig_p.add_trace(
                go.Scatter(
                    x=curva_p["mes"], y=curva_p["comprometido_acum"], mode="lines",
                    name="Comprometido", line=dict(color="#F59E0B", dash="dash", width=2),
                )
            )
            aplicar_tema_plotly(fig_p, height=285)
            fig_p.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_p, width="stretch")

        with col_mid:
            st.markdown("###### 💧 Decomposição Orçamentária (BAC → EAC)")
            bac_v = float(p_row["orcamento_base"])
            cont_v = float(p_row["contingencia"])
            tot_v = float(p_row["orcamento_total"])
            estouro_evm = float(p_row["eac"] - p_row["orcamento_base"])
            mud_v = float(p_row["mudancas_aprovadas"])
            eac_tot_v = float(p_row["eac_total"])

            fig_wf = go.Figure(
                go.Waterfall(
                    orientation="v",
                    measure=["absolute", "relative", "total", "relative", "relative", "total"],
                    x=["BAC Base", "+ Conting.", "CAPEX Total", "Desvio EVM", "Mudanças", "EAC Final"],
                    y=[bac_v, cont_v, tot_v, estouro_evm - cont_v, mud_v, eac_tot_v],
                    connector={"line": {"color": "#475569", "width": 1.5, "dash": "dot"}},
                    increasing={"marker": {"color": "#EF4444"}},
                    decreasing={"marker": {"color": "#10B981"}},
                    totals={"marker": {"color": "#3B82F6"}},
                )
            )
            aplicar_tema_plotly(fig_wf, height=285, show_legend=False)
            fig_wf.update_layout(yaxis_title="USD")
            st.plotly_chart(fig_wf, width="stretch")

        with col_right:
            st.markdown("###### 🚨 Achados de Auditoria do Projeto")
            p_achados = df_achados[df_achados["codigo"] == cod_escolhido]
            if p_achados.empty:
                st.success("✅ Nenhuma não-conformidade detectada neste projeto.")
            else:
                for _, a in p_achados.iterrows():
                    cor_badge = (
                        "badge-red"
                        if a["severidade"] == "Crítico"
                        else ("badge-yellow" if a["severidade"] == "Alto" else "badge-green")
                    )
                    st.markdown(
                        f"<div class='metric-card'>"
                        f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
                        f"<span class='{cor_badge}'>{a['severidade']}</span>"
                        f"<span style='font-size:11px;color:#94A3B8;font-weight:600;'>{a['categoria']} • {a['regra']}</span>"
                        f"</div>"
                        f"<div style='font-weight:600;font-size:13px;color:#F8FAFC;margin-bottom:3px;'>{a['titulo']}</div>"
                        f"<div style='font-size:12px;color:#CBD5E1;line-height:1.4;'>{a['detalhe']}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        c_rk, c_dc, c_mc = st.columns(3)
        with c_rk:
            st.markdown("###### ⚠️ Riscos Abertos do Projeto")
            rk_proj = port.riscos[(port.riscos["projeto_id"] == pid_escolhido) & (port.riscos["status"] == "Aberto")]
            if rk_proj.empty:
                st.caption("Sem riscos em aberto para este projeto.")
            else:
                st.dataframe(
                    rk_proj[["titulo", "nivel", "probabilidade", "impacto", "responsavel", "plano_resposta"]],
                    height=175,
                    width="stretch",
                    hide_index=True,
                )
        with c_dc:
            st.markdown("###### 📄 Checklist de Stage-Gate (FEL)")
            dc_proj = port.documentos_gate[port.documentos_gate["projeto_id"] == pid_escolhido]
            if dc_proj.empty:
                st.caption("Fase atual não exige documentação adicional ou sem registros.")
            else:
                st.dataframe(
                    dc_proj[["documento", "status"]],
                    height=175,
                    width="stretch",
                    hide_index=True,
                )
        with c_mc:
            st.markdown("###### 🏁 Marcos do Cronograma (Milestones)")
            mc_proj = port.marcos[port.marcos["projeto_id"] == pid_escolhido]
            if mc_proj.empty:
                st.caption("Sem marcos cadastrados para este projeto.")
            else:
                st.dataframe(
                    mc_proj[["nome", "critico", "data_planejada", "data_real"]],
                    height=175,
                    width="stretch",
                    hide_index=True,
                )

# ------------------------------------------------------------------------------
# ABA 3: AUDITORIA & STAGE-GATE + MATRIZ DE RISCOS CORPORATIVA (CROSS-FILTER)
# ------------------------------------------------------------------------------
with tab_auditoria:
    n_crit = int((achados_filtrados["severidade"] == "Crítico").sum())
    n_alt = int((achados_filtrados["severidade"] == "Alto").sum())
    total_achados = len(achados_filtrados)

    c_audit1, c_audit2, c_audit3, c_audit4 = st.columns(4)
    c_audit1.metric(
        "Total de Não-Conformidades",
        f"{total_achados}",
        delta=f"Em {achados_filtrados['codigo'].nunique()} projetos",
        delta_color="off",
    )
    c_audit2.metric("Severidade Crítica", f"{n_crit}", delta="Ação imediata comitê", delta_color="inverse" if n_crit > 0 else "off")
    c_audit3.metric("Severidade Alta", f"{n_alt}", delta="Bloqueio de Stage-Gate", delta_color="inverse" if n_alt > 0 else "off")
    c_audit4.metric("Recall vs Gabarito Mock", f"{eval_gab['recall']:.1%}", delta=f"{eval_gab['detectados']}/{eval_gab['total']} falhas injetadas", delta_color="normal")

    st.space("small")

    col_cat1, col_cat2 = st.columns([1.15, 1.15])
    with col_cat1:
        with st.container(border=True):
            st.markdown("##### 📊 Violações por Categoria (Clique para Filtrar)")
            st.caption("Clique em uma barra para filtrar a matriz de achados e todo o portfólio por categoria")

            df_para_cat = aplicar_mascara_cf(df_base, ignorar="audit_cat")
            achados_para_cat = df_achados[df_achados["codigo"].isin(set(df_para_cat["codigo"]))]

            if achados_para_cat.empty:
                st.success("Nenhum achado de auditoria para os filtros selecionados.")
            else:
                df_cat_sev = (
                    achados_para_cat.groupby(["categoria", "severidade"], as_index=False)
                    .size()
                    .rename(columns={"size": "Qtd"})
                )
                fig_cat = px.bar(
                    df_cat_sev,
                    x="Qtd",
                    y="categoria",
                    color="severidade",
                    orientation="h",
                    barmode="stack",
                    color_discrete_map=CORES_SEVERIDADE,
                    category_orders={"severidade": ["Crítico", "Alto", "Médio"]},
                )
                aplicar_tema_plotly(fig_cat, height=295)
                fig_cat.update_layout(
                    xaxis_title="Quantidade de Achados",
                    yaxis_title="",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
                )
                st.plotly_chart(
                    fig_cat,
                    width="stretch",
                    key=f"chart_audit_cat_{rev}",
                    on_select="rerun",
                    selection_mode="points",
                )

    with col_cat2:
        with st.container(border=True):
            st.markdown("##### 🎲 Matriz de Riscos Corporativa 5×5 (Probabilidade × Impacto)")
            st.caption("Concentração de riscos em aberto nos projetos filtrados")

            ids_f = set(df_filtrado["id"])
            rk_abertos = port.riscos[(port.riscos["projeto_id"].isin(ids_f)) & (port.riscos["status"] == "Aberto")]

            matriz_z = np.zeros((5, 5), dtype=int)
            for _, r in rk_abertos.iterrows():
                p_idx = int(np.clip(r["probabilidade"], 1, 5)) - 1
                i_idx = int(np.clip(r["impacto"], 1, 5)) - 1
                matriz_z[p_idx, i_idx] += 1

            fig_hm = go.Figure(
                data=go.Heatmap(
                    z=matriz_z,
                    x=["1 - Muito Baixo", "2 - Baixo", "3 - Moderado", "4 - Alto", "5 - Catastrófico"],
                    y=["1 - Rara", "2 - Improvável", "3 - Possível", "4 - Provável", "5 - Quase Certa"],
                    text=matriz_z,
                    texttemplate="<b>%{text}</b>",
                    textfont={"size": 13, "family": "Inter"},
                    colorscale=[
                        [0.0, "#0F172A"],
                        [0.25, "#1E3A8A"],
                        [0.55, "#F59E0B"],
                        [1.0, "#EF4444"],
                    ],
                    showscale=True,
                    hovertemplate="Impacto: %{x}<br>Probabilidade: %{y}<br>Riscos Abertos: <b>%{z}</b><extra></extra>",
                )
            )
            aplicar_tema_plotly(fig_hm, height=295)
            fig_hm.update_layout(xaxis_title="Impacto no Projeto", yaxis_title="Probabilidade")
            st.plotly_chart(fig_hm, width="stretch")

    col_regras, col_gab = st.columns([1.2, 1.1])
    with col_regras:
        with st.container(border=True):
            st.markdown("##### 🏆 Ranking de Regras Violadas (Clique para Filtrar)")
            df_para_reg = aplicar_mascara_cf(df_base, ignorar="audit_reg")
            achados_para_reg = df_achados[df_achados["codigo"].isin(set(df_para_reg["codigo"]))]
            if cf_ativos["categoria"]:
                achados_para_reg = achados_para_reg[achados_para_reg["categoria"].isin(cf_ativos["categoria"])]

            if not achados_para_reg.empty:
                df_reg = (
                    achados_para_reg.groupby(["regra", "titulo", "severidade"], as_index=False)
                    .size()
                    .rename(columns={"size": "Ocorrências"})
                    .sort_values("Ocorrências", ascending=True)
                )
                fig_reg = px.bar(
                    df_reg,
                    x="Ocorrências",
                    y="regra",
                    color="severidade",
                    orientation="h",
                    hover_data=["titulo"],
                    color_discrete_map=CORES_SEVERIDADE,
                )
                aplicar_tema_plotly(fig_reg, height=270)
                fig_reg.update_layout(
                    yaxis_title="",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
                )
                st.plotly_chart(
                    fig_reg,
                    width="stretch",
                    key=f"chart_audit_reg_{rev}",
                    on_select="rerun",
                    selection_mode="points",
                )
            else:
                st.info("Sem ocorrências para exibir.")

    with col_gab:
        with st.container(border=True):
            st.markdown("##### 🧪 Auditoria Determinística vs Gabarito Oficial (Mock Recall)")
            st.caption(
                f"Injetados: **{eval_gab['total']}** | Detectados: **{eval_gab['detectados']}** "
                f"(**{eval_gab['recall']:.1%} recall**) | Precisão: **{eval_gab['precisao']:.1%}**"
            )
            if not eval_gab["por_regra"].empty:
                st.dataframe(
                    eval_gab["por_regra"],
                    column_config={
                        "problema": st.column_config.TextColumn("Regra Auditada"),
                        "injetados": st.column_config.NumberColumn("Injetados"),
                        "detectados": st.column_config.NumberColumn("Detectados"),
                        "recall": st.column_config.ProgressColumn("Taxa de Detecção", format="%.0f%%", min_value=0.0, max_value=1.0),
                        "extras": st.column_config.NumberColumn("Achados Orgânicos"),
                    },
                    height=245,
                    width="stretch",
                    hide_index=True,
                )

    with st.container(border=True):
        st.markdown("##### 📋 Matriz Completa de Não-Conformidades Auditadas")
        st.dataframe(
            achados_filtrados[["severidade", "codigo", "projeto", "unidade", "pm", "categoria", "regra", "titulo", "detalhe"]],
            column_config={
                "severidade": st.column_config.TextColumn("Severidade", width="small"),
                "codigo": st.column_config.TextColumn("Código", width="small"),
                "projeto": st.column_config.TextColumn("Projeto", width="medium"),
                "unidade": st.column_config.TextColumn("Complexo", width="small"),
                "pm": st.column_config.TextColumn("PM", width="small"),
                "categoria": st.column_config.TextColumn("Categoria", width="small"),
                "regra": st.column_config.TextColumn("Regra", width="small"),
                "titulo": st.column_config.TextColumn("Título da Regra", width="medium"),
                "detalhe": st.column_config.TextColumn("Evidência Determinística", width="large"),
            },
            height=320,
            width="stretch",
            hide_index=True,
        )

# ------------------------------------------------------------------------------
# ABA 4: PMO COPILOT IA (CREWAI)
# ------------------------------------------------------------------------------
with tab_copilot:
    with st.container(border=True):
        st.subheader("📑 Geração Autônoma de Relatório Executivo (Equipe CrewAI + Gemini)")
        st.caption(
            "Os 4 agentes consomem exclusivamente as ferramentas determinísticas em Python (zero contas no LLM) "
            "e passam por validador anti-alucinação de códigos de projeto."
        )

        ag1, ag2, ag3, ag4 = st.columns(4)
        with ag1:
            with st.container(border=True):
                st.markdown("**🧮 Controller CAPEX & EVM**")
                st.caption("Diagnostica desvios orçamentários, CPI, EAC e queima precoce de contingência.")
        with ag2:
            with st.container(border=True):
                st.markdown("**🔍 Auditor de Stage-Gate**")
                st.caption("Fiscaliza baselines aprovadas, documentos obrigatórios FEL e projetos zumbis.")
        with ag3:
            with st.container(border=True):
                st.markdown("**⚠️ Especialista em Riscos**")
                st.caption("Mapeia riscos críticos sem dono, ausência de plano de mitigação e sobrecarga de PMs.")
        with ag4:
            with st.container(border=True):
                st.markdown("**📝 Gerente Geral do PMO**")
                st.caption("Consolida o parecer executivo para o Comitê de Investimentos da MineraSul.")

        chave_atual = os.getenv("GEMINI_API_KEY", "").strip()

        col_btn, col_info = st.columns([1.2, 2.8])
        with col_btn:
            gerar_acionado = st.button("🚀 Executar Equipe de Agentes PMO", type="primary", width="stretch")
        with col_info:
            st.caption("Tempo médio de execução da Crew completa: 30 a 60 segundos.")

        if gerar_acionado:
            if not chave_atual:
                st.error("❌ GEMINI_API_KEY não configurada. Defina no arquivo `.env` ou insira na barra lateral.")
            else:
                with st.spinner("Executando agentes CrewAI com Gemini... Isso pode levar de 30 a 60 segundos."):
                    try:
                        from pmo_copilot.cli import gerar_relatorio_executivo
                        rel_path = gerar_relatorio_executivo(api_key=chave_atual)
                        st.success("✅ Relatório executivo gerado com sucesso!")
                        st.session_state["ultimo_relatorio"] = rel_path.read_text(encoding="utf-8")
                    except Exception as e:
                        st.error(f"Erro ao executar agentes: {e}")

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    relatorios_existentes = sorted(list(config.REPORTS_DIR.glob("*.md")), reverse=True)

    with st.container(border=True):
        if "ultimo_relatorio" in st.session_state:
            st.markdown("#### 📄 Relatório Recém-Gerado")
            st.download_button(
                "📥 Baixar Relatório (.md)",
                st.session_state["ultimo_relatorio"],
                file_name="relatorio_pmo_copilot.md",
            )
            st.markdown(st.session_state["ultimo_relatorio"])
        elif relatorios_existentes:
            c_r1, c_r2 = st.columns([2, 1])
            with c_r1:
                escolha_rel = st.selectbox(
                    "📁 Histórico de Relatórios Executivos Salvos:",
                    relatorios_existentes,
                    format_func=lambda p: p.name,
                )
            conteudo_rel = escolha_rel.read_text(encoding="utf-8")
            with c_r2:
                st.space("small")
                st.download_button(
                    "📥 Baixar Este Relatório (.md)",
                    conteudo_rel,
                    file_name=escolha_rel.name,
                    width="stretch",
                )
            st.markdown(conteudo_rel)
        else:
            st.info("Nenhum relatório foi gerado ainda. Clique no botão acima para acionar a equipe de agentes!")

