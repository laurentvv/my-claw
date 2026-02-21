# MIGRATION-MULTI-AGENT.md — Plan de migration vers architecture multi-agent

> Document destiné à une IA de codage (Claude Code, Cursor, Cline…)
> Lire AGENTS.md et PROGRESS.md avant de commencer.
> RÈGLE ABSOLUE : un checkpoint validé → commit → étape suivante.
> Ne jamais toucher à un module validé sans validation explicite.

---

## CONTEXTE ET OBJECTIF

### État actuel (avant migration)
```
main.py — UN SEUL CodeAgent monolithique
├── 6 tools locaux (file_system, os_exec, clipboard, screenshot, mouse_keyboard, analyze_image)
└── 26 tools MCP Chrome DevTools (via lifespan FastAPI)
= 32 tools dans un seul agent → contexte surchargé, modèle confus
```

### Cible après migration
```
main.py — Manager Agent + 3 ManagedAgents spécialisés
├── MANAGER (glm-4.7) → tools directs : file_system, os_exec, clipboard
├── pc_control_agent (qwen3-vl:2b + UI-TARS-2B) → screenshot, analyze_image, mouse_keyboard
├── browser_agent (qwen3:8b) → 26 tools Chrome DevTools MCP
└── web_agent (qwen3:8b) → webSearchPrime, webReader, zread (TOOL-4/5/6 futurs)
```

### Pourquoi maintenant
- Avant d'ajouter TOOL-4/5/6 (MCP Z.ai) dans un agent déjà surchargé
- UI-TARS-2B-SFT s'intègre naturellement dans pc_control_agent
- Chaque agent ne voit que ses tools → moins de tokens, meilleure précision
- qwen3:8b local = 0 quota Z.ai pour browser_agent et web_agent

---

## MODÈLES À UTILISER

| Agent | Modèle | Raison |
|-------|--------|--------|
| Manager | `glm-4.7` (reason) ou `qwen3:8b` | Orchestration, délégation |
| pc_control_agent | `qwen3-vl:2b` (vision) | Petit, local, vision native |
| browser_agent | `qwen3:8b` (smart) | 0 quota, bon raisonnement |
| web_agent | `qwen3:8b` (smart) | 0 quota, recherche |
| UI-TARS grounding | `hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M` | Ollama local, ~1.6GB |

**Garder les modèles PLUS PETITS que les originaux :**
- `qwen3:14b` → remplacé par `qwen3:8b` pour les sous-agents (moins de RAM)
- `qwen3-vl:4b` → remplacé par `qwen3-vl:2b` déjà installé et validé
- UI-TARS-7B → UI-TARS-2B-SFT Q4_K_M (~1.6GB au lieu de ~8GB)

---

## NOUVEAU TOOL : UITarsGroundingTool (TOOL-11)

### Pourquoi UI-TARS-2B-SFT
UI-TARS-2B-SFT est un modèle ByteDance spécialisé GUI grounding :
- Entraîné sur des millions de screenshots avec coordonnées annotées
- Retourne des coordonnées RELATIVES [0..1] ou ABSOLUES selon le prompt
- Champion ScreenSpot benchmark (meilleur rapport taille/précision à 2B)
- Tourne via Ollama avec GGUF mradermacher Q4_K_M (~1.6GB)

### Installation préalable
```bash
ollama pull hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M
```

### Format de réponse UI-TARS
UI-TARS retourne les coordonnées au format relatif [0..1] :
```
[0.73, 0.21]
```
Il faut multiplier par la résolution écran pour obtenir les pixels absolus.

### Fichier : agent/tools/ui_tars_grounding.py

