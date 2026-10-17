# 📋 Status Executivo do Projeto — PMO Copilot (MineraSul S.A.)
> Documentação executiva consolidada: marcos alcançados, arquitetura, trabalho realizado hoje e roadmap futuro.

---

## 🌟 1. Highlights do Projeto (O que foi Feito)

### 🔹 Engenharia Confiável de IA: Princípio Determinístico
- **Separação Rígida de Responsabilidades:** O LLM **nunca** calcula números, médias, somatórios ou desvios. O motor Python (Pandas/NumPy) processa todas as métricas de EVM, curvas S, semáforos e auditoria.
- **Camada de IA Focada em Síntese:** Os modelos (Google Gemini 2.5 Flash via CrewAI) atuam exclusivamente naquilo em que são superiores: síntese executiva, análise de correlações e interação conversacional.
- **Motor Anti-Alucinação:** Validador embutido (`reporting.py`) que audita via Regex os códigos de projetos citados pela IA. Se o modelo inventar um código fictício (ex.: `PRJ-SA-004`), o sistema sinaliza com alerta visual vermelho.

### 🔹 Motor de Auditoria e Recall de 100%
- **Catálogo de 16 Regras de Governança:** Mapeia desvios financeiros (CPI, estouro de EAC, queima prematura de contingência), cronograma (SPI, marcos atrasados, prazo expirado), governança (projetos sem baseline, documentos mandatórios ausentes, projetos zumbis) e riscos (riscos críticos sem responsável ou sem plano).
- **Benchmark com Gabarito Conhecido:** O gerador sintético injetou 115 falhas intencionais na base mock de 350 projetos. O motor determinístico atingiu **100% de recall (115/115 detectadas)** na auditoria.

### 🔹 Interface Executiva AI-First (Gemini Web + PowerBI Cross-Filtering)
- **Assistente no Topo Estilo Gemini Web:** Saudação centralizada em gradiente (`✦ Olá, Executivo do PMO`), barra de digitar arredondada em formato pílula (`st.chat_input`) e pílulas de perguntas sugeridas posicionadas **abaixo** da barra de digitar.
- **Cross-Filtering Dinâmico (Estilo PowerBI):** Clique em qualquer barra de complexo, fatia do semáforo, etapa do funil FEL, categoria de auditoria ou seleção de bolhas no Quadrante EVM (`CPI × SPI`) para recalcular instantaneamente todos os demais gráficos, KPIs e Curva S.
- **Design System Deep Slate:** Tipografia **Inter** nativa, paleta `#0F172A` e `#1E293B`, gráficos Plotly em tema escuro (`template="plotly_dark"` com fundos transparentes) e logotipo oficial vetorial do Google Gemini na barra lateral.

---

## 🚀 2. Principais Funcionalidades

### 1. Copiloto Conversacional no Topo da Página Principal (Estilo Gemini Web)
- Interação conversacional direta com o agente PMO em linguagem natural logo ao abrir o aplicativo.
- Barra de digitar centralizada com 4 pílulas de consulta executiva abaixo:
  - *"🚩 Tapajós com SPI < 0.9"*
  - *"⚠️ Riscos críticos sem dono"*
  - *"👤 PMs sobrecarregados"*
  - *"💸 Maiores estouros de EAC"*
- Histórico expansível sob demanda com botão discreto de *Nova conversa*.

### 2. Painel Executivo Interativo com Cross-Filtering PowerBI (Aba 1)
- **6 KPIs Executivos com Sparklines e Deltas:** Portfólio Selecionado, CAPEX Aprovado, Realizado (AC com sparkline de barras), EAC Projetado Final (com sparkline de EV), CPI Consolidado e SPI Consolidado.
- **Alocação por Complexo Clicável & Treemap CAPEX:** Comparativo de Orçamento, Comprometido, Realizado e marcadores de EAC Projetado, ou visão hierárquica em Treemap (`Unidade → Tipo → Projeto`) colorida por CPI.
- **Distribuição Multi-Perspectiva Clicável:** Alternância rápida entre **Semáforo (Donut)**, **Funil Stage-Gate FEL** e **Barras por Tipo de Investimento**.
- **Curva S Multi-Modo com Range Selector (`6M`, `1A`, `2A`, `Tudo`):** Alternância entre *Acumulado (Curva S)*, *Desembolso Mensal* e *Variações Acumuladas (`CV` e `SV`)*.
- **Matriz de Quadrantes EVM (`CPI × SPI`):** Gráfico de bolhas interativo com suporte a clique individual, *Box Select* e *Lasso Select*.

### 3. Semáforo & Raio-X Detalhado de Projetos por Clique (Aba 2)
- **Seleção Direta na Tabela (`on_select="rerun"`):** Basta clicar em qualquer linha da tabela para carregar o Raio-X completo do projeto abaixo, com ordenação rápida por *Score de Risco*, *Maior CAPEX*, *Pior CPI* ou *Maior Estouro EAC*.
- **Inspeção Individual (Deep Dive):**
  - 6 KPIs individuais do projeto (Status/Fase, CAPEX/BAC, EAC Final, Contingência Restante, CPI/SPI e PM/Complexo).
  - Curva S individual do projeto (PV, EV, AC e Comprometido).
  - Gráfico **Waterfall de Decomposição Orçamentária (`BAC → EAC`)**.
  - Cartões de achados de auditoria, tabela de riscos abertos, checklist de documentos FEL e tabela de marcos (*milestones*).

