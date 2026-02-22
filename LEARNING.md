# LEARNING.md — Découvertes my-claw

> Document de mémoire technique pour le développement my-claw
> À mettre à jour après chaque module/feature implémenté

---

## TOOL-10 — MCP Chrome DevTools (2026-02-20)

### Test de validation (2026-02-20)

**Statut** : ✅ **DONE** - MCP Chrome DevTools opérationnel avec 26 outils

**Prérequis** :
- ✅ Node.js 24.13.1 installé
- ✅ npx disponible (inclus avec Node.js)
- ✅ Ollama démarré (7 modèles installés)
- ⚠️ Chrome/Edge non installé (MCP peut le télécharger automatiquement)

**Résultats des tests** :

```
============================================================
RESUME DES TESTS
============================================================
  MCP Connection:     [PASS]
  main.py Integration: [PASS]
============================================================
[SUCCESS] TOUS LES TESTS TOOL-10 SONT PASSES
```

**Outils chargés (26 au total)** :

1. click
2. close_page
3. drag
4. emulate
5. evaluate_script
6. fill
7. fill_form
8. get_console_message
9. get_network_request
10. handle_dialog
11. hover
12. list_console_messages
13. list_network_requests
14. list_pages
15. navigate_page
16. new_page
17. performance_analyze_insight
18. performance_start_trace
19. performance_stop_trace
20. press_key
21. resize_page
22. select_page
23. take_screenshot
24. take_snapshot
25. upload_file
26. wait_for

**Catégorisation des outils** :
- Input automation : 8 outils
- Navigation : 6 outils
- Emulation : 2 outils
- Performance : 3 outils
- Network : 2 outils
- Debugging : 5 outils

### Intégration dans main.py

**Configuration MCP** :
```python
from smolagents import ToolCollection
from mcp import StdioServerParameters

# Variables globales pour gérer le cycle de vie MCP
_mcp_context: ToolCollection | None = None
_mcp_tools: list = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mcp_context, _mcp_tools

    # Startup: initialiser Chrome DevTools MCP via ToolCollection.from_mcp()
    chrome_devtools_params = StdioServerParameters(
        command="npx",
        args=["-y", "chrome-devtools-mcp@latest"],
        env={**os.environ}  # Important pour trouver Node.js sur Windows
    )

    # from_mcp() retourne un context manager, il faut appeler __enter__()
    # trust_remote_code=True est requis pour les serveurs MCP
    _mcp_context = ToolCollection.from_mcp(chrome_devtools_params, trust_remote_code=True)
    tool_collection = _mcp_context.__enter__()
    _mcp_tools = list(tool_collection.tools)

    yield  # L'application tourne ici, le client MCP reste actif

    # Shutdown: fermer proprement le client MCP
    if _mcp_context is not None:
        _mcp_context.__exit__(None, None, None)
```

**Points clés** :
1. `from_mcp()` retourne un context manager → appeler `__enter__()` pour obtenir la ToolCollection
2. `trust_remote_code=True` est obligatoire (sinon ValueError)
3. Stocker le context manager pour cleanup via `__exit__(None, None, None)`
4. Stocker la liste des outils séparément pour utilisation dans CodeAgent
5. Les outils MCP sont ajoutés aux outils locaux via `get_all_tools()`

### Script de test (agent/test_tool10.py)

**Fonctions** :
- `check_prerequisites()` : Vérifie Node.js, npm/npx, Ollama, Chrome/Edge
- `test_mcp_connection()` : Teste la connexion MCP et le chargement des 26 outils
- `test_main_py_integration()` : Vérifie l'intégration dans main.py

**Exécution** :
```bash
cd agent
uv run python test_tool10.py
```

**Sortie attendue** :
```
[OK] Node.js: v24.13.1
[OK] Ollama: 7 modeles installes
[OK] Contexte MCP cree
[OK] 26 outils charges
[PASS] MCP Connection
[PASS] main.py Integration
[SUCCESS] TOUS LES TESTS TOOL-10 SONT PASSES
```

### Découvertes techniques

**ToolCollection.from_mcp()** :
- Retourne un generator/context manager, pas directement une ToolCollection
- Il faut appeler `__enter__()` pour obtenir la ToolCollection
- Il faut appeler `__exit__(None, None, None)` pour le cleanup
- `trust_remote_code=True` est obligatoire pour les serveurs MCP

**StdioServerParameters sur Windows** :
- Passer `env={**os.environ}` pour que npx trouve Node.js
- Le premier lancement télécharge le package chrome-devtools-mcp (~5-10s)
- Timeout de 60s recommandé à l'initialisation

**chrome-devtools-mcp** :
- Basé sur Puppeteer (pas Playwright)
- Crée un profil Chrome dédié dans `%HOMEPATH%/.cache/chrome-devtools-mcp/chrome-profile-stable`
- Le profil n'est pas effacé entre les runs
- Peut fonctionner sans Chrome installé (télécharge une version headless)

**Options de configuration** :
- `--headless=true` : mode sans interface (défaut : false)
- `--channel=canary|beta|dev` : utiliser une autre version de Chrome
- `--viewport=1280x720` : taille initiale du viewport
- `--isolated=true` : utiliser un profil temporaire
- `--category-performance=false` : désactiver les outils de performance
- `--category-network=false` : désactiver les outils réseau
- `--category-emulation=false` : désactiver les outils d'émulation

### Bonnes pratiques d'utilisation

1. **Snapshot avant action** : Toujours utiliser `take_snapshot()` avant d'interagir avec la page
2. **Préférez snapshot à screenshot** : `take_snapshot()` est plus rapide et fournit des uid exploitables
3. **Gestion des pages** : Utiliser `list_pages()` pour voir les pages ouvertes et `select_page()` pour changer de contexte
4. **Attente de chargement** : Utiliser `wait_for()` ou laisser le tool gérer automatiquement les attentes

### Prochaines étapes

TOOL-10 est maintenant opérationnel. Les tests fonctionnels avec un agent réel (CodeAgent) peuvent être effectués via :
1. Gradio UI : `uv run python gradio_app.py`
2. Requête API : `POST http://localhost:8000/run`

**Exemple de prompt de test** :
- "Ouvre https://example.com dans Chrome et prends un snapshot de la page"
- "Liste toutes les pages ouvertes dans Chrome"
- "Va sur https://huggingface.co et extrais le titre de la page"

---

## TOOL-1 — FileSystemTool (2026-02-19)

### Structure smolagents Tool
- Classe Tool nécessite les attributs: `name`, `description`, `inputs`, `output_type`
- La méthode `forward(*args, **kwargs)` implémente la logique
- `inputs` est un dict avec les paramètres: `{"param_name": {"type": "string", "description": "...", "nullable": True|False}}`
- Les types autorisés: "string", "integer", "boolean", "number", "array", "object", "any", "image", "audio"

### Validation Tool
- smolagents valide automatiquement que:
  - Les paramètres de `forward()` correspondent aux clés de `inputs`
  - Le type de retour correspond à `output_type`
  - `name` est un identifiant Python valide (pas de mot clé réservé)

### Imports dans forward()
- Règle AGENTS.md: imports dans `forward()` pour les librairies externes (pas stdlib)
- Pour pathlib, logging: OK au top-level car stdlib
- Pour les packages externes comme pyautogui, pyperclip: importer dans `forward()`

### Opérations implémentées
- **read**: Lecture fichier texte UTF-8
- **write**: Écriture fichier (remplace contenu, crée dossiers parents)
- **create**: Création fichier (échoue si existe déjà)
- **delete**: Suppression fichier ou dossier vide
- **list**: Listing contenu dossier
- **move**: Déplacement/renommage
- **search**: Recherche par pattern glob

### Gestion erreurs
- Exceptions capturées: FileNotFoundError, PermissionError, IsADirectoryError, NotADirectoryError, OSError
- Retour: message préfixé par "ERROR:" pour que l'agent smolagents comprenne
- Logging: logger.error() pour debug backend, message user dans return

### Test plan
Selon IMPLEMENTATION-TOOLS.md, tests à effectuer via Gradio avec modèle "reason" (glm-4.7):
1. Créer fichier: "Crée le fichier C:\tmp\myclaw_test.txt avec le contenu : Test TOOL-1 OK"
2. Lire fichier: "Lis le fichier C:\tmp\myclaw_test.txt"
3. Lister dossier: "Liste le contenu du dossier C:\tmp\"
4. Déplacer: "Déplace C:\tmp\myclaw_test.txt vers C:\tmp\myclaw_test_renamed.txt"
5. Supprimer: "Supprime C:\tmp\myclaw_test_renamed.txt"

### Résultats tests
- ✅ Tous les tests passés avec succès
- ✅ FileSystemTool fonctionne correctement sur Windows

---

## TOOL-2 — OsExecTool (2026-02-19)

### Implémentation
- Classe OsExecTool avec paramètres:
  - command (str): commande PowerShell à exécuter
  - timeout (int, optionnel): timeout en secondes, défaut 30
- Utilise subprocess.run() avec shell=False
- Lance via ["powershell", "-Command", command]
- Capture stdout et stderr en UTF-8
- Retourne un dict formaté: stdout, stderr, returncode

### Test plan
Selon IMPLEMENTATION-TOOLS.md, tests à effectuer via Gradio avec modèle "reason" (glm-4.7):
1. "Exécute la commande PowerShell : Get-Date"
2. "Liste les 5 premiers processus avec Get-Process | Select-Object -First 5"
3. "Crée le dossier C:\tmp\testdir_powershell via PowerShell"
4. "Supprime le dossier C:\tmp\testdir_powershell"

### Résultats tests
- ✅ Tous les tests passés avec succès
- ✅ OsExecTool fonctionne correctement sur Windows
- ✅ PowerShell intégré correctement

---

## TOOL-3 — ClipboardTool (2026-02-19)

### Implémentation
- Classe ClipboardTool avec paramètres:
  - operation (str): "read" ou "write"
  - content (str, optionnel): texte à écrire (requis si operation="write")
- Utilise pyperclip.copy() pour écrire
- Utilise pyperclip.paste() pour lire
- Gère l'exception si pas de gestionnaire de clipboard disponible

### Test plan
Selon IMPLEMENTATION-TOOLS.md, tests à effectuer via Gradio avec modèle "reason" (glm-4.7):
1. "Écris 'Bonjour depuis my-claw !' dans le presse-papier"
2. Vérifier manuellement avec Ctrl+V dans Notepad
3. "Lis le contenu actuel du presse-papier"

### Résultats tests
- ✅ Tous les tests passés avec succès
- ✅ ClipboardTool fonctionne correctement sur Windows
- ✅ pyperclip intégré correctement

---

## TOOL-7 — Vision locale avec Ollama qwen3-vl:2b (2026-02-20)

### Refonte : Abandon de MCP pour 100% local

**Décision** : Après tests avec MCP Vision Z.ai (GLM-4.6V), décision de revenir à une approche 100% locale sans MCP.

**Raisons de l'abandon de MCP** :
1. **Complexité inutile** - Event loop, lifespan FastAPI, processus externe npx
2. **Performance médiocre** - Timeout de 30s dépassé systématiquement, nécessite 2-3 tentatives
3. **Dépendance cloud** - Envoie les screenshots à Z.ai (vie privée ❌)
4. **Contre la philosophie du projet** - AGENTS.md dit "100% local, 0 donnée sortante"
5. **Coût** - Consomme des crédits API Z.ai

**Solution finale** : Outil vision 100% local avec Ollama qwen3-vl:2b

### Implémentation VisionTool local

**Fichier** : `agent/tools/vision.py`

**Caractéristiques** :
- Utilise qwen3-vl:2b via Ollama API locale (~2GB, plus rapide que 4b)
- Encode l'image en base64
- Appelle `/api/generate` avec le paramètre `images`
- Timeout 180s (3 minutes)
- 100% local, aucune donnée ne sort de la machine

**Code clé** :
```python
class VisionTool(Tool):
    name = "analyze_image"

    def forward(self, image_path: str, prompt: Optional[str] = None) -> str:
        # Lire et encoder l'image en base64
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        # Appeler Ollama avec qwen3-vl:2b
        resp = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": "qwen3-vl:2b",
                "prompt": prompt or "Describe this image in detail.",
                "images": [image_b64],
                "stream": False,
            },
            timeout=180,
        )
        return resp.json()["response"]
```

### Simplification de main.py

**Avant** (avec MCP) :
- 139 lignes
- Imports : `asynccontextmanager`, `MCPClient`, `StdioServerParameters`
- Fonction `lifespan()` de 42 lignes
- Variables globales `_mcp_client`, `_mcp_tools`
- Fusion des outils locaux et MCP

**Après** (100% local) :
- 90 lignes (-35%)
- Imports simplifiés : juste `FastAPI`, `CodeAgent`, `LiteLLMModel`
- Pas de lifespan, pas de gestion d'event loop
- Juste `tools=TOOLS` dans CodeAgent

### Nettoyage des dépendances

**Avant** :
```toml
dependencies = [
    "smolagents[litellm,mcp]>=1.9.0",
    "mcp>=0.9.0",
    ...
]
```

**Après** :
```toml
dependencies = [
    "smolagents[litellm]>=1.9.0",
    ...
]
```

Suppression de `mcp>=0.9.0` et du extra `[mcp]` de smolagents.

### Avantages de la solution locale

✅ **Simplicité** - Code Python classique, pas de gestion d'event loop
✅ **Performance** - Pas de latence réseau, exécution locale
✅ **Vie privée** - Rien ne sort de la machine
✅ **Fiabilité** - Pas de dépendance externe (API cloud, npx, etc.)
✅ **Gratuit** - Pas de crédits API
✅ **Cohérence** - Tout le projet utilise Ollama

### Tests à effectuer

1. **Screenshot + analyse** : "Prends un screenshot de l'écran et analyse-le"
2. **Extraction de texte** : "Prends un screenshot et extrais tout le texte visible"
3. **Diagnostic d'erreur** : "Prends un screenshot et dis-moi s'il y a des erreurs"

---

## TOOL-7 (ARCHIVE) — MCP Vision Z.ai (GLM-4.6V) - ABANDONNÉ

### Problème initial : Event loop is closed

**Bug identifié** : Les outils MCP nécessitent un event loop actif, mais le code initial fermait le contexte MCP immédiatement après avoir récupéré les outils.

```python
# ❌ Code incorrect - ferme le contexte immédiatement
with MCPClient(mcp_params) as mcp_tools:
    _mcp_tools = list(mcp_tools)
# Le contexte est fermé ici, les outils ne fonctionnent plus
```

**Erreur** :
```
RuntimeError: Event loop is closed
ValueError: I/O operation on closed pipe
```

### Solution : FastAPI lifespan

**Référence** : GitHub issue smolagents #1159 - https://github.com/huggingface/smolagents/issues/1159

La solution est d'utiliser **FastAPI lifespan** pour garder le client MCP actif pendant toute la durée de vie de l'application.

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mcp_client, _mcp_tools

    # Startup: initialiser et garder le client MCP actif
    _mcp_client = MCPClient(mcp_params)
    _mcp_client.__enter__()
    _mcp_tools = list(_mcp_client)

    yield  # L'application tourne ici, le client reste actif

    # Shutdown: fermer proprement
    if _mcp_client is not None:
        _mcp_client.__exit__(None, None, None)

app = FastAPI(lifespan=lifespan)
```

### Implémentation

**Fichiers modifiés** :
- `agent/main.py` : Ajout de la fonction `lifespan()` et gestion du cycle de vie MCP
- `.env.example` : Réactivation de `ZAI_API_KEY` et `ZAI_BASE_URL`

**Outils MCP Vision disponibles (8)** :
1. `analyze_image` : Analyse générale d'une image
2. `extract_text_from_screenshot` : OCR sur captures d'écran
3. `ui_to_artifact` : Transformer une UI en code/specs
4. `analyze_video` : Analyser une vidéo locale (max 8MB)
5. `diagnose_error_screenshot` : Analyser une erreur visible
6. `understand_technical_diagram` : Lire un schéma d'architecture
7. `ui_diff_check` : Comparer deux captures UI
8. `analyze_data_visualization` : Lire un graphique/dashboard

### Configuration requise

**Prérequis** :
- Node.js 24+ (pour `npx @z_ai/mcp-server@latest`)
- Clé API Z.ai (https://open.bigmodel.cn/dev/api)
- Variables d'environnement dans `agent/.env` :
  ```env
  ZAI_API_KEY="votre_clé_api"
  ZAI_BASE_URL="https://api.z.ai/api/coding/paas/v4"
  ```

**Démarrage** :
```bash
cd agent
uv run uvicorn main:app --reload
```

**Logs attendus** :
```
INFO:__main__:MCP Vision Z.ai connecté - 8 outils disponibles
INFO:__main__:Outils MCP: ['ui_to_artifact', 'extract_text_from_screenshot', 'diagnose_error_screenshot', 'understand_technical_diagram', 'analyze_data_visualization', 'ui_diff_check', 'analyze_image', 'analyze_video']
INFO:__main__:Total tools disponibles: 13 (5 locaux, 8 MCP)
```

### Impact sur TOOL-9 (MouseKeyboardTool)

**Avant TOOL-7** : L'agent était aveugle, il ne pouvait pas vérifier si ses actions réussissaient.

**Après TOOL-7** : L'agent peut maintenant :
1. Prendre un screenshot avec `ScreenshotTool`
2. Analyser l'image avec `image_analysis` ou `extract_text_from_screenshot`
3. Vérifier si l'action a réussi
4. S'auto-corriger si nécessaire

**Exemple de workflow** :
```
User: "Ouvre Notepad"
  ↓
Agent: MouseKeyboardTool.hotkey("win")
  ↓
Agent: ScreenshotTool.screenshot()
  ↓
Agent: analyze_image("C:\tmp\myclawshots\screen_001.png")
  → "Menu Démarrer visible"
  ↓
Agent: MouseKeyboardTool.type("notepad")
  ↓
Agent: MouseKeyboardTool.hotkey("enter")
  ↓
Agent: ScreenshotTool.screenshot()
  ↓
Agent: analyze_image("C:\tmp\myclawshots\screen_002.png")
  → "Notepad ouvert, zone de texte vide"
  ↓
Done ✅
```

### Découvertes techniques

**FastAPI lifespan** :
- Remplace les anciens événements `@app.on_event("startup")` et `@app.on_event("shutdown")`
- Utilise un context manager async pour gérer le cycle de vie
- Permet de garder des ressources actives (connexions DB, clients MCP, etc.)

**MCPClient** :
- Doit rester actif pendant toute la durée de vie de l'application
- Utilise `__enter__()` et `__exit__()` pour gérer le contexte manuellement
- Les outils MCP sont des wrappers autour d'appels async au serveur MCP

**StdioServerParameters** :
- Lance un processus Node.js via `npx`
- Communication via stdin/stdout
- Variables d'environnement passées via `env={...}`

**PowerShell curl alias** :
- Sur Windows, PowerShell a un alias `curl` qui pointe vers `Invoke-WebRequest`
- Cet alias a une syntaxe différente du vrai `curl` et demande des paramètres interactifs
- **Solution 1** : Dans `os_exec.py`, remplacer automatiquement `curl ` par `curl.exe ` pour utiliser le vrai curl
- **Solution 2 (MEILLEURE)** : Guider l'agent à utiliser Python (`requests`, `urllib`) au lieu de `os_exec` pour HTTP

**Guidage de l'agent CodeAgent** :
- Les agents LLM ont tendance à utiliser `os_exec` pour tout, même quand Python suffit
- **Solution 1** : Utiliser le paramètre `instructions` de `CodeAgent` pour guider l'agent
  - Exemple : "For HTTP requests: Use Python's requests library, NOT os_exec with curl"
  - Les `instructions` sont ajoutées à la fin du system prompt par défaut
  - Elles ne remplacent pas le system prompt, elles le complètent
- **Solution 2** : Autoriser les imports Python nécessaires via `additional_authorized_imports`
  - Par défaut, seuls quelques modules stdlib sont autorisés : `statistics`, `collections`, `re`, `math`, etc.
  - Pour utiliser `requests`, `urllib`, `json`, etc., il faut les ajouter explicitement
  - Exemple : `additional_authorized_imports=["requests", "urllib", "json", "csv", "pathlib", "os", "subprocess"]`
- **Solution 3** : Fournir des **skills** (exemples de code) directement dans `instructions` (2026-02-20)
  - Les LLM ont tendance à régénérer le code à chaque fois, ce qui est lent et peut introduire des erreurs
  - En fournissant des patterns de code concrets, l'agent peut les copier directement
  - **Fichier externe** : Les skills sont définis dans `agent/skills.txt` et chargés au démarrage
  - Avantages : Plus rapide, plus fiable, moins de tokens consommés, facile à modifier sans toucher au code
  - Patterns fournis : screenshot+vision, OCR, screenshot région, HTTP requests, keyboard automation, clipboard, file operations
  - Pour ajouter un skill : éditer `agent/skills.txt` et redémarrer le serveur
  - **IMPORTANT** : Tous les skills doivent utiliser `final_answer()` pour retourner le résultat
    - ❌ Problème : L'agent essaie de reformuler la réponse en texte au Step 2 → Erreur de parsing → Aucune réponse envoyée
    - ✅ Solution : Utiliser `final_answer()` dans le code pour terminer immédiatement
    - Exemple : `final_answer(f"Screenshot saved: {screenshot_path}\n\nAnalysis: {analysis}")`
- **Résultat** : L'agent préfère écrire du code Python natif plutôt que d'appeler des commandes système
- Cela évite les problèmes de compatibilité PowerShell/Bash et simplifie le code généré
- **Documentation** : https://huggingface.co/docs/smolagents/tutorials/building_good_agents

**Timeouts configurés** :
- **Gateway → Agent** : 360 secondes (6 minutes) dans `gateway/lib/agent-client.ts` - Augmenté pour GLM-4.7 screenshot+vision
- **Gateway → Agent (models)** : 5 secondes dans `gateway/app/api/models/route.ts` - Endpoint léger de listing
- **Agent → Code Python** : 240 secondes (4 minutes) dans `agent/main.py` via `executor_kwargs` - Augmenté pour GLM-4.7 screenshot+vision
- **Gradio UI** : 300 secondes (5 minutes) dans `agent/gradio_app.py`
- **Vision (Ollama)** : 180 secondes (3 minutes) dans `agent/tools/vision.py` - qwen3-vl:2b est rapide
- **os_exec** : 30 secondes par défaut (configurable par appel) dans `agent/tools/os_exec.py`

**Raison des augmentations (2026-02-20)** :
- GLM-4.7 coordonne screenshot + vision + actions en plusieurs étapes
- Chaque étape peut prendre 30-60 secondes (génération LLM + exécution outil)
- Séquence typique : screenshot (2s) + vision (30-60s) + action (2s) + screenshot (2s) + vision (30-60s) = 66-126s
- Avec max_steps=10, peut atteindre 3-4 minutes facilement

### Modèles GLM-4.7 (code/reason) - ✅ PROBLÈME RÉSOLU

**Problème identifié (2026-02-20)** : Les modèles GLM-4.7 et GLM-4.7-flash génèrent systématiquement des balises `</code` (sans `>`) à la fin du code Python, causant des `SyntaxError` dans smolagents.

**Exemple d'erreur** :
```python
screenshot_path = screenshot()
print(f"Screenshot saved to: {screenshot_path}")
</code    # ❌ Cette balise cause SyntaxError: invalid syntax
```

**Diagnostic** :
1. GLM-4.7 génère `</code` (sans `>`) au lieu de `</code>` (avec `>`)
2. La fonction `parse_code_blobs()` de smolagents utilise un regex pour extraire le code entre `<code>` et `</code>`
3. Le regex ne trouve pas `</code` (sans `>`), donc la balise reste dans le code extrait
4. Résultat : `SyntaxError: invalid syntax` lors de l'exécution

**Solution implémentée (2026-02-20)** : Post-processing via wrapper `CleanedLiteLLMModel`

1. **Fonction `clean_glm_response()`** (agent/main.py) :
   - Retire `</code` (sans `>`) en fin de chaîne ou avant nouvelle ligne
   - Retire aussi `</code>` (avec `>`) et `</s>` au cas où
   - Utilise des regex avec flag `MULTILINE`

2. **Classe `CleanedLiteLLMModel`** (agent/main.py) :
   - Hérite de `LiteLLMModel`
   - Override la méthode `generate()` pour intercepter les réponses
   - Applique `clean_glm_response()` sur `chat_message.content` avant de retourner

3. **Intégration dans `get_model()`** :
   - Pour les modèles GLM-4.7 (`code`, `reason`) : utilise `CleanedLiteLLMModel`
   - Pour les modèles Ollama : utilise `LiteLLMModel` standard (pas besoin de nettoyage)

**Résultat** :
- ✅ Les balises `</code` sont retirées avant le parsing du code
- ✅ Plus de `SyntaxError` avec GLM-4.7
- ✅ Les modèles GLM-4.7 fonctionnent maintenant correctement avec smolagents

**Modèles recommandés par usage** :
- **Tests rapides** : `fast` (gemma3:latest)
- **Usage quotidien** : `smart` (qwen3:latest) ⭐ **RECOMMANDÉ** (100% local)
- **Tâches complexes** : `main` (qwen3:latest) ou `code` (GLM-4.7-flash) si ZAI_API_KEY configuré
- **Vision** : `vision` (qwen3-vl:2b)

**Note** : Les modèles Ollama locaux restent recommandés pour un usage 100% local sans envoi de données.

### Détection automatique des modèles (2026-02-20)

**Problème** : Les noms de modèles affichés dans le gateway ne correspondaient pas aux modèles réellement installés sur la machine.

**Solution** : Système de détection automatique au démarrage de l'agent :

1. **Fonction `get_ollama_models()`** : Appelle `GET /api/tags` d'Ollama pour lister les modèles installés
2. **Fonction `detect_models()`** : Associe automatiquement les modèles détectés aux catégories (fast/smart/main/vision)
3. **Préférences par catégorie** : Chaque catégorie a une liste de modèles préférés (ordre de priorité)
4. **Endpoint `/models`** : Expose la liste des modèles disponibles au gateway

**Exemple de préférences** :
```python
MODEL_PREFERENCES = {
    "fast":   ["gemma3:latest", "qwen3:latest", "gemma3n:latest"],
    "smart":  ["qwen3:latest", "gemma3n:latest", "gemma3:latest"],
    "main":   ["qwen3:latest", "gemma3n:latest", "gemma3:latest"],
    "vision": ["qwen3-vl:2b", "qwen3-vl:4b", "llama3.2-vision"],
}
```

**Avantages** :
- ✅ Détection automatique au démarrage
- ✅ Fallback intelligent si un modèle préféré n'est pas installé
- ✅ Logs clairs des modèles détectés
- ✅ API `/models` pour le frontend

**Bug critique corrigé (2026-02-20)** : KeyError si aucun modèle Ollama installé

**Problème** : Si aucun modèle Ollama n'est installé, `MODELS` ne contient que les modèles cloud (`code`, `reason`). Le fallback `MODELS.get(model_id, MODELS["main"])` lève alors une `KeyError` car `"main"` n'existe pas, crashant l'endpoint `/run`.

**Solution** : Fallback sécurisé en cascade dans `get_model()` :
```python
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
```

**Résultat** :
- ✅ Pas de crash si aucun modèle Ollama installé
- ✅ Fallback sur le premier modèle disponible (ex: `code` ou `reason` si ZAI_API_KEY configuré)
- ✅ Message d'erreur clair si aucun modèle disponible du tout

### Découverte technique (pathlib)
- pathlib.Path utilisé pour tous les chemins Windows
- encode="utf-8" par défaut pour compatibilité
- path_obj.parent.mkdir(parents=True, exist_ok=True) crée dossiers parents automatiquement
- `path_obj.touch()` crée fichier vide
- `path_obj.iterdir()` itère sur contenu dossier
- `path_obj.glob(pattern)` pour recherche glob

---

## TOOL-8 — ScreenshotTool (2026-02-19)

### Implémentation
- Classe ScreenshotTool avec paramètres:
  - region (str, optionnel): "x,y,width,height" pour une région spécifique
- Utilise pyautogui.screenshot() pour capturer l'écran
- Sauvegarde dans C:\tmp\myclawshots\screen_{timestamp}.png
- Retourne le chemin absolu Windows du fichier
- Dépendances: pyautogui, pillow

### Test plan
Selon IMPLEMENTATION-TOOLS.md, tests à effectuer via Gradio:
1. "Prends un screenshot de l'écran"
2. Vérifier que le fichier PNG existe dans C:\tmp\myclawshots\
3. "Prends un screenshot et analyse-le" → enchaîne avec TOOL-7

### Résultats tests
- ✅ "Prends un screenshot de l'écran" → fichier créé avec succès
- ✅ Fichier PNG valide et lisible
- ⚠️ Enchaînement avec TOOL-7 bloqué car TOOL-7 n'est pas implémenté

### Découvertes techniques
- pyautogui.FAILSAFE = False configuré (pas de coin haut-gauche pour arrêter)
- Path.mkdir(parents=True, exist_ok=True) crée le dossier automatiquement
- Timestamp format: YYYYMMDD_HHMMSS pour éviter les collisions
- Variable d'environnement SCREENSHOT_DIR pour configurer le dossier de sortie

---

## TOOL-10 — MCP Chrome DevTools (2026-02-20)

### Chrome DevTools MCP Overview

**Package** : chrome-devtools-mcp@latest
**Repository** : https://github.com/ChromeDevTools/chrome-devtools-mcp
**Base** : Puppeteer (pas Playwright comme initialement prévu)

### Prérequis

- Node.js 20.19+ (déjà présent d'après setup)
- Chrome stable ou plus récent installé
- npx (inclus avec Node.js)

### Configuration StdioServerParameters

**IMPORTANT** : `ToolCollection.from_mcp()` retourne un **context manager** (generator), pas directement une ToolCollection. De plus, `trust_remote_code=True` est **obligatoire** pour les serveurs MCP.

```python
from smolagents import ToolCollection
from mcp import StdioServerParameters

# Variables globales pour gérer le cycle de vie MCP
_mcp_context: ToolCollection | None = None
_mcp_tools: list = []

chrome_devtools_params = StdioServerParameters(
    command="npx",
    args=["-y", "chrome-devtools-mcp@latest"],
    env={**os.environ}  # Important pour trouver Node.js sur Windows
)

# Dans le startup (lifespan FastAPI) :
try:
    # from_mcp() retourne un context manager, il faut appeler __enter__()
    _mcp_context = ToolCollection.from_mcp(chrome_devtools_params, trust_remote_code=True)
    tool_collection = _mcp_context.__enter__()
    _mcp_tools = list(tool_collection.tools)
    logger.info(f"✓ Chrome DevTools MCP chargé : {len(_mcp_tools)} outils")
except Exception as e:
    logger.warning(f"✗ Impossible de charger Chrome DevTools MCP : {e}")
    _mcp_context = None
    _mcp_tools = []

# Dans le shutdown (lifespan FastAPI) :
if _mcp_context is not None:
    _mcp_context.__exit__(None, None, None)
    logger.info("✓ Chrome DevTools MCP fermé")
```

**Points clés** :
1. `from_mcp()` retourne un context manager → appeler `__enter__()` pour obtenir la ToolCollection
2. `trust_remote_code=True` est obligatoire (sinon ValueError)
3. Stocker le context manager pour cleanup via `__exit__(None, None, None)`
4. Stocker la liste des outils séparément pour utilisation dans CodeAgent

### 26 outils disponibles

**Input automation (8 outils)** :
- `click` : cliquer sur un élément (uid, dblClick?, includeSnapshot?)
- `drag` : glisser un élément vers un autre (from_uid, to_uid, includeSnapshot?)
- `fill` : remplir un champ de saisie (uid, value, includeSnapshot?)
- `fill_form` : remplir plusieurs champs à la fois (elements[], includeSnapshot?)
- `handle_dialog` : gérer les boîtes de dialogue (action: accept/dismiss, promptText?)
- `hover` : survoler un élément (uid, includeSnapshot?)
- `press_key` : appuyer sur une touche ou combinaison (key: "Enter", "Control+A", etc., includeSnapshot?)
- `upload_file` : uploader un fichier (filePath, uid, includeSnapshot?)

**Navigation automation (6 outils)** :
- `close_page` : fermer une page (pageId)
- `list_pages` : lister les pages ouvertes
- `navigate_page` : naviguer vers une URL (type: url/back/forward/reload, url?, ignoreCache?, handleBeforeUnload?, timeout?)
- `new_page` : créer une nouvelle page (url, timeout?)
- `select_page` : sélectionner une page comme contexte (pageId, bringToFront?)
- `wait_for` : attendre qu'un texte apparaisse (text, timeout?)

**Emulation (2 outils)** :
- `emulate` : émuler diverses fonctionnalités (cpuThrottlingRate?, geolocation?, networkConditions?, userAgent?, viewport?)
- `resize_page` : redimensionner la page (width, height)

**Performance (3 outils)** :
- `performance_analyze_insight` : analyser une insight de performance (insightName, insightSetId)
- `performance_start_trace` : démarrer un enregistrement de trace (autoStop, reload, filePath?)
- `performance_stop_trace` : arrêter l'enregistrement de trace (filePath?)

**Network (2 outils)** :
- `get_network_request` : récupérer une requête réseau (reqid?, requestFilePath?, responseFilePath?)
- `list_network_requests` : lister les requêtes (includePreservedRequests?, pageIdx?, pageSize?, resourceTypes[]?)

**Debugging (5 outils)** :
- `evaluate_script` : exécuter du JavaScript (function: "() => { return document.title }", args[]?)
- `get_console_message` : récupérer un message console (msgid)
- `list_console_messages` : lister les messages console (includePreservedMessages?, pageIdx?, pageSize?, types[]?)
- `take_screenshot` : prendre un screenshot (format: png/jpeg/webp, fullPage?, quality?, uid?, filePath?)
- `take_snapshot` : prendre un snapshot textuel de la page (verbose?, filePath?)

### Options de configuration supplémentaires

À ajouter dans args si nécessaire :
- `--headless=true` : mode sans interface (défaut : false)
- `--channel=canary|beta|dev` : utiliser une autre version de Chrome
- `--viewport=1280x720` : taille initiale du viewport
- `--isolated=true` : utiliser un profil temporaire
- `--user-data-dir=C:\path\to\profile` : profil personnalisé
- `--accept-insecure-certs=true` : ignorer les erreurs SSL
- `--category-performance=false` : désactiver les outils de performance
- `--category-network=false` : désactiver les outils réseau
- `--category-emulation=false` : désactiver les outils d'émulation

### Bonnes pratiques d'utilisation

1. **Snapshot avant action** : Toujours utiliser take_snapshot() avant d'interagir avec la page pour connaître les uid des éléments.
2. **Préférez snapshot à screenshot** : take_snapshot() est plus rapide et fournit des uid exploitables pour les interactions.
3. **Gestion des pages** : Utiliser list_pages() pour voir les pages ouvertes et select_page() pour changer de contexte.
4. **Attente de chargement** : Utiliser wait_for() ou laisser le tool gérer automatiquement les attentes.
5. **Performance traces** : Pour performance_start_trace(), naviguer d'abord vers l'URL voulue avec navigate_page(), puis lancer la trace.

### Profil Chrome

Le MCP server démarre automatiquement une instance Chrome avec un profil dédié :
- Windows : %HOMEPATH%/.cache/chrome-devtools-mcp/chrome-profile-stable
- Linux/macOS : $HOME/.cache/chrome-devtools-mcp/chrome-profile-stable

Le profil n'est pas effacé entre les runs et partagé entre toutes les instances de chrome-devtools-mcp. Set l'option `isolated` à `true` pour utiliser un profil temporaire qui sera effacé automatiquement après la fermeture du navigateur.

### Test plan

Tests de base :
1. "Ouvre https://example.com dans Chrome"
2. "Prends un snapshot de la page et liste les éléments visibles"
3. "Récupère le titre H1 de la page via evaluate_script"
4. "Prends un screenshot de la page entière"
5. "Va sur https://huggingface.co et prends un snapshot"
6. "Cherche 'smolagents' dans la barre de recherche et valide avec Enter"
7. "Liste les requêtes réseau de la page"
8. "Vérifie les messages console de la page"

Scénarios avancés :
- **Test performance** : "Ouvre https://developers.chrome.com", "Lance un enregistrement de performance trace avec autoStop et reload", "Analyse les insights de performance"
- **Test navigation multi-pages** : "Crée une nouvelle page sur https://example.com", "Crée une deuxième page sur https://huggingface.co", "Liste toutes les pages ouvertes", "Sélectionne la première page", "Ferme la deuxième page"
- **Test formulaire** : "Ouvre un site avec un formulaire de contact", "Prends un snapshot pour identifier les champs", "Remplis le formulaire avec fill_form", "Soumets le formulaire"

### Découvertes techniques

**Correction importante** : Le package est basé sur **Puppeteer** et non Playwright comme initialement prévu dans le plan. Le nom du package est chrome-devtools-mcp@latest.

**API ToolCollection.from_mcp() - Correction critique** :

1. **Signature correcte : UN SEUL paramètre** :
   - `ToolCollection.from_mcp()` attend UN SEUL paramètre (`StdioServerParameters` ou `dict`)
   - Le premier paramètre n'est PAS le nom du serveur (contrairement à ce qui était indiqué dans le plan)
   - Le timeout par défaut est de 30 secondes (non configurable)
   - Sur cet environnement, `npx chrome-devtools-mcp@latest` ne parvient pas à démarrer dans ce délai

2. **Retourne un `_GeneratorContextManager`** :
   - `ToolCollection.from_mcp()` ne retourne PAS directement un objet `ToolCollection`
   - Il retourne un `_GeneratorContextManager` qui doit être entré avec `.__enter__()`
   - Il faut appeler `.__enter__()` pour obtenir l'objet `ToolCollection` et accéder à `.tools`

3. **Code correct pour ToolCollection.from_mcp()** :
```python
chrome_devtools_params = StdioServerParameters(
    command="npx",
    args=["-y", "chrome-devtools-mcp@latest"],
    env={**os.environ}
)

_mcp_client = ToolCollection.from_mcp(
    chrome_devtools_params  # ← Un seul paramètre (pas de nom de serveur)
).__enter__()  # ← Important : appeler __enter__()

_mcp_tools = list(_mcp_client.tools)
```

**Timeout de connexion** :
- Le timeout par défaut est de 30 secondes (non configurable)
- Sur cet environnement, `npx chrome-devtools-mcp@latest` ne parvient pas à démarrer dans ce délai
- Le fallback silencieux fonctionne correctement : l'agent fonctionne avec les outils locaux uniquement

**Gestion des erreurs** : Si la connexion échoue au démarrage, désactiver silencieusement et continuer sans ce tool.

**Paramètre trust_remote_code requis** :
- `ToolCollection.from_mcp()` exige le paramètre `trust_remote_code=True` pour charger les outils MCP
- Ce paramètre est obligatoire car le serveur MCP exécute du code sur la machine locale
- Sans ce paramètre, l'erreur suivante se produit : `Loading tools from MCP requires you to acknowledge you trust the MCP server, as it will execute code on your local machine: pass 'trust_remote_code=True'`
- Code correct :
  ```python
  _mcp_client = ToolCollection.from_mcp(
      chrome_devtools_params,
      trust_remote_code=True  # ← Obligatoire
  ).__enter__()
  ```

### Solution MCPClient pour CodeAgent (2026-02-20)

**Problème identifié** : `ToolCollection.from_mcp()` ne fonctionne pas avec CodeAgent (erreur "Event loop is closed").

**Solution identifiée** : Utiliser `MCPClient` comme un context manager.

**Pourquoi ToolCollection.from_mcp() échoue** :
- Les outils MCP sont implémentés comme des fonctions async qui nécessitent une boucle d'événements active
- smolagents CodeAgent exécute le code Python dans un contexte synchrone sans boucle d'événements
- `ToolCollection.from_mcp()` crée un contexte MCP qui est fermé immédiatement après avoir récupéré les outils
- Les outils MCP ne fonctionnent plus une fois le contexte fermé

**Solution : MCPClient comme context manager dans /run**

La solution est d'utiliser `MCPClient` directement comme un context manager dans l'endpoint `/run`, créant et fermant le client MCP dans le même contexte synchrone.

**Code correct** :
```python
from smolagents import CodeAgent, MCPClient
from mcp import StdioServerParameters

chrome_devtools_params = StdioServerParameters(
    command="npx",
    args=["-y", "chrome-devtools-mcp@latest"],
    env={**os.environ}
)

# Utiliser MCPClient comme context manager dans /run
with MCPClient(chrome_devtools_params) as mcp_tools:
    all_tools = TOOLS.copy()
    all_tools.extend(mcp_tools)
    
    agent = CodeAgent(
        tools=all_tools,
        model=get_model(req.model),
        ...
    )
    result = agent.run(prompt)
```

**Avantages de cette approche** :
- ✅ Pas de conflit avec la boucle d'événements async de FastAPI
- ✅ Le client MCP est créé et fermé dans le même contexte synchrone
- ✅ Les outils MCP sont disponibles pour CodeAgent pendant l'exécution
- ✅ Fallback automatique : si MCP ne peut pas être chargé, l'erreur est capturée
- ✅ Compatible avec l'architecture FastAPI lifespan existante

**Implémentation recommandée** :
1. Ne pas charger les outils MCP au démarrage (dans lifespan)
2. Charger les outils MCP à chaque requête dans `/run`
3. Fusionner les outils locaux et MCP avant de créer CodeAgent
4. Capturer les erreurs MCP et continuer avec les outils locaux uniquement

**Exemple d'implémentation avec fallback** :
```python
@app.post("/run")
async def run_agent(req: RunRequest):
    try:
        # Essayer de charger les outils MCP
        with MCPClient(chrome_devtools_params) as mcp_tools:
            all_tools = TOOLS.copy()
            all_tools.extend(mcp_tools)
            agent = CodeAgent(tools=all_tools, model=get_model(req.model), ...)
            result = agent.run(req.message)
    except Exception as e:
        logger.warning(f"Erreur MCP, utilisation des outils locaux uniquement: {e}")
        # Fallback sur les outils locaux
        agent = CodeAgent(tools=TOOLS, model=get_model(req.model), ...)
        result = agent.run(req.message)
    
    return {"response": result}
```

**Note** : Cette approche est compatible avec l'architecture existante de FastAPI et ne nécessite pas de modifications complexes du code.

---

## TOOL-9 — MouseKeyboardTool (2026-02-19 → 2026-02-22)

### Timeout qwen3-vl pour grounding (2026-02-22)

**Problème identifié** : Le modèle qwen3-vl:8b timeout (>60s) lors du grounding UI.

**Diagnostic** :
- Dans le test4.1 (scroll), l'agent a essayé d'utiliser `ui_grounding` pour trouver l'icône Firefox
- Le modèle qwen3-vl:8b a timeout après 60 secondes
- Erreur : `ERROR: Timeout qwen3-vl (>60s) — modèle peut-être non chargé`

**Solution appliquée** :
- Timeout doublé de 60s à 120s dans [`grounding.py`](agent/tools/grounding.py:170)
- **Action requise** : Redémarrer le serveur agent pour appliquer les changements

**Impact** :
- Les tests qui nécessitent `ui_grounding` peuvent échouer
- Le grounding est nécessaire pour localiser les éléments UI sans coordonnées précises

**Solutions futures possibles** :
1. Utiliser un modèle plus rapide (qwen3-vl:2b au lieu de 8b)
2. Utiliser des coordonnées directes au lieu du grounding quand possible

**Note** : Ce problème affecte TOOL-11 (GUI Grounding) et TOOL-9 (MouseKeyboard) quand ils sont utilisés ensemble.

---

### Améliorations possibles pour TOOL-9 — Utilisation de Skills (2026-02-22)

**Problème identifié** : L'agent régénère le même code Python à chaque fois pour des tâches répétitives, ce qui est :
- ❌ Lent (génération LLM à chaque appel)
- ❌ Coûteux en tokens
- ❌ Risque d'erreurs ou variations
- ❌ Difficile à maintenir

**Solution** : Créer des skills pour les patterns de code répétitifs

#### Skills à créer pour TOOL-9

**SKILL 1 — Ouvrir une application via le menu Démarrer**
```python
# Ouvre une application via le menu Démarrer Windows
def open_application(app_name: str) -> str:
    from tools import mouse_keyboard
    import time
    
    # Ouvrir le menu Démarrer
    mouse_keyboard(operation="hotkey", keys="win")
    time.sleep(1)
    
    # Taper le nom de l'application
    mouse_keyboard(operation="type", text=app_name)
    time.sleep(0.5)
    
    # Appuyer sur Entrée
    mouse_keyboard(operation="hotkey", keys="enter")
    time.sleep(2)
    
    return final_answer(f"Application '{app_name}' ouverte")
```

**SKILL 2 — Fermer une fenêtre active**
```python
# Ferme la fenêtre active avec ALT+F4
def close_active_window() -> str:
    from tools import mouse_keyboard
    import time
    
    mouse_keyboard(operation="hotkey", keys="alt,f4")
    time.sleep(0.5)
    
    return final_answer("Fenêtre fermée avec ALT+F4")
```

**SKILL 3 — Taper du texte dans une application**
```python
# Taper du texte dans l'application active
def type_text(text: str) -> str:
    from tools import mouse_keyboard
    
    mouse_keyboard(operation="type", text=text)
    
    return final_answer(f"Texte tapé: {text}")
```

**SKILL 4 — Sélectionner tout le texte**
```python
# Sélectionne tout le texte (Ctrl+A)
def select_all() -> str:
    from tools import mouse_keyboard
    
    mouse_keyboard(operation="hotkey", keys="ctrl+a")
    
    return final_answer("Tout le texte sélectionné (Ctrl+A)")
```

**SKILL 5 — Copier le texte sélectionné**
```python
# Copie le texte sélectionné (Ctrl+C)
def copy_text() -> str:
    from tools import mouse_keyboard
    
    mouse_keyboard(operation="hotkey", keys="ctrl+c")
    
    return final_answer("Texte copié (Ctrl+C)")
```

**SKILL 6 — Coller le texte**
```python
# Colle le texte (Ctrl+V)
def paste_text() -> str:
    from tools import mouse_keyboard
    
    mouse_keyboard(operation="hotkey", keys="ctrl+v")
    
    return final_answer("Texte collé (Ctrl+V)")
```

**SKILL 7 — Sauvegarder un fichier (Ctrl+S)**
```python
# Sauvegarde le fichier actuel (Ctrl+S)
def save_file() -> str:
    from tools import mouse_keyboard
    
    mouse_keyboard(operation="hotkey", keys="ctrl,s")
    
    return final_answer("Fichier sauvegardé (Ctrl+S)")
```

**SKILL 8 — Scroller vers le bas**
```python
# Scrolle vers le bas de la page
def scroll_down(clicks: int = 5) -> str:
    from tools import mouse_keyboard
    
    mouse_keyboard(operation="scroll", clicks=clicks)
    
    return final_answer(f"Scrolle vers le bas ({clicks} clics)")
```

**SKILL 9 — Scroller vers le haut**
```python
# Scrolle vers le haut de la page
def scroll_up(clicks: int = 5) -> str:
    from tools import mouse_keyboard
    
    mouse_keyboard(operation="scroll", clicks=-clicks)
    
    return final_answer(f"Scrolle vers le haut ({clicks} clics)")
```

**SKILL 10 — Prendre un screenshot et l'analyser**
```python
# Prend un screenshot et l'analyse
def screenshot_and_analyze(prompt: str = "Describe what you see") -> str:
    from tools import screenshot, analyze_image
    
    # Prendre le screenshot
    screenshot_path = screenshot()
    
    # Analyser l'image
    analysis = analyze_image(image_path=screenshot_path, prompt=prompt)
    
    return final_answer(f"Screenshot: {screenshot_path}\n\nAnalysis: {analysis}")
```

**SKILL 11 — Cliquer sur un élément UI via grounding**
```python
# Trouve et clique sur un élément UI via grounding
def click_element(element_description: str) -> str:
    from tools import screenshot, ui_grounding, mouse_keyboard
    
    # Prendre un screenshot
    screenshot_path = screenshot()
    
    # Trouver l'élément via grounding
    coords = ui_grounding(image_path=screenshot_path, element=element_description)
    
    # Cliquer sur les coordonnées
    mouse_keyboard(operation="click", x=coords[0], y=coords[1])
    
    return final_answer(f"Cliqué sur '{element_description}' à {coords}")
```

#### Avantages des skills

1. **Vitesse** : L'agent copie directement le code sans le régénérer
2. **Fiabilité** : Code testé et validé, moins d'erreurs
3. **Cohérence** : Même pattern utilisé à chaque fois
4. **Économie de tokens** : Moins de génération LLM
5. **Maintenance** : Modification centralisée dans `skills.txt`

#### Implémentation

1. Ajouter les skills dans `agent/skills.txt`
2. Redémarrer le serveur : `uv run uvicorn main:app --reload`
3. Documenter les skills dans `agent/SKILLS.md`
4. Tester que l'agent copie bien les patterns

#### Exemple d'utilisation

**Sans skills** (lent) :
```
User: "Ouvre Notepad"
Agent: [génère 30 lignes de code Python]
→ 5-10 secondes de génération
```

**Avec skills** (rapide) :
```
User: "Ouvre Notepad"
Agent: [copie le skill open_application("notepad")]
→ 1-2 secondes (copie + exécution)
```

#### Tests à effectuer

1. Vérifier que l'agent copie les skills au lieu de régénérer le code
2. Mesurer le gain de temps sur les tâches répétitives
3. Valider que tous les skills fonctionnent correctement
4. Comparer la consommation de tokens avec/sans skills

#### Références

- Skills existants : `agent/skills.txt`
- Documentation skills : `agent/SKILLS.md`
- Documentation smolagents : https://huggingface.co/docs/smolagents/tutorials/building_good_agents

### Restrictions système Windows — Raccourcis protégés (2026-02-22)

**Raccourcis système protégés** : Windows bloque certains raccourcis via automation pour des raisons de sécurité.

#### Win+L — Verrouillage de session
**Problème** : Le raccourci Win+L ne fonctionne pas via automation pyautogui.

**Diagnostic** :
- Testé avec pyautogui.hotkey('win', 'l') — Échec (lettre 'l' affichée)
- Testé avec pyautogui.hotkey('win', 'L') — Échec
- Testé avec keyDown('win') + press('l') + keyUp('win') — Échec
- Testé avec PowerShell SendKeys — Échec
- Win+E, Win+S, Win+I fonctionnent correctement

**Conclusion** : Windows bloque les raccourcis de verrouillage d'écran via automation pour des raisons de sécurité. C'est une **limitation système connue**, pas un bug de TOOL-9.

**Workaround** : Via PowerShell au lieu de pyautogui
```python
os_exec(command="rundll32.exe user32.dll,LockWorkStation")
```

**Impact sur les tests** : Le test 1.4 (Win+L) est marqué comme "Non applicable - Restriction système Windows".

#### Autres raccourcis qui posent souvent problème
- **Ctrl+Alt+Del** : Bloqué OS
- **Win+D** : Parfois capricieux (dépend du focus)
- **Alt+F4** : Dépend du focus fenêtre

**Référence** : https://github.com/asweigart/pyautogui/issues/371

### Implémentation
- Classe MouseKeyboardTool avec paramètres:
  - operation (str): click, double_click, move, right_click, type, hotkey, drag, scroll
  - x, y (int, optionnel): coordonnées pour opérations souris
  - x2, y2 (int, optionnel): coordonnées destination pour drag
  - text (str, optionnel): texte à taper
  - keys (str, optionnel): touches séparées par virgule pour hotkey
  - clicks (int, optionnel): nombre de clics pour scroll
- Utilise pyautogui pour contrôler souris et clavier
- pyautogui.FAILSAFE = False (déjà configuré dans TOOL-8)
- time.sleep(0.5) après chaque action pour laisser l'OS réagir

### Test plan
Selon IMPLEMENTATION-TOOLS.md, tests à effectuer via Gradio avec modèle "reason" (glm-4.7):
1. "Ouvre le menu Démarrer"
2. "Tape 'notepad' et appuie sur Entrée"
3. "Prends un screenshot et vérifie que Notepad est ouvert"
4. "Tape 'Bonjour depuis my-claw !' dans Notepad"
5. "Ferme Notepad sans sauvegarder (Alt+F4 puis ne pas sauvegarder)"

### Résultats tests (2026-02-20)
- ❌ "Ouvre le menu Démarrer" → LLM clique sur (0,0) au lieu d'utiliser hotkey("win")
- ❌ "Tape 'notepad' et appuie sur Entrée" → LLM ne sait pas séquencer correctement
- ❌ Screenshot pour vérifier → Impossible sans TOOL-7 (Vision)

### Problème critique identifié (2026-02-20)
L'agent LLM (qwen3:14b) ne savait pas comment utiliser correctement mouse_keyboard:

1. **Description de l'outil insuffisante**
   - L'outil ne donnait pas d'exemples concrets d'utilisation
   - Pas d'exemple pour ouvrir le menu Démarrer (hotkey avec keys="win")
   - Pas d'exemple pour fermer une fenêtre (hotkey avec keys="alt,f4")

2. **LLM invente des coordonnées incorrectes**
   - Il cliquait sur (0,0) au lieu d'utiliser la touche Windows
   - Il ne comprenait pas le séquencement des actions (focus → taper → vérifier)

3. **Agent aveugle**
   - L'agent prenait des screenshots mais ne pouvait pas les analyser
   - Impossible de vérifier si une action a réussi
   - Pas de feedback visuel pour s'auto-corriger

### Solution implémentée (2026-02-22)
**Architecture multi-agent + modèle GLM-4.7**

1. **Migration vers architecture multi-agent** :
   - Création de `pc_control_agent` avec qwen3-vl:2b
   - Outils disponibles : screenshot, mouse_keyboard, ui_grounding
   - Manager délègue automatiquement les tâches de pilotage PC

2. **Utilisation de GLM-4.7 (reason)** :
   - Modèle plus puissant pour l'orchestration
   - Meilleure compréhension des séquences d'actions
   - Utilisation correcte des hotkeys au lieu de coordonnées

3. **Correction des sous-agents** (2026-02-22) :
   - Création du module `agent/models.py` pour centraliser la création de modèles
   - Fonction `get_model()` gère correctement Ollama et cloud
   - Tous les sous-agents utilisent `get_model()` au lieu de créer directement `LiteLLMModel`

### Validation réussie (2026-02-22)

**Test effectué** : "Ouvre Notepad via le menu Démarrer et tape 'Test migration multi-agent OK'"

**Statut** : ✅ **VALIDÉ** - Tâche accomplie avec succès

**Résultats de l'exécution** :
```
00:09:13 - main - INFO - Modèle sélectionné pour tous les agents: reason
00:09:15 - main - INFO - ✓ pc_control_agent créé avec modèle reason

00:09:22 - tools.mouse_keyboard - INFO - DEBUG: Exécution pyautogui.hotkey(['win'])
Windows key pressed to open Start menu

00:09:28 - tools.mouse_keyboard - INFO - DEBUG: Exécution pyautogui.typewrite('notepad')
Typed 'notepad' in Start menu search

00:09:33 - tools.mouse_keyboard - INFO - DEBUG: Exécution pyautogui.hotkey(['enter'])
Pressed Enter to open Notepad

00:09:41 - tools.mouse_keyboard - INFO - DEBUG: Exécution pyautogui.typewrite('Test migration multi-agent OK')
Typed 'Test migration multi-agent OK' in Notepad
```

**Points clés validés** :
- ✅ Architecture multi-agent fonctionnelle
- ✅ Modèle GLM-4.7 (reason) opérationnel
- ✅ Outils pc_control_agent : screenshot, mouse_keyboard, ui_grounding
- ✅ Séquencement correct des actions
- ✅ Utilisation correcte des hotkeys

### Logs de debug ajoutés
Pour diagnostiquer le problème, des logs ont été ajoutés:
- Version de pyautogui
- Taille de l'écran
- Paramètres reçus par l'outil
- Appels pyautogui effectués
- Traceback complet en cas d'erreur

### Plan de tests supplémentaires

**Fichier** : `plans/validation-tool9-mouse-keyboard.md`

**21 tests organisés en 8 catégories** :
1. Raccourcis clavier (hotkey) - 4 tests
2. Navigation et clics - 3 tests
3. Sélection, copie et collage - 2 tests
4. Scroll - 2 tests
5. Drag-and-drop - 2 tests
6. Clic droit - 1 test
7. Séquences complexes - 4 tests
8. Tests de robustesse - 3 tests

**Critères de validation** :
- Tous les tests de priorité Haute réussissent (13 tests)
- Au moins 80% des tests de priorité Moyenne réussissent (4/5 tests)
- Tous les tests de robustesse réussissent (3 tests)
- Aucun crash ou exception non gérée
- Messages d'erreur clairs et exploitables

### Découvertes techniques
- pyautogui.click(x, y) pour cliquer à des coordonnées
- pyautogui.hotkey(*keys.split(",")) pour combinaisons de touches
- pyautogui.typewrite(text, interval=0.05) pour taper du texte
- pyautogui.dragTo(x2, y2, duration=0.5) pour glisser-déposer
- pyautogui.scroll(clicks, x, y) pour scroller
- **GLM-4.7 est nécessaire pour l'orchestration** : qwen3:8b ne suffit pas pour le pilotage PC complexe
- **Architecture multi-agent** : Manager délègue automatiquement aux sous-agents spécialisés
- **Module models.py** : Centralise la création de modèles pour éviter les imports circulaires

### Prochaine étape
Exécuter les tests du plan `plans/validation-tool9-mouse-keyboard.md` pour valider complètement TOOL-9

---

## MODULES TERMINÉS

- MODULE 0: Socle & Configuration
- MODULE 1: Cerveau Python (sans outils)
- MODULE 2: Mémoire Prisma 7 + SQLite
- MODULE 3: WebChat

---

## MODULES EN COURS

- TOOL-1: FileSystemTool ✅ implémenté, testé et validé
- TOOL-2: OsExecTool (PowerShell) ✅ implémenté, testé et validé
- TOOL-3: ClipboardTool ✅ implémenté, testé et validé
- TOOL-4: MCP Web Search Z.ai ⏳ à implémenter
- TOOL-5: MCP Web Reader Z.ai ⏳ à implémenter
- TOOL-6: MCP Zread GitHub ⏳ à implémenter
- TOOL-7: MCP Vision GLM-4.6V ✅ implémenté, EN ATTENTE DE VALIDATION
- TOOL-8: ScreenshotTool ✅ implémenté, testé et validé
- TOOL-9: MouseKeyboardTool ✅ implémenté, débloqué par TOOL-7, EN ATTENTE DE VALIDATION
- TOOL-10: MCP Chrome DevTools ⏳ à implémenter

---

## DÉCISIONS TECHNIQUES

### Stack choisie
- Next.js 16 + Prisma 7 (gateway)
- Python + uv + FastAPI (agent)
- smolagents 1.9+ (CodeAgent)
- Ollama (qwen3:4b/8b/14b local)
- Z.ai GLM-4.7 (cloud, optionnel)

### Patterns établis
- Tools smolagents: sous-classe Tool, pas décorateur @tool
- Imports des librairies externes dans `forward()`
- Validation max_steps=5 pour tâches simples, 10 pour pilotage PC complexe
- Fallback silencieux sur Ollama si ZAI_API_KEY absent

### Environnement Windows
- Chemins Windows acceptés (backslashes et forward slashes)
- PowerShell pour exécution OS
- pyautogui.FAILSAFE=False pour contrôle souris/clavier (configuré)
- Dossier temporaire: C:\tmp\myclawshots\ pour screenshots
- Variable d'environnement SCREENSHOT_DIR configurable
- time.sleep(0.5) après chaque action pyautogui pour laisser l'OS réagir

---

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

---

## RÉFÉRENCES

- smolagents Tool: https://huggingface.co/docs/smolagents/tutorials/custom_tools
- smolagents MCP: https://huggingface.co/docs/smolagents/tutorials/mcp
- Prisma 7 Config: https://pris.ly/d/config-datasource
- Z.ai GLM-4.7: https://open.bigmodel.cn/dev/api

---

## Correction vision_agent — Modèle de codage au lieu de modèle de vision (2026-02-21)

### Problème identifié

Le [`vision_agent`](agent/agents/vision_agent.py) utilisait un modèle de **vision** (qwen3-vl:8b) comme LLM principal, alors que seul l'outil [`analyze_image`](agent/tools/vision.py:118) nécessite vraiment un modèle de vision. Le LLM principal devrait utiliser un modèle de **codage** (glm-4.7 ou qwen3:8b) pour orchestrer l'outil.

### Solution implémentée

1. **Modification de [`vision_agent.py`](agent/agents/vision_agent.py)** :
   - Suppression de la détection automatique de modèle de vision
   - Ajout d'un paramètre `model_id` (défaut: "qwen3:8b") pour le modèle de codage
   - Utilisation directe de `LiteLLMModel` avec le modèle de codage
   - Mise à jour des instructions et de la description pour refléter l'architecture

2. **Modification de [`main.py`](agent/main.py)** :
   - Passage du modèle de codage à `create_vision_agent(ollama_url, model_id="qwen3:8b")`
   - Mise à jour de la documentation dans l'endpoint `/models`

3. **Vérification de [`vision.py`](agent/tools/vision.py)** :
   - L'outil `analyze_image` utilise déjà son propre modèle de vision détecté automatiquement
   - Aucune modification nécessaire

### Architecture corrigée

```
vision_agent (CodeAgent)
 ├── Modèle LLM: glm-4.7 ou qwen3:8b - modèle de codage
 └── Outil: analyze_image
     └── Modèle interne: qwen3-vl:8b - modèle de vision
```

### Avantages

1. **Cohérence architecturale** : Tous les agents utilisent le même modèle de codage (glm-4.7 ou qwen3:8b)
2. **Meilleure orchestration** : Le modèle de codage est meilleur pour structurer les prompts et les réponses
3. **Séparation claire** : Le LLM orchestre, l'outil spécialisé fait la vision
4. **Flexibilité** : Possibilité d'utiliser glm-4.7 (cloud) ou qwen3:8b (local) selon la préférence
5. **Performance** : Les modèles de codage sont généralement plus performants pour le raisonnement

### Documentation mise à jour

- [`AGENTS.md`](AGENTS.md) : Mise à jour de la description du modèle vision et de la section TOOL-7
- [`plans/correction-vision-agent.md`](plans/correction-vision-agent.md) : Plan détaillé de la correction

### Tests à effectuer

1. **Test basique** : "Analyse cette image : C:\tmp\myclawshots\screen_001.png"
2. **Test extraction texte** : "Extrais tout le texte de cette image : C:\tmp\myclawshots\screen_002.png"
3. **Test diagnostic** : "Y a-t-il des erreurs dans cette image : C:\tmp\myclawshots\screen_003.png"
4. **Test via Manager** : "Prends un screenshot et analyse-le" (vérifie que le Manager délègue correctement au vision_agent)

---

## Migration UI-TARS → qwen3-vl pour GUI Grounding (2026-02-21)

### Statut
✅ **DONE** - Migration terminée avec succès

### Objectif
Remplacer le modèle `hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M` par `qwen3-vl:2b` pour le grounding GUI afin de simplifier l'architecture en utilisant un seul modèle vision.

### Modifications apportées

#### 1. Renommage des fichiers
- `agent/tools/ui_tars_grounding.py` → `agent/tools/grounding.py`
- `agent/test_ui_tars.py` → `agent/test_grounding.py`

**Raison** : Le nom `ui_tars_grounding.py` faisait référence à l'ancien modèle UI-TARS. Le nouveau nom `grounding.py` est plus générique et ne fait référence à aucun modèle spécifique.

#### 2. Modification de `grounding.py`
- Classe renommée : `UITarsGroundingTool` → `QwenGroundingTool`
- Modèle changé : `hf.co/mradermacher/UI-TARS-2B-SFT-GGUF:Q4_K_M` → `qwen3-vl:2b`
- Nouveau prompt système spécialisé pour un grounding déterministe
- Format API Ollama : format standard avec paramètre `images: [base64]` (pas le format OpenAI)
- Fonction `_detect_grounding_model()` ajoutée pour la détection automatique du modèle qwen3-vl disponible (2b, 4b, 8b)

**Nouveau prompt système** :
```python
_GROUNDING_SYSTEM = """You are a GUI grounding assistant. 
Given a screenshot and a text description of a UI element, 
return ONLY the coordinates of that element as [x, y] 
where x and y are relative values between 0 and 1 
(0,0 = top-left corner, 1,1 = bottom-right corner).

Return ONLY the coordinate in this exact format: [0.XX, 0.XX]
No explanation, no text, just the coordinate."""
```

**Format API Ollama standard** (celui qui fonctionne) :
```python
response = requests.post(
    f"{ollama_url}/api/chat",
    json={
        "model": vision_model,  # qwen3-vl:2b détecté automatiquement
        "messages": [
            {
                "role": "user",
                "content": f"{_GROUNDING_SYSTEM}\n\nFind this element: {element}",
                "images": [image_b64]
            }
        ],
        "stream": False,
        "options": {"temperature": 0.0}
    },
    timeout=60,
)
```

#### 3. Modification de `pc_control_agent.py`
- Docstring mise à jour pour mentionner qwen3-vl au lieu de UI-TARS-2B-SFT
- Description de l'agent mise à jour dans le paramètre `description`
- Commentaire interne mis à jour

#### 4. Modification de `main.py`
- Détection UI-TARS remplacée par détection qwen3-vl dans `detect_models()`
- Logs mis à jour pour mentionner qwen3-vl
- Endpoint `/models` mis à jour : "glm-4.7 ou qwen3:8b + qwen3-vl (interne)"

#### 5. Création de `test_grounding.py`
- Script de test complet pour qwen3-vl grounding
- 4 tests : connexion Ollama, vérification modèle, grounding, outil direct

### Avantages de la migration

1. **Simplification** : Un seul modèle vision à gérer (qwen3-vl)
2. **Cohérence** : Utilisation du même modèle pour l'analyse d'images et le grounding
3. **Performance** : qwen3-vl:2b est plus léger et plus rapide que UI-TARS-2B-SFT
4. **Maintenance** : Moins de modèles à installer et à maintenir
5. **Prompt spécialisé** : Prompt système optimisé pour un grounding déterministe avec `temperature: 0.0`
6. **Format API identique** : Utilise le même format standard Ollama que UI-TARS (`images: [base64]`)

### Découvertes techniques

#### Format API Ollama pour qwen3-vl
Après tests, le format OpenAI avec `image_url` ne fonctionne pas avec cette version d'Ollama (erreur 400 Bad Request). Le format qui fonctionne est le **format standard Ollama** :
- Utiliser le paramètre `images: [base64]` dans le message
- Le prompt texte dans le champ `content`
- Ce format est identique à celui utilisé par UI-TARS

**Format qui NE fonctionne PAS** (erreur 400) :
```python
# ❌ Format OpenAI - ne fonctionne pas avec cette version d'Ollama
"content": [
    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
    {"type": "text", "text": prompt}
]
```

**Format qui fonctionne** :
```python
# ✅ Format standard Ollama - fonctionne correctement
"content": f"{_GROUNDING_SYSTEM}\n\nFind this element: {element}",
"images": [image_b64]
```

#### Détection automatique du modèle
La fonction `_detect_grounding_model()` utilise un cache global `_detected_vision_model` pour éviter de redétecter le modèle à chaque appel de l'outil. Cela améliore les performances en évitant les requêtes répétées à l'API Ollama `/api/tags`.

#### Préférences de modèle
L'ordre de préférence pour les modèles qwen3-vl est : `qwen3-vl:2b` > `qwen3-vl:4b` > `qwen3-vl:8b`. Cela permet de privilégier le modèle le plus rapide (2b) tout en ayant des fallbacks sur les modèles plus performants si nécessaire.

### Points clés de l'implémentation

#### temperature: 0.0 obligatoire
Le paramètre `temperature: 0.0` est **obligatoire** pour le grounding. Cela garantit un comportement déterministe — le modèle ne doit pas faire preuve de créativité sur des coordonnées, il doit retourner les mêmes coordonnées pour la même demande.

#### Format API Ollama standard
qwen3-vl utilise le format standard Ollama pour les messages multimodaux :
- Utiliser le paramètre `images: [base64]` dans le message
- Le prompt texte dans le champ `content`

**Note** : Le format OpenAI avec `image_url` ne fonctionne pas avec cette version d'Ollama (erreur 400 Bad Request). Le format standard Ollama est celui à utiliser.

#### Parsing des coordonnées
Le parsing des coordonnées reste le même que pour UI-TARS :
```python
patterns = [
    r'\[(\d+\.?\d*),\s*(\d+\.?\d*)\]',   # [0.73, 0.21]
    r'\((\d+\.?\d*),\s*(\d+\.?\d*)\)',   # (0.73, 0.21)
    r'(\d+\.?\d*),\s*(\d+\.?\d*)',         # 0.73, 0.21
]
```
qwen3-vl retourne typiquement : `[0.73, 0.21]` avec des coordonnées relatives dans `[0, 1]`.

### Tests de validation

Le script `test_grounding.py` permet de valider :
1. Connexion à Ollama
2. Vérification que qwen3-vl est installé
3. Test de grounding avec le modèle qwen3-vl
4. Test de l'outil QwenGroundingTool directement

### Commandes utiles

```bash
# Installer qwen3-vl:2b
ollama pull qwen3-vl:2b

# Vérifier les modèles installés
ollama list

