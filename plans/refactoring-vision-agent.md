# Plan de Refactoring - Séparation de l'Agent Vision

## Problème

Le [`pc_control_agent`](agent/agents/pc_control_agent.py) utilise actuellement un modèle de vision ([`qwen3-vl:8b`](agent/agents/pc_control_agent.py:71)) pour TOUTES ses tâches, alors que seule l'analyse d'image ([`analyze_image`](agent/tools/vision.py:23)) nécessite vraiment un modèle de vision. Les autres outils ([`screenshot`](agent/tools/screenshot.py:22), [`ui_grounding`](agent/tools/ui_tars_grounding.py:36), [`mouse_keyboard`](agent/tools/mouse_keyboard.py:17)) n'ont pas besoin de vision.

## Architecture Actuelle

```mermaid
flowchart TD
    M[Manager] -->|délègue| PC[pc_control_agent]

    subgraph PC[pc_control_agent - qwen3-vl:8b]
        PC --> SS[screenshot]
        PC --> AI[analyze_image]
        PC --> UI[ui_grounding]
        PC --> MK[mouse_keyboard]
    end

    style PC fill:#ff9999
    style AI fill:#ff6666
```

**Problème**: Le modèle de vision est utilisé pour TOUTES les tâches, même celles qui n'en ont pas besoin.

---

## Architecture Proposée

```mermaid
flowchart TD
    M[Manager<br/>Modèle: glm-4.7 ou qwen3:8b<br/>Tools: file_system, os_exec, clipboard] -->|délègue| PC[pc_control_agent<br/>Modèle: glm-4.7 ou qwen3:8b]
    M -->|délègue| V[vision_agent<br/>Modèle: qwen3-vl:8b]
    M -->|délègue| B[browser_agent<br/>Modèle: glm-4.7 ou qwen3:8b]
    M -->|délègue| W[web_agent<br/>Modèle: glm-4.7 ou qwen3:8b]

    subgraph PC[pc_control_agent]
        PC --> SS[screenshot]
        PC --> UI[ui_grounding]
        PC --> MK[mouse_keyboard]
    end

    subgraph V[vision_agent]
        V --> AI[analyze_image]
    end

    UI --> UIT[UI-TARS-2B-SFT<br/>Modèle interne du tool]

    style M fill:#ffcc00
    style PC fill:#99ff99
    style V fill:#9999ff
    style B fill:#ff9999
    style W fill:#ff99ff
    style AI fill:#6666ff
    style UIT fill:#ffcc99
```

**Avantages**:
- `pc_control_agent`, `browser_agent`, `web_agent` utilisent le même modèle standard (glm-4.7 ou qwen3:8b)
- `vision_agent` utilise un modèle de vision uniquement pour l'analyse d'image
- Meilleure séparation des responsabilités
- Optimisation des ressources

---

## Répartition des Modèles

| Agent | Modèle LLM | Modèles internes des tools |
|-------|-----------|---------------------------|
| **Manager** | glm-4.7 ou qwen3:8b | - |
| **pc_control_agent** | glm-4.7 ou qwen3:8b | UI-TARS-2B-SFT (dans ui_grounding) |
| **vision_agent** | qwen3-vl:8b | qwen3-vl:2b (dans analyze_image) |
| **browser_agent** | glm-4.7 ou qwen3:8b | - |
| **web_agent** | glm-4.7 ou qwen3:8b | - |

### Note importante sur UI-TARS-2B-SFT

`UI-TARS-2B-SFT` est un modèle **spécialisé pour le GUI grounding uniquement**. Il ne peut pas être utilisé comme modèle LLM principal pour un `CodeAgent`. Il est utilisé **en interne** par le tool [`ui_grounding`](agent/tools/ui_tars_grounding.py:36) pour localiser des éléments d'interface dans un screenshot.

---

## Étapes d'Implémentation

### 1. Créer le nouveau sous-agent `vision_agent`

**Fichier**: `agent/agents/vision_agent.py`

