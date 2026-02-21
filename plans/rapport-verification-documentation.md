# Rapport de Vérification de Documentation Technique
> my-claw - Analyse des divergences entre code et documentation
> Date : 2026-02-21
> Analyse basée sur : Code source actuel vs Documentation Markdown (.md)

---

## Résumé Exécutif

| Catégorie | Statut | Divergences trouvées |
|-----------|---------|---------------------|
| Architecture Multi-Agent | ⚠️ PARTIEL | 4 divergences majeures |
| Outils smolagents | ⚠️ PARTIEL | 3 divergences majeures |
| Modèles LLM | ⚠️ PARTIEL | 2 divergences majeures |
| Documentation fichiers | ✅ OK | Pas de divergence majeure |
| Gateway/API | ✅ OK | Pas de divergence majeure |

**Total** : **9 divergences majeures** identifiées nécessitant une mise à jour de la documentation.

---

## Divergence #1 : Module `agent/models.py` non documenté

### Fichier concerné
- [`agent/models.py`](agent/models.py) (176 lignes)

### Description
Un nouveau module centralisé `agent/models.py` a été créé pour gérer la création et la configuration des modèles LLM. Ce module évite les imports circulaires et centralise la logique de détection des modèles.

### Fonctionnalités implémentées
- `get_model(model_id)` : Crée un LiteLLMModel configuré correctement
- `get_default_model()` : Retourne le modèle par défaut selon les priorités
- `detect_models()` : Détection automatique des modèles Ollama installés
- `MODELS` : Dictionnaire des modèles disponibles (Ollama + cloud)
- `get_ollama_models()` : Récupère la liste des modèles Ollama
- `CleanedLiteLLMModel` : Wrapper qui nettoie les balises parasites de GLM-4.7
- `clean_glm_response()` : Fonction de nettoyage des balises `</code`

### Documentation manquante
**Fichiers à mettre à jour :**
- [`AGENTS.md`](AGENTS.md) - Section "MODÈLES LLM" ne mentionne pas le module `models.py`
- [`LEARNING.md`](LEARNING.md) - Section "Correction modèle 'reason' pour les sous-agents" mentionne le module mais pas dans la section principale

**Contenu à ajouter dans AGENTS.md :**

```markdown
## GESTION DES MODÈLES — Module agent/models.py

Le module [`agent/models.py`](agent/models.py) centralise la création et la configuration des modèles LLM pour éviter les imports circulaires et la duplication de code.

### Fonctions principales

#### get_model(model_id: str = "main") -> LiteLLMModel
Crée un modèle LiteLLMModel correctement configuré selon l'identifiant fourni.

**Priorités de sélection :**
1. Modèle spécifié par `model_id`
2. Fallback sur "main" si modèle non trouvé
3. Premier modèle disponible si "main" non trouvé
4. Exception si aucun modèle disponible

**Comportement :**
- Modèles cloud (glm-4.7, glm-4.7-flash) : Utilise `CleanedLiteLLMModel` avec API Z.ai
- Modèles locaux (qwen3:*, gemma3:*) : Utilise `LiteLLMModel` standard avec Ollama

#### get_default_model() -> str
Retourne le modèle par défaut selon les priorités :
1. Variable d'environnement `DEFAULT_MODEL`
2. "reason" (glm-4.7) si `ZAI_API_KEY` configuré
3. "main" (qwen3:8b) en fallback local

#### detect_models() -> dict[str, tuple[str, str]]
Détecte automatiquement les modèles disponibles (Ollama + cloud).

**Préférences par catégorie :**
```python
MODEL_PREFERENCES = {
    "fast":   ["gemma3:latest", "qwen3:4b", "gemma3n:latest"],
    "smart":  ["qwen3:8b", "qwen3:4b", "gemma3n:latest", "gemma3:latest"],
    "main":   ["qwen3:8b", "qwen3:4b", "gemma3n:latest", "gemma3:latest"],
    "vision": ["qwen3-vl:8b", "qwen3-vl:2b", "qwen3-vl:4b", "llama3.2-vision"],
}
```

### CleanedLiteLLMModel

Wrapper spécial pour les modèles GLM-4.7 qui nettoie automatiquement les balises parasites générées par ces modèles.

**Balises nettoyées :**
- `</code>` (avec `>`)
- `</code` (sans `>`)
- `</s>`

**Exemple d'utilisation :**
```python
from models import get_model

