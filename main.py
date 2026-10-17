import os
from datetime import datetime
from getpass import getpass
from dotenv import load_dotenv, set_key
from crewai import Agent, Task, Crew, Process, LLM

# Carrega a chave de API do arquivo .env
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_PATH)

# ==========================================
# 0. Configurando o Gemini
# ==========================================
def obter_chave_gemini() -> str:
    """Lê a GEMINI_API_KEY do ambiente/.env ou pede ao usuário no terminal."""
    chave = os.getenv("endedo", "").strip()
    if chave:
        return chave

    chave = getpass("Digite sua GEMINI_API_KEY (entrada oculta): ").strip()
    if not chave:
        raise SystemExit("Erro: nenhuma GEMINI_API_KEY informada.")

    if input("Salvar a chave no arquivo .env? [s/N]: ").strip().lower() == "s":
        set_key(ENV_PATH, "GEMINI_API_KEY", chave)
        print(f"Chave salva em {ENV_PATH}")

    os.environ["GEMINI_API_KEY"] = chave
    return chave


gemini_llm = LLM(
    model=f"gemini/{os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')}",
    api_key=obter_chave_gemini(),
    temperature=0.7,
)

# ==========================================
# 1. Definindo os Agentes
# ==========================================
pesquisador = Agent(
    role='Pesquisador Sênior de Tecnologia',
    goal='Descobrir as tendências mais recentes sobre arquiteturas Multi-Agentes',
    backstory='Você é um pesquisador experiente em Inteligência Artificial, focado em descobrir padrões arquiteturais inovadores e ferramentas de ponta.',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

redator = Agent(
    role='Redator Técnico de IA',
    goal='Criar um artigo técnico engajador e fácil de entender sobre sistemas multi-agentes',
    backstory='Você é um escritor técnico renomado que simplifica conceitos complexos de IA para engenheiros de software.',
    verbose=True,
    allow_delegation=False,
    llm=gemini_llm
)

# ==========================================
# 2. Definindo as Tarefas
# ==========================================
tarefa_pesquisa = Task(
    description='Faça uma análise concisa sobre os benefícios de usar o framework CrewAI para orquestração de LLMs.',
    expected_output='Uma lista em bullet points com os 3 principais benefícios do CrewAI.',
    agent=pesquisador
)

tarefa_escrita = Task(
    description='Usando os insights do pesquisador, escreva um parágrafo introdutório para um blog post de tecnologia.',
    expected_output='Um parágrafo formatado em Markdown, com título e texto atrativo.',
    agent=redator
)

# ==========================================
# 3. Montando a Equipe (Crew)
# ==========================================
equipe = Crew(
    agents=[pesquisador, redator],
    tasks=[tarefa_pesquisa, tarefa_escrita],
    process=Process.sequential, # As tarefas rodam em ordem cronológica
    verbose=True
)

# ==========================================
# 4. Executando o Sistema
# ==========================================
print("Iniciando a execução da Crew...")
resultado_final = equipe.kickoff()

print("\n\n######################")
print("RESULTADO FINAL DO SISTEMA:")
print("######################\n")
print(resultado_final)

# ==========================================
# 5. Salvando os Resultados em Arquivo
# ==========================================
PASTA_RESULTADO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultado")
os.makedirs(PASTA_RESULTADO, exist_ok=True)
carimbo = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

arquivos = {
    f"{carimbo}_pesquisa.md": tarefa_pesquisa.output.raw,
    f"{carimbo}_artigo.md": resultado_final.raw,
}
for nome, conteudo in arquivos.items():
    caminho = os.path.join(PASTA_RESULTADO, nome)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    print(f"Arquivo salvo: {caminho}")