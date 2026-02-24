# LEARNING.md — Découvertes my-claw

> Mémoire technique du projet. Mise à jour après chaque feature.

---

## Environnement & Stack (2026-02-21)

### Python 3.14
- `pathlib.Path.move(target)` et `.copy(target)` : méthodes natives — remplacent `shutil`
- `asyncio.get_event_loop()` lève `RuntimeError` si aucune boucle active → toujours utiliser `asyncio.get_running_loop()` ou `asyncio.run()`
- `asyncio.to_thread()` : bonne pratique pour appeler du code synchrone (agent.run()) depuis un contexte async
- Annotations : `X | None` plutôt que `Optional[X]` (PEP 604), f-strings imbriquées supportées nativement
- `from __future__ import annotations` pour eval lazy

### Stack technique
- Python 3.14 / uv / FastAPI + lifespan
- smolagents >= 1.24.0 (CodeAgent, ManagedAgent, Tool)
- Ollama local (qwen3-vl:2b vision/grounding, Nanbeige4.1-3B browser/web, qwen3:8b manager)
- GLM-4.7 Z.ai cloud optionnel (ZAI_API_KEY dans agent/.env)
- Next.js 16 + Prisma 7 (gateway), Node.js 25, ESLint 9

### Timeouts configurés
- Gateway → Agent : 360s (6 min)
- Agent → Code Python : 300s (5 min) via `executor_kwargs`
- Vision (Ollama) : 180s — qwen3-vl:2b rapide
- os_exec : 30s par défaut (configurable)
- Gradio UI : 300s

---

## TOOL-4 + TOOL-5 — Web Search & Web Reader (2026-02-23)

### Architecture choisie : Outils directs au manager

**Décision importante :** Les outils web sont passés **directement au manager**, pas via un managed_agent.

**Pourquoi :**
- Simplifie l'architecture (pas de délégation nécessaire pour des outils simples)
- Évite les problèmes de contexte entre agents
- Plus rapide (un seul appel, pas de handover)
- smolagents 1.24.0 gère parfaitement les outils natifs

**Implémentation :**
```python
# main.py — build_multi_agent_system()
web_tools = [WebSearchTool(), WebVisitTool()]
manager_tools_list = get_manager_tools()
all_manager_tools = manager_tools_list + web_tools

manager = CodeAgent(
    tools=all_manager_tools,  # ← Outils web inclus directement
    model=get_model(model_id),
    managed_agents=[pc_control, vision, browser],
)
```

### Graceful degradation pour les dépendances

**Problème :** Si `ddgs` ou `markdownify` ne sont pas installés, l'agent ne doit pas planter.

**Solution :** Imports conditionnels dans `tools/__init__.py`

```python
# agent/tools/__init__.py
WebSearchTool = None
WebVisitTool = None

try:
    from .web_search_tool import WebSearchTool
    logger.info("✓ WebSearchTool (DuckDuckGo) disponible")
except ImportError as e:
    logger.warning(f"✗ WebSearchTool indisponible: {e}")
    WebSearchTool = None

try:
    from .web_visit_tool import WebVisitTool
    logger.info("✓ WebVisitTool (web reader) disponible")
except ImportError as e:
    logger.warning(f"✗ WebVisitTool indisponible: {e}")
    WebVisitTool = None

# Ajout conditionnel à la liste TOOLS
TOOLS = [FileSystemTool(), OsExecTool(), ...]
if WebSearchTool is not None:
    TOOLS.append(WebSearchTool())
if WebVisitTool is not None:
    TOOLS.append(WebVisitTool())
```

### Wrappers avec configuration par défaut

**Pourquoi :** Les built-in smolagents n'ont pas de configuration par défaut.

**Solution :** Wrappers légers avec valeurs optimisées

```python
# agent/tools/web_search_tool.py
class WebSearchTool(DuckDuckGoSearchTool):
    def __init__(self, max_results: int = 5, rate_limit: float = 1.0):
        super().__init__(max_results=max_results, rate_limit=rate_limit)

# agent/tools/web_visit_tool.py
class WebVisitTool(VisitWebpageTool):
    max_output_length = 8000  # Adapté pour contexte 8192 tokens
```

### Sécurité URL — Validation SSRF

**Risque :** L'utilisateur pourrait demander de lire `file:///etc/passwd` ou `http://localhost`.

**Solution :** Validation URL dans `WebVisitTool.__call__()`

```python
ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1"}

def __call__(self, url: str, **kwargs) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in self.ALLOWED_SCHEMES:
        return f"ERROR: Invalid URL scheme '{parsed.scheme}'"
    if parsed.hostname in self.BLOCKED_HOSTS:
        return f"ERROR: Access to internal hosts blocked"
    return super().__call__(url, **kwargs)
```

---

## Corrections techniques — Encodage Windows (2026-02-23)

### Problème : UnicodeDecodeError dans os_exec

**Erreur :**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0x82 in position 12
```

**Cause :** PowerShell sur Windows utilise cp1252 (Western European), pas UTF-8.

**Solution :** Changer l'encodage dans `subprocess.run()`

```python
# agent/tools/os_exec.py
result = subprocess.run(
    ["powershell", "-Command", command],
    capture_output=True,
    text=True,
    encoding="cp1252",  # ← Windows Western European
    errors="replace",   # ← Remplace les caractères invalides
    timeout=timeout,
    shell=False,
)
```

**Résultat :** Les commandes PowerShell avec accents fonctionnent maintenant.

---

## Architecture Multi-Agent — Délégation validée (2026-02-23)

### Workflow Screenshot + Vision

**Test validé :** "Prends un screenshot et décris ce que tu vois"

**Flux de délégation :**
```
Manager (glm-4.7)
  ↓ délègue à pc_control
pc_control (qwen3:8b)
  ↓ appelle screenshot()
ScreenshotTool → C:\tmp\myclawshots\screen_XXX.png
  ↓ délègue à vision
vision (qwen3:8b + qwen3-vl:2b interne)
  ↓ appelle analyze_image()
VisionTool → Description détaillée (5109 chars)
  ↓ retourne au manager
Manager → final_answer()
```

**Temps total :** ~4min (240s)

**Leçons apprises :**
1. La délégation automatique fonctionne parfaitement
2. Les sous-agents ont leurs propres instructions via `final_answer()` structuré
3. Le manager peut enchaîner plusieurs délégations (pc_control → vision)
4. Le cache par modèle (`get_or_build_agent()`) évite de reconstruire à chaque requête

### Pattern de délégation dans skills.txt

**Important :** Les skills doivent clarifier quels outils sont directs vs délégation.

```
## AVAILABLE DIRECT TOOLS (Manager)
- file_system, os_exec, clipboard, web_search, visit_webpage

## TOOLS REQUIRING DELEGATION
- screenshot, analyze_image, mouse_keyboard → pc_control
- click, fill, navigate_page → browser
```

---
- `instructions` ajoutées à la fin du system prompt (ne remplace pas, complète)
- Skills dans `agent/skills.txt` chargés au démarrage — patterns de code copiés par l'agent
- `final_answer()` obligatoire dans les skills sinon erreur de parsing au step 2
- `max_steps=5` pour tâches simples, `10+` pour pilotage PC

### FastAPI lifespan — pattern MCP
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    _mcp_context = ToolCollection.from_mcp(params, trust_remote_code=True)
    tool_collection = _mcp_context.__enter__()   # ← retourne _GeneratorContextManager, pas ToolCollection directement
    _mcp_tools = list(tool_collection.tools)
    yield
    # Shutdown
    if _mcp_context is not None:
        _mcp_context.__exit__(None, None, None)
```

### Environnement Windows
- Chemins Windows : backslashes et forward slashes acceptés
- `env={**os.environ}` dans StdioServerParameters pour que npx trouve Node.js
- `pyautogui.FAILSAFE = False` — pas de coin haut-gauche pour arrêter
- `time.sleep(0.5)` après chaque action pyautogui
- Dossier screenshots : `C:\tmp\myclawshots\`, configurable via `SCREENSHOT_DIR`
- Win+L bloqué par Windows via automation → workaround : `os_exec("rundll32.exe user32.dll,LockWorkStation")`
- Ctrl+Alt+Del : bloqué OS. Alt+F4 / Win+D : parfois capricieux selon le focus

---

## Modèles — Gestion centralisée (models.py)

### MODULE models.py
- `get_model(model_id)` : crée LiteLLMModel correct selon cloud ou Ollama
- `get_default_model()` : env `DEFAULT_MODEL` → "reason" si ZAI_API_KEY → "main" fallback
- `detect_models()` : appelle `GET /api/tags` Ollama, associe aux catégories
- Fallback sécurisé : si "main" absent → premier modèle dispo → RuntimeError si aucun

### Préférences actuelles
```python
MODEL_PREFERENCES = {
    "fast":   ["hf.co/tantk/Nanbeige4.1-3B-GGUF:Q4_K_M", "qwen3:4b", "gemma3:latest"],
    "smart":  ["qwen3:8b", "qwen3:4b", "hf.co/tantk/Nanbeige4.1-3B-GGUF:Q4_K_M"],
    "main":   ["qwen3:8b", "qwen3:4b", "hf.co/tantk/Nanbeige4.1-3B-GGUF:Q4_K_M"],
    "vision": ["qwen3-vl:2b", "qwen3-vl:4b", "qwen3-vl:8b"],
}
```
> ⚠️ `lfm2.5-thinking:1.2b` retiré de "fast" — incompatible smolagents (pas de balises `<code>`, déraille en LaTeX)

### Nanbeige4.1-3B — validé 2026-02-22
- BFCL-V4: 56.5 (vs qwen3:8b: 42.2) — meilleur tool-use
- `ollama pull hf.co/tantk/Nanbeige4.1-3B-GGUF:Q4_K_M` (2.44GB Q4_K_M)
- Utilisé pour : browser_agent, web_agent

### GLM-4.7 — bug balise `</code`
GLM-4.7 génère `</code` (sans `>`) → SyntaxError dans smolagents.
**Solution : `CleanedLiteLLMModel`** — wrapper qui override `generate()` et nettoie la réponse via regex avant parsing.

### Sous-agents — erreur `ollama_chat/reason`
Les sous-agents forçaient `ollama_chat/{model_id}`. Quand model_id="reason" (GLM-4.7 cloud) → erreur Ollama.
**Fix : tous les sous-agents utilisent `get_model(model_id)` depuis models.py.**

---

## Architecture Multi-Agent

### Structure validée (2026-02-22)
```
Manager (glm-4.7 / qwen3:8b)
├── pc_control_agent  → qwen3-vl:2b  (screenshot, mouse_keyboard, ui_grounding)
├── vision_agent      → qwen3:8b LLM + qwen3-vl:2b interne pour analyze_image
├── browser_agent     → Nanbeige4.1-3B + 26 tools Chrome DevTools MCP
└── web_agent         → Nanbeige4.1-3B + DuckDuckGoSearchTool
```

### Règles d'architecture
- `ManagedAgent` : wrapping agent → callable comme tool par le Manager
- `pc_control_agent` utilise qwen3-vl:2b (vision native, pas qwen3:8b)
- `vision_agent` : LLM de codage orchestre, `analyze_image` fait la vision en interne
- `browser_agent` : qwen3:8b suffit (snapshot = texte, pas besoin de vision)
- Gradio 6.6.0 : `type="messages"` obligatoire dans `gr.ChatInterface`

### Décision TOOL-4/5 : built-in vs MCP Z.ai
- `DuckDuckGoSearchTool` (TOOL-4) : 0 quota, 0 config, built-in smolagents
- `VisitWebpageTool` (TOOL-5) : 0 quota, 0 config, built-in smolagents
- 100 calls/mois Z.ai économisés pour TOOL-6 (Zread GitHub — sans équivalent gratuit)
- `DuckDuckGoSearchTool` n'est pas un context manager → pas de cleanup lifespan

---

## Architecture Multi-Agent — Cache par modèle (2026-02-23)

### Problème : Singleton web_search_agent incompatible avec cache multi-modèles

Le `_web_search_agent` était initialisé comme singleton dans `lifespan()` avec le modèle par défaut (`model_id=None`), mais les autres sous-agents (pc_control, vision, browser) étaient créés dans `build_multi_agent_system()` avec le `model_id` spécifié.

**Incohérence :** Quand un utilisateur demandait un modèle non-défaut (ex: "fast"), tous les autres sous-agents utilisaient ce modèle, mais `_web_search_agent` restait avec le modèle par défaut du démarrage.

### Solution : Création dynamique dans `build_multi_agent_system()`

```python
# ❌ Avant (singleton dans lifespan)
_web_search_agent = create_web_search_agent(model_id=None)  # modèle par défaut