# Pour GLM-4.7 (cloud)
model = get_model("reason")  # Retourne CleanedLiteLLMModel

# Pour qwen3:8b (local)
model = get_model("main")  # Retourne LiteLLMModel standard
```
```

---

## Divergence #2 : Architecture Multi-Agent incomplète dans AGENTS.md

### Fichiers concernés
- [`agent/main.py`](agent/main.py) - Fonction `build_multi_agent_system()`
- [`agent/agents/pc_control_agent.py`](agent/agents/pc_control_agent.py)
- [`agent/agents/vision_agent.py`](agent/agents/vision_agent.py)
- [`agent/agents/browser_agent.py`](agent/agents/browser_agent.py)
- [`agent/agents/web_agent.py`](agent/agents/web_agent.py)

### Description
L'architecture multi-agent est implémentée avec un Manager et 4 sous-agents spécialisés, mais cette architecture n'est pas documentée dans AGENTS.md.

### Architecture implémentée

```
Manager (glm-4.7 / qwen3:8b)
├── Tools directs : file_system, os_exec, clipboard
├── pc_control_agent (glm-4.7 / qwen3:8b)
│   ├── screenshot
│   ├── ui_grounding (qwen3-vl interne)
│   └── mouse_keyboard
├── vision_agent (glm-4.7 / qwen3:8b)
│   └── analyze_image (qwen3-vl:8b interne)
├── browser_agent (glm-4.7 / qwen3:8b)
│   └── 26 outils Chrome DevTools MCP
└── web_agent (glm-4.7 / qwen3:8b)
    └── webSearchPrime, webReader, zread (si ZAI_API_KEY)
```

### Documentation manquante

**Fichier à mettre à jour :**
- [`AGENTS.md`](AGENTS.md) - Ajouter une nouvelle section "ARCHITECTURE MULTI-AGENT"

**Contenu à ajouter dans AGENTS.md :**

