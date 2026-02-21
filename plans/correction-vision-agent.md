# Plan de Correction - vision_agent avec modèle de codage

## Problème

Le [`vision_agent`](agent/agents/vision_agent.py) utilise actuellement un modèle de **vision** (qwen3-vl:8b) comme LLM principal, alors que seul l'outil [`analyze_image`](agent/tools/vision.py:118) nécessite vraiment un modèle de vision. Le LLM principal devrait utiliser un modèle de **codage** (glm-4.7 ou qwen3:8b) pour orchestrer l'outil.

## Architecture Actuelle

```mermaid
flowchart TD
    M[Manager] -->|délègue| V[vision_agent]

    subgraph V[vision_agent - qwen3-vl:8b]
        V --> AI[analyze_image]
    end

    subgraph AI[analyze_image]
        AI --> VM[qwen3-vl:8b interne]
    end

    style V fill:#ff9999
    style AI fill:#ff6666
    style VM fill:#ff3333
```

**Problème**: Le modèle de vision est utilisé comme LLM principal, alors qu'il est moins performant pour le raisonnement et l'orchestration.

---

## Architecture Proposée

```mermaid
flowchart TD
    M[Manager] -->|délègue| V[vision_agent]

    subgraph V[vision_agent - glm-4.7 ou qwen3:8b]
        V --> AI[analyze_image]
    end

    subgraph AI[analyze_image]
        AI --> VM[qwen3-vl:8b interne]
    end

    style V fill:#99ff99
    style AI fill:#6666ff
    style VM fill:#ff6666
```

**Avantages**:
- Le LLM principal utilise un modèle de codage performant (glm-4.7 ou qwen3:8b)
- L'outil `analyze_image` utilise son propre modèle de vision (qwen3-vl:8b) en interne
- Cohérence avec l'architecture globale (tous les agents utilisent le même modèle de codage)
- Meilleure orchestration des prompts et des réponses

---

## Répartition des Modèles

| Agent | Modèle LLM | Modèles internes des tools |
|-------|-----------|---------------------------|
| **Manager** | glm-4.7 ou qwen3:8b | - |
| **pc_control_agent** | glm-4.7 ou qwen3:8b | UI-TARS-2B-SFT (dans ui_grounding) |
| **vision_agent** | glm-4.7 ou qwen3:8b | qwen3-vl:8b (dans analyze_image) |
| **browser_agent** | glm-4.7 ou qwen3:8b | - |
| **web_agent** | glm-4.7 ou qwen3:8b | - |

---

## Étapes d'Implémentation

### 1. Modifier `vision_agent.py`

**Fichier**: `agent/agents/vision_agent.py`

**Changements**:
- Remplacer la détection automatique de modèle de vision par l'utilisation d'un modèle de codage
- Utiliser la fonction `get_model()` de `main.py` ou créer directement un modèle de codage
- Mettre à jour les instructions pour refléter l'utilisation d'un modèle de codage
- Mettre à jour la description