# ✅ Après (création dynamique)
web_agent = create_web_search_agent(model_id=model_id)  # modèle spécifique
managed_agents.append(web_agent)
```

### Impact

- **Consistance :** Tous les sous-agents utilisent maintenant le même `model_id` que le manager
- **Cache par modèle :** Le système de cache `_agent_cache[model_id]` fonctionne correctement pour tous les agents
- **Health endpoint :** Utilise `diagnose_web_search()["available"]` au lieu de `_web_search_agent is not None`

### Règle d'architecture

**Tous les sous-agents doivent être créés dans `build_multi_agent_system(model_id)`**, pas dans `lifespan()`, pour garantir la cohérence avec le cache par modèle.

---

## Erreur ManagedAgent — smolagents 1.24.0 (2026-02-23)

### Problème
Le code tentait d'importer et d'utiliser `ManagedAgent` depuis `smolagents`, mais cette classe n'existe PAS dans smolagents 1.24.0.

```python
# ❌ NE PAS FAIRE
from smolagents import CodeAgent, DuckDuckGoSearchTool, ManagedAgent, VisitWebpageTool

managed_agent = ManagedAgent(
    agent=web_agent,
    name="web_search",
    description="..."
)
```

### Solution
Dans smolagents 1.24.0, on passe directement les `CodeAgent` dans le paramètre `managed_agents` du manager. Le `CodeAgent` doit avoir `name` et `description` configurés.

```python
# ✅ CORRECT
from smolagents import CodeAgent, DuckDuckGoSearchTool, VisitWebpageTool

web_agent = CodeAgent(
    tools=[DuckDuckGoSearchTool(), VisitWebpageTool()],
    model=model,
    name="web_search",
    description="Agent web : recherche et lecture de pages web.",
    max_steps=8,
)

# Le manager utilise directement web_agent dans managed_agents
manager = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[web_agent],  # ← CodeAgent, pas ManagedAgent
)
```

### Pourquoi cette erreur ?
- Documentation obsolète ou confusion avec une version précédente de smolagents
- `ManagedAgentPromptTemplate` existe (TypedDict), mais PAS `ManagedAgent` (classe)
- Le pattern a changé dans smolagents 1.24.0

### Vérification
Pour vérifier si une classe existe dans smolagents :
```python
import smolagents
print([name for name in dir(smolagents) if 'Managed' in name])
# Résultat : ['ManagedAgentPromptTemplate']  ← PAS de ManagedAgent
```

### Règle
**Toujours vérifier la documentation officielle smolagents 1.24.0** :
- https://huggingface.co/docs/smolagents/tutorials/building_good_agents
- https://github.com/huggingface/smolagents/blob/main/docs/source/en/examples/multiagents.md

---

## TOOL-10 — MCP Chrome DevTools

### Pattern d'intégration
```python
from smolagents import ToolCollection
from mcp import StdioServerParameters