```markdown
## ARCHITECTURE MULTI-AGENT

Le système utilise une architecture Manager + Sous-agents spécialisés pour optimiser l'utilisation des modèles et des outils.

### Manager

**Rôle :** Orchestrateur principal qui délègue les tâches aux sous-agents appropriés.

**Modèle :** Par défaut (glm-4.7 avec ZAI_API_KEY, sinon qwen3:8b)

**Tools directs :**
- `file_system` : Opérations sur les fichiers
- `os_exec` : Exécution de commandes PowerShell
- `clipboard` : Lecture/écriture du presse-papier

**Configuration :**
```python
manager = CodeAgent(
    tools=manager_tools,
    model=get_model(model_id),
    managed_agents=managed_agents,
    max_steps=10,
    verbosity_level=2,
    additional_authorized_imports=["requests", "urllib", "json", "csv", "pathlib", "os", "subprocess"],
    executor_kwargs={"timeout_seconds": 240},
    instructions=SKILLS,
)
```

### Sous-agents

#### pc_control_agent

**Fichier :** [`agent/agents/pc_control_agent.py`](agent/agents/pc_control_agent.py)

**Rôle :** Pilotage de l'interface graphique Windows

**Outils :**
- `screenshot` : Capture d'écran
- `ui_grounding` : Localisation d'éléments UI avec qwen3-vl
- `mouse_keyboard` : Contrôle souris/clavier

**Modèle :** Par défaut (glm-4.7 ou qwen3:8b)

**Instructions spécifiques :** Workflow screenshot → grounding → action

**Configuration :**
```python
agent = CodeAgent(
    tools=pc_tools,
    model=get_model(model_id),
    max_steps=15,
    verbosity_level=1,
    additional_authorized_imports=["json", "re", "time", "os"],
    executor_kwargs={"timeout_seconds": 300},
    instructions=_PC_CONTROL_INSTRUCTIONS,
    name="pc_control",
    description="Agent spécialisé pour piloter l'interface graphique Windows...",
)
```

#### vision_agent

**Fichier :** [`agent/agents/vision_agent.py`](agent/agents/vision_agent.py)

**Rôle :** Analyse d'images avec modèle de codage

**Outils :**
- `analyze_image` : Analyse d'images (qwen3-vl:8b interne)

**Modèle :** Par défaut (glm-4.7 ou qwen3:8b) - modèle de CODAGE
**Note :** L'outil `analyze_image` utilise son propre modèle de vision (qwen3-vl:8b)

**Configuration :**
```python
agent = CodeAgent(
    tools=vision_tools,
    model=get_model(model_id),
    max_steps=5,
    verbosity_level=1,
    additional_authorized_imports=["json", "re", "time", "os"],
    executor_kwargs={"timeout_seconds": 180},
    instructions=_VISION_INSTRUCTIONS,
    name="vision",
    description="Agent spécialisé dans l'analyse d'images...",
)
```

#### browser_agent

**Fichier :** [`agent/agents/browser_agent.py`](agent/agents/browser_agent.py)

**Rôle :** Automatisation de Chrome via DevTools MCP

**Outils :** 26 outils Chrome DevTools MCP (navigation, click, fill, screenshot, snapshot...)

**Modèle :** Par défaut (glm-4.7 ou qwen3:8b)

**Configuration :**
```python
agent = CodeAgent(
    tools=mcp_tools,
    model=get_model(model_id),
    max_steps=12,
    verbosity_level=1,
    additional_authorized_imports=["json", "re", "time"],
    executor_kwargs={"timeout_seconds": 240},
    instructions=_BROWSER_INSTRUCTIONS,
    name="browser",
    description="Agent spécialisé dans l'automatisation de Chrome...",
)
```

#### web_agent

**Fichier :** [`agent/agents/web_agent.py`](agent/agents/web_agent.py)

**Rôle :** Recherche web et lecture de contenu via MCP Z.ai

**Outils :** (si ZAI_API_KEY configuré)
- `webSearchPrime` : Recherche web temps réel
- `webReader` : Lecture de pages web
- `zread` : Lecture de repos GitHub

**Modèle :** Par défaut (glm-4.7 ou qwen3:8b)

**Note :** Retourne `None` si aucun tool MCP Z.ai n'est disponible

### Délégation automatique

Le Manager délègue automatiquement les tâches aux sous-agents appropriés selon leur description et leurs outils.

**Exemples :**
- "Ouvre Notepad" → Délégué à `pc_control_agent`
- "Analyse cette image" → Délégué à `vision_agent`
- "Ouvre https://example.com" → Délégué à `browser_agent`
- "Recherche des infos sur smolagents" → Délégué à `web_agent` (si disponible)
```

---

## Divergence #3 : Tool `grounding.py` (anciennement `ui_tars_grounding.py`) renommé

### Fichiers concernés
- [`agent/tools/grounding.py`](agent/tools/grounding.py) (228 lignes)
- Ancien : `agent/tools/ui_tars_grounding.py` (supprimé)

### Description
L'outil de grounding GUI a été renommé de `ui_tars_grounding.py` à `grounding.py` et migré du modèle UI-TARS-2B-SFT vers qwen3-vl.

### Modifications apportées

1. **Renommage de la classe :** `UITarsGroundingTool` → `QwenGroundingTool`
2. **Changement de modèle :** `hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M` → `qwen3-vl:2b`
3. **Nouveau prompt système :** Prompt spécialisé pour grounding déterministe
4. **Format API :** Format standard Ollama avec `images: [base64]` (pas format OpenAI)
5. **Détection automatique :** Fonction `_detect_grounding_model()` pour détecter le meilleur modèle qwen3-vl disponible

### Documentation manquante

