import os
import logging
import re
import requests
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from smolagents import CodeAgent, LiteLLMModel, MCPClient
from mcp import StdioServerParameters
from dotenv import load_dotenv
from tools import TOOLS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les skills depuis le fichier externe
def load_skills() -> str:
    """Charge les skills (patterns de code) depuis agent/skills.txt"""
    skills_path = Path(__file__).parent / "skills.txt"
    try:
        with open(skills_path, "r", encoding="utf-8") as f:
            skills = f.read()
        logger.info(f"✓ Skills chargés depuis {skills_path} ({len(skills)} chars)")
        return skills
    except FileNotFoundError:
        logger.warning(f"✗ Fichier skills.txt non trouvé: {skills_path}")
        return "You are a Python coding expert. ALWAYS prefer writing Python code directly over using external tools."
    except Exception as e:
        logger.error(f"✗ Erreur lors du chargement des skills: {e}")
        return "You are a Python coding expert. ALWAYS prefer writing Python code directly over using external tools."

SKILLS = load_skills()

# Configuration des modèles par catégorie
# Chaque catégorie a une liste de modèles préférés (ordre de priorité)
MODEL_PREFERENCES: dict[str, list[str]] = {
    "fast":   ["gemma3:latest", "qwen3:latest", "gemma3n:latest"],
    "smart":  ["qwen3:latest", "gemma3n:latest", "gemma3:latest"],
    "main":   ["qwen3:latest", "gemma3n:latest", "gemma3:latest"],
    "vision": ["qwen3-vl:2b", "qwen3-vl:4b", "llama3.2-vision"],
}

