"""
pc_control_agent — Agent spécialisé pilotage PC Windows.

Outils : screenshot, ui_grounding (qwen3-vl), mouse_keyboard
Modèle : glm-4.7 ou qwen3:8b (local, 0 quota)
Rôle : Voir l'écran, localiser les éléments, cliquer, taper

NOTE : ui_grounding utilise qwen3-vl en interne pour le GUI grounding.
"""

import logging

from smolagents import CodeAgent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Instructions spécifiques pc_control_agent
_PC_CONTROL_INSTRUCTIONS = """
Tu es un agent spécialisé dans le pilotage de l'interface graphique Windows.

Pour localiser un élément et cliquer dessus :
```python
screenshot_path = screenshot()
result = ui_grounding(image_path=screenshot_path, element="description de l'élément")
if result.get("found"):
    mouse_keyboard(operation="click", x=result["x"], y=result["y"])
    final_answer(f"Élément trouvé et cliqué aux coordonnées ({result['x']}, {result['y']})")
else:
    final_answer(f"Élément non trouvé: {result}")
```

Pour taper du texte :
```python
mouse_keyboard(operation="type", text="texte à taper")
```

IMPORTANT :
- Pour analyser une image, délègue au sous-agent vision_agent
- Toujours utiliser final_answer() pour retourner le résultat
"""


def create_pc_control_agent(ollama_url: str, model_id: str = "qwen3:8b") -> CodeAgent:
    """
    Crée le sous-agent de pilotage PC avec qwen3-vl grounding.

    Args:
        ollama_url: URL du serveur Ollama (non utilisé, conservé pour compatibilité)
        model_id: Modèle à utiliser (défaut: "qwen3:8b")

    Returns:
        CodeAgent pour utilisation dans le manager
    """
    from models import get_model
    from tools import TOOLS

    # Filtrer uniquement les tools pertinents pour le pilotage PC (sans analyze_image)
    pc_tools_names = {"screenshot", "ui_grounding", "mouse_keyboard"}
    pc_tools = [t for t in TOOLS if t.name in pc_tools_names]

    if not pc_tools:
        raise RuntimeError(f"Aucun outil PC trouvé. Outils disponibles: {[t.name for t in TOOLS]}")

    logger.info(f"pc_control_agent tools: {[t.name for t in pc_tools]}")

    # Modèle standard : glm-4.7 ou qwen3:8b (pas besoin de vision pour pilotage PC)
    # Le modèle LLM orchestre les outils, ui_grounding utilise qwen3-vl en interne
    model = get_model(model_id)

    agent = CodeAgent(
        tools=pc_tools,
        model=model,
        max_steps=15,           # Plus d'étapes car workflow screenshot→grounding→action
        verbosity_level=1,
        additional_authorized_imports=["json", "re", "time", "os"],
        executor_kwargs={"timeout_seconds": 300},
        instructions=_PC_CONTROL_INSTRUCTIONS,
        name="pc_control",
        description=(
            "Agent spécialisé pour piloter l'interface graphique Windows. "
            "Peut prendre des screenshots, localiser précisément les éléments UI (qwen3-vl grounding), "
            "et interagir avec la souris et le clavier. "
            "Utilise-le pour : ouvrir des applications, cliquer sur des boutons, "
            "remplir des formulaires, naviguer dans Windows. "
            "Pour analyser des images, délègue au sous-agent vision_agent."
        ),
    )

    return agent