**Fichiers à mettre à jour :**
- [`AGENTS.md`](AGENTS.md) - Section "OUTILS smolagents" mentionne encore "MouseKeyboardTool" mais pas "QwenGroundingTool"
- [`LEARNING.md`](LEARNING.md) - La section "Migration UI-TARS → qwen3-vl pour GUI Grounding" existe mais doit être référencée dans AGENTS.md
- [`PROGRESS.md`](PROGRESS.md) - Section "TOOL-11 — UITarsGroundingTool" doit être mise à jour

**Contenu à ajouter dans AGENTS.md :**

```markdown
### V1 — Actifs (implémentés et validés)
- **FileSystemTool** (TOOL-1) : read/write/create/delete/list/move/search
- **OsExecTool** (TOOL-2) : exécution PowerShell
- **ClipboardTool** (TOOL-3) : lecture/écriture presse-papier
- **ScreenshotTool** (TOOL-8) : capture d'écran Windows
- **VisionTool** (TOOL-7) : analyse d'images avec qwen3-vl
- **QwenGroundingTool** (TOOL-11) : GUI grounding avec qwen3-vl
- **ChromeDevTools MCP** (TOOL-10) : pilotage Chrome (Puppeteer)
```

**Contenu à mettre à jour dans PROGRESS.md :**

```markdown
## TOOL-11 — QwenGroundingTool (anciennement UITarsGroundingTool)
**Statut : DONE**

Fichiers créés :
- agent/tools/grounding.py : sous-classe Tool, grounding GUI avec qwen3-vl
- Modèle : qwen3-vl:2b (détecté automatiquement)
- Retourne coordonnées pixel absolues depuis description textuelle + screenshot

Modifications :
- Renommage : ui_tars_grounding.py → grounding.py
- Classe : UITarsGroundingTool → QwenGroundingTool
- Modèle : UI-TARS-2B-SFT → qwen3-vl:2b
- Prompt système spécialisé pour grounding déterministe (temperature: 0.0)
- Détection automatique du modèle qwen3-vl disponible (2b, 4b, 8b)

Checkpoint :
- ✅ Installer qwen3-vl:2b : `ollama pull qwen3-vl:2b`
- ✅ Test grounding : "Trouve le bouton Démarrer dans ce screenshot"
- ✅ Vérification coordonnées : Retourne [x, y] relatifs → conversion en absolus
- ✅ Commit : feat: tool-11 — qwen3-vl grounding tool
```

---

## Divergence #4 : TOOL-7 Vision - Migration MCP Z.ai → Ollama local

### Fichiers concernés
- [`agent/tools/vision.py`](agent/tools/vision.py) (203 lignes)

### Description
TOOL-7 (Vision) a été migré de l'approche MCP Z.ai (GLM-4.6V cloud) vers une approche 100% locale avec Ollama qwen3-vl.

### Modifications apportées

1. **Abandon de MCP** : Plus de dépendance à `mcp` pour la vision
2. **Modèle local** : Utilisation de qwen3-vl:8b (ou 2b, 4b) via Ollama
3. **Détection automatique** : Fonction `_detect_vision_model()` pour détecter le meilleur modèle disponible
4. **Format API** : Format standard Ollama `/api/chat` avec `images: [base64]`
5. **Timeout** : 180 secondes (3 minutes) pour l'analyse

### Documentation manquante

**Fichiers à mettre à jour :**
- [`AGENTS.md`](AGENTS.md) - Section "OUTILS smolagents" mentionne encore "MCP Vision Z.ai (GLM-4.6V)"
- [`PROGRESS.md`](PROGRESS.md) - La section TOOL-7 mentionne "Ollama qwen3-vl:2b" mais AGENTS.md ne reflète pas ce changement

**Contenu à mettre à jour dans AGENTS.md :**

```markdown
### V1 — Actifs (implémentés et validés)
- **VisionTool** (TOOL-7) : analyse d'images locale avec qwen3-vl (100% local, 0 donnée sortante)
```

