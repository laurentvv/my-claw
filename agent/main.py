import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from mcp import StdioServerParameters
from pydantic import BaseModel
from smolagents import CodeAgent, ToolCollection

from models import get_default_model, get_model, get_models, get_ollama_models, is_cloud_model
from tools import TOOLS

load_dotenv()

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
logging.getLogger("smolagents").setLevel(logging.DEBUG)
logging.getLogger("LiteLLM").setLevel(logging.INFO)

# Ignorer le FutureWarning de smolagents concernant structured_output
# Ce warning est interne à smolagents et sera corrigé dans une future version


# ─── Skills ─────────────────────────────────────────────────────────────────
def load_skills() -> str:
    skills_path = Path(__file__).parent / "skills.txt"
    try:
        with open(skills_path, "r", encoding="utf-8") as f:
            skills = f.read()
        logger.info(f"✓ Skills chargés ({len(skills)} chars)")
        return skills
    except FileNotFoundError:
        logger.warning("✗ skills.txt non trouvé")
        return "You are a Python coding expert. Always use final_answer() to return results."
    except Exception as e:
        logger.error(f"✗ Erreur chargement skills: {e}")
        return ""


SKILLS = load_skills()


# ─── MCP Chrome DevTools — état global lifespan ──────────────────────────────
_chrome_mcp_context: ToolCollection | None = None
_chrome_mcp_tools: list = []

# MCP Z.ai (web search, web reader, zread) — chargés dans lifespan
_web_search_context: ToolCollection | None = None
_web_search_tools: list = []

# Cache des agents par modèle pour éviter de reconstruire à chaque requête
_agent_cache: dict[str, CodeAgent] = {}
_cache_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _chrome_mcp_context, _chrome_mcp_tools
    global _web_search_context, _web_search_tools

    # ── Chrome DevTools MCP ──────────────────────────────────────────────────
    logger.info("Initialisation Chrome DevTools MCP...")
    try:
        chrome_params = StdioServerParameters(
            command="npx",
            args=["-y", "chrome-devtools-mcp@latest"],
            env={**os.environ},
        )
        _chrome_mcp_context = ToolCollection.from_mcp(chrome_params, trust_remote_code=True)
        tool_collection = _chrome_mcp_context.__enter__()
        _chrome_mcp_tools = list(tool_collection.tools)
        logger.info(f"✓ Chrome DevTools MCP: {len(_chrome_mcp_tools)} outils")
    except Exception as e:
        logger.warning(f"✗ Chrome DevTools MCP: {e}")
        _chrome_mcp_context = None
        _chrome_mcp_tools = []

        # ── Web Search MCP Z.ai (TOOL-4) ──────────────────────────────────
    # IMPORTANT : décommenter quand ZAI_API_KEY configuré et TOOL-4 implémenté
    # logger.info("Initialisation Web Search MCP Z.ai...")
    # try:
    #     if os.environ.get("ZAI_API_KEY"):
    #         web_search_params = {
    #             "url": "https://api.z.ai/api/mcp/web_search_prime/mcp",
    #             "type": "streamable-http",
    #             "headers": {"Authorization": f"Bearer {os.environ['ZAI_API_KEY']}"}
    #         }
        #         _web_search_context = ToolCollection.from_mcp(
        #             web_search_params, trust_remote_code=True
        #         )
    #         tool_collection = _web_search_context.__enter__()
    #         _web_search_tools = list(tool_collection.tools)
    #         logger.info(f"✓ Web Search MCP Z.ai: {len(_web_search_tools)} outils")
    #     else:
    #         logger.warning("✗ ZAI_API_KEY absent, Web Search MCP désactivé")
    # except Exception as e:
    #     logger.warning(f"✗ Web Search MCP Z.ai: {e}")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    if _chrome_mcp_context is not None:
        try:
            _chrome_mcp_context.__exit__(None, None, None)
            logger.info("✓ Chrome DevTools MCP fermé")
        except Exception as e:
            logger.error(f"✗ Fermeture Chrome MCP: {e}")

    if _web_search_context is not None:
        try:
            _web_search_context.__exit__(None, None, None)
            logger.info("✓ Web Search MCP Z.ai fermé")
        except Exception as e:
            logger.error(f"✗ Fermeture Web Search MCP: {e}")


app = FastAPI(title="my-claw agent", version="0.2.0", lifespan=lifespan)


# ─── Tools directs du Manager ────────────────────────────────────────────────
# Le manager utilise seulement les tools simples (fichiers, OS, clipboard)
# Les tools vision/screenshot/mouse sont dans pc_control_agent
MANAGER_TOOLS_NAMES = {"file_system", "os_exec", "clipboard"}


