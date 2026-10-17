# ⛏️ PMO Copilot — MineraSul S.A.

Assistente autônomo de inteligência artificial para **Governança de Portfólio, Auditoria Stage-Gate (FEL) e Controle Financeiro de CAPEX** em uma mineradora multinacional.

Desenvolvido com **CrewAI + Google Gemini**, **Streamlit (Dark Theme)**, **Plotly** e **Pandas/NumPy**.

---

## 🎯 Arquitetura & Princípio Fundamental
O sistema foi concebido com uma premissa inegociável de **engenharia confiável de IA**:
> **O LLM NUNCA FAZ CONTAS.**
> 
> Todos os cálculos contábeis e de engenharia (EVM, CPI, SPI, EAC, VAC, queima de contingência, curvas S acumuladas e checagem de 16 regras de conformidade) são executados exclusivamente por código **Python determinístico**.
> 
> A equipe de IA (CrewAI + Google Gemini) é alimentada com esses dados exatos e atua no que a IA generativa faz de melhor: **interpretação estratégica, correlação causal, síntese executiva e respostas conversacionais em linguagem natural**.

```
MineraSul S.A. (>300 Projetos Mock — ~US$ 14.5 Bi)
       │
       ▼
┌────────────────────────────────────────────────────────┐
│  Motor Determinístico Python (Pandas/NumPy)            │
│  - EVM: CPI, SPI, EAC, VAC, Contingência, Curvas S     │
│  - Auditoria: 16 regras (Stage-Gate, Baselines, Riscos)│
│  - Semáforo de Saúde: 🟢 Verde | 🟡 Amarelo | 🔴 Vermelho│
└────────────────────────────────────────────────────────┘
       │
       ▼ (Tools Determinísticas: KPIs, Filtros, Ficha, Riscos, PMs)
┌────────────────────────────────────────────────────────┐
│  Camada de Inteligência (CrewAI + Gemini 2.5 Flash)    │
│  1. 🤖 Assistente Conversacional (Chat com Portfólio)  │
│  2. 📝 Equipe de Relatório Executivo Mensal            │
│     - Controller de CAPEX & EVM                        │
│     - Auditor de Stage-Gate (FEL)                      │
│     - Especialista em Riscos e Alocação de PMs         │
│     - Gerente Geral do PMO (Compilação e Decisões)     │
│  3. 🛡️ Validador Anti-Alucinação (Regex Sanitizer)    │
└────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────┐
│  Interface Executiva AI-First (app.py — Dark Mode)     │
│  - ✦ Topo: Chat estilo Gemini Web (Input + Sugestões)  │
│  - ⚡ Cross-Filtering Dinâmico entre Gráficos (PowerBI) │
│  - 📊 Aba 1: Painel Executivo, Curva S & Quadrante EVM │
│  - 🚦 Aba 2: Semáforo, Waterfall & Raio-X por Clique   │
│  - 🔍 Aba 3: Auditoria Stage-Gate & Matriz Riscos 5×5  │
│  - 📑 Aba 4: Relatório Executivo CrewAI (.md)          │
└────────────────────────────────────────────────────────┘
```

---

## 🗂️ Estrutura do Projeto

```
teste/
├── app.py                      # Aplicação web Streamlit (AI-First + Cross-Filtering PowerBI)
├── pyproject.toml              # Empacotamento profissional (Python >=3.10)
├── README.md                   # Documentação completa do projeto
├── AGENTS.md                   # Contexto de projeto para o Antigravity CLI (economiza tokens)
├── GEMINI.md                   # Ponte de regras para agentes Gemini
├── .env                        # Chaves de API (GEMINI_API_KEY, GEMINI_MODEL)
├── .streamlit/
│   └── config.toml             # Tema escuro profissional (Deep Slate + Inter)
├── data/
│   ├── portfolio.db            # Banco SQLite com tabelas relacionais do portfólio
│   └── gabarito.csv            # Gabarito de falhas injetadas (Recall de 100%)
├── reports/                    # Relatórios executivos gerados pelos agentes em Markdown
├── src/
│   └── pmo_copilot/
│       ├── __init__.py
│       ├── config.py           # Configurações de caminhos e inicialização do Gemini
│       ├── domain.py           # Regras de conformidade, limites, matriz de risco e fases FEL
│       ├── reporting.py        # Montagem do relatório e validador anti-alucinação
│       ├── cli.py              # Linha de comando para rodar a Crew autônoma
│       ├── data/
│       │   ├── generator.py    # Gerador sintético com curvas S, EVM e injeção de falhas
│       │   └── repository.py   # Carregamento e abstração do SQLite
│       ├── analytics/
│       │   ├── metrics.py      # Fórmulas EVM, agregadores e curva S acumulada
│       │   └── compliance.py   # Motor de auditoria das 16 regras e semáforo
│       └── agents/
│           ├── tools.py        # Ferramentas CrewAI determinísticas
│           ├── crew.py         # Montagem da equipe de 4 agentes especializados
│           └── chat.py         # Orquestrador conversacional do chat interativo
└── tests/
    ├── test_analytics.py       # Testes unitários de EVM e consistência contábil
    ├── test_compliance.py      # Testes de auditoria e recall contra o gabarito mock
    ├── test_chat.py            # Testes do agente conversacional
    └── test_reporting.py       # Testes do validador anti-alucinação de códigos
```

---

## 🚀 Como Executar

### 1. Ativar o Ambiente Virtual
```bash
source .venv/bin/activate
```

### 2. Iniciar o Dashboard Streamlit (Recomendado)
```bash
streamlit run app.py
```
Acesse no seu navegador: `http://localhost:8501`.