**Supprimer de AGENTS.md :**
```markdown
### V1 — Roadmap (À venir)
- **Web Search MCP** (TOOL-4) : ⏳ recherche web Z.ai
- **Web Reader MCP** (TOOL-5) : ⏳ lecture URL Z.ai
- **Zread MCP** (TOOL-6) : ⏳ lecture GitHub Z.ai
```

**Remplacer par :**
```markdown
### V1 — Roadmap (À venir)
- **Web Search MCP** (TOOL-4) : ⏳ recherche web Z.ai
- **Web Reader MCP** (TOOL-5) : ⏳ lecture URL Z.ai
- **Zread MCP** (TOOL-6) : ⏳ lecture GitHub Z.ai
- **MouseKeyboardTool** (TOOL-9) : 🔄 contrôle souris/clavier (nécessite orchestration)
```

---

## Divergence #5 : Skills système non documenté dans AGENTS.md

### Fichiers concernés
- [`agent/skills.txt`](agent/skills.txt)
- [`agent/SKILLS.md`](agent/SKILLS.md)
- [`agent/main.py`](agent/main.py) - Fonction `load_skills()`

### Description
Un système de skills (patterns de code réutilisables) a été implémenté pour éviter que l'agent régénère le même code à chaque fois.

### Fonctionnalités implémentées

1. **Fichier skills.txt** : Contient les patterns de code réutilisables
2. **Chargement au démarrage** : Fonction `load_skills()` dans `main.py`
3. **Passage à CodeAgent** : Via paramètre `instructions`
4. **Documentation** : [`agent/SKILLS.md`](agent/SKILLS.md) documente les skills disponibles

### Skills disponibles

1. **Screenshot + Vision** : Prendre un screenshot et l'analyser
2. **OCR (Extraction de texte)** : Extraire le texte visible
3. **Screenshot d'une région** : Capturer une partie de l'écran
4. **Requête HTTP avec Python** : Faire des requêtes HTTP (pas os_exec)
5. **Ouvrir une application** : Ouvrir des applications Windows via le menu Démarrer

### Documentation manquante

**Fichier à mettre à jour :**
- [`AGENTS.md`](AGENTS.md) - Ajouter une section "SKILLS — Patterns de code réutilisables"

**Contenu à ajouter dans AGENTS.md :**

```markdown
## SKILLS — Patterns de code réutilisables

Le système de skills fournit des patterns de code concrets à l'agent pour éviter qu'il régénère le même code à chaque fois.

### Pourquoi des skills ?

Les LLM ont tendance à régénérer le code à chaque fois, ce qui :
- ❌ Prend du temps (génération LLM)
- ❌ Consomme des tokens inutilement
- ❌ Peut introduire des erreurs ou variations

En fournissant des patterns de code concrets, l'agent peut :
- ✅ Copier directement le code sans le régénérer
- ✅ Exécuter plus rapidement
- ✅ Être plus fiable et cohérent
- ✅ Économiser des tokens

### Architecture

```
agent/
├── skills.txt          ← Patterns de code chargés au démarrage
├── SKILLS.md           ← Documentation des skills
└── main.py             ← Charge skills.txt via load_skills()
```

### Flux de chargement

1. Au démarrage, `main.py` appelle `load_skills()`
2. `load_skills()` lit `agent/skills.txt`
3. Le contenu est stocké dans la variable `SKILLS`
4. `SKILLS` est passé au paramètre `instructions` de `CodeAgent`
5. L'agent reçoit les patterns et peut les copier directement

### Skills disponibles

Voir [`agent/SKILLS.md`](agent/SKILLS.md) pour la documentation complète des skills disponibles :
1. Screenshot + Vision
2. OCR (Extraction de texte)
3. Screenshot d'une région spécifique
4. Requête HTTP avec Python
5. Ouvrir une application avec le clavier

### Comment ajouter un nouveau skill ?

1. Identifier un pattern répétitif
2. Créer un exemple concret (code minimal et fonctionnel)
3. Ajouter dans `agent/skills.txt`
4. Redémarrer le serveur : `uv run uvicorn main:app --reload`
5. Documenter dans `agent/SKILLS.md`
6. Tester : Vérifier que l'agent copie bien le pattern

**Avantage** : Pas besoin de modifier le code Python, juste éditer `skills.txt` !
```