def get_manager_tools() -> list:
    """Tools directs du manager (fichiers, OS, clipboard uniquement)."""
    return [t for t in TOOLS if t.name in MANAGER_TOOLS_NAMES]


# ─── Construction du système multi-agent ─────────────────────────────────────
def build_multi_agent_system(model_id: str | None = None) -> CodeAgent:
    """
    Construit le système Manager + sous-agents selon les tools disponibles.

    Architecture :
    - Manager : modèle par défaut (coding → main) + tools directs (file_system, os_exec, clipboard)
    - pc_control : modèle par défaut + screenshot, ui_grounding, mouse_keyboard
    - vision : modèle par défaut + analyze_image
    - browser : modèle par défaut + Chrome DevTools MCP (si disponible)
    - web_search : modèle par défaut + MCP Z.ai (si ZAI_API_KEY configuré)

    NOTE : Tous les agents utilisent le même modèle LLM par défaut.
    Les outils spécialisés (ui_grounding, analyze_image) utilisent leurs propres modèles internes.

    Args:
        model_id: Modèle spécifique (optionnel, utilise le défaut sinon)

    Returns:
        CodeAgent: Le manager avec ses sous-agents
    """
    from agents.browser_agent import create_browser_agent
    from agents.pc_control_agent import create_pc_control_agent
    from agents.vision_agent import create_vision_agent
    from agents.web_agent import create_web_agent

    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    managed_agents = []

    # Déterminer le modèle à utiliser
    if model_id is None:
        model_id = get_default_model()

    logger.info(f"Modèle sélectionné pour tous les agents: {model_id}")

    # ── Sous-agent pilotage PC ────────────────────────────────────────────────
    try:
        pc_agent = create_pc_control_agent(ollama_url, model_id=model_id)
        managed_agents.append(pc_agent)
        logger.info(f"✓ pc_control_agent créé avec modèle {model_id}")
    except Exception as e:
        logger.warning(f"✗ pc_control_agent non disponible: {e}")

    # ── Sous-agent vision ────────────────────────────────────────────────────
    try:
        vision_agent = create_vision_agent(ollama_url, model_id=model_id)
        managed_agents.append(vision_agent)
        logger.info(f"✓ vision_agent créé avec modèle {model_id}")
    except Exception as e:
        logger.warning(f"✗ vision_agent non disponible: {e}")

    # ── Sous-agent browser Chrome ─────────────────────────────────────────────
    if _chrome_mcp_tools:
        try:
            browser_agent = create_browser_agent(ollama_url, _chrome_mcp_tools, model_id=model_id)
            managed_agents.append(browser_agent)
            logger.info(
                f"✓ browser_agent créé ({len(_chrome_mcp_tools)} tools Chrome DevTools) "
                f"avec modèle {model_id}"
            )
        except Exception as e:
            logger.warning(f"✗ browser_agent non disponible: {e}")
    else:
        logger.warning("✗ browser_agent ignoré (Chrome DevTools MCP non disponible)")

    # ── Sous-agent web search Z.ai ────────────────────────────────────────────
    if _web_search_tools:
        try:
            web_agent = create_web_agent(ollama_url, _web_search_tools, model_id=model_id)
            if web_agent:
                managed_agents.append(web_agent)
                logger.info(
                    f"✓ web_agent créé ({len(_web_search_tools)} tools Z.ai) avec modèle {model_id}"
                )
        except Exception as e:
            logger.warning(f"✗ web_agent non disponible: {e}")
    else:
        logger.info("✗ web_agent ignoré (aucun tool MCP Z.ai)")

    # ── Manager ───────────────────────────────────────────────────────────────
    manager_tools = get_manager_tools()
    logger.info(f"Manager tools directs: {[t.name for t in manager_tools]}")
    logger.info(f"Sous-agents disponibles: {[m.name for m in managed_agents]}")

    manager = CodeAgent(
        tools=manager_tools,
        model=get_model(model_id),
        managed_agents=managed_agents,
        max_steps=10,
        verbosity_level=2,
        additional_authorized_imports=[
            "requests",
            "urllib",
            "json",
            "csv",
            "pathlib",
            "os",
            "subprocess",
        ],
        executor_kwargs={"timeout_seconds": 240},
        instructions=SKILLS,
    )

    return manager