```python
"""
UITarsGroundingTool — Détection d'éléments UI avec UI-TARS-2B-SFT via Ollama.

Spécialisé pour le GUI grounding : localise précisément les éléments
d'interface à partir d'une description textuelle et d'un screenshot.
Retourne les coordonnées pixel absolues pour pyautogui.
"""

import logging
import os
import base64
import json
import re
from pathlib import Path
from typing import Optional

from smolagents import Tool

logger = logging.getLogger(__name__)

# Prompt système UI-TARS pour grounding desktop
_GROUNDING_SYSTEM = (
    "Based on the screenshot of the page, I give a text description and you give its "
    "corresponding location. The coordinate represents a clickable location [x, y] for "
    "an element, which is a relative coordinate on the screenshot, scaled from 0 to 1."
)


class UITarsGroundingTool(Tool):
    """Localise un élément UI dans un screenshot avec UI-TARS-2B-SFT.
    
    Utilise le modèle spécialisé GUI grounding UI-TARS-2B-SFT via Ollama local.
    Retourne les coordonnées pixel absolues (x, y) pour pyautogui.
    """

    name = "ui_grounding"
    description = (
        "Localise un élément d'interface utilisateur dans un screenshot et retourne "
        "ses coordonnées pixel absolues (x, y) pour cliquer dessus avec pyautogui. "
        "Utilise UI-TARS-2B-SFT, modèle spécialisé GUI grounding. "
        "Exemple: ui_grounding(image_path='C:/tmp/screen.png', element='bouton OK') "
        "→ retourne '{\"x\": 960, \"y\": 540, \"found\": true}'"
    )
    inputs = {
        "image_path": {
            "type": "string",
            "description": "Chemin absolu vers le screenshot PNG à analyser",
        },
        "element": {
            "type": "string",
            "description": "Description textuelle de l'élément à localiser (ex: 'bouton OK', 'champ de recherche', 'menu Fichier')",
        },
    }
    output_type = "string"

    def forward(self, image_path: str, element: str) -> str:
        """
        Localise un élément UI dans le screenshot.

        Args:
            image_path: Chemin absolu vers le screenshot
            element: Description de l'élément à localiser

        Returns:
            JSON string: {"x": int, "y": int, "found": bool, "rel_x": float, "rel_y": float}
            ou "ERROR: ..." en cas d'échec
        """
        import requests
        from PIL import Image

        try:
            # Vérifier que le fichier existe
            if not Path(image_path).exists():
                return f"ERROR: Screenshot non trouvé: {image_path}"

            # Obtenir les dimensions de l'image pour conversion coordonnées relatives → absolues
            with Image.open(image_path) as img:
                screen_width, screen_height = img.size

            logger.info(f"UI-TARS grounding: '{element}' dans {image_path} ({screen_width}x{screen_height})")

            # Encoder l'image en base64
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            # Appel Ollama avec UI-TARS-2B-SFT
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            response = requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": "hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M",
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{_GROUNDING_SYSTEM}\n\n{element}",
                            "images": [image_b64],
                        }
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.0,  # Déterministe pour le grounding
                        "num_ctx": 4096,
                    },
                },
                timeout=60,  # UI-TARS-2B est rapide
            )
            response.raise_for_status()

            raw_output = response.json().get("message", {}).get("content", "").strip()
            logger.info(f"UI-TARS output brut: {raw_output}")

            # Parser les coordonnées relatives [x, y] retournées par UI-TARS
            coords = self._parse_coordinates(raw_output)
            if coords is None:
                return json.dumps({
                    "found": False,
                    "error": f"Impossible de parser les coordonnées depuis: {raw_output}",
                    "raw": raw_output,
                })

            rel_x, rel_y = coords

            # Convertir en coordonnées absolues pixel
            abs_x = int(rel_x * screen_width)
            abs_y = int(rel_y * screen_height)

            logger.info(f"Élément '{element}' trouvé: rel=({rel_x:.3f}, {rel_y:.3f}) → abs=({abs_x}, {abs_y})")

            return json.dumps({
                "found": True,
                "x": abs_x,
                "y": abs_y,
                "rel_x": round(rel_x, 4),
                "rel_y": round(rel_y, 4),
                "screen_size": f"{screen_width}x{screen_height}",
                "element": element,
            })

        except requests.Timeout:
            return "ERROR: Timeout UI-TARS (>60s) — modèle peut-être non chargé"
        except requests.RequestException as e:
            return f"ERROR: Ollama non accessible: {e}"
        except Exception as e:
            logger.error(f"Erreur UITarsGroundingTool: {e}", exc_info=True)
            return f"ERROR: {type(e).__name__}: {e}"

    def _parse_coordinates(self, text: str) -> Optional[tuple[float, float]]:
        """Parse les coordonnées relatives [x, y] depuis la réponse UI-TARS."""
        # UI-TARS retourne typiquement: [0.73, 0.21]
        # Parfois avec du texte autour
        patterns = [
            r'\[(\d+\.?\d*),\s*(\d+\.?\d*)\]',   # [0.73, 0.21]
            r'\((\d+\.?\d*),\s*(\d+\.?\d*)\)',   # (0.73, 0.21)
            r'(\d+\.?\d*),\s*(\d+\.?\d*)',         # 0.73, 0.21
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                x, y = float(match.group(1)), float(match.group(2))
                # Valider que les coordonnées sont dans [0, 1]
                if 0 <= x <= 1 and 0 <= y <= 1:
                    return x, y
        return None
```

---

## ÉTAPE 1 — Créer UITarsGroundingTool (TOOL-11)

**Fichier à créer** : `agent/tools/ui_tars_grounding.py`
**Contenu** : voir section NOUVEAU TOOL ci-dessus

**Modifications `agent/tools/__init__.py`** :
```python
from .ui_tars_grounding import UITarsGroundingTool

TOOLS = [
    FileSystemTool(),
    OsExecTool(),
    ClipboardTool(),
    ScreenshotTool(),
    MouseKeyboardTool(),
    VisionTool(),
    UITarsGroundingTool(),  # ← AJOUTER ICI
]
```

**Dépendances** : Pillow déjà présente, requests déjà présente. Rien à ajouter.

**Prérequis Ollama** :
```bash
ollama pull hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M
```

### Checkpoint ÉTAPE 1
Test dans Gradio avec modèle `smart` (qwen3:8b) :
1. "Prends un screenshot, puis localise le bouton Démarrer de Windows"
   → Attendu : JSON avec coordonnées pixel proches du coin bas-gauche
2. "Prends un screenshot du bureau, localise l'icône de la corbeille"
   → Attendu : JSON {"found": true, "x": ..., "y": ..., "rel_x": ..., "rel_y": ...}
3. Vérifier dans les logs Ollama que `UI-TARS-2B-SFT-GGUF` est bien appelé