No dashboard você pode:
- **Conversar com o Assistente no Topo (Estilo Gemini Web):** Barra de digitar centralizada com chips de perguntas sugeridas logo abaixo (*"Tapajós com SPI < 0.9"*, *"Riscos críticos sem dono"*, *"PMs sobrecarregados"*, *"Maiores estouros de EAC"*).
- **Usar Cross-Filtering Dinâmico (Estilo PowerBI):** Clicar em qualquer barra de complexo, fatia do semáforo, etapa do funil FEL, categoria de auditoria ou selecionar bolhas no Quadrante EVM (`CPI × SPI`) para filtrar instantaneamente todos os outros gráficos, KPIs e Curva S.
- **Inspecionar o Raio-X por Clique:** Clicar em qualquer linha da tabela de projetos na Aba 2 para atualizar na hora a Curva S individual, a decomposição orçamentária Waterfall (`BAC → EAC`), achados de auditoria, riscos, documentos FEL e marcos.
- **Auditar Stage-Gate & Matriz de Riscos 5×5:** Analisar o Heatmap `Probabilidade × Impacto`, ranking das 16 regras e validação de 100% de recall contra o gabarito mock.
- **Gerar Relatórios Autônomos (CrewAI):** Acionar a equipe de 4 agentes para produzir o parecer executivo completo com download imediato em `.md`.

### 3. Gerar Relatório Executivo via Terminal
```bash
python -m pmo_copilot.cli
```
O relatório será gravado automaticamente na pasta `reports/`.

### 4. Rodar a Suíte de Testes Automatizados (13 Testes)
```bash
pytest -v
```

### 5. Regenerar ou Alterar o Volume da Base Mock
```bash
python -m pmo_copilot.data.generator --n 350 --seed 42
```
Também disponível interativamente na barra lateral do Streamlit!


---

## 📌 As 16 Regras de Governança Auditadas

| Categoria | Regra | Condição de Disparo | Gravidade |
|---|---|---|---|
| **Financeiro** | `CPI_BAIXO` | CPI < 0.90 (ou crítico se < 0.80) — custo real superando valor entregue | Alto / Crítico |
| **Financeiro** | `EAC_ESTOURO` | EAC Projetado > Orçamento Total (Base + Contingência) | Crítico |
| **Financeiro** | `CONTINGENCIA` | < 25% de contingência disponível com avanço físico < 60% | Crítico |
| **Financeiro** | `OPEX_EM_CAPEX` | Despesas operacionais classificadas indevidamente como investimento | Alto |
| **Financeiro** | `COMPROMETIDO_ABERTO` | Projeto encerrado mantendo contratos ou pedidos em aberto | Alto |
| **Prazo** | `SPI_BAIXO` | SPI < 0.90 (ou crítico se < 0.80) — cronograma atrasado | Alto / Crítico |
| **Prazo** | `PRAZO_VENCIDO` | Data de término da linha de base ultrapassada e projeto segue ativo | Crítico |
| **Prazo** | `MARCO_ATRASADO` | Marco crítico com atraso superior a 60 dias sem entrega concluída | Alto |
| **Governança** | `SEM_BASELINE` | Projeto em fase de Execução sem linha de base formalizada | Crítico |
| **Governança** | `DOC_GATE_AUSENTE` | Documento mandatório da fase (ex: Licença, Projeto Executivo) ausente | Crítico |
| **Governança** | `REPORT_ATRASADO` | Status report mensal sem atualização há mais de 40 dias | Médio |
| **Governança** | `MUDANCA_PENDENTE` | Solicitação de mudança (change request) travada há mais de 60 dias | Médio |
| **Governança** | `ZUMBI` | Projeto classificado como ativo, mas sem desembolso nos últimos 4 meses | Alto |
| **Governança** | `PM_SOBRECARREGADO` | Gerente de projetos (PM) acumulando mais de 6 projetos sob sua gestão | Alto |
| **Riscos** | `RISCO_SEM_DONO` | Risco Alto ou Crítico em aberto sem gestor responsável designado | Crítico |
| **Riscos** | `RISCO_SEM_PLANO` | Risco Alto ou Crítico aberto sem plano de mitigação aprovado | Alto |

---

## 🛡️ Validador Anti-Alucinação (`reporting.py`)
Para impedir erros comuns em relatórios gerados por IA generativa:
1. **Validação de Sintaxe e Existência:** Varre o texto gerado em busca de códigos de projeto no padrão corporativo (`ABC-2024-001`). Se o modelo citar um código inexistente, um aviso com tarja vermelha é injetado no relatório.
2. **Detecção de Códigos Inventados:** Identifica padrões artificiais frequentes em modelos (ex: `PRJ-SA-004`) e notifica a governança.
3. **Tabelas e KPIs Nativos:** As tabelas executivas não são geradas pela IA; elas são compiladas diretamente pelo Python e anexadas ao Markdown final.

---

## 🤖 Integração com Antigravity CLI (`AGENTS.md`)
O repositório inclui o arquivo de governança de agentes `AGENTS.md` (e `GEMINI.md`) na raiz. Quando qualquer sessão do **Antigravity CLI** é iniciada, ele carrega automaticamente esse contexto, garantindo:
- **Economia maciça de tokens**: A IA não precisa navegar e reler arquivos dezenas de vezes para entender a arquitetura.
- **Aderência estrita à regra determinística**: Impede que futuras sessões tentem fazer cálculos matemáticos no prompt.
- **Padronização de código e UI**: Preserva o Dark Theme e o estilo dos componentes Streamlit.