```python
"""
vision_agent — Agent spécialisé analyse d'images avec modèle de codage.

Outils : analyze_image (qwen3-vl:8b interne)
Modèle LLM : glm-4.7 ou qwen3:8b (codage, 100% local)
Rôle : Analyser des images, extraire du texte, diagnostiquer des erreurs

NOTE : L'outil analyze_image utilise qwen3-vl:8b en interne pour la vision.
"""

import os
import logging
from smolagents import CodeAgent, LiteLLMModel

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
    "### 3. Additional context (if relevant)": "L'analyse a été effectuée avec le modèle de vision qwen3-vl:8b via l'outil analyze_image"
})
```
"""


def create_vision_agent(ollama_url: str, model_id: str = "qwen3:8b") -> CodeAgent:
    """
    Crée le sous-agent d'analyse d'image avec modèle de codage.

    Args:
        ollama_url: URL du serveur Ollama
        model_id: Modèle de codage à utiliser (défaut: "qwen3:8b")

    Returns:
        CodeAgent pour utilisation dans le manager
    """
    from tools import TOOLS

    # Filtrer uniquement l'outil analyze_image
    vision_tools = [t for t in TOOLS if t.name == "analyze_image"]

    if not vision_tools:
        raise RuntimeError(f"Outil analyze_image non trouvé. Outils disponibles: {[t.name for t in TOOLS]}")

    logger.info(f"vision_agent tools: {[t.name for t in vision_tools]}")

    # Utiliser un modèle de codage (glm-4.7 ou qwen3:8b)
    # L'outil analyze_image utilise qwen3-vl:8b en interne pour la vision
    model = LiteLLMModel(
        model_id=f"ollama_chat/{model_id}",
        api_base=ollama_url,
        api_key="ollama",
        num_ctx=32768,
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
            "Agent spécialisé dans l'analyse d'images avec un modèle de codage. "
            "Utilise l'outil analyze_image (qwen3-vl:8b interne) pour décrire le contenu d'images, "
            "extraire du texte, diagnostiquer des erreurs, et analyser des captures d'écran. "
            "Utilise-le pour : analyser des screenshots, extraire du texte d'images, "
            "comprendre des interfaces visuelles, diagnostiquer des problèmes visuels."
        ),
    )

    logger.info(f"✓ vision_agent créé avec modèle LLM: {model_id} (vision interne: qwen3-vl:8b)")
    return agent
```

---

### 2. Modifier `main.py` pour passer le modèle de codage

**Fichier**: `agent/main.py`

**Changements**:
- Modifier l'appel à `create_vision_agent()` pour passer un modèle de codage
- Mettre à jour la documentation dans `/models` endpoint

```python
# Dans build_multi_agent_system()
def build_multi_agent_system(model_id: str = "main") -> CodeAgent:
    """
    Construit le système Manager + sous-agents selon les tools disponibles.

    Architecture :
    - Manager : glm-4.7 ou qwen3:8b + tools directs (file_system, os_exec, clipboard)
    - pc_control : glm-4.7 ou qwen3:8b + screenshot, ui_grounding, mouse_keyboard
    - vision : glm-4.7 ou qwen3:8b + analyze_image (qwen3-vl:8b interne)
    - browser : glm-4.7 ou qwen3:8b + Chrome DevTools MCP (si disponible)
    - web_search : glm-4.7 ou qwen3:8b + MCP Z.ai (si ZAI_API_KEY configuré)

    NOTE : Tous les agents utilisent le même modèle LLM (glm-4.7 ou qwen3:8b).
    Les outils spécialisés (ui_grounding, analyze_image) utilisent leurs propres modèles internes.
    """
    from agents.pc_control_agent import create_pc_control_agent
    from agents.vision_agent import create_vision_agent
    from agents.browser_agent import create_browser_agent
    from agents.web_agent import create_web_agent

    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    managed_agents = []

    # ── Sous-agent pilotage PC ────────────────────────────────────────────────
    try:
        # Utiliser le même modèle que le Manager (glm-4.7 ou qwen3:8b)
        pc_model = "qwen3:8b"
        pc_agent = create_pc_control_agent(ollama_url, model_id=pc_model)
        managed_agents.append(pc_agent)
        logger.info(f"✓ pc_control_agent créé (screenshot + UI-TARS + mouse/keyboard) avec modèle {pc_model}")
    except Exception as e:
        logger.warning(f"✗ pc_control_agent non disponible: {e}")

    # ── Sous-agent vision ────────────────────────────────────────────────────
    try:
        # Utiliser le même modèle de codage que le Manager (glm-4.7 ou qwen3:8b)
        # L'outil analyze_image utilise qwen3-vl:8b en interne pour la vision
        vision_model = "qwen3:8b"
        vision_agent = create_vision_agent(ollama_url, model_id=vision_model)
        managed_agents.append(vision_agent)
        logger.info(f"✓ vision_agent créé avec modèle LLM: {vision_model} (vision interne: qwen3-vl:8b)")
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
            "vision": "glm-4.7 ou qwen3:8b + analyze_image (qwen3-vl:8b interne)",
            "browser": f"glm-4.7 ou qwen3:8b + {len(_chrome_mcp_tools)} tools Chrome DevTools",
            "web_search": f"glm-4.7 ou qwen3:8b + {len(_web_search_tools)} tools Z.ai MCP",
        },
    }
```

---

### 3. Vérifier que `vision.py` n'a pas besoin de modification

**Fichier**: `agent/tools/vision.py`

**Vérification**:
- L'outil `analyze_image` utilise déjà son propre modèle de vision détecté automatiquement via `_detect_vision_model()`
- Aucune modification nécessaire pour `vision.py`

---

### 4. Mettre à jour la documentation

**Fichiers à mettre à jour**:
- `AGENTS.md` : Mettre à jour la description du `vision_agent` pour indiquer qu'il utilise un modèle de codage
- `LEARNING.md` : Documenter cette correction
- `plans/refactoring-vision-agent.md` : Mettre à jour le plan de refactoring pour refléter cette correction

---

## Résumé des modifications

| Fichier | Action | Description |
|---------|--------|-------------|
| `agent/agents/vision_agent.py` | MODIFIER | Remplacer modèle de vision par modèle de codage (glm-4.7 ou qwen3:8b) |
| `agent/main.py` | MODIFIER | Passer le modèle de codage à `create_vision_agent()` |
| `agent/tools/vision.py` | VÉRIFIER | Aucune modification nécessaire (déjà correct) |
| `AGENTS.md` | MODIFIER | Mettre à jour la description du `vision_agent` |
| `LEARNING.md` | MODIFIER | Documenter cette correction |

---

## Avantages de cette correction

1. **Cohérence architecturale** : Tous les agents utilisent le même modèle de codage (glm-4.7 ou qwen3:8b)
2. **Meilleure orchestration** : Le modèle de codage est meilleur pour structurer les prompts et les réponses
3. **Séparation claire** : Le LLM orchestre, l'outil spécialisé fait la vision
4. **Flexibilité** : Possibilité d'utiliser glm-4.7 (cloud) ou qwen3:8b (local) selon la préférence
5. **Performance** : Les modèles de codage sont généralement plus performants pour le raisonnement

---

## Tests à effectuer après la correction

1. **Test basique** : "Analyse cette image : C:\tmp\myclawshots\screen_001.png"
2. **Test extraction texte** : "Extrais tout le texte de cette image : C:\tmp\myclawshots\screen_002.png"
3. **Test diagnostic** : "Y a-t-il des erreurs dans cette image : C:\tmp\myclawshots\screen_003.png"
4. **Test via Manager** : "Prends un screenshot et analyse-le" (vérifie que le Manager délègue correctement au vision_agent)