**Commit** : `feat(tools): tool-11 ui-tars grounding 2b`

---

## ÉTAPE 2 — Créer les sous-agents spécialisés

### 2A — Créer `agent/agents/pc_control_agent.py`

```python
"""
pc_control_agent — Agent spécialisé pilotage PC Windows.

Outils : screenshot, analyze_image (qwen3-vl:2b), ui_grounding (UI-TARS-2B), mouse_keyboard
Modèle : qwen3-vl:2b (vision native, 100% local)
Rôle : Voir l'écran, localiser les éléments, cliquer, taper
"""

import os
import logging
from smolagents import CodeAgent, LiteLLMModel, ManagedAgent

logger = logging.getLogger(__name__)

# Instructions spécifiques pc_control_agent
_PC_CONTROL_INSTRUCTIONS = """
Tu es un agent spécialisé dans le pilotage de l'interface graphique Windows.

WORKFLOW OBLIGATOIRE pour toute action :
1. screenshot() → capture l'état actuel de l'écran
2. analyze_image(image_path=..., prompt="Décris ce que tu vois") → comprendre l'écran
3. ui_grounding(image_path=..., element="description de l'élément") → obtenir coordonnées {x, y}
4. mouse_keyboard(operation="click", x=..., y=...) → cliquer avec les coordonnées absolues

RÈGLES IMPORTANTES :
- TOUJOURS prendre un screenshot avant d'agir
- TOUJOURS utiliser ui_grounding pour obtenir les coordonnées — NE JAMAIS inventer des coordonnées
- Après chaque action importante, reprendre un screenshot pour vérifier
- Si ui_grounding retourne {"found": false}, essayer une description différente de l'élément
- Pour taper du texte : d'abord cliquer sur le champ, puis mouse_keyboard(operation="type", text="...")
- Pour ouvrir une app : mouse_keyboard(operation="hotkey", keys="win"), puis type le nom, puis Enter

EXEMPLES DE GROUNDING :
- ui_grounding(image_path=screenshot_path, element="bouton OK")
- ui_grounding(image_path=screenshot_path, element="champ de recherche Windows")  
- ui_grounding(image_path=screenshot_path, element="barre des tâches bouton Démarrer")
- ui_grounding(image_path=screenshot_path, element="zone de texte Notepad")
"""


def create_pc_control_agent(ollama_url: str) -> tuple[CodeAgent, ManagedAgent]:
    """
    Crée le sous-agent de pilotage PC avec vision + UI-TARS grounding.
    
    Returns:
        Tuple (agent, managed_agent) pour utilisation dans le manager
    """
    from tools import TOOLS

    # Filtrer uniquement les tools pertinents pour le pilotage PC
    pc_tools_names = {"screenshot", "analyze_image", "ui_grounding", "mouse_keyboard"}
    pc_tools = [t for t in TOOLS if t.name in pc_tools_names]

    if not pc_tools:
        raise RuntimeError(f"Aucun outil PC trouvé. Outils disponibles: {[t.name for t in TOOLS]}")

    logger.info(f"pc_control_agent tools: {[t.name for t in pc_tools]}")

    # Modèle : qwen3-vl:2b (vision native, 100% local, déjà installé et validé)
    model = LiteLLMModel(
        model_id="ollama_chat/qwen3-vl:2b",
        api_base=ollama_url,
        api_key="ollama",
        num_ctx=8192,          # Plus de contexte pour screenshots encodés en base64
        extra_body={"think": False},
    )

    agent = CodeAgent(
        tools=pc_tools,
        model=model,
        max_steps=15,           # Plus d'étapes car workflow screenshot→vision→grounding→action
        verbosity_level=1,
        additional_authorized_imports=["json", "re", "time", "os"],
        executor_kwargs={"timeout_seconds": 300},
        instructions=_PC_CONTROL_INSTRUCTIONS,
    )

    managed = ManagedAgent(
        agent=agent,
        name="pc_control",
        description=(
            "Agent spécialisé pour piloter l'interface graphique Windows. "
            "Peut voir l'écran (screenshot), comprendre l'interface (vision IA), "
            "localiser précisément les éléments UI (UI-TARS grounding), "
            "et interagir avec la souris et le clavier. "
            "Utilise-le pour : ouvrir des applications, cliquer sur des boutons, "
            "remplir des formulaires, naviguer dans Windows."
        ),
    )

    return agent, managed
```

### 2B — Créer `agent/agents/browser_agent.py`