# ─── Cache des agents ──────────────────────────────────────────────────────────
async def get_or_build_agent(model_id: str | None = None) -> CodeAgent:
    """
    Récupère l'agent depuis le cache ou le construit si nécessaire.

    Thread-safe : empêche le double-build avec un lock global.

    Args:
        model_id: Identifiant du modèle (optionnel, utilise le défaut sinon)

    Returns:
        CodeAgent: L'agent manager avec ses sous-agents
    """
    if model_id is None:
        model_id = get_default_model()

    # Acquérir le lock AVANT le check pour empêcher le double-build
    async with _cache_lock:
        if model_id not in _agent_cache:
            logger.info(f"Construction du système multi-agent pour modèle {model_id}")
            # Construire l'agent dans un thread séparé (appel bloquant)
            loop = asyncio.get_running_loop()
            new_agent = await loop.run_in_executor(None, build_multi_agent_system, model_id)
            _agent_cache[model_id] = new_agent
        else:
            logger.info(f"Utilisation du cache pour modèle {model_id}")

    return _agent_cache[model_id]


# ─── Helpers ─────────────────────────────────────────────────────────────────
def validate_model_id(model_id: str | None) -> str:
    """
    Valide l'identifiant du modèle avant construction.

    Cette fonction utilise la même logique de validation que get_model() :
    - Si le modèle n'est pas trouvé, elle fait un fallback sur "main"
      ou le premier modèle disponible
    - Elle valide que les modèles cloud ont leur clé API configurée

    Note: Contrairement à get_model() qui lève RuntimeError (contexte interne),
    cette fonction lève HTTPException (contexte API endpoint).

    Args:
        model_id: Identifiant du modèle à valider

    Returns:
        str: Identifiant du modèle validé (peut être différent de l'entrée en cas de fallback)

    Raises:
        HTTPException: Si aucun modèle n'est disponible ou si la clé API est manquante
    """
    if model_id is None:
        model_id = get_default_model()

    # Vérifier que le modèle existe (même logique que get_model)
    models = get_models()
    if model_id not in models:
        # Vérifier si c'est un modèle Ollama direct
        ollama_models = get_ollama_models()
        if model_id not in ollama_models:
            # Fallback sur main ou le premier modèle disponible (comme get_model)
            if not models:
                raise HTTPException(status_code=400, detail="Aucun modèle disponible")
            # Utiliser le fallback
            fallback_model = "main" if "main" in models else next(iter(models.keys()))
            logger.warning(f"Modèle '{model_id}' non trouvé, fallback sur {fallback_model}")
            model_id = fallback_model

    # Vérifier que les modèles cloud ont leur clé API
    if is_cloud_model(model_id, models):
        if not os.environ.get("ZAI_API_KEY"):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Modèle cloud '{model_id}' requiert ZAI_API_KEY. "
                    "Configurez-le dans agent/.env"
                ),
            )

    return model_id


def build_prompt_with_history(message: str, history: list[dict]) -> str:
    if not history:
        return message
    lines = [
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in history[-10:]
    ]
    return f"Previous conversation:\n{chr(10).join(lines)}\n\nCurrent message: {message}"


# ─── API ──────────────────────────────────────────────────────────────────────
class RunRequest(BaseModel):
    message: str
    history: list[dict] = []
    model: str = "main"


@app.post("/run")
async def run(req: RunRequest):
    try:
        # Valider le modèle avant construction
        validated_model = validate_model_id(req.model)
        agent = await get_or_build_agent(validated_model)  # Utilise le cache
        prompt = build_prompt_with_history(req.message, req.history)
        # Exécuter l'agent dans un thread séparé pour ne pas bloquer l'event loop
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: agent.run(prompt, reset=True))
        return {"response": str(result)}
    except HTTPException:
        # Relever les HTTPException de validate_model_id sans modification
        raise
    except RuntimeError as e:
        # Erreur de configuration/validation → 400 Bad Request
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Erreur serveur interne → 500 Internal Server Error
        logger.error(f"Agent error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "module": "2-multi-agent",
        "chrome_mcp": len(_chrome_mcp_tools),
        "web_mcp": len(_web_search_tools),
    }


@app.get("/models")
async def list_models():
    default_model = get_default_model()
    models_info = {}
    for category, (model_name, base_url) in get_models().items():
        display_name = model_name.split("/")[-1] if "/" in model_name else model_name
        is_local = "ollama_chat/" in model_name or "localhost" in base_url
        is_default = category == default_model
        models_info[category] = {
            "name": display_name,
            "full_name": model_name,
            "type": "local" if is_local else "cloud",
            "available": True,
            "is_default": is_default,
        }
    return {
        "default_model": default_model,
        "models": models_info,
        "ollama_models": get_ollama_models(),
        "sub_agents": {
            "pc_control": f"{default_model} + qwen3-vl (interne)",
            "vision": f"{default_model} + analyze_image (qwen3-vl interne)",
            "browser": f"{default_model} + {len(_chrome_mcp_tools)} tools Chrome DevTools",
            "web_search": f"{default_model} + {len(_web_search_tools)} tools Z.ai MCP",
        },
    }