chrome_devtools_params = StdioServerParameters(
    command="npx",
    args=["-y", "chrome-devtools-mcp@latest"],
    env={**os.environ}           # ← requis Windows pour trouver Node.js
)
# Dans lifespan startup :
_mcp_context = ToolCollection.from_mcp(chrome_devtools_params, trust_remote_code=True)
tool_collection = _mcp_context.__enter__()   # ← obligatoire : retourne _GeneratorContextManager
_mcp_tools = list(tool_collection.tools)     # 26 outils
# Dans lifespan shutdown :
_mcp_context.__exit__(None, None, None)
```

### Points clés
- `trust_remote_code=True` obligatoire (sinon ValueError)
- Basé sur Puppeteer (pas Playwright)
- Profil Chrome : `%HOMEPATH%/.cache/chrome-devtools-mcp/chrome-profile-stable` (persistant entre runs)
- `--isolated=true` pour profil temporaire effacé à la fermeture
- Premier lancement : télécharge chrome-devtools-mcp (~5-10s)

### 26 outils (catégories)
- **Input** (8) : click, drag, fill, fill_form, handle_dialog, hover, press_key, upload_file
- **Navigation** (6) : close_page, list_pages, navigate_page, new_page, select_page, wait_for
- **Emulation** (2) : emulate, resize_page
- **Performance** (3) : performance_analyze_insight, performance_start_trace, performance_stop_trace
- **Network** (2) : get_network_request, list_network_requests
- **Debug** (5) : evaluate_script, get_console_message, list_console_messages, take_screenshot, take_snapshot

### Bonnes pratiques
1. `take_snapshot()` avant action → fournit uid des éléments, plus rapide que screenshot
2. `list_pages()` pour contexte multi-pages, `select_page()` pour changer
3. `wait_for(text=...)` ou laisser le tool gérer les attentes automatiquement

---

## TOOL-9 — MouseKeyboardTool / GUI Grounding

### qwen3-vl pour grounding (migration depuis UI-TARS)
- Modèle : `qwen3-vl:2b` (détection auto `_detect_grounding_model()` : 2b > 4b > 8b)
- Format API Ollama standard — le format OpenAI `image_url` ne fonctionne pas (erreur 400)
- `temperature: 0.0` obligatoire pour comportement déterministe
- Timeout : 120s (doublé depuis 60s — qwen3-vl:8b peut être lent)

```python
# ✅ Format qui fonctionne
{"content": f"{_GROUNDING_SYSTEM}\n\nFind: {element}", "images": [image_b64]}

# ❌ Format OpenAI — erreur 400
{"content": [{"type": "image_url", "image_url": {"url": f"data:...{b64}"}}]}
```

Coordonnées retournées : `[rel_x, rel_y]` dans [0..1] → `abs_x = int(rel_x * screen_width)`

### pyautogui
```python
pyautogui.click(x, y)
pyautogui.hotkey(*keys.split(","))
pyautogui.typewrite(text, interval=0.05)
pyautogui.dragTo(x2, y2, duration=0.5)
pyautogui.scroll(clicks, x, y)
```

---

## Corrections techniques (code review 2026-02-22)

### Race condition `get_or_build_agent()`
Acquérir le lock **avant** le check (pas double-check locking) :
```python
async with _cache_lock:
    if model_id not in _agent_cache:
        new_agent = await asyncio.to_thread(build_multi_agent_system, model_id)
        _agent_cache[model_id] = new_agent