```python
"""
browser_agent — Agent spécialisé pilotage Chrome via DevTools MCP.

Outils : 26 tools Chrome DevTools MCP (navigation, click, fill, screenshot, snapshot...)
Modèle : qwen3:8b (local, 0 quota)
Rôle : Naviguer sur le web, remplir des formulaires, extraire du contenu
"""

import os
import logging
from contextlib import contextmanager
from smolagents import CodeAgent, LiteLLMModel, ManagedAgent, ToolCollection
from mcp import StdioServerParameters

logger = logging.getLogger(__name__)

_BROWSER_INSTRUCTIONS = """
Tu es un agent spécialisé dans l'automatisation de Chrome via Chrome DevTools MCP.

WORKFLOW RECOMMANDÉ :
1. navigate_page(url=...) → naviguer vers une URL
2. take_snapshot() → obtenir la structure de la page avec les uid des éléments
3. click(uid=...) ou fill(uid=..., value=...) → interagir avec les éléments
4. wait_for(text=...) → attendre le chargement si nécessaire

BONNES PRATIQUES :
- Toujours take_snapshot() avant d'interagir pour connaître les uid
- Préférer take_snapshot() à take_screenshot() (plus rapide, uid exploitables)
- Utiliser wait_for() après une navigation si la page charge lentement
- Pour les recherches web : éviter Google (CAPTCHA), préférer DuckDuckGo ou Bing
- Utiliser evaluate_script() pour extraire du contenu dynamique
- Toujours retourner un résumé clair de ce qui a été fait ou trouvé
"""


def create_browser_managed_agent(
    ollama_url: str,
    mcp_tools: list,
) -> ManagedAgent:
    """
    Crée le sous-agent browser avec les tools Chrome DevTools MCP déjà chargés.
    
    Args:
        ollama_url: URL du serveur Ollama
        mcp_tools: Liste des tools MCP déjà initialisés (depuis lifespan)
    
    Returns:
        ManagedAgent wrappant le browser agent
    """
    if not mcp_tools:
        logger.warning("browser_agent: aucun tool MCP Chrome DevTools disponible")

    # Modèle : qwen3:8b local (0 quota, bon pour navigation structurée)
    model = LiteLLMModel(
        model_id="ollama_chat/qwen3:8b",
        api_base=ollama_url,
        api_key="ollama",
        num_ctx=32768,
        extra_body={"think": False},
    )

    agent = CodeAgent(
        tools=mcp_tools,
        model=model,
        max_steps=12,
        verbosity_level=1,
        additional_authorized_imports=["json", "re", "time"],
        executor_kwargs={"timeout_seconds": 240},
        instructions=_BROWSER_INSTRUCTIONS,
    )

    managed = ManagedAgent(
        agent=agent,
        name="browser",
        description=(
            "Agent spécialisé dans l'automatisation de Chrome. "
            "Peut naviguer vers des URLs, prendre des snapshots de pages web, "
            "cliquer sur des éléments, remplir des formulaires, exécuter du JavaScript, "
            "et extraire du contenu de pages web. "
            "Utilise-le pour : visiter des sites, faire des recherches web, "
            "remplir des formulaires en ligne, extraire des données de pages web."
        ),
    )

    return managed
```

### 2C — Créer `agent/agents/web_agent.py`

```python
"""
web_agent — Agent spécialisé recherche et lecture web via MCP Z.ai.

Outils : webSearchPrime, webReader, zread (chargés dynamiquement si ZAI_API_KEY)
Modèle : qwen3:8b (local, 0 quota pour le LLM)
Rôle : Recherche web temps réel, lecture d'articles, exploration de repos GitHub
"""

import logging
from smolagents import CodeAgent, LiteLLMModel, ManagedAgent

logger = logging.getLogger(__name__)

_WEB_INSTRUCTIONS = """
Tu es un agent spécialisé dans la recherche et la lecture de contenu web.

OUTILS DISPONIBLES (si configurés) :
- webSearchPrime(search_query="...", search_recency_filter="oneWeek") → recherche web temps réel
- webReader(url="...") → lire le contenu complet d'une page web
- search_doc / get_repo_structure / read_file → explorer des repos GitHub publics

BONNES PRATIQUES :
- Garder les requêtes de recherche courtes et précises (max 70 caractères)
- Utiliser search_recency_filter="oneWeek" pour les actualités récentes
- Utiliser search_domain_filter="huggingface.co" pour cibler un site précis
- Résumer les résultats de manière concise et structurée
- Si aucun tool Z.ai n'est disponible (pas de ZAI_API_KEY), le signaler clairement

QUOTA : 100 calls/mois partagés entre recherche, lecture et GitHub. Utiliser avec parcimonie.
"""


def create_web_managed_agent(
    ollama_url: str,
    web_search_tools: list,
) -> ManagedAgent | None:
    """
    Crée le sous-agent web avec les tools MCP Z.ai déjà chargés.
    Retourne None si aucun tool web n'est disponible.
    
    Args:
        ollama_url: URL du serveur Ollama
        web_search_tools: Liste des tools MCP Z.ai (peut être vide)
    
    Returns:
        ManagedAgent ou None si pas de tools disponibles
    """
    if not web_search_tools:
        logger.warning("web_agent: aucun tool web MCP disponible (ZAI_API_KEY manquant?)")
        return None

    model = LiteLLMModel(
        model_id="ollama_chat/qwen3:8b",
        api_base=ollama_url,
        api_key="ollama",
        num_ctx=32768,
        extra_body={"think": False},
    )

    agent = CodeAgent(
        tools=web_search_tools,
        model=model,
        max_steps=8,
        verbosity_level=1,
        additional_authorized_imports=["json", "re"],
        executor_kwargs={"timeout_seconds": 120},
        instructions=_WEB_INSTRUCTIONS,
    )

    managed = ManagedAgent(
        agent=agent,
        name="web_search",
        description=(
            "Agent spécialisé dans la recherche web et la lecture de contenu en ligne. "
            "Peut effectuer des recherches web en temps réel, lire des articles et pages web, "
            "et explorer des repositories GitHub publics. "
            "Utilise-le pour : trouver des informations récentes, lire la documentation, "
            "explorer du code source sur GitHub."
        ),
    )

    return managed
```

