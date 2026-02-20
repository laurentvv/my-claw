# LEARNING.md — Découvertes my-claw

> Document de mémoire technique pour le développement my-claw
> À mettre à jour après chaque module/feature implémenté

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
- **Résultat** : L'agent préfère écrire du code Python natif plutôt que d'appeler des commandes système
- Cela évite les problèmes de compatibilité PowerShell/Bash et simplifie le code généré
- **Documentation** : https://huggingface.co/docs/smolagents/tutorials/building_good_agents

**Timeouts configurés** :
- **Gateway → Agent** : 360 secondes (6 minutes) dans `gateway/lib/agent-client.ts` - Augmenté pour GLM-4.7 screenshot+vision
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

## TOOL-9 — MouseKeyboardTool (2026-02-19)

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

### Résultats tests
- ❌ "Ouvre le menu Démarrer" → LLM clique sur (0,0) au lieu d'utiliser hotkey("win")
- ❌ "Tape 'notepad' et appuie sur Entrée" → LLM ne sait pas séquencer correctement
- ❌ Screenshot pour vérifier → Impossible sans TOOL-7 (Vision)

### Problème critique identifié
L'agent LLM (qwen3:14b) ne sait pas comment utiliser correctement mouse_keyboard:

1. **Description de l'outil insuffisante**
   - L'outil ne donne pas d'exemples concrets d'utilisation
   - Pas d'exemple pour ouvrir le menu Démarrer (hotkey avec keys="win")
   - Pas d'exemple pour fermer une fenêtre (hotkey avec keys="alt,f4")

2. **LLM invente des coordonnées incorrectes**
   - Il clique sur (0,0) au lieu d'utiliser la touche Windows
   - Il ne comprend pas le séquencement des actions (focus → taper → vérifier)

3. **Agent aveugle**
   - L'agent prend des screenshots mais ne peut pas les analyser
   - Impossible de vérifier si une action a réussi
   - Pas de feedback visuel pour s'auto-corriger

### Logs de debug ajoutés
Pour diagnostiquer le problème, des logs ont été ajoutés:
- Version de pyautogui
- Taille de l'écran
- Paramètres reçus par l'outil
- Appels pyautogui effectués
- Traceback complet en cas d'erreur

### Solution requise
**Option 1 - Améliorer la description de l'outil** (rapide, partiel)
- Ajouter des exemples concrets dans la description
- Documenter comment ouvrir le menu Démarrer, fermer une fenêtre, etc.
- Améliorer les instructions de séquencement

**Option 2 - Implémenter TOOL-7 (MCP Vision GLM-4.6V)** (recommandé)
- Permet à l'agent de "voir" les screenshots
- L'agent peut s'auto-corriger en analysant ce qu'il voit
- Résout le problème de l'agent aveugle

### Découvertes techniques
- pyautogui.click(x, y) pour cliquer à des coordonnées
- pyautogui.hotkey(*keys.split(",")) pour combinaisons de touches
- pyautogui.typewrite(text, interval=0.05) pour taper du texte
- pyautogui.dragTo(x2, y2, duration=0.5) pour glisser-déposer
- pyautogui.scroll(clicks, x, y) pour scroller

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
- TOOL-10: MCP Chrome Playwright ⏳ à implémenter

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

## RÉFÉRENCES

- smolagents Tool: https://huggingface.co/docs/smolagents/tutorials/custom_tools
- smolagents MCP: https://huggingface.co/docs/smolagents/tutorials/mcp
- Prisma 7 Config: https://pris.ly/d/config-datasource
- Z.ai GLM-4.7: https://open.bigmodel.cn/dev/api