```

### Auth Z.ai — fail fast
`api_key=os.environ.get("ZAI_API_KEY", "ollama")` → retournait "ollama" silencieusement → erreur 401 à l'exécution.
Fix : lever `RuntimeError` immédiatement si ZAI_API_KEY absent pour modèles cloud.

### MODELS = detect_models() au moment de l'import
Appel HTTP Ollama au `import models` → timeout si Ollama absent → crash.
Fix : lazy init ou try/except au démarrage.

### num_ctx grounding.py
`num_ctx: 32768` excessif pour qwen3-vl:2b grounding → réduire à 4096.

---

## Décisions techniques

| Décision | Choix | Raison |
|----------|-------|--------|
| Vision locale | qwen3-vl:2b Ollama | 100% local, vie privée, pas de quota |
| MCP Vision Z.ai | ❌ Abandonné | Timeout, cloud, contre philosophie projet |
| Web search | DuckDuckGoSearchTool | 0 quota vs 100 calls/mois Z.ai |
| Web reader | VisitWebpageTool | 0 quota, built-in smolagents |
| Browser | chrome-devtools-mcp (Puppeteer) | 26 outils, MCP officiel Chrome |
| Grounding | qwen3-vl:2b | Même modèle que vision, plus léger que UI-TARS |
| Modèles gestion | models.py centralisé | Évite imports circulaires, DRY |

---

## Code Review v4 - 2025-02-24

### Surcharge de Tool dans smolagents

**Problème :** Surcharger `__call__()` vs `forward()` dans les outils smolagents.

**Leçon :**
- `Tool.__call__()` appelle `self.forward()`, donc surcharger `__call__()` est nécessaire pour intercepter les appels avant validation
- Ne JAMAIS appeler `super().__call__()` depuis `forward()` car cela crée une récursion infinie
- Utiliser `super().forward()` pour déléguer au parent

**Exemple incorrect (récursion infinie) :**
```python
def forward(self, url: str) -> str:
    # Validation...
    return super().__call__(url)  # ❌ Récursion infinie !
```

**Exemple correct :**
```python
def __call__(self, url: str) -> str:
    """Valider l'URL avant de déléguer au parent."""
    # Validation SSRF...
    return super().__call__(url)

def forward(self, url: str) -> str:
    # Implémentation...
    return super().forward(url)  # ✅ Appel direct à forward()
```

---

### Validation SSRF dans les outils web

**Problème :** La validation SSRF doit être dans `__call__()` car smolagents n'appelle jamais `forward()` directement via l'agent executor.

**Leçon :**
- `urlparse.hostname` extrait correctement le hostname même avec des credentials (`http://user:pass@host.com`)
- Utiliser `ipaddress.is_reserved` et `ipaddress.is_multicast` pour bloquer les IP réservées et multicast
- Vérifier `parsed.hostname` n'est pas None avant de l'utiliser

**Exemple de validation SSRF complète :**
```python
ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1"}

def __call__(self, url: str) -> str:
    """Valider l'URL avant de déléguer au parent."""
    try:
        parsed = urlparse(url)

        if parsed.scheme not in self.ALLOWED_SCHEMES:
            return f"ERROR: Invalid URL scheme '{parsed.scheme}'. Only http/https allowed."

        if not parsed.hostname:
            return "ERROR: URL has no hostname."

        # urlparse.hostname extrait correctement même avec credentials
        hostname = parsed.hostname
        if self._is_blocked_host(hostname):
            return f"ERROR: Access to '{hostname}' is blocked for security reasons."

    except (ValueError, TypeError) as e:
        return f"ERROR: Invalid URL format: {e}"

    return super().__call__(url)

@staticmethod
def _is_blocked_host(hostname: str) -> bool:
    """Vérifier si un hôte doit être bloqué pour prévenir les attaques SSRF."""
    if hostname.lower() in WebVisitTool.BLOCKED_HOSTS:
        return True

    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        return False  # Pas une adresse IP, c'est un hostname — autorisé

    # Bloquer si privé, loopback, link-local, réservé ou multicast
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )
```

---

### Gestion des exceptions lors de l'instanciation d'outils

**Problème :** Les APIs externes peuvent changer de signature et lever des erreurs inattendues.

**Leçon :**
- Toujours capturer `TypeError` et `ValueError` en plus de `Exception` lors de l'instanciation d'outils
- Logger un warning informatif pour aider au diagnostic