### 2D — Créer `agent/agents/__init__.py`

```python
"""Agents package — sous-agents spécialisés pour my-claw."""
```

### Checkpoint ÉTAPE 2
Vérifier que les fichiers sont créés sans erreur d'import :
```bash
cd agent
uv run python -c "from agents.pc_control_agent import create_pc_control_agent; print('OK')"
uv run python -c "from agents.browser_agent import create_browser_managed_agent; print('OK')"
uv run python -c "from agents.web_agent import create_web_managed_agent; print('OK')"
```

**Commit** : `refactor(agents): structure multi-agent — créer sous-agents spécialisés`

---

## ÉTAPE 3 — Refondre main.py

C'est la modification centrale. Remplacer le CodeAgent monolithique par le Manager + sous-agents.

### main.py complet (remplacement total)

```python
import os
import logging
import re
import requests
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from smolagents import CodeAgent, LiteLLMModel, ManagedAgent, ToolCollection
from mcp import StdioServerParameters
from dotenv import load_dotenv
from tools import TOOLS

load_dotenv()

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)
logging.getLogger("smolagents").setLevel(logging.DEBUG)
logging.getLogger("LiteLLM").setLevel(logging.INFO)


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


# ─── Détection modèles Ollama ────────────────────────────────────────────────
MODEL_PREFERENCES: dict[str, list[str]] = {
    "fast":   ["gemma3:latest", "qwen3:4b", "gemma3n:latest"],
    "smart":  ["qwen3:8b", "qwen3:4b", "gemma3n:latest", "gemma3:latest"],
    "main":   ["qwen3:8b", "qwen3:4b", "gemma3n:latest", "gemma3:latest"],
    "vision": ["qwen3-vl:2b", "qwen3-vl:4b", "llama3.2-vision"],
}

CLOUD_MODELS: dict[str, tuple[str, str]] = {
    "code":   ("openai/glm-4.7-flash", os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")),
    "reason": ("openai/glm-4.7",       os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")),
}

_detected_models: dict[str, tuple[str, str]] | None = None


def get_ollama_models() -> list[str]:
    try:
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        return [m["name"] for m in response.json().get("models", [])]
    except Exception as e:
        logger.warning(f"Ollama non accessible: {e}")
        return []


def detect_models() -> dict[str, tuple[str, str]]:
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

    # Vérifier présence UI-TARS pour pc_control_agent
    uitars_model = "hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M"
    if uitars_model in available:
        logger.info(f"✓ UI-TARS-2B-SFT détecté pour pc_control_agent")
    else:
        logger.warning(f"✗ UI-TARS-2B-SFT non trouvé — installer avec: ollama pull {uitars_model}")

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


# ─── MCP Chrome DevTools — état global lifespan ──────────────────────────────
_chrome_mcp_context: ToolCollection | None = None
_chrome_mcp_tools: list = []

# MCP Z.ai (web search, web reader, zread) — chargés dans lifespan
_web_search_context: ToolCollection | None = None
_web_search_tools: list = []


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

    # ── Web Search MCP Z.ai (TOOL-4) ─────────────────────────────────────────
    # IMPORTANT : décommenter quand ZAI_API_KEY configuré et TOOL-4 implémenté
    # logger.info("Initialisation Web Search MCP Z.ai...")
    # try:
    #     if os.environ.get("ZAI_API_KEY"):
    #         web_search_params = {
    #             "url": "https://api.z.ai/api/mcp/web_search_prime/mcp",
    #             "type": "streamable-http",
    #             "headers": {"Authorization": f"Bearer {os.environ['ZAI_API_KEY']}"}
    #         }
    #         _web_search_context = ToolCollection.from_mcp(web_search_params, trust_remote_code=True)
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
def build_multi_agent_system(model_id: str = "main") -> CodeAgent:
    """
    Construit le système Manager + sous-agents selon les tools disponibles.
    
    Architecture :
    - Manager : glm-4.7 ou qwen3:8b + tools directs (file_system, os_exec, clipboard)
    - pc_control : qwen3-vl:2b + screenshot, analyze_image, ui_grounding, mouse_keyboard
    - browser : qwen3:8b + Chrome DevTools MCP (si disponible)
    - web_search : qwen3:8b + MCP Z.ai (si ZAI_API_KEY configuré)
    """
    from agents.pc_control_agent import create_pc_control_agent
    from agents.browser_agent import create_browser_managed_agent
    from agents.web_agent import create_web_managed_agent

    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    managed_agents = []

    # ── Sous-agent pilotage PC ────────────────────────────────────────────────
    try:
        _, managed_pc = create_pc_control_agent(ollama_url)
        managed_agents.append(managed_pc)
        logger.info("✓ pc_control_agent créé (screenshot + vision + UI-TARS + mouse/keyboard)")
    except Exception as e:
        logger.warning(f"✗ pc_control_agent non disponible: {e}")

    # ── Sous-agent browser Chrome ─────────────────────────────────────────────
    if _chrome_mcp_tools:
        try:
            managed_browser = create_browser_managed_agent(ollama_url, _chrome_mcp_tools)
            managed_agents.append(managed_browser)
            logger.info(f"✓ browser_agent créé ({len(_chrome_mcp_tools)} tools Chrome DevTools)")
        except Exception as e:
            logger.warning(f"✗ browser_agent non disponible: {e}")
    else:
        logger.warning("✗ browser_agent ignoré (Chrome DevTools MCP non disponible)")

    # ── Sous-agent web search Z.ai ────────────────────────────────────────────
    if _web_search_tools:
        try:
            managed_web = create_web_managed_agent(ollama_url, _web_search_tools)
            if managed_web:
                managed_agents.append(managed_web)
                logger.info(f"✓ web_agent créé ({len(_web_search_tools)} tools Z.ai)")
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


# ─── Helpers ─────────────────────────────────────────────────────────────────
def build_prompt_with_history(message: str, history: list[dict]) -> str:
    if not history:
        return message
    lines = [
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in history[-10:]
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
        agent = build_multi_agent_system(req.model)
        prompt = build_prompt_with_history(req.message, req.history)
        result = agent.run(prompt)
        return {"response": str(result)}
    except Exception as e:
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
            "pc_control": "qwen3-vl:2b + UI-TARS-2B-SFT",
            "browser": f"qwen3:8b + {len(_chrome_mcp_tools)} tools Chrome DevTools",
            "web_search": f"qwen3:8b + {len(_web_search_tools)} tools Z.ai MCP",
        },
    }
```

