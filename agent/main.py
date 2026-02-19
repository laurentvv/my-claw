import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from smolagents import CodeAgent, LiteLLMModel
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
    "code":   ("openai/glm-4.7-flash",  "https://open.bigmodel.cn/api/paas/v4"),
    "reason": ("openai/glm-4.7",        "https://open.bigmodel.cn/api/paas/v4"),
}


def get_model(model_id: str = "main") -> LiteLLMModel:
    if model_id in ("code", "reason") and not os.environ.get("ZAI_API_KEY"):
        logger.warning("ZAI_API_KEY absent — fallback sur main (qwen3:14b)")
        model_id = "main"

    model_name, base_url = MODELS.get(model_id, MODELS["main"])
    is_ollama = "ollama" in model_name

    return LiteLLMModel(
        model_id=model_name,
        api_base=base_url,
        api_key="ollama" if is_ollama else os.environ["ZAI_API_KEY"],
        num_ctx=32768 if is_ollama else None,
        extra_body={"think": False} if is_ollama else None,
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
        agent = CodeAgent(
            tools=TOOLS,
            model=get_model(req.model),
            max_steps=5,
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