### 4. Auditoria Stage-Gate & Matriz de Riscos 5×5 (Aba 3)
- Contadores de não-conformidades por severidade e Recall vs. Gabarito Mock (100%).
- Gráfico empilhado de violações por categoria e severidade (clicável para cross-filter).
- **Matriz de Riscos Corporativa 5×5 (Heatmap `Probabilidade × Impacto`)** dos riscos abertos.
- Ranking clicável das 16 regras oficiais do PMO e tabela completa de evidências determinísticas.

### 5. Relatório Executivo Autônomo com Equipe CrewAI (Aba 4)
- **Equipe Especializada de 4 Agentes:** Controller de CAPEX & EVM, Auditor de Stage-Gate, Especialista em Riscos e Gerente Geral do PMO.
- **Histórico e Exportação:** Visualização no app e botão de download imediato em Markdown (`.md`).

---

## 🛠️ 3. O Que Foi Realizado (Resumo das Entregas)

1. **Redesign Executivo AI-First (Estilo Gemini Web) & PowerBI Cross-Filtering:**
   - Posicionamento do **Assistente de IA do PMO no topo da página principal**, com saudação minimalista em gradiente, barra de digitar em pílula arredondada e sugestões posicionadas abaixo da barra.
   - Implementação de **Cross-Filtering bidirecional entre gráficos** via `st.plotly_chart(..., on_select="rerun")`, com barra de status dinâmica de filtros ativos e botão de reset instantâneo.
   - Adição de novos visuais executivos: **KPIs com Sparklines de 12 meses**, **Matriz de Quadrantes EVM (`CPI × SPI`)**, **Funil Stage-Gate FEL**, **Treemap Hierárquico de CAPEX**, **Waterfall Orçamentário (`BAC → EAC`)** e **Heatmap 5×5 da Matriz de Riscos**.
   - Seleção interativa por clique de linha (`on_select="rerun"`) na tabela de projetos para atualização imediata do Raio-X.

2. **Correção de Regressões e Erros Críticos:**
   - **`KeyError: 'pv_acum'`**: Corrigida a agregação de séries temporais na função `curva_s_portfolio` em `metrics.py`.
   - **`UnboundLocalError: local variable 'df' referenced before assignment`**: Corrigida a extração de dados nas ferramentas CrewAI em `tools.py`.
   - **Erros de Sintaxe em Arquivos Core**: Removidos caracteres acidentais no topo de `generator.py`, `config.py` e `pyproject.toml`.

3. **Segurança, Identidade Visual e Testes Automatizados:**
   - Proteção da chave `GEMINI_API_KEY` via `.env` ou campo `type="password"`, com badge vetorial do Google Gemini na sidebar.
   - Padronização completa em Dark Mode (`#0F172A` / `#1E293B`), fonte **Inter** e substituição de parâmetros depreciados por `width="stretch"`.
   - Aprovação integral dos **13 testes unitários** (`pytest`) e validação headless da interface com `AppTest` (0 exceções).


---

## 🧭 4. O Que Falta / Próximos Passos (Roadmap)

Embora o sistema esteja 100% funcional, robusto e esteticamente refinado, as seguintes evoluções elevarão o PMO Copilot a um nível corporativo de classe mundial:

### 1. Conectores de Dados Reais da Mineração (Fase 1 de Produção)
- [ ] **Importador de Cronogramas:** Suporte à importação de arquivos `.xer` (Oracle Primavera P6) ou `.mpp` (MS Project) para cálculo dinâmico da curva S física.
- [ ] **Integração ERP/Contábil:** Leitura de planilhas Excel padronizadas ou conexão com SAP/Totvs para importação de pedidos de compra e lançamentos reais de CAPEX.

### 2. Exportação de Relatórios Executivos em PDF Formatado
- [ ] Gerador de PDF corporativo via `WeasyPrint` ou `ReportLab`, contendo o relatório executivo gerado pelos agentes, gráficos Plotly convertidos em imagem de alta resolução e layout timbrado da MineraSul S.A.

### 3. Automação de Alertas e Notificações (Workflows Ativos)
- [ ] Envio automático de alertas semanais via e-mail ou webhook (Microsoft Teams / Slack) para gerentes de projeto cujos projetos entraram no semáforo vermelho ou possuem riscos críticos sem dono.

### 4. Simulação de Cenários (*What-If* / Monte Carlo)
- [ ] Aba adicional para modelar cenários de alocação de capital: *"E se contingenciarmos 15% do Complexo Tapajós e remanejarmos para Serra Azul?"*, calculando o impacto no EAC e na taxa de entrega do portfólio.

### 5. Controle de Acesso e Governança Multi-Perfil
- [ ] Integração com autenticação corporativa (SSO / OAuth2) diferenciando perfis de acesso: Diretoria Executiva (visão ampla consolidada), Gerentes de Projeto (somente seus projetos) e Auditores de Governança.
