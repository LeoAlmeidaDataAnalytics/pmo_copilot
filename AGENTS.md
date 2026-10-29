# AGENTS.md — PMO Copilot (MineraSul S.A.)
> Documento de contexto e diretrizes de engenharia para o Antigravity CLI e agentes de desenvolvimento.
> Carregado automaticamente pelo Antigravity ao inicializar neste repositório para economia de tokens e alinhamento instantâneo.

---

## 🏢 Domínio e Contexto do Projeto
- **Empresa:** MineraSul S.A. (Mineradora multinacional fictícia com complexos em Tapajós, Serra Azul, Carajás Norte, Unidade Andina e Minas Centrais).
- **Portfólio:** 350 projetos de capital (CAPEX) totalizando ~US$ 14,5 Bilhões em moeda estrangeira (**sempre USD**).
- **Frameworks de Governança:** 
  - EVM (*Earned Value Management* / Valor Agregado: PV, EV, AC, CPI, SPI, EAC, VAC).
  - Metodologia *Front-End Loading* (FEL 1 - Identificação, FEL 2 - Seleção, FEL 3 - Definição, Implantação e Operação/Encerramento).
  - Matriz de Riscos Corporativa (Crítico, Alto, Médio, Baixo).

---

## ⚖️ Princípio Arquitetural Fundamental (Regra de Ouro)
> **O LLM NUNCA FAZ CONTAS.**
1. **Cálculos Determinísticos em Python:** Todos os cálculos de EVM, métricas agregadas de portfólio, verificação das 16 regras de conformidade e semáforos de saúde (🔴/🟡/🟢) são obrigatoriamente executados em Python puro com Pandas/NumPy (`metrics.py`, `compliance.py`).
2. **Papel dos Modelos de IA (CrewAI + Gemini):** O LLM é acionado unicamente para redigir análises estratégicas executivas em prosa e responder a dúvidas conversacionais em linguagem natural com base nos dados exatos fornecidos via tools determinísticas (`tools.py`, `chat.py`).
3. **Validação Anti-Alucinação (`reporting.py`):** Todo texto gerado pela IA passa por validação com expressões regulares (`REGEX_CODIGO`, `REGEX_CODIGO_SUSPEITO`) para garantir que nenhum código de projeto seja inventado.

---

## 🗂️ Estrutura do Código e Módulos
- **`app.py`:** Dashboard executivo principal em Streamlit (AI-First + Cross-Filtering estilo PowerBI):
  - **Topo da Página Principal (Assistente Gemini Web):** Saudação minimalista em gradiente (`✦ Olá, Executivo do PMO`), barra de digitar em formato pílula (`st.chat_input`) centralizada e 4 chips de perguntas sugeridas posicionados **abaixo** da barra de digitar.
  - **Barra de Status Cross-Filter (PowerBI):** Exibe chips ativos quando qualquer elemento de gráfico é clicado e botão `🔄 Limpar Seleção dos Gráficos`.
  - **4 Abas Analíticas Abaixo do Assistente:**
    1. *Painel Executivo Interativo (PowerBI):* 6 KPIs com sparklines e deltas, Alocação por Complexo clicável (`Barras` ou `Treemap`), Distribuição clicável (`Semáforo`, `Funil FEL`, `Por Tipo`), Curva S multi-modo (`Acumulado`, `Desembolso Mensal`, `Variações CV & SV`) e Matriz de Quadrantes EVM (`CPI × SPI`) com suporte a clique, Box e Lasso select.
    2. *Semáforo & Raio-X de Projetos:* Tabela interativa com seleção de linha (`on_select="rerun"`), ordenação rápida, Curva S individual, gráfico Waterfall (`BAC → EAC`), cartões de achados, riscos abertos, checklist FEL e marcos (milestones).
    3. *Auditoria Stage-Gate & Matriz 5×5:* Violações por categoria/severidade clicáveis, Matriz de Riscos Corporativa 5×5 (Heatmap `Probabilidade × Impacto`), ranking clicável das 16 regras oficiais, validação de recall vs gabarito mock (100% de recall em 115 falhas injetadas) e matriz completa de não-conformidades.
    4. *Relatório Executivo Autônomo (CrewAI):* Geração autônoma com equipe de 4 agentes e download de relatórios salvos em `reports/`.
