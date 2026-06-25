"""
Modèles LLM — Création et gestion des modèles pour les agents.

Ce module centralise la logique de création de modèles pour éviter les imports
circulaires entre main.py et les agents.
"""

import logging
import os

import requests
from free_llm_api_keys import FreeLLMClient
from smolagents import LiteLLMModel, Model
from smolagents.models import ChatMessage, MessageRole

logger = logging.getLogger(__name__)


# ─── Détection modèles Ollama ────────────────────────────────────────────────
MODEL_PREFERENCES: dict[str, list[str]] = {
    "fast": ["hf.co/tantk/Nanbeige4.1-3B-GGUF:Q4_K_M", "qwen3:4b", "gemma3:latest"],
    "smart": ["qwen3:14b", "qwen3:8b", "qwen3:4b", "hf.co/tantk/Nanbeige4.1-3B-GGUF:Q4_K_M"],
    "main": ["qwen3:14b", "qwen3:8b", "qwen3:4b", "hf.co/tantk/Nanbeige4.1-3B-GGUF:Q4_K_M"],
    "vision": ["qwen3-vl:8b", "qwen3-vl:2b", "qwen3-vl:4b", "llama3.2-vision"],
}

CLOUD_MODELS: dict[str, tuple[str, str]] = {}

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


def _detect_models_impl() -> dict[str, tuple[str, str]]:
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
        logger.warning("✗ qwen3-vl non trouvé — installer avec: ollama pull qwen3-vl:2b")

    detected.update(CLOUD_MODELS)
    _detected_models = detected
    return detected



def get_models() -> dict[str, tuple[str, str]]:
    """
    Retourne les modèles détectés avec cache lazy.

    La détection est faite à la première utilisation, pas à l'import.
    Cela permet au serveur de démarrer même si Ollama est down.

    Returns:
        dict: Mapping {category: (model_name, base_url)}
    """
    try:
        return _detect_models_impl()
    except Exception as e:
        logger.warning(f"Échec détection modèles: {e}")
        return {}  # Fallback vide


class FreeLLMClientModel(Model):
    """Wrapper Model pour utiliser free-llm-api-keys avec fallback vers Ollama."""

    def __init__(self, fallback_model_id: str = "main", **kwargs):
        super().__init__(**kwargs)
        self.fallback_model_id = fallback_model_id
        self.client = FreeLLMClient(type="texte")
        self.model_id = "free-llm-api-keys"

    def __call__(self, messages, stop_sequences=None, **kwargs):
        return self.generate(messages, stop_sequences=stop_sequences, **kwargs)

    def generate(
        self, messages, stop_sequences=None, response_format=None, tools_to_call_from=None, **kwargs
    ) -> ChatMessage:
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                formatted_messages.append(msg)
            elif hasattr(msg, "role") and hasattr(msg, "content"):
                role_str = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
                content = msg.content
                if not isinstance(content, list):
                    content = str(content)
                formatted_messages.append({"role": role_str, "content": content})
            else:
                formatted_messages.append(msg)

        try:
            logger.info("Tentative de génération avec FreeLLMClient (type=texte)")
            clean_kwargs = {k: v for k, v in kwargs.items() \
                            if k in ["temperature", "max_tokens", "top_p"]}
            response_text = self.client.chat(formatted_messages, **clean_kwargs)
            return ChatMessage(role=MessageRole.ASSISTANT, content=response_text)

        except Exception as e:
            logger.warning(
                f"FreeLLMClient a échoué ({e.__class__.__name__}: {e}). "
                f"Fallback vers {self.fallback_model_id}."
            )
            fallback_model = get_model(self.fallback_model_id, bypass_free=True)
            return fallback_model.generate(
                messages, stop_sequences, response_format, tools_to_call_from, **kwargs
            )


def get_model(model_id: str = "free", bypass_free: bool = False) -> Model:
    """
    Crée un modèle LLM à partir d'un identifiant.

    Args:
        model_id: Identifiant du modèle (free, main, smart, fast, vision)
                   OU nom direct d'un modèle Ollama
        bypass_free: Si True, force l'utilisation de LiteLLMModel (Ollama)

    Returns:
        Model configuré (FreeLLMClientModel ou LiteLLMModel)
    """
    models = get_models()

    if model_id in ["free", "code", "reason"] and not bypass_free:
        logger.info(f"✓ Utilisation du modèle FreeLLMClientModel pour '{model_id}'")
        return FreeLLMClientModel(fallback_model_id="main")

    if model_id in models:
        model_name, base_url = models[model_id]
    else:
        ollama_models = get_ollama_models()
        if model_id in ollama_models:
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            model_name = f"ollama_chat/{model_id}"
            base_url = ollama_url
            logger.info(f"✓ Utilisation du modèle Ollama direct: {model_id}")
        else:
            if "main" in models:
                model_name, base_url = models["main"]
            elif models:
                model_name, base_url = next(iter(models.values()))
                logger.warning(
                    f"Modèle '{model_id}' non trouvé dans Ollama, "
                    f"fallback sur {model_name}"
                )
            else:
                raise RuntimeError("Aucun modèle local Ollama n'est disponible en fallback.")

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
    2. "free" (free-llm-api-keys)
    3. "main" (Ollama local) en fallback

    Returns:
        str: Identifiant du modèle par défaut
    """
    get_models()  # Initialise le cache des modèles si besoin
    
    env_default = os.environ.get("DEFAULT_MODEL")
    if env_default:
        logger.info(f"✓ Modèle par défaut depuis env: {env_default}")
        return env_default

    logger.info("✓ Modèle par défaut: free (free-llm-api-keys)")
    return "free"