---

## Divergence #6 : TOOL-10 Chrome DevTools MCP - Catégorisation des 26 outils

### Fichiers concernés
- [`agent/main.py`](agent/main.py) - Section lifespan Chrome DevTools MCP

### Description
TOOL-10 (Chrome DevTools MCP) est implémenté avec 26 outils organisés en 6 catégories, mais cette catégorisation n'est pas documentée dans AGENTS.md.

### 26 outils disponibles

**Input automation (8 outils) :**
- `click` : cliquer sur un élément
- `drag` : glisser un élément vers un autre
- `fill` : remplir un champ de saisie
- `fill_form` : remplir plusieurs champs à la fois
- `handle_dialog` : gérer les boîtes de dialogue
- `hover` : survoler un élément
- `press_key` : appuyer sur une touche ou combinaison
- `upload_file` : uploader un fichier

**Navigation automation (6 outils) :**
- `close_page` : fermer une page
- `list_pages` : lister les pages ouvertes
- `navigate_page` : naviguer vers une URL
- `new_page` : créer une nouvelle page
- `select_page` : sélectionner une page comme contexte
- `wait_for` : attendre qu'un texte apparaisse

**Emulation (2 outils) :**
- `emulate` : émuler diverses fonctionnalités
- `resize_page` : redimensionner la page

**Performance (3 outils) :**
- `performance_analyze_insight` : analyser une insight de performance
- `performance_start_trace` : démarrer un enregistrement de trace
- `performance_stop_trace` : arrêter l'enregistrement de trace

**Network (2 outils) :**
- `get_network_request` : récupérer une requête réseau
- `list_network_requests` : lister les requêtes

**Debugging (5 outils) :**
- `evaluate_script` : exécuter du JavaScript
- `get_console_message` : récupérer un message console
- `list_console_messages` : lister les messages console
- `take_screenshot` : prendre un screenshot
- `take_snapshot` : prendre un snapshot textuel

### Documentation manquante

**Fichier à mettre à jour :**
- [`AGENTS.md`](AGENTS.md) - Section "OUTILS smolagents" mentionne "ChromeDevTools MCP (TOOL-10)" mais ne détaille pas les 26 outils

**Contenu à mettre à jour dans AGENTS.md :**

```markdown
### V1 — Actifs (implémentés et validés)
- **ChromeDevTools MCP** (TOOL-10) : pilotage Chrome via Puppeteer (26 outils)

**26 outils organisés en 6 catégories :**

**Input automation (8 outils) :**
- `click` : cliquer sur un élément (uid, dblClick?, includeSnapshot?)
- `drag` : glisser un élément vers un autre (from_uid, to_uid)
- `fill` : remplir un champ de saisie (uid, value)
- `fill_form` : remplir plusieurs champs à la fois (elements[])
- `handle_dialog` : gérer les boîtes de dialogue (action: accept/dismiss)
- `hover` : survoler un élément (uid)
- `press_key` : appuyer sur une touche ou combinaison (key: "Enter", "Control+A")
- `upload_file` : uploader un fichier (filePath, uid)

**Navigation automation (6 outils) :**
- `close_page` : fermer une page (pageId)
- `list_pages` : lister les pages ouvertes
- `navigate_page` : naviguer vers une URL (type: url/back/forward/reload)
- `new_page` : créer une nouvelle page (url)
- `select_page` : sélectionner une page comme contexte (pageId)
- `wait_for` : attendre qu'un texte apparaisse (text, timeout?)

**Emulation (2 outils) :**
- `emulate` : émuler diverses fonctionnalités (cpuThrottlingRate?, geolocation?, networkConditions?)
- `resize_page` : redimensionner la page (width, height)

**Performance (3 outils) :**
- `performance_analyze_insight` : analyser une insight de performance (insightName, insightSetId)
- `performance_start_trace` : démarrer un enregistrement de trace (autoStop, reload)
- `performance_stop_trace` : arrêter l'enregistrement de trace

**Network (2 outils) :**
- `get_network_request` : récupérer une requête réseau (reqid?)
- `list_network_requests` : lister les requêtes (pageIdx?, pageSize?, resourceTypes[]?)

**Debugging (5 outils) :**
- `evaluate_script` : exécuter du JavaScript (function)
- `get_console_message` : récupérer un message console (msgid)
- `list_console_messages` : lister les messages console (pageIdx?, pageSize?, types[]?)
- `take_screenshot` : prendre un screenshot (format, fullPage?, quality?, uid?)
- `take_snapshot` : prendre un snapshot textuel de la page (verbose?)

**Options de configuration :**
- `--headless=true` : mode sans interface (défaut : false)
- `--channel=canary|beta|dev` : utiliser une autre version de Chrome
- `--viewport=1280x720` : taille initiale du viewport
- `--isolated=true` : utiliser un profil temporaire
- `--category-performance=false` : désactiver les outils de performance
- `--category-network=false` : désactiver les outils réseau
- `--category-emulation=false` : désactiver les outils d'émulation
```

---

## Divergence #7 : Modèles vision - qwen3-vl au lieu de qwen3-vl:2b

### Fichiers concernés
- [`agent/tools/vision.py`](agent/tools/vision.py) - Ligne 44
- [`agent/tools/grounding.py`](agent/tools/grounding.py) - Ligne 56

### Description
Les préférences de modèles vision sont différentes entre `vision.py` et `grounding.py` :

- **vision.py** : `["qwen3-vl:8b", "qwen3-vl:2b", "qwen3-vl:4b"]` (préfère 8b)
- **grounding.py** : `["qwen3-vl:2b", "qwen3-vl:4b", "qwen3-vl:8b"]` (préfère 2b)

### Documentation manquante

**Fichiers à mettre à jour :**
- [`AGENTS.md`](AGENTS.md) - Section "MODÈLES LLM" mentionne "vision | qwen3-vl:8b | Local | Vision locale"

**Contenu à mettre à jour dans AGENTS.md :**

```markdown
### Ollama — 100% local, 0 donnée sortante

| ID | Modèle | Taille | Usage |
|----|--------|--------|-------|
| fast | gemma3:latest | 3.3GB | Réponses rapides |
| smart | qwen3:8b | 5.2GB | Usage quotidien — recommandé |
| main | qwen3:8b | 5.2GB | Modèle principal — défaut sans ZAI_API_KEY |
| vision | qwen3-vl:2b | 2.3GB | Vision locale (TOOL-7, analyse d'images) |
| grounding | qwen3-vl:2b | 2.3GB | GUI grounding (TOOL-11, pilotage PC) |

**Note :** Les modèles qwen3-vl:2b sont préférés pour la vision et le grounding car ils sont plus rapides et plus légers.
```

---

## Divergence #8 : PROGRESS.md - Date de dernière mise à jour obsolète

### Fichiers concernés
- [`PROGRESS.md`](PROGRESS.md) - Ligne 3

### Description
La date de dernière mise à jour de PROGRESS.md est "2026-02-20" alors que LEARNING.md contient des entrées jusqu'à "2026-02-22".

### Documentation manquante

**Fichier à mettre à jour :**
- [`PROGRESS.md`](PROGRESS.md) - Mettre à jour la date de dernière mise à jour

**Contenu à mettre à jour dans PROGRESS.md :**

```markdown
# PROGRESS.md — État d'avancement my-claw

Dernière mise à jour : 2026-02-22
Repo : https://github.com/laurentvv/my-claw
```

---

## Divergence #9 : STATUS.md - Date de dernière mise à jour obsolète

### Fichiers concernés
- [`STATUS.md`](STATUS.md) - Ligne 3

### Description
La date de dernière mise à jour de STATUS.md est "2026-02-20" alors que LEARNING.md contient des entrées jusqu'à "2026-02-22".

### Documentation manquante

**Fichier à mettre à jour :**
- [`STATUS.md`](STATUS.md) - Mettre à jour la date de dernière mise à jour

**Contenu à mettre à jour dans STATUS.md :**

```markdown
# STATUS — Vue rapide my-claw

> Dernière mise à jour : 2026-02-22  
> Repo : https://github.com/laurentvv/my-claw
```

---

## Résumé des fichiers à modifier

| Fichier | Priorité | Type de modification |
|----------|------------|---------------------|
| [`AGENTS.md`](AGENTS.md) | 🔴 CRITIQUE | Ajouter section "GESTION DES MODÈLES — Module agent/models.py" |
| [`AGENTS.md`](AGENTS.md) | 🔴 CRITIQUE | Ajouter section "ARCHITECTURE MULTI-AGENT" |
| [`AGENTS.md`](AGENTS.md) | 🟠 ÉLEVÉE | Mettre à jour "OUTILS smolagents" - Ajouter QwenGroundingTool |
| [`AGENTS.md`](AGENTS.md) | 🟠 ÉLEVÉE | Mettre à jour "OUTILS smolagents" - Détail des 26 outils Chrome DevTools |
| [`AGENTS.md`](AGENTS.md) | 🟠 ÉLEVÉE | Mettre à jour "MODÈLES LLM" - Correction modèle vision |
| [`AGENTS.md`](AGENTS.md) | 🟡 MOYENNE | Ajouter section "SKILLS — Patterns de code réutilisables" |
| [`AGENTS.md`](AGENTS.md) | 🟡 MOYENNE | Mettre à jour TOOL-7 Vision (Ollama local) |
| [`PROGRESS.md`](PROGRESS.md) | 🟡 MOYENNE | Mettre à jour TOOL-11 (QwenGroundingTool) |
| [`PROGRESS.md`](PROGRESS.md) | 🟢 FAIBLE | Mettre à jour date de dernière mise à jour |
| [`STATUS.md`](STATUS.md) | 🟢 FAIBLE | Mettre à jour date de dernière mise à jour |

---

## Recommandations

### Priorité 1 - Critique (à faire immédiatement)

1. **Mettre à jour AGENTS.md avec l'architecture multi-agent** : C'est un changement architectural majeur qui doit être documenté.
2. **Documenter le module agent/models.py** : C'est un nouveau module central qui est utilisé par tous les agents.
3. **Mettre à jour TOOL-11** : Renommage de UITarsGroundingTool vers QwenGroundingTool.

### Priorité 2 - Élevée (à faire prochainement)

4. **Documenter les 26 outils Chrome DevTools** : Cette catégorisation est utile pour les développeurs.
5. **Mettre à jour TOOL-7 Vision** : Migration de MCP Z.ai vers Ollama local.
6. **Documenter le système de skills** : C'est une fonctionnalité importante pour les performances.

### Priorité 3 - Moyenne/Faible (à faire quand possible)

7. **Corriger le modèle vision dans AGENTS.md** : qwen3-vl:2b au lieu de qwen3-vl:8b.
8. **Mettre à jour les dates** : PROGRESS.md et STATUS.md.

---

## Conclusion

L'analyse a révélé **9 divergences majeures** entre le code source actuel et la documentation Markdown. Les modifications les plus importantes concernent :

1. **Architecture multi-agent** : Non documentée dans AGENTS.md
2. **Module agent/models.py** : Nouveau module centralisé non documenté
3. **Renommage TOOL-11** : UITarsGroundingTool → QwenGroundingTool non documenté
4. **Migration TOOL-7** : MCP Z.ai → Ollama local non documentée
5. **Skills système** : Non documenté dans AGENTS.md
6. **Chrome DevTools MCP** : 26 outils non détaillés dans AGENTS.md

Ces divergences doivent être corrigées pour maintenir la documentation à jour avec l'état actuel du code.