```python
"""
vision_agent — Agent spécialisé analyse d'images avec modèle vision.

Outils : analyze_image (qwen3-vl:8b)
Modèle : qwen3-vl:8b (vision native, 100% local)
Rôle : Analyser des images, extraire du texte, diagnostiquer des erreurs
"""

import os
import logging
from smolagents import CodeAgent, LiteLLMModel

logger = logging.getLogger(__name__)

_VISION_INSTRUCTIONS = """
Tu es un agent spécialisé dans l'analyse d'images avec un modèle de vision.

OUTIL DISPONIBLE :
- analyze_image(image_path="...", prompt="...") → analyse une image

BONNES PRATIQUES :
- Toujours fournir un prompt clair et précis
- Pour extraire du texte : prompt="Extrais tout le texte visible dans cette image"
- Pour décrire : prompt="Décris cette image en détail"
- Pour diagnostiquer : prompt="Y a-t-il des erreurs ou des problèmes dans cette image ?"
- Toujours utiliser final_answer() pour retourner le résultat

MODÈLE : qwen3-vl:8b (vision native, 100% local)
"""


def create_vision_agent(ollama_url: str) -> CodeAgent:
    """
    Crée le sous-agent d'analyse d'image avec modèle vision.

    Args:
        ollama_url: URL du serveur Ollama

    Returns:
        CodeAgent pour utilisation dans le manager
    """
    from tools import TOOLS

    # Filtrer uniquement l'outil analyze_image
    vision_tools = [t for t in TOOLS if t.name == "analyze_image"]

    if not vision_tools:
        raise RuntimeError(f"Outil analyze_image non trouvé. Outils disponibles: {[t.name for t in TOOLS]}")

    logger.info(f"vision_agent tools: {[t.name for t in vision_tools]}")

    # Détection automatique du modèle de vision disponible
    try:
        import requests
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        available_models = [m["name"] for m in response.json().get("models", [])]

        # Préférences : qwen3-vl:8b (installé), qwen3-vl:2b (plus petit), qwen3-vl:4b
        vision_preferences = ["qwen3-vl:8b", "qwen3-vl:2b", "qwen3-vl:4b"]

        # Chercher d'abord les modèles qwen3-vl:*
        vision_models = [m for m in available_models if m.startswith("qwen3-vl")]

        logger.info(f"DEBUG: available_models = {available_models}")

        # Si aucun modèle qwen3-vl trouvé, chercher les modèles avec "vision" ou "vl"
        if not vision_models:
            vision_models = [m for m in available_models if any(keyword in m.lower() for keyword in ["vision", "vl", "llava", "minicpm", "bakllava"])]

        # Supprimer les doublons
        vision_models = list(set(vision_models))

        logger.info(f"Modèles de vision détectés: {vision_models}")

        if vision_models:
            # Préférences : qwen3-vl:8b (installé), qwen3-vl:2b (plus petit), qwen3-vl:4b
            vision_model = None
            for pref in vision_preferences:
                if pref in vision_models:
                    vision_model = pref
                    logger.info(f"✓ vision_agent utilise modèle vision: {vision_model}")
                    break
            if vision_model is None:
                # Fallback sur le premier modèle de vision disponible
                vision_model = vision_models[0]
                logger.info(f"✓ vision_agent utilise modèle vision (fallback): {vision_model}")
        else:
            # Aucun modèle de vision trouvé, fallback sur qwen3:8b (supporte la vision)
            vision_model = "qwen3:8b"
            logger.warning(
                f"⚠️ Aucun modèle de vision trouvé. "
                f"vision_agent utilise qwen3:8b comme fallback. "
                f"Pour la vision, installez un modèle avec 'vision' ou 'vl' dans le nom : "
                f"ollama pull qwen3-vl:2b"
            )
    except Exception as e:
        logger.warning(f"Impossible de détecter les modèles Ollama: {e}. Utilisation de qwen3:8b comme fallback.")
        vision_model = "qwen3:8b"

    # Création du modèle avec le modèle détecté
    model = LiteLLMModel(
        model_id=f"ollama_chat/{vision_model}",
        api_base=ollama_url,
        api_key="ollama",
        num_ctx=8192,          # Plus de contexte pour screenshots encodés en base64
        extra_body={"think": False},
    )

    agent = CodeAgent(
        tools=vision_tools,
        model=model,
        max_steps=5,           # Analyse simple, pas besoin de beaucoup d'étapes
        verbosity_level=1,
        additional_authorized_imports=["json", "re", "time", "os"],
        executor_kwargs={"timeout_seconds": 180},
        instructions=_VISION_INSTRUCTIONS,
        name="vision",
        description=(
            "Agent spécialisé dans l'analyse d'images avec un modèle de vision. "
            "Peut décrire le contenu d'images, extraire du texte, diagnostiquer des erreurs, "
            "et analyser des captures d'écran. "
            "Utilise-le pour : analyser des screenshots, extraire du texte d'images, "
            "comprendre des interfaces visuelles, diagnostiquer des problèmes visuels."
        ),
    )

    return agent
```

---

### 2. Modifier `pc_control_agent`

**Fichier**: `agent/agents/pc_control_agent.py`