# Modèles cloud (toujours disponibles si ZAI_API_KEY est configuré)
CLOUD_MODELS: dict[str, tuple[str, str]] = {
    "code":   ("openai/glm-4.7-flash", os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")),
    "reason": ("openai/glm-4.7",       os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")),
}

# Cache des modèles détectés
_detected_models: dict[str, tuple[str, str]] | None = None


def get_ollama_models() -> list[str]:
    """Récupère la liste des modèles Ollama installés."""
    try:
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        return [m["name"] for m in models]
    except Exception as e:
        logger.warning(f"Impossible de récupérer les modèles Ollama: {e}")
        return []


def detect_models() -> dict[str, tuple[str, str]]:
    """Détecte les modèles disponibles et les associe aux catégories."""
    global _detected_models

    if _detected_models is not None:
        return _detected_models

    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    available_models = get_ollama_models()

    logger.info(f"Modèles Ollama détectés: {available_models}")

    detected = {}

    # Pour chaque catégorie, trouver le premier modèle disponible
    for category, preferences in MODEL_PREFERENCES.items():
        for model_name in preferences:
            if model_name in available_models:
                detected[category] = (f"ollama_chat/{model_name}", ollama_url)
                logger.info(f"✓ {category}: {model_name}")
                break
        else:
            # Aucun modèle trouvé pour cette catégorie
            logger.warning(f"✗ {category}: aucun modèle trouvé parmi {preferences}")

    # Ajouter les modèles cloud
    detected.update(CLOUD_MODELS)

    _detected_models = detected
    return detected


# Initialiser la détection au démarrage
MODELS = detect_models()


app = FastAPI(title="my-claw agent", version="0.1.0")

# Log des outils disponibles au démarrage
logger.info(f"Tools disponibles: {len(TOOLS)} outils locaux")
logger.info(f"Outils locaux: {[t.name for t in TOOLS]}")


class CleanedLiteLLMModel(LiteLLMModel):
    """
    Wrapper pour LiteLLMModel qui nettoie les balises problématiques de GLM-4.7.

    Applique clean_glm_response() sur toutes les réponses du modèle avant
    qu'elles ne soient parsées par smolagents CodeAgent.
    """

    def generate(self, messages, stop_sequences=None, response_format=None, tools_to_call_from=None, **kwargs):
        """Override de la méthode generate() pour nettoyer la réponse."""
        # Appeler le modèle parent
        chat_message = super().generate(messages, stop_sequences, response_format, tools_to_call_from, **kwargs)

        # Nettoyer le contenu de la réponse
        if chat_message.content:
            original_len = len(chat_message.content)
            chat_message.content = clean_glm_response(chat_message.content)
            cleaned_len = len(chat_message.content)

            if original_len != cleaned_len:
                logger.info(f"✓ Nettoyage GLM-4.7: {original_len} -> {cleaned_len} chars ({original_len - cleaned_len} chars retirés)")

        return chat_message


def get_model(model_id: str = "main") -> LiteLLMModel:
    # Fallback sécurisé : si model_id n'existe pas, essayer "main", sinon prendre le premier modèle disponible
    if model_id not in MODELS:
        if "main" in MODELS:
            fallback = MODELS["main"]
        elif MODELS:
            # Prendre le premier modèle disponible
            fallback = next(iter(MODELS.values()))
            logger.warning(f"Modèle '{model_id}' non trouvé, fallback sur {fallback[0]}")
        else:
            # Aucun modèle disponible du tout
            raise RuntimeError("Aucun modèle LLM disponible. Vérifiez qu'Ollama est démarré ou que ZAI_API_KEY est configuré.")
        model_name, base_url = fallback
    else:
        model_name, base_url = MODELS[model_id]

    # Déterminer l'API key selon le provider
    if model_id in ["code", "reason"]:
        api_key = os.environ.get("ZAI_API_KEY", "ollama")
        # Ajouter stop sequences pour éviter les balises </code> et </s> dans le code généré
        stop_sequences = ["</code>", "</s>"]
        # Utiliser le wrapper nettoyant pour GLM-4.7
        model_class = CleanedLiteLLMModel
    else:
        api_key = "ollama"
        stop_sequences = None
        # Utiliser le modèle standard pour Ollama
        model_class = LiteLLMModel

    # Construire les kwargs de base
    kwargs = {
        "model_id": model_name,
        "api_base": base_url,
        "api_key": api_key,
        "stop": stop_sequences,
    }

    # Ajouter les paramètres spécifiques à Ollama uniquement pour les modèles Ollama
    if model_id not in ["code", "reason"]:
        kwargs["num_ctx"] = 32768
        kwargs["extra_body"] = {"think": False}

    return model_class(**kwargs)


def clean_glm_response(text: str) -> str:
    """
    Nettoie les balises de fermeture problématiques générées par GLM-4.7.

    GLM-4.7 et GLM-4.7-flash génèrent systématiquement des balises </code> et </s>
    à la fin du code Python, causant des SyntaxError dans smolagents.

    Cette fonction retire ces balises pour permettre au code de s'exécuter correctement.

    Référence: GitHub issue ollama/ollama#13840, HuggingFace GLM-4.7-Flash-GGUF#14
    """
    if not text:
        return text

    # Retirer </code (SANS >) en fin de chaîne - c'est ce que GLM-4.7 génère réellement
    text = re.sub(r'</code\s*$', '', text, flags=re.MULTILINE)

    # Retirer </code> (avec >) en fin de chaîne au cas où
    text = re.sub(r'</code>\s*$', '', text, flags=re.MULTILINE)

    # Retirer </s> en fin de chaîne
    text = re.sub(r'</s>\s*$', '', text, flags=re.MULTILINE)

    # Retirer </code (sans >) avant une nouvelle ligne ou fin de chaîne
    text = re.sub(r'</code(\s*\n|$)', r'\1', text, flags=re.MULTILINE)

    # Retirer </code> (avec >) avant une nouvelle ligne ou fin de chaîne
    text = re.sub(r'</code>(\s*\n|$)', r'\1', text, flags=re.MULTILINE)

    # Retirer </s> avant une nouvelle ligne ou fin de chaîne
    text = re.sub(r'</s>(\s*\n|$)', r'\1', text, flags=re.MULTILINE)

    return text


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
        # Configurer les paramètres MCP pour Chrome DevTools
        chrome_devtools_params = StdioServerParameters(
            command="npx",
            args=["-y", "chrome-devtools-mcp@latest"],
            env={**os.environ}
        )
        
        # Utiliser MCPClient comme context manager
        with MCPClient(chrome_devtools_params) as mcp_tools:
            # Fusionner les outils locaux et MCP
            all_tools = TOOLS.copy()
            all_tools.extend(mcp_tools)
            
            mcp_count = len(mcp_tools)
            logger.info(f"Exécution avec {len(TOOLS)} outils locaux + {mcp_count} outils MCP Chrome DevTools")
            
            agent = CodeAgent(
                tools=all_tools,
                model=get_model(req.model),
                max_steps=10,
                verbosity_level=1,
                additional_authorized_imports=[
                    "requests",
                    "urllib",
                    "json",
                    "csv",
                    "pathlib",
                    "os",
                    "subprocess",
                ],
                executor_kwargs={
                    "timeout_seconds": 240,
                },
                instructions=SKILLS,
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


@app.get("/models")
async def list_models():
    """Retourne la liste des modèles disponibles avec leurs catégories."""
    models_info = {}

    for category, (model_name, base_url) in MODELS.items():
        # Extraire le nom du modèle sans le prefix ollama_chat/ ou openai/
        display_name = model_name.split("/")[-1] if "/" in model_name else model_name

        # Déterminer le type (local ou cloud)
        # Local = modèle Ollama (prefix ollama_chat/) ou base_url localhost
        is_local = "ollama_chat/" in model_name or "localhost" in base_url

        models_info[category] = {
            "name": display_name,
            "full_name": model_name,
            "type": "local" if is_local else "cloud",
            "available": True
        }

    return {
        "models": models_info,
        "ollama_models": get_ollama_models()
    }