### Checkpoint ÉTAPE 3
```bash
cd agent
uv run uvicorn main:app --reload
```
Vérifier dans les logs :
```
✓ Chrome DevTools MCP: 26 outils
✓ pc_control_agent créé (screenshot + vision + UI-TARS + mouse/keyboard)
✓ browser_agent créé (26 tools Chrome DevTools)
```

Test basique via curl :
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"message": "Liste les fichiers dans C:/tmp", "model": "smart"}'
```

**Commit** : `refactor(main): migration architecture multi-agent manager + sous-agents`

---

## ÉTAPE 4 — Mettre à jour gradio_app.py (Gradio 6.6.0)

### Changements Gradio 6 vs 5
- `gr.ChatInterface` : paramètre `type="messages"` devient obligatoire en Gradio 6
- Historique : toujours format `list[dict]` avec `role`/`content`
- Nouveau : `gr.ChatInterface` accepte `additional_inputs_accordion` pour mieux organiser

### gradio_app.py mis à jour (Gradio 6.6.0)

```python
"""
Gradio 6.6.0 — Interface de développement my-claw multi-agent.
Compatible Gradio 6.x (type="messages" obligatoire).
"""

import gradio as gr
import requests
import os
from dotenv import load_dotenv

load_dotenv()

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8000")