**Exemple :**
```python
# Dans main.py
if WebSearchTool is not None:
    try:
        search_tool = WebSearchTool()
        web_tools.append(search_tool)
        logger.info("✓ TOOL-4 DuckDuckGoSearchTool configuré")
    except (TypeError, ValueError, Exception) as e:
        logger.warning(f"✗ TOOL-4 DuckDuckGoSearchTool erreur d'initialisation: {e}")
        logger.warning("  → Vérifiez que ddgs>=9.0.0 est installé")
```

---

### Encoding PowerShell sur Windows

**Problème :** `cp1252` est l'encoding par défaut de PowerShell sur Windows, mais peut échouer.

**Leçon :**
- Implémenter un fallback `cp1252 → utf-8` avec `errors="replace"` seulement en fallback
- Logger un warning lors du fallback pour diagnostiquer les problèmes

**Exemple :**
```python
# Dans os_exec.py
if sys.platform == "win32":
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            encoding="cp1252",
            timeout=timeout,
            shell=False,
        )
    except UnicodeDecodeError:
        # Fallback sur utf-8 si cp1252 échoue
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # Remplacer seulement en fallback
            timeout=timeout,
            shell=False,
        )
        logger.warning("Fallback sur utf-8 pour encoding PowerShell")
else:
    result = subprocess.run(
        ["powershell", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        shell=False,
    )
```

---

### Architecture des outils multi-agent

**Problème :** Comprendre la séparation entre outils locaux et outils web.

**Leçon :**
- Les outils locaux sont instanciés dans `TOOLS` (pour les sous-agents)
- Les outils web sont instanciés séparément dans `main.py` et ajoutés uniquement au manager
- Cette séparation est intentionnelle pour éviter que les sous-agents aient accès aux outils web

**Exemple :**
```python
# Dans tools/__init__.py
# ── Tool list (local tools only) ─────────────────────────────────────────────
# NOTE: Les outils web (WebSearchTool, WebVisitTool) sont instanciés
# séparément dans main.py et ajoutés uniquement au manager, pas aux sous-agents.
# Les sous-agents utilisent uniquement les outils locaux.
TOOLS = [
    FileSystemTool(),
    OsExecTool(),
    ClipboardTool(),
    ScreenshotTool(),
    VisionTool(),
    QwenGroundingTool(),
    MouseKeyboardTool(),
]

# Dans main.py
# Outils web pour le manager uniquement
web_tools = []
if WebSearchTool is not None:
    try:
        search_tool = WebSearchTool()
        web_tools.append(search_tool)
    except (TypeError, ValueError, Exception) as e:
        logger.warning(f"✗ TOOL-4 DuckDuckGoSearchTool erreur: {e}")

if WebVisitTool is not None:
    try:
        visit_tool = WebVisitTool()
        web_tools.append(visit_tool)
    except (TypeError, ValueError, Exception) as e:
        logger.warning(f"✗ TOOL-5 WebVisitTool erreur: {e}")

# Manager reçoit TOOLS + web_tools
manager_tools_list = get_manager_tools()
all_manager_tools = manager_tools_list + web_tools
```

---

### Timeouts pour les health checks

**Problème :** Un health check doit être rapide pour ne pas bloquer l'interface utilisateur.

**Leçon :**
- Utiliser `timeout=3` pour les requêtes de health check
- Un timeout de 10s est trop long et bloque l'interface utilisateur

**Exemple :**
```python
# Dans gradio_app.py
resp = requests.get(url, timeout=3)  # Health check rapide (< 3s)
```

---

## Références

- smolagents built-in tools : https://huggingface.co/docs/smolagents/reference/default_tools
- smolagents MCP : https://huggingface.co/docs/smolagents/tutorials/mcp
- Building good agents : https://huggingface.co/docs/smolagents/tutorials/building_good_agents
- Ollama API : https://github.com/ollama/ollama/blob/main/docs/api.md
- qwen3-vl : https://ollama.com/library/qwen3-vl
- chrome-devtools-mcp : https://github.com/ChromeDevTools/chrome-devtools-mcp
