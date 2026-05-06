"""
Refactoring AgentOS — Detector + Recommender + Critic
"""
from agno.agent import Agent
from agno.team import Team
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIChat
from agno.tools import tool
from agno.tools.file import FileTools
from agno.tools.shell import ShellTools
from agno.tools.e2b import E2BTools
from agno.tools.knowledge import KnowledgeTools
from agno.os import AgentOS

# ---------------------------------------------------------------------------
# DB compartilhado (sessões, memórias, traces)
# ---------------------------------------------------------------------------
db = PostgresDb(id="refactor-db", db_url="postgresql+psycopg://ai:ai@localhost:5532/ai")

# ---------------------------------------------------------------------------
# Custom Tools (regras estritas — anti-alucinação)
# ---------------------------------------------------------------------------
DESIGN_PATTERNS = {
    "Strategy": {...},
    "Factory": {...},
    "Observer": {...},
    "Decorator": {...},
    "Adapter": {...},
}

@tool(name="design_pattern_reference_tool",
      description="Retorna estrutura estrita de um dos 5 Design Patterns suportados.")
def design_pattern_reference_tool(pattern_name: str) -> dict:
    return DESIGN_PATTERNS.get(pattern_name, {"error": "pattern not supported"})

@tool(name="ast_analyzer_tool",
      description="Calcula complexidade ciclomática e detecta God Classes via AST.")
def ast_analyzer_tool(source_code: str) -> dict:
    import ast
    from radon.complexity import cc_visit
    tree = ast.parse(source_code)
    metrics = [{"name": b.name, "complexity": b.complexity} for b in cc_visit(source_code)]
    god_classes = [n.name for n in ast.walk(tree)
                   if isinstance(n, ast.ClassDef) and len(n.body) > 20]
    return {"complexity": metrics, "god_classes": god_classes}

@tool(name="diff_generator_tool",
      description="Gera diff unificado entre código original e refatorado.")
def diff_generator_tool(original: str, refactored: str) -> str:
    import difflib
    return "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        refactored.splitlines(keepends=True),
        fromfile="original.py", tofile="refactored.py"))

# ---------------------------------------------------------------------------
# Agente Rastreador (Detector)
# ---------------------------------------------------------------------------
detector_agent = Agent(
    name="Detector Agent",
    role="Detecta code smells e mede complexidade no código fonte",
    model=OpenAIChat(id="gpt-4o"),
    db=db,
    tools=[FileTools(), ast_analyzer_tool],
    instructions="""
Leia o arquivo com FileTools (preserve numeração).
Execute ast_analyzer_tool e retorne classes/métodos com:
- complexidade ciclomática > 10
- God Classes
""",
    markdown=True,
)

# ---------------------------------------------------------------------------
# Agente Arquiteto (Recommender)
# ---------------------------------------------------------------------------
recommender_agent = Agent(
    name="Recommender Agent",
    role="Sugere Design Pattern adequado para os smells detectados",
    model=OpenAIChat(id="gpt-4o"),
    db=db,
    tools=[design_pattern_reference_tool, KnowledgeTools(knowledge=...)],
    instructions="""
Para cada smell recebido do Detector, consulte design_pattern_reference_tool
e justifique a escolha entre os 5 padrões suportados. NÃO invente padrões.
""",
)

# ---------------------------------------------------------------------------
# Agente Revisor (Critic)
# ---------------------------------------------------------------------------
critic_agent = Agent(
    name="Critic Agent",
    role="Valida sintaxe e compara regras de negócio do refatorado",
    model=OpenAIChat(id="gpt-4o"),
    db=db,
    tools=[E2BTools(), diff_generator_tool, ShellTools()],
    instructions="""
1. Rode ast.parse / ruff no E2B sandbox para validar sintaxe.
2. Gere diff com diff_generator_tool.
3. Aponte qualquer regra de negócio perdida.
""",
)

# ---------------------------------------------------------------------------
# Team coordenador
# ---------------------------------------------------------------------------
refactor_team = Team(
    id="refactor-team",
    name="Refactoring Team",
    model=OpenAIChat(id="gpt-4o"),
    db=db,
    members=[detector_agent, recommender_agent, critic_agent],
    instructions="""
Pipeline:
1. Detector → identifica smells
2. Recommender → sugere padrão + código refatorado
3. Critic → valida e aprova/rejeita
Retorne relatório final consolidado.
""",
)

# ---------------------------------------------------------------------------
# AgentOS
# ---------------------------------------------------------------------------
agent_os = AgentOS(
    description="Sistema multi-agente de refatoração com Design Patterns",
    agents=[detector_agent, recommender_agent, critic_agent],
    teams=[refactor_team],
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="main:app", reload=True)