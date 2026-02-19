import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from smolagents import CodeAgent, LiteLLMModel, MCPClient
from mcp import StdioServerParameters
from dotenv import load_dotenv
from tools import TOOLS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="my-claw agent", version="0.1.0")

MODELS: dict[str, tuple[str, str]] = {
    "fast":   ("ollama_chat/qwen3:4b",  "http://localhost:11434"),
    "smart":  ("ollama_chat/qwen3:8b",  "http://localhost:11434"),
    "main":   ("ollama_chat/qwen3:14b", "http://localhost:11434"),
    "code":   ("openai/glm-4.7-flash",  os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")),
    "reason": ("openai/glm-4.7",        os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")),
}

# Initialisation MCP Vision Z.ai (TOOL-7)
_mcp_tools: list | None = None

if "ZAI_API_KEY" in os.environ:
    try:
        mcp_params = StdioServerParameters(
            command="npx",
            args=["-y", "@z_ai/mcp-server@latest"],
            env={
                **os.environ,
                "Z_AI_API_KEY": os.environ["ZAI_API_KEY"],
                "Z_AI_MODE": "ZAI",
            },
        )
        with MCPClient(mcp_params) as mcp_tools:
            _mcp_tools = list(mcp_tools)
            logger.info(f"MCP Vision Z.ai connecté - {len(_mcp_tools)} outils disponibles")
            logger.info(f"Outils MCP: {[t.name for t in _mcp_tools]}")
    except Exception as e:
        logger.warning(f"Échec connexion MCP Vision Z.ai: {type(e).__name__}: {e}")
        _mcp_tools = None
else:
    logger.warning("ZAI_API_KEY non défini - MCP Vision Z.ai désactivé")

# Fusion des tools locaux et MCP
ALL_TOOLS = TOOLS + (_mcp_tools if _mcp_tools else [])
logger.info(f"Total tools disponibles: {len(ALL_TOOLS)} ({len(TOOLS)} locaux, {len(_mcp_tools) if _mcp_tools else 0} MCP)")


def get_model(model_id: str = "main") -> LiteLLMModel:
    model_name, base_url = MODELS.get(model_id, MODELS["main"])
    
    # Déterminer l'API key selon le provider
    if model_id in ["code", "reason"]:
        api_key = os.environ.get("ZAI_API_KEY", "ollama")
        # Ajouter stop sequences pour éviter les balises </code> et </s> dans le code généré
        stop_sequences = ["</code>", "</s>"]
    else:
        api_key = "ollama"
        stop_sequences = None
    
    return LiteLLMModel(
        model_id=model_name,
        api_base=base_url,
        api_key=api_key,
        num_ctx=32768,
        extra_body={"think": False},
        stop=stop_sequences,
    )


def build_prompt_with_history(message: str, history: list[dict]) -> str:
    if not history:
        return message
    lines = [
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in history[-10:]
    ]
    return f"Previous conversation:\n{chr(10).join(lines)}\n\nCurrent message: {message}"


class RunRequest(BaseModel):
    message: str
    history: list[dict] = []
    model: str = "main"


@app.post("/run")
async def run(req: RunRequest):
    try:
        logger.info(f"Tools disponibles: {len(ALL_TOOLS)} ({len(TOOLS)} locaux, {len(_mcp_tools) if _mcp_tools else 0} MCP)")
        
        agent = CodeAgent(
            tools=ALL_TOOLS,
            model=get_model(req.model),
            max_steps=10,
            verbosity_level=1,
        )
        prompt = build_prompt_with_history(req.message, req.history)
        result = agent.run(prompt)
        return {"response": str(result)}
    except Exception as e:
        logger.error(f"Agent error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "module": "1-agent"}
