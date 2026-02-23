"""
vision_agent — Agent spécialisé analyse d'images avec modèle de codage.

Outils : analyze_image (qwen3-vl:8b interne)
Modèle LLM : glm-4.7 ou qwen3:8b (codage, 100% local)
Rôle : Analyser des images, extraire du texte, diagnostiquer des erreurs

NOTE : L'outil analyze_image utilise qwen3-vl:8b en interne pour la vision.
"""

import logging

from smolagents import CodeAgent

logger = logging.getLogger(__name__)

_VISION_INSTRUCTIONS = """
Tu es un agent spécialisé dans l'analyse d'images avec un modèle de codage.

OUTIL DISPONIBLE :
- analyze_image(image_path="...", prompt="...") → analyse une image

BONNES PRATIQUES :
- Le manager peut te fournir un argument 'image' qui contient le chemin de l'image
- Pour utiliser l'image fournie : analyze_image(image_path=image, prompt="...")
- Toujours fournir un prompt clair et précis
- Pour extraire du texte : prompt="Extrais tout le texte visible dans cette image"
- Pour décrire : prompt="Décris cette image en détail"
- Pour diagnostiquer : prompt="Y a-t-il des erreurs ou des problèmes dans cette image ?"
- TOUJOURS exécuter du code Python pour utiliser l'outil
- TOUJOURS utiliser final_answer() pour retourner le résultat avec les 3 sections requises

MODÈLE LLM : glm-4.7 ou qwen3:8b (codage)
MODÈLE VISION INTERNE : qwen3-vl:8b (dans l'outil analyze_image)

EXEMPLE :
```python
# Analyser l'image fournie
result = analyze_image(image_path=image, prompt="Décris cette image en détail")
final_answer({
    "### 1. Task outcome (short version)": result,
    "### 2. Task outcome (extremely detailed version)": f"Analyse complète de l'image : {result}",
    "### 3. Additional context (if relevant)": (
        "L'analyse a été effectuée avec le modèle de vision "
        "qwen3-vl:8b via l'outil analyze_image"
    )
})
```
"""


def create_vision_agent(ollama_url: str, model_id: str = "qwen3:8b") -> CodeAgent:
    """
    Crée le sous-agent d'analyse d'image avec modèle de codage.

    Args:
        ollama_url: URL du serveur Ollama (non utilisé, conservé pour compatibilité)
        model_id: Modèle de codage à utiliser (défaut: "qwen3:8b")

    Returns:
        CodeAgent pour utilisation dans le manager
    """
    from models import get_model
    from tools import TOOLS

    # Filtrer uniquement l'outil analyze_image
    vision_tools = [t for t in TOOLS if t.name == "analyze_image"]

    if not vision_tools:
        raise RuntimeError(
            f"Outil analyze_image non trouvé. Outils disponibles: {[t.name for t in TOOLS]}"
        )

    logger.info(f"vision_agent tools: {[t.name for t in vision_tools]}")

    # Utiliser un modèle de codage (glm-4.7 ou qwen3:8b)
    # L'outil analyze_image utilise qwen3-vl:8b en interne pour la vision
    model = get_model(model_id)

    agent = CodeAgent(
        tools=vision_tools,
        model=model,
        max_steps=5,  # Analyse simple, pas besoin de beaucoup d'étapes
        verbosity_level=1,
        additional_authorized_imports=["json", "re", "time", "os"],
        executor_kwargs={"timeout_seconds": 180},
        instructions=_VISION_INSTRUCTIONS,
        name="vision",
        description=(
            "Agent spécialisé dans l'analyse d'images avec un modèle de codage. "
            "Utilise l'outil analyze_image (qwen3-vl:8b interne) pour décrire le "
            "contenu d'images, extraire du texte, diagnostiquer des erreurs, "
            "et analyser des captures d'écran. "
            "Utilise-le pour : analyser des screenshots, extraire du texte d'images, "
            "comprendre des interfaces visuelles, diagnostiquer des problèmes visuels."
        ),
    )

    logger.info(f"✓ vision_agent créé avec modèle LLM: {model_id} (vision interne: qwen3-vl:8b)")
    return agent


# ── Diagnostic autonome ───────────────────────────────────────────────────────

def diagnose_vision() -> dict[str, bool | str | None]:
    """
    Diagnostique la disponibilité du vision_agent.

    Vérifie les dépendances :
    - qwen3-vl modèle de vision (pour analyze_image)

    Returns:
        dict avec les clés : available, tool_name, vision_model, error
    """
    try:
        # Vérifier qu'un modèle de vision est disponible
        import requests
        import os

        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        available_models = [m["name"] for m in response.json().get("models", [])]

        # Chercher les modèles de vision (qwen3-vl ou autres)
        vision_models = [
            m
            for m in available_models
            if any(
                keyword in m.lower()
                for keyword in ["vision", "vl", "llava", "minicpm", "bakllava"]
            )
        ]

        if not vision_models:
            return {
                "available": False,
                "tool_name": "analyze_image",
                "vision_model": None,
                "error": "Aucun modèle de vision trouvé",
                "fix": "ollama pull qwen3-vl:2b",
            }

        # Préférences : qwen3-vl:8b, qwen3-vl:2b, qwen3-vl:4b
        vision_preferences = ["qwen3-vl:8b", "qwen3-vl:2b", "qwen3-vl:4b"]
        vision_model = None
        for pref in vision_preferences:
            if pref in vision_models:
                vision_model = pref
                break
        if vision_model is None:
            vision_model = vision_models[0]

        return {
            "available": True,
            "tool_name": "analyze_image",
            "vision_model": vision_model,
            "error": None,
        }

    except Exception as e:
        return {
            "available": False,
            "tool_name": "analyze_image",
            "vision_model": None,
            "error": f"Impossible de vérifier les modèles Ollama: {e}",
            "fix": "Vérifiez qu'Ollama est accessible et qu'un modèle de vision est installé",
        }