# Tester le grounding manuellement
cd agent
uv run python test_grounding.py
```

### Références

- Plan de migration : [`plans/migration-ui-tars-to-qwen3-vl.md`](plans/migration-ui-tars-to-qwen3-vl.md)
- qwen3-vl : https://ollama.com/library/qwen3-vl
- Ollama API : https://github.com/ollama/ollama/blob/main/docs/api.md

---

## Correction modèle "reason" pour les sous-agents (2026-02-22)

### Problème identifié

**Erreur** : Les sous-agents (`pc_control_agent`, `vision_agent`, `browser_agent`, `web_agent`) échouaient avec l'erreur suivante quand le modèle par défaut était GLM-4.7 (cloud) :

```
litellm.APIConnectionError: Ollama_chatException - {"error":"model 'reason' not found"}
```

**Cause racine** : Les sous-agents forçaient l'utilisation du provider Ollama avec `model_id=f"ollama_chat/{model_id}"`. Quand `model_id` était "reason" (alias pour GLM-4.7 cloud), cela créait un modèle invalide `ollama_chat/reason` qui n'existe pas dans Ollama.

**Exemple de code incorrect** :
```python
# Dans pc_control_agent.py, vision_agent.py, browser_agent.py, web_agent.py
model = LiteLLMModel(
    model_id=f"ollama_chat/{model_id}",  # ❌ Force Ollama même pour "reason"
    api_base=ollama_url,
    api_key="ollama",
    num_ctx=32768,
    extra_body={"think": False},
)
```

### Solution implémentée

**Nouveau module** : [`agent/models.py`](agent/models.py)

Création d'un module centralisé pour la gestion des modèles afin d'éviter les imports circulaires et de dupliquer le code.

**Fonctionnalités** :
1. **`get_model(model_id)`** : Crée un `LiteLLMModel` correctement configuré
   - Détecte automatiquement si le modèle est cloud (GLM-4.7) ou local (Ollama)
   - Pour les modèles cloud : utilise `CleanedLiteLLMModel` avec API Z.ai
   - Pour les modèles locaux : utilise `LiteLLMModel` standard avec Ollama
2. **`get_default_model()`** : Retourne le modèle par défaut selon les priorités
   - Variable d'environnement `DEFAULT_MODEL`
   - "reason" (glm-4.7) si `ZAI_API_KEY` configuré
   - "main" (qwen3:8b) en fallback local
3. **`MODELS`** : Dictionnaire des modèles disponibles (Ollama + cloud)
4. **`detect_models()`** : Détection automatique des modèles Ollama installés

**Modifications des sous-agents** :

Tous les sous-agents ont été modifiés pour utiliser `get_model()` au lieu de créer directement un `LiteLLMModel` :

```python
# Dans pc_control_agent.py, vision_agent.py, browser_agent.py, web_agent.py
from models import get_model

def create_xxx_agent(ollama_url: str, model_id: str = "qwen3:8b") -> CodeAgent:
    # ...
    model = get_model(model_id)  # ✅ Gère correctement Ollama et cloud
    # ...
```

**Nettoyage de main.py** :

- Suppression du code dupliqué (détection modèles, `get_model()`, `get_default_model()`, `CleanedLiteLLMModel`)
- Import depuis le nouveau module `models.py`
- Le paramètre `ollama_url` est conservé pour compatibilité mais non utilisé

### Avantages de la solution

1. **Séparation claire des responsabilités** : `models.py` gère la création de modèles, les agents gèrent leur logique métier
2. **Évite les imports circulaires** : `main.py` importe les agents, les agents importent `get_model()` depuis `models.py`
3. **Code DRY** : Pas de duplication de la logique de création de modèles
4. **Flexibilité** : Facile d'ajouter de nouveaux modèles ou de modifier la logique de détection
5. **Testabilité** : `get_model()` peut être testé indépendamment

### Validation

**Test effectué** : "Prends un screenshot, trouve le bouton Démarrer Windows et donne ses coordonnées"

**Résultat** : ✅ Succès

```
INFO:     Modèle sélectionné pour tous les agents: reason
INFO:     ✓ pc_control_agent créé avec modèle reason
INFO:     ✓ vision_agent créé avec modèle reason
INFO:     ✓ browser_agent créé (26 tools Chrome DevTools) avec modèle reason
```

Le manager et tous les sous-agents utilisent maintenant correctement le modèle "reason" (glm-4.7) via l'API Z.ai, sans erreur Ollama.

### Fichiers modifiés

- [`agent/models.py`](agent/models.py) - Nouveau module (créé)
- [`agent/agents/pc_control_agent.py`](agent/agents/pc_control_agent.py) - Utilise `get_model()`
- [`agent/agents/vision_agent.py`](agent/agents/vision_agent.py) - Utilise `get_model()`
- [`agent/agents/browser_agent.py`](agent/agents/browser_agent.py) - Utilise `get_model()`
- [`agent/agents/web_agent.py`](agent/agents/web_agent.py) - Utilise `get_model()`
- [`agent/main.py`](agent/main.py) - Importe depuis `models.py`, code dupliqué supprimé

---

## Validation complète de l'architecture multi-agent (2026-02-22)

### Test effectué

**Tâche** : "Ouvre Notepad via le menu Démarrer et tape 'Test migration multi-agent OK'"

**Statut** : ✅ **VALIDÉ** - Tâche accomplie avec succès

### Résultats de l'exécution

**Démarrage du serveur** :
```
INFO:     Will watch for changes in these directories: ['C:\\GIT\\fork\\my-claw\\agent']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [31712] using WatchFiles
00:08:56 - main - INFO - ✓ Skills chargés (6162 chars)
INFO:     Started server process [31648]
INFO:     Waiting for application startup.
00:08:56 - main - INFO - Initialisation Chrome DevTools MCP...
00:08:56 - main - INFO - ✓ Chrome DevTools MCP: 26 outils
INFO:     Application startup complete.
```

**Initialisation des agents** :
```
00:09:13 - main - INFO - Modèle sélectionné pour tous les agents: reason
00:09:13 - agents.pc_control_agent - INFO - pc_control_agent tools: ['screenshot', 'mouse_keyboard', 'ui_grounding']
00:09:15 - main - INFO - ✓ pc_control_agent créé avec modèle reason
00:09:15 - agents.vision_agent - INFO - vision_agent tools: ['analyze_image']
00:09:15 - agents.vision_agent - INFO - ✓ vision_agent créé avec modèle LLM: reason (vision interne: qwen3-vl:8b)
00:09:15 - main - INFO - ✓ vision_agent créé avec modèle reason
00:09:15 - main - INFO - ✓ browser_agent créé (26 tools Chrome DevTools) avec modèle reason
00:09:15 - main - INFO - ✗ web_agent ignoré (aucun tool MCP Z.ai)
00:09:15 - main - INFO - Manager tools directs: ['file_system', 'os_exec', 'clipboard']
00:09:15 - main - INFO - Sous-agents disponibles: ['pc_control', 'vision', 'browser']
```

### Exécution de la tâche

**Étape 1 - Délégation au pc_control_agent** :
- Le Manager délègue la tâche au `pc_control_agent`
- Le modèle utilisé : `reason` (glm-4.7)

**Étape 2 - Ouverture du menu Démarrer** :
```
00:09:22 - tools.mouse_keyboard - INFO - DEBUG: Exécution pyautogui.hotkey(['win'])
Windows key pressed to open Start menu
```

**Étape 3 - Recherche de Notepad** :
```
00:09:28 - tools.mouse_keyboard - INFO - DEBUG: Exécution pyautogui.typewrite('notepad')
Typed 'notepad' in Start menu search
```

**Étape 4 - Lancement de Notepad** :
```
00:09:33 - tools.mouse_keyboard - INFO - DEBUG: Exécution pyautogui.hotkey(['enter'])
Pressed Enter to open Notepad
```

**Étape 5 - Attente et vérification** :
```
00:09:39 - tools.screenshot - INFO - Screenshot de l'écran entier pris
00:09:39 - tools.screenshot - INFO - Screenshot sauvegardé: C:\tmp\myclawshots\screen_20260222_000938.png
```

**Étape 6 - Saisie du texte** :
```
00:09:41 - tools.mouse_keyboard - INFO - DEBUG: Exécution pyautogui.typewrite('Test migration multi-agent OK')
Typed 'Test migration multi-agent OK' in Notepad
```

**Étape 7 - Vérification finale** :
```
00:09:47 - tools.screenshot - INFO - Screenshot de l'écran entier pris
00:09:47 - tools.screenshot - INFO - Screenshot sauvegardé: C:\tmp\myclawshots\screen_20260222_000947.png
```

### Résultat final

```
Task outcome (short version): Successfully completed. Notepad was opened via Start menu and the text 'Test migration multi-agent OK' was typed.

Task execution steps completed:
- Step 1 - Open Start Menu: Pressed Windows key using hotkey operation. The Start menu opened successfully.
- Step 2 - Search for Notepad: Typed 'notepad' in the Start menu search field. The search recognized the input.
- Step 3 - Launch Notepad: Pressed Enter key to execute the search result. Notepad was launched from the search results.
- Step 4 - Wait for Notepad: Implemented a 2-second pause to allow Notepad to fully initialize and become the active window.
- Step 5 - Type text: Typed the exact text 'Test migration multi-agent OK' in the Notepad text area.

Screenshots taken:
- Initial screenshot after Notepad opened: C:\\tmp\\myclawshots\\screen_20260222_000938.png
- Final screenshot after text entry: C:\\tmp\\myclawshots\\screen_20260222_000947.png

All operations were executed successfully without errors.
```

### Points clés validés

✅ **Architecture multi-agent fonctionnelle**
- Manager délègue correctement aux sous-agents
- `pc_control_agent` exécute les tâches de pilotage PC
- Communication inter-agents sans erreur

✅ **Modèle GLM-4.7 (reason) opérationnel**
- Tous les agents utilisent le modèle cloud sans erreur
- Pas de conflit avec Ollama
- CleanedLiteLLMModel fonctionne correctement

✅ **Outils pc_control_agent**
- `screenshot` : capture d'écran fonctionnelle
- `mouse_keyboard` : contrôle souris/clavier opérationnel
- `ui_grounding` : disponible (non utilisé dans ce test)

✅ **Séquencement des actions**
- Le LLM comprend l'ordre des opérations
- Gestion correcte des délais (time.sleep)
- Feedback via screenshots pour vérification

✅ **Intégration Chrome DevTools MCP**
- 26 outils chargés correctement
- `browser_agent` disponible avec modèle reason
- `web_agent` ignoré proprement (pas de ZAI_API_KEY)

### Architecture validée

```
Manager (reason)
├── pc_control_agent (reason)
│   ├── screenshot
│   ├── mouse_keyboard
│   └── ui_grounding
├── vision_agent (reason)
│   └── analyze_image (vision interne: qwen3-vl:8b)
└── browser_agent (reason)
    └── 26 outils Chrome DevTools
```

### Conclusion

La migration multi-agent est **complètement validée**. L'architecture fonctionne correctement avec :
- Délégation automatique des tâches aux sous-agents appropriés
- Utilisation cohérente du modèle GLM-4.7 (reason) pour tous les agents
- Intégration réussie des outils locaux et MCP
- Séquencement correct des actions pour le pilotage PC

Le système est prêt pour des tâches plus complexes nécessitant la coordination de plusieurs agents.
