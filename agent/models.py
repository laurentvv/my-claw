"""
Modèles LLM — Création et gestion des modèles pour les agents.

Ce module centralise la logique de création de modèles pour éviter les imports
circulaires entre main.py et les agents.
"""

import os
import logging
import re
import requests
from pathlib import Path
from smolagents import LiteLLMModel

logger = logging.getLogger(__name__)


# ─── Détection modèles Ollama ────────────────────────────────────────────────
MODEL_PREFERENCES: dict[str, list[str]] = {
    "fast":   ["gemma3:latest", "qwen3:4b", "gemma3n:latest"],
    "smart":  ["qwen3:8b", "qwen3:4b", "gemma3n:latest", "gemma3:latest"],
    "main":   ["qwen3:8b", "qwen3:4b", "gemma3n:latest", "gemma3:latest"],
    "vision": ["qwen3-vl:8b", "qwen3-vl:2b", "qwen3-vl:4b", "llama3.2-vision"],
}

CLOUD_MODELS: dict[str, tuple[str, str]] = {
    "code":   ("openai/glm-4.7-flash", os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")),
    "reason": ("openai/glm-4.7",       os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")),
}

_detected_models: dict[str, tuple[str, str]] | None = None


def get_ollama_models() -> list[str]:
    """Récupère la liste des modèles Ollama disponibles."""
    try:
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        return [m["name"] for m in response.json().get("models", [])]
    except Exception as e:
        logger.warning(f"Ollama non accessible: {e}")
        return []


def detect_models() -> dict[str, tuple[str, str]]:
    """Détecte les modèles disponibles (Ollama + cloud)."""
    global _detected_models
    if _detected_models is not None:
        return _detected_models

    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    available = get_ollama_models()
    logger.info(f"Modèles Ollama détectés: {available}")

    detected = {}
    for category, preferences in MODEL_PREFERENCES.items():
        for model_name in preferences:
            if model_name in available:
                detected[category] = (f"ollama_chat/{model_name}", ollama_url)
                logger.info(f"✓ {category}: {model_name}")
                break
        else:
            logger.warning(f"✗ {category}: aucun modèle trouvé parmi {preferences}")

    # Vérifier présence qwen3-vl pour pc_control_agent (grounding)
    vision_models = [m for m in available if m.startswith("qwen3-vl")]
    if vision_models:
        logger.info(f"✓ qwen3-vl détecté pour pc_control_agent grounding: {vision_models}")
    else:
        logger.warning(f"✗ qwen3-vl non trouvé — installer avec: ollama pull qwen3-vl:2b")

    detected.update(CLOUD_MODELS)
    _detected_models = detected
    return detected


MODELS = detect_models()


# ─── GLM-4.7 cleanup ────────────────────────────────────────────────────────
def clean_glm_response(text: str) -> str:
    """Nettoie les balises </code parasites générées par GLM-4.7."""
    if not text:
        return text
    text = re.sub(r'</code>?\s*(\n|$)', r'\1', text)
    text = re.sub(r'</s>\s*(\n|$)', r'\1', text)
    text = re.sub(r'</code>\s*$', '', text)
    text = re.sub(r'</code\s*$', '', text)
    text = re.sub(r'</s>\s*$', '', text)
    return text


class CleanedLiteLLMModel(LiteLLMModel):
    """Wrapper LiteLLMModel qui nettoie les balises parasites de GLM-4.7."""
    def generate(self, messages, stop_sequences=None, response_format=None,
                 tools_to_call_from=None, **kwargs):
        chat_message = super().generate(messages, stop_sequences, response_format,
                                        tools_to_call_from, **kwargs)
        if chat_message.content:
            original_len = len(chat_message.content)
            chat_message.content = clean_glm_response(chat_message.content)
            if original_len != len(chat_message.content):
                logger.info(f"✓ GLM cleanup: {original_len} → {len(chat_message.content)} chars")
        return chat_message


def get_model(model_id: str = "main") -> LiteLLMModel:
    """
    Crée un modèle LiteLLMModel à partir d'un identifiant.

    Args:
        model_id: Identifiant du modèle (main, smart, fast, vision, code, reason)

    Returns:
        LiteLLMModel configuré correctement

    Raises:
        RuntimeError: Si aucun modèle n'est disponible
    """
    if model_id not in MODELS:
        if "main" in MODELS:
            model_name, base_url = MODELS["main"]
        elif MODELS:
            model_name, base_url = next(iter(MODELS.values()))
            logger.warning(f"Modèle '{model_id}' non trouvé, fallback")
        else:
            raise RuntimeError("Aucun modèle disponible.")
    else:
        model_name, base_url = MODELS[model_id]

    is_glm = "z.ai" in base_url.lower() or model_id in ["code", "reason"]

    if is_glm:
        return CleanedLiteLLMModel(
            model_id=model_name,
            api_base=base_url,
            api_key=os.environ.get("ZAI_API_KEY", "ollama"),
            stop=["</code>", "</code", "</s>"],
        )
    else:
        return LiteLLMModel(
            model_id=model_name,
            api_base=base_url,
            api_key="ollama",
            num_ctx=32768,
            extra_body={"think": False},
        )


def get_default_model() -> str:
    """
    Retourne le modèle par défaut pour le manager et les sous-agents.

    Priorité :
    1. Variable d'environnement DEFAULT_MODEL
    2. "reason" (glm-4.7) si ZAI_API_KEY configuré
    3. "main" (qwen3:8b local) en fallback

    Returns:
        str: Identifiant du modèle par défaut (main, coding, reason, smart, fast, vision)
    """
    # Priorité 1 : variable d'environnement
    env_default = os.environ.get("DEFAULT_MODEL")
    if env_default and env_default in MODELS:
        logger.info(f"✓ Modèle par défaut depuis env: {env_default}")
        return env_default

    # Priorité 2 : GLM4.7 si API key configuré
    if os.environ.get("ZAI_API_KEY"):
        logger.info("✓ Modèle par défaut: reason (glm-4.7)")
        return "reason"

    # Priorité 3 : fallback local
    logger.info("✓ Modèle par défaut: main (qwen3:8b local)")
    return "main"