def get_available_models() -> list[str]:
    """Récupère les modèles disponibles depuis l'agent."""
    try:
        resp = requests.get(f"{AGENT_URL}/models", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = list(data.get("models", {}).keys())
        return models if models else ["fast", "smart", "main", "vision", "code", "reason"]
    except Exception:
        return ["fast", "smart", "main", "vision", "code", "reason"]


def chat(
    message: str,
    history: list[dict],  # Gradio 6 : toujours list[dict] avec type="messages"
    model_choice: str,
) -> str:
    """
    Fonction de chat compatible Gradio 6.6.0.
    history est déjà au format list[dict] avec type="messages".
    """
    # Convertir l'historique Gradio 6 au format attendu par l'API
    history_dicts = []
    for m in history:
        if isinstance(m, dict) and "role" in m and "content" in m:
            history_dicts.append({"role": m["role"], "content": str(m["content"])})

    try:
        resp = requests.post(
            f"{AGENT_URL}/run",
            json={"message": message, "history": history_dicts, "model": model_choice},
            timeout=360,  # 6 minutes pour les tâches complexes multi-agent
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except requests.Timeout:
        return "⏱️ Timeout (6min) — tâche trop longue ou modèle surchargé."
    except requests.ConnectionError:
        return "❌ Agent non accessible sur http://localhost:8000 — démarrer l'agent d'abord."
    except Exception as e:
        return f"❌ Erreur: {e}"


def get_agent_status() -> str:
    """Vérifie le statut de l'agent et des sous-agents."""
    try:
        resp = requests.get(f"{AGENT_URL}/health", timeout=3)
        data = resp.json()
        chrome = data.get("chrome_mcp", 0)
        web = data.get("web_mcp", 0)
        return (
            f"✅ Agent en ligne | "
            f"Chrome DevTools: {chrome} tools | "
            f"Web MCP: {web} tools"
        )
    except Exception:
        return "❌ Agent hors ligne — démarrer: `uv run uvicorn main:app --reload`"


# ── Interface Gradio 6.6.0 ───────────────────────────────────────────────────
AVAILABLE_MODELS = get_available_models()

with gr.Blocks(title="my-claw — Dev Interface") as demo:
    gr.Markdown("# 🦞 my-claw — Interface de développement")
    gr.Markdown("Architecture multi-agent : Manager → pc_control | browser | web_search")

    with gr.Row():
        status_box = gr.Textbox(
            label="Statut agent",
            value=get_agent_status(),
            interactive=False,
            scale=4,
        )
        refresh_btn = gr.Button("🔄 Rafraîchir", scale=1)

    refresh_btn.click(fn=get_agent_status, outputs=status_box)

    with gr.Row():
        model_dropdown = gr.Dropdown(
            choices=AVAILABLE_MODELS,
            value="smart" if "smart" in AVAILABLE_MODELS else AVAILABLE_MODELS[0],
            label="Modèle Manager",
            info="Le manager délègue aux sous-agents selon la tâche",
            scale=2,
        )

    # ChatInterface Gradio 6.6.0 — type="messages" obligatoire
    chat_interface = gr.ChatInterface(
        fn=chat,
        type="messages",          # ← OBLIGATOIRE en Gradio 6
        additional_inputs=[model_dropdown],
        examples=[
            ["Liste les fichiers dans C:/tmp"],
            ["Prends un screenshot et décris ce que tu vois"],
            ["Ouvre Chrome sur https://example.com et prends un snapshot"],
            ["Ouvre Notepad et tape 'Bonjour depuis my-claw !'"],
            ["Prends un screenshot, localise le bouton Démarrer, et clique dessus"],
        ],
        title=None,               # Titre géré par le Blocks parent
    )


if __name__ == "__main__":
    demo.launch(server_port=7860, share=False)
```

### Checkpoint ÉTAPE 4
```bash
cd agent
uv run python gradio_app.py
```
- Ouvrir http://localhost:7860
- Vérifier que le statut agent s'affiche correctement
- Tester un message simple ("Liste les fichiers dans C:/tmp")
- Vérifier que l'historique fonctionne sur plusieurs tours

**Commit** : `feat(gradio): migration gradio 6.6.0 + interface multi-agent`

---

## ÉTAPE 5 — Mettre à jour pyproject.toml

```toml
[project]
name = "my-claw-agent"
version = "0.2.0"
description = "my-claw — Agent Python smolagents multi-agent"
requires-python = ">=3.11"

dependencies = [
    "smolagents[litellm,mcp]>=1.9.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "requests>=2.32.0",
    "httpx>=0.27.0",
    "gradio>=6.6.0",          # ← Mis à jour depuis 5.x
    "python-dotenv>=1.0.0",
    "pyperclip>=1.11.0",
    "pyautogui>=0.9.54",
    "pillow>=12.1.1",
    "mcp>=0.9.0",
    "mcpadapt>=0.1.19",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.8.0",
    "pyright>=1.1.0",
]
```

Mise à jour dépendances :
```bash
cd agent
uv add "gradio>=6.6.0"
uv sync
```

**Commit** : `chore(deps): gradio 6.6.0 + version 0.2.0`

---

## ÉTAPE 6 — Tests de validation end-to-end

### 6A — Test Manager seul (tools directs)
Prompt : "Crée le fichier C:/tmp/migration_test.txt avec le contenu 'Multi-agent OK'"
Attendu : Le manager utilise file_system directement, sans déléguer

### 6B — Test délégation pc_control
Prompt : "Prends un screenshot de l'écran et décris ce que tu vois"
Attendu dans les logs :
```
Manager → délègue à pc_control_agent
pc_control_agent → screenshot() → analyze_image() → final_answer(description)
```

### 6C — Test délégation browser
Prompt : "Ouvre https://example.com dans Chrome et donne-moi le titre de la page"
Attendu :
```
Manager → délègue à browser_agent
browser_agent → navigate_page() → take_snapshot() → final_answer(titre)
```

### 6D — Test pilotage PC avec UI-TARS
Prompt : "Prends un screenshot, trouve le bouton Démarrer Windows et donne ses coordonnées"
Attendu :
```
pc_control_agent → screenshot() → ui_grounding(element="bouton Démarrer") 
→ {"found": true, "x": 15, "y": 1065, ...}
```

### 6E — Test tâche complète multi-agent
Prompt : "Ouvre Notepad via le menu Démarrer et tape 'Test migration multi-agent OK'"
Attendu : pc_control_agent orchestre screenshot → ui_grounding → mouse_keyboard en séquence

**Commit** : `test(multi-agent): validation end-to-end tous sous-agents`

---

## ÉTAPE 7 — Mettre à jour PROGRESS.md et LEARNING.md

### Sections à mettre à jour dans PROGRESS.md

Remplacer la section "MODULE TOOLS" par :

```markdown
## ARCHITECTURE MULTI-AGENT — DONE

Migration vers architecture Manager + 3 sous-agents spécialisés (2026-02-21)

Manager (glm-4.7 / qwen3:8b) → tools directs : file_system, os_exec, clipboard
├── pc_control_agent (qwen3-vl:2b) → screenshot, analyze_image, ui_grounding, mouse_keyboard
├── browser_agent (qwen3:8b) → 26 tools Chrome DevTools MCP
└── web_agent (qwen3:8b) → webSearchPrime, webReader, zread (activer avec ZAI_API_KEY)

## TOOL-11 — UITarsGroundingTool
**Statut : DONE**
- Modèle : hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M (~1.6GB)
- Retourne coordonnées absolues pixel depuis description textuelle + screenshot
- Intégré dans pc_control_agent
```

### Section à ajouter dans LEARNING.md

```markdown
## Architecture Multi-Agent — Migration (2026-02-21)

### Décisions architecture
- ManagedAgent smolagents : wrapping agent → callable comme tool par le manager
- pc_control_agent utilise qwen3-vl:2b (vision native) au lieu de qwen3:8b
- browser_agent : qwen3:8b suffit (pas besoin de vision, snapshot = texte)
- web_agent : créé vide si pas de ZAI_API_KEY, retourne None proprement

### UI-TARS-2B-SFT coordonnées
- Retourne [rel_x, rel_y] dans [0..1]
- Conversion : abs_x = int(rel_x * screen_width)
- temperature=0.0 obligatoire pour grounding déterministe
- Modèle : hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M via Ollama

### Gradio 6.6.0 breaking changes
- type="messages" obligatoire dans gr.ChatInterface (Gradio 6)
- history format : list[dict] avec "role" et "content" (toujours en Gradio 6)
- gr.Blocks + gr.ChatInterface ensemble : title=None dans ChatInterface
```

**Commit** : `docs: mise à jour PROGRESS.md et LEARNING.md migration multi-agent`

---

## RÉCAPITULATIF ORDRE D'IMPLÉMENTATION

```
ÉTAPE 1  UITarsGroundingTool (TOOL-11)         ← Créer tools/ui_tars_grounding.py
ÉTAPE 2  Sous-agents spécialisés               ← Créer agents/ package (3 fichiers)
ÉTAPE 3  Refonte main.py                        ← Manager + ManagedAgents
ÉTAPE 4  Mise à jour gradio_app.py              ← Gradio 6.6.0
ÉTAPE 5  Mise à jour pyproject.toml             ← gradio>=6.6.0
ÉTAPE 6  Tests end-to-end (6A→6E)              ← Valider chaque délégation
ÉTAPE 7  Mise à jour PROGRESS.md + LEARNING.md ← Documentation
──────────────────────────────────────────────────────
→ CHECKPOINT FINAL validé → passer TOOL-4 (MCP Web Search Z.ai)
```

---

## STRUCTURE REPO APRÈS MIGRATION

```
agent/
├── main.py                    ← Manager + lifespan MCP + endpoints
├── gradio_app.py              ← Gradio 6.6.0
├── skills.txt                 ← Skills partagés (manager + sous-agents)
├── pyproject.toml             ← gradio>=6.6.0, version 0.2.0
├── agents/
│   ├── __init__.py
│   ├── pc_control_agent.py    ← qwen3-vl:2b + screenshot/vision/ui_tars/mouse
│   ├── browser_agent.py       ← qwen3:8b + Chrome DevTools MCP
│   └── web_agent.py           ← qwen3:8b + MCP Z.ai (TOOL-4/5/6)
└── tools/
    ├── __init__.py            ← TOOLS = [7 outils dont UITarsGroundingTool]
    ├── file_system.py
    ├── os_exec.py
    ├── clipboard.py
    ├── vision.py
    ├── screenshot.py
    ├── mouse_keyboard.py
    └── ui_tars_grounding.py   ← NOUVEAU TOOL-11
```

---

## PRÉREQUIS AVANT DE COMMENCER

```bash
# 1. Installer UI-TARS-2B-SFT via Ollama
ollama pull hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M

# 2. Vérifier que qwen3-vl:2b est bien installé
ollama list | grep qwen3-vl

# 3. Vérifier que qwen3:8b est installé (pour browser_agent et web_agent)
ollama list | grep qwen3:8b

# 4. Mettre à jour gradio
cd agent && uv add "gradio>=6.6.0"
```

---

## VARIABLES ENV — AUCUN CHANGEMENT REQUIS

Les variables existantes dans agent/.env suffisent :
```env
OLLAMA_BASE_URL=http://localhost:11434
ZAI_API_KEY=ton_token_zai          # Optionnel — active web_agent si présent
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
SCREENSHOT_DIR=C:\tmp\myclawshots
```

---

## NOTES IMPORTANTES POUR L'IA DE CODAGE

1. **Ordre strict** : respecter ÉTAPE 1 → 2 → 3 → 4 → 5 → 6 → 7
2. **Un checkpoint validé avant de passer à l'étape suivante**
3. **Ne pas modifier** TOOL-1, TOOL-2, TOOL-3, TOOL-7, TOOL-8 — ils sont validés
4. **TOOL-9 (mouse_keyboard)** reste en cours — intégré dans pc_control_agent mais validation end-to-end à faire en ÉTAPE 6E
5. **web_agent** crée un ManagedAgent `None` si pas de tools — gérer ce cas dans build_multi_agent_system
6. **GLM-4.7 stop sequences** : maintenir `CleanedLiteLLMModel` pour les modèles cloud
7. **Gradio 6.6.0** : `type="messages"` est obligatoire — sinon TypeError au runtime
8. **UI-TARS coordonnées** : toujours vérifier que rel_x et rel_y sont dans [0..1] avant conversion — rejeter si hors bornes
9. **qwen3:8b** : vérifier qu'il est bien installé avant de créer browser_agent et web_agent
