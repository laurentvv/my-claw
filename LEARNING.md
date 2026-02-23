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
- Agent → Code Python : 240s (4 min) via `executor_kwargs`
- Vision (Ollama) : 180s — qwen3-vl:2b rapide
- os_exec : 30s par défaut (configurable)
- Gradio UI : 300s

---

## Patterns smolagents établis

### Structure Tool
```python
class MyTool(Tool):
    name = "my_tool"          # identifiant Python valide, pas de mot réservé
    description = "..."
    inputs = {
        "param": {"type": "string", "description": "...", "nullable": False}
    }
    output_type = "string"    # string | integer | boolean | number | array | object | any | image | audio

    def forward(self, param: str) -> str:
        import external_lib   # ← imports externes DANS forward(), pas au top-level
        ...
```

### Patterns clés
- `additional_authorized_imports` pour autoriser des imports dans CodeAgent
- `instructions` ajoutées à la fin du system prompt (ne remplace pas, complète)
- Skills dans `agent/skills.txt` chargés au démarrage — patterns de code copiés par l'agent
- `final_answer()` obligatoire dans les skills sinon erreur de parsing au step 2
- `max_steps=5` pour tâches simples, `8` pour search+visit, `10+` pour pilotage PC

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
└── web_agent         → Nanbeige4.1-3B + DuckDuckGoSearchTool + VisitWebpageTool
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

## Références

- smolagents built-in tools : https://huggingface.co/docs/smolagents/reference/default_tools
- smolagents MCP : https://huggingface.co/docs/smolagents/tutorials/mcp
- Building good agents : https://huggingface.co/docs/smolagents/tutorials/building_good_agents
- Ollama API : https://github.com/ollama/ollama/blob/main/docs/api.md
- qwen3-vl : https://ollama.com/library/qwen3-vl
- chrome-devtools-mcp : https://github.com/ChromeDevTools/chrome-devtools-mcp