- **`src/pmo_copilot/`:**
  - `config.py`: Gestão de caminhos (`DATA_DIR`, `REPORTS_DIR`, `DB_PATH`) e carregamento de chaves (`GEMINI_API_KEY`).
  - `domain.py`: Constantes, fases FEL, enumerações de risco e catálogo oficial das 16 regras de auditoria.
  - `data/generator.py`: Gerador sintético de 350 projetos, curvas temporais S, riscos e documentos com injeção de falhas conhecidas.
  - `data/repository.py`: Acesso ao banco de dados relacional SQLite (`data/portfolio.db`).
  - `analytics/metrics.py`: Fórmulas exatas de EVM e cálculo de curvas S acumuladas.
  - `analytics/compliance.py`: Motor determinístico de auditoria e atribuição de semáforo.
  - `reporting.py`: Montagem de relatórios com números do sistema e validador anti-alucinação de códigos.
  - `health.py`: Health checks determinísticos (liveness, readiness, deep) com status RFC pass/warn/fail: SQLite, motor EVM, API Gemini (chave mascarada) e I/O. Exibido no dashboard (pílula `/health` + popover na sidebar).
  - `agents/tools.py`: Ferramentas estruturadas (`@tool`) para CrewAI consumirem o motor determinístico.
  - `agents/crew.py`: Definição dos 4 agentes CrewAI (Controller CAPEX, Auditor Stage-Gate, Especialista em Riscos, Gerente Geral PMO).
  - `agents/chat.py`: Orquestrador conversacional do chat com injeção de contexto estruturado.
  - `cli.py`: Ponto de entrada CLI para geração de relatórios sem interface web.
- **`tests/`:** Suíte completa com 17 testes unitários cobrindo analytics, compliance, chat, reporting e health.
- **`.streamlit/config.toml`:** Configuração padrão do Tema Escuro (*Dark Mode* / Deep Slate) com fonte Inter nativa.

---

## 🎨 Diretrizes de UI / Streamlit
1. **Tema Noturno Obrigatório:** Cores de fundo `#0F172A` (background) e `#1E293B` (secondary), texto `#F1F5F9`, bordas `#334155`.
2. **Chat Estilo Gemini Web no Topo:** O chat conversacional fica sempre no topo da página principal, sem borda pesada, com barra de digitar arredondada e pílulas de sugestão abaixo da barra.
3. **Gráficos Plotly & Cross-Filtering (PowerBI):** Todos os gráficos devem conter `template="plotly_dark"`, fundos transparentes `paper_bgcolor="rgba(0,0,0,0)"`, `plot_bgcolor="rgba(0,0,0,0)"`, fontes `Inter` e suporte a seleção interativa (`on_select="rerun"`) para filtrar os demais visuais dinamicamente.
4. **Depreciações:** NUNCA utilizar `use_container_width=True`. Utilizar `width="stretch"` ou a nova API nativa do Streamlit.
5. **Segurança de API Key:** A chave `GEMINI_API_KEY` nunca deve ser exibida em texto aberto no front-end. Utilizar campo de senha `type="password"` ou carregar de `.env`.

---

## 🧪 Comandos Úteis de Desenvolvimento
- **Executar testes:** `.venv/bin/pytest -v`
- **Verificar compilação:** `.venv/bin/python -m compileall src/ app.py tests/`
- **Testar Streamlit sem abrir navegador (Headless):**
  `.venv/bin/python -c "from streamlit.testing.v1 import AppTest; at = AppTest.from_file('app.py').run(); assert len(at.exception) == 0; print('OK')"`
- **Executar app:** `.venv/bin/streamlit run app.py`