**Changements**:
- Retirer l'outil `analyze_image` de la liste des tools
- Changer le modèle de `qwen3-vl:8b` vers `glm-4.7` ou `qwen3:8b` (modèle standard)
- Mettre à jour les instructions pour ne plus inclure l'analyse d'image
- Mettre à jour la description

```python
"""
pc_control_agent — Agent spécialisé pilotage PC Windows.

Outils : screenshot, ui_grounding (UI-TARS-2B), mouse_keyboard
Modèle : glm-4.7 ou qwen3:8b (local, 0 quota)
Rôle : Voir l'écran, localiser les éléments, cliquer, taper

NOTE : ui_grounding utilise UI-TARS-2B-SFT en interne pour le GUI grounding.
"""

import os
import logging
from smolagents import CodeAgent, LiteLLMModel

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
    Crée le sous-agent de pilotage PC avec UI-TARS grounding.

    Args:
        ollama_url: URL du serveur Ollama
        model_id: Modèle à utiliser (défaut: "qwen3:8b")

    Returns:
        CodeAgent pour utilisation dans le manager
    """
    from tools import TOOLS

    # Filtrer uniquement les tools pertinents pour le pilotage PC (sans analyze_image)
    pc_tools_names = {"screenshot", "ui_grounding", "mouse_keyboard"}
    pc_tools = [t for t in TOOLS if t.name in pc_tools_names]

    if not pc_tools:
        raise RuntimeError(f"Aucun outil PC trouvé. Outils disponibles: {[t.name for t in TOOLS]}")

    logger.info(f"pc_control_agent tools: {[t.name for t in pc_tools]}")

    # Modèle standard : glm-4.7 ou qwen3:8b (pas besoin de vision pour pilotage PC)
    # Le modèle LLM orchestre les outils, ui_grounding utilise UI-TARS en interne
    model = LiteLLMModel(
        model_id=f"ollama_chat/{model_id}",
        api_base=ollama_url,
        api_key="ollama",
        num_ctx=32768,
        extra_body={"think": False},
    )

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
            "Peut prendre des screenshots, localiser précisément les éléments UI (UI-TARS grounding), "
            "et interagir avec la souris et le clavier. "
            "Utilise-le pour : ouvrir des applications, cliquer sur des boutons, "
            "remplir des formulaires, naviguer dans Windows. "
            "Pour analyser des images, délègue au sous-agent vision_agent."
        ),
    )

    return agent
```

---

### 3. Modifier `main.py` pour intégrer le nouveau sous-agent

**Fichier**: `agent/main.py`

**Changements**:
- Importer `create_vision_agent`
- Ajouter la création du `vision_agent` dans `build_multi_agent_system()`
- Mettre à jour le endpoint `/models` pour inclure le nouveau sous-agent

```python
# Dans build_multi_agent_system()
def build_multi_agent_system(model_id: str = "main") -> CodeAgent:
    """
    Construit le système Manager + sous-agents selon les tools disponibles.

    Architecture :
    - Manager : glm-4.7 ou qwen3:8b + tools directs (file_system, os_exec, clipboard)
    - pc_control : glm-4.7 ou qwen3:8b + screenshot, ui_grounding, mouse_keyboard
    - vision : qwen3-vl:8b + analyze_image
    - browser : glm-4.7 ou qwen3:8b + Chrome DevTools MCP (si disponible)
    - web_search : glm-4.7 ou qwen3:8b + MCP Z.ai (si ZAI_API_KEY configuré)

    NOTE : Tous les agents sauf vision_agent utilisent le même modèle LLM (glm-4.7 ou qwen3:8b).
    Les outils spécialisés (ui_grounding, analyze_image) utilisent leurs propres modèles internes.
    """
    from agents.pc_control_agent import create_pc_control_agent
    from agents.vision_agent import create_vision_agent  # NOUVEAU
    from agents.browser_agent import create_browser_agent
    from agents.web_agent import create_web_agent

    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    managed_agents = []

    # ── Sous-agent pilotage PC ────────────────────────────────────────────────
    try:
        # Utiliser le même modèle que le Manager (glm-4.7 ou qwen3:8b)
        pc_model = "qwen3:8b"  # Peut être dynamique selon la préférence
        pc_agent = create_pc_control_agent(ollama_url, model_id=pc_model)
        managed_agents.append(pc_agent)
        logger.info(f"✓ pc_control_agent créé (screenshot + UI-TARS + mouse/keyboard) avec modèle {pc_model}")
    except Exception as e:
        logger.warning(f"✗ pc_control_agent non disponible: {e}")

    # ── Sous-agent vision ────────────────────────────────────────────────────
    # NOUVEAU
    try:
        vision_agent = create_vision_agent(ollama_url)
        managed_agents.append(vision_agent)
        logger.info("✓ vision_agent créé (analyze_image avec qwen3-vl:8b)")
    except Exception as e:
        logger.warning(f"✗ vision_agent non disponible: {e}")

    # ── Sous-agent browser Chrome ─────────────────────────────────────────────
    if _chrome_mcp_tools:
        try:
            # Utiliser le même modèle que le Manager
            browser_agent = create_browser_agent(ollama_url, _chrome_mcp_tools, model_id="qwen3:8b")
            managed_agents.append(browser_agent)
            logger.info(f"✓ browser_agent créé ({len(_chrome_mcp_tools)} tools Chrome DevTools) avec modèle qwen3:8b")
        except Exception as e:
            logger.warning(f"✗ browser_agent non disponible: {e}")
    else:
        logger.warning("✗ browser_agent ignoré (Chrome DevTools MCP non disponible)")

    # ── Sous-agent web search Z.ai ────────────────────────────────────────────
    if _web_search_tools:
        try:
            # Utiliser le même modèle que le Manager
            web_agent = create_web_agent(ollama_url, _web_search_tools, model_id="qwen3:8b")
            if web_agent:
                managed_agents.append(web_agent)
                logger.info(f"✓ web_agent créé ({len(_web_search_tools)} tools Z.ai) avec modèle qwen3:8b")
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
            "requests", "urllib", "json", "csv", "pathlib", "os", "subprocess",
        ],
        executor_kwargs={"timeout_seconds": 240},
        instructions=SKILLS,
    )

    return manager
```

```python
# Dans /models endpoint
@app.get("/models")
async def list_models():
    models_info = {}
    for category, (model_name, base_url) in MODELS.items():
        display_name = model_name.split("/")[-1] if "/" in model_name else model_name
        is_local = "ollama_chat/" in model_name or "localhost" in base_url
        models_info[category] = {
            "name": display_name,
            "full_name": model_name,
            "type": "local" if is_local else "cloud",
            "available": True,
        }
    return {
        "models": models_info,
        "ollama_models": get_ollama_models(),
        "sub_agents": {
            "pc_control": "glm-4.7 ou qwen3:8b + UI-TARS-2B-SFT (interne)",
            "vision": "qwen3-vl:8b + analyze_image (qwen3-vl:2b interne)",
            "browser": f"glm-4.7 ou qwen3:8b + {len(_chrome_mcp_tools)} tools Chrome DevTools",
            "web_search": f"glm-4.7 ou qwen3:8b + {len(_web_search_tools)} tools Z.ai MCP",
        },
    }
```

**Note**: Il faut aussi mettre à jour les fonctions `create_browser_agent` et `create_web_agent` pour accepter un paramètre `model_id` optionnel.

---

### 4. Mettre à jour la documentation

**Fichiers à mettre à jour**:
- `AGENTS.md` : Ajouter la description du nouveau `vision_agent`
- `IMPLEMENTATION-TOOLS.md` : Mettre à jour la section TOOL-7 pour mentionner l'agent dédié
- `MIGRATION-MULTI-AGENT.md` : Documenter ce refactoring

---

## Résumé des modifications

| Fichier | Action | Description |
|---------|--------|-------------|
| `agent/agents/vision_agent.py` | CRÉER | Nouveau sous-agent pour l'analyse d'image |
| `agent/agents/pc_control_agent.py` | MODIFIER | Retirer `analyze_image`, utiliser glm-4.7 ou qwen3:8b |
| `agent/agents/browser_agent.py` | MODIFIER | Ajouter paramètre `model_id` optionnel |
| `agent/agents/web_agent.py` | MODIFIER | Ajouter paramètre `model_id` optionnel |
| `agent/main.py` | MODIFIER | Intégrer `vision_agent` dans le système multi-agent |
| `AGENTS.md` | MODIFIER | Documenter le nouveau sous-agent |
| `IMPLEMENTATION-TOOLS.md` | MODIFIER | Mettre à jour TOOL-7 |
| `MIGRATION-MULTI-AGENT.md` | MODIFIER | Documenter le refactoring |

---

## Avantages de cette refonte

1. **Séparation des responsabilités** : Chaque sous-agent a une responsabilité claire
2. **Optimisation des ressources** : `pc_control_agent` utilise un modèle standard plus léger
3. **Maintenabilité** : Plus facile de modifier ou remplacer l'un des agents
4. **Flexibilité** : Possibilité d'utiliser différents modèles pour chaque agent
5. **Clarté** : Le workflow est plus explicite et compréhensible
6. **Uniformité** : Manager, pc_control_agent, browser_agent, web_agent utilisent le même modèle LLM
