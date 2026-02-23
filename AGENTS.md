# AGENTS.md — my-claw Assistant Personnel Hybride
> Fichier de guidage pour les IA de codage (Kilo Code, Crush, Claude Code, Cursor, Codex, Windsurf...)
> Architecture : Next.js 16 (gateway) + Python smolagents (cerveau) + Gradio (UI dev)

---

## RÈGLES IMPÉRATIVES POUR L'IA DE CODAGE

0. **Lis LEARNING.md** - avant chaque tâche. Mets **LEARNING.md** à jour avec les nouvelles découvertes après.
1. **STOP à chaque CHECKPOINT** — attendre validation explicite de l'utilisateur avant de continuer
2. **Un module à la fois** — ne jamais anticiper le module suivant
3. **Lire le skill correspondant** dans `.claude/skills/` avant de coder quoi que ce soit
4. **Ne jamais implémenter un module V2** — ils sont marqués en attente et bloqués intentionnellement
5. **uv uniquement** pour Python — jamais pip install, jamais requirements.txt
6. **Pas de console.log** en prod côté Next.js — logger structuré uniquement
7. **Pas de secrets dans le code** — toujours process.env ou os.environ
8. **Webhooks** : répondre HTTP 200 immédiatement, traiter en async
9. **Valider TypeScript** : npx tsc --noEmit doit passer avant chaque commit
10. **lancement serveur** : Ne jamais exectuter : **npm run** dev ou **uv run uvicorn main:app --reload**, demander à l'utilisateur de le lancer et de donné les erreurs/informations
11. **max_steps** : 5 pour tâches simples, 10 pour pilotage PC complexe (TOOL-9)

---

## STACK TECHNIQUE

| Couche | Technologie | Version | Notes |
|--------|-------------|---------|-------|
| Gateway | Next.js | 16+ | App Router obligatoire |
| ORM | Prisma | 7+ | SQLite local |
| Runtime JS | Node.js | 25+ | |
| Gestionnaire Python | uv | latest | Jamais pip |
| Agent LLM | smolagents | 1.24+ | CodeAgent |
| API serveur Python | FastAPI | 0.131+ | |
| UI dev | Gradio | 6+ | |
| LLM local | Ollama | latest | Port 11434 |
| LLM cloud | Z.ai GLM-4.7 | — | OpenAI-compatible |
| Language | TypeScript | 5+ | strict: true |

---

## MODÈLES LLM

### Ollama — 100% local, 0 donnée sortante

| ID | Modèle | Taille | Usage |
|----|--------|--------|-------|
| | fast | gemma3:latest | 3.3GB | Réponses rapides |
| | smart | qwen3:8b | 5.2GB | Usage quotidien — recommandé |
| | main | qwen3:8b | 5.2GB | Modèle principal — défaut sans ZAI_API_KEY |
| | vision | qwen3-vl:2b | 2.3GB | Vision locale (TOOL-7, analyse d'images) |
| | grounding | qwen3-vl:2b | 2.3GB | GUI grounding (TOOL-11, pilotage PC) |

**Note :** Les modèles qwen3-vl:2b sont préférés pour la vision et le grounding car ils sont plus rapides et plus légers.

### Z.ai — Cloud (données envoyées à Z.ai)

| ID | Modèle | Usage |
|----|--------|-------|
| | code | glm-4.7-flash | Code, tâches techniques rapides |
| | reason | glm-4.7 | Raisonnement profond — défaut avec ZAI_API_KEY |

### Configuration du modèle par défaut

Le modèle par défaut pour le manager et tous les sous-agents est déterminé par la fonction `get_default_model()` avec la priorité suivante :

1. **Variable d'environnement `DEFAULT_MODEL`** : Si définie et valide
2. **`reason` (glm-4.7)** : Si `ZAI_API_KEY` est configuré
3. **`main` (qwen3:8b)** : Fallback local

Exemples de configuration dans `agent/.env` :

```bash
# Utiliser glm-4.7 par défaut (recommandé pour le raisonnement)
DEFAULT_MODEL=reason

# Utiliser glm-4.7-flash pour le coding rapide
DEFAULT_MODEL=code

# Forcer le modèle local (gratuit)
DEFAULT_MODEL=main
```

### Règles modèles

- Modèle par défaut : `reason` (glm-4.7) si ZAI_API_KEY configuré, sinon `main` (qwen3:8b)
- **Détection automatique** : L'agent détecte les modèles Ollama installés au démarrage via `GET /api/tags`
- **Préférences par catégorie** : Chaque catégorie (fast/smart/main/vision) a une liste de modèles préférés
- **Fallback intelligent** : Si le modèle préféré n'est pas installé, utilise le suivant dans la liste
- Si ZAI_API_KEY absent : fallback silencieux sur main
- think: false en mode agent (évite verbosité Qwen3)
- num_ctx: 32768 pour tous les modèles Ollama
- max_steps=5 pour tâches simples, 10 pour pilotage PC complexe
- Provider Ollama : LiteLLMModel avec prefix ollama_chat/
- Provider Z.ai : LiteLLMModel avec prefix openai/ (compatible OpenAI)
- TOOL-7 (analyze_image) : utilise qwen3-vl:8b en local via Ollama (interne à l'outil)
- vision_agent : utilise glm-4.7 ou qwen3:8b comme LLM, qwen3-vl:8b en interne pour la vision
- **API `/models`** : Endpoint pour récupérer la liste des modèles disponibles

---

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

---

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

---

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

---

## SCHÉMA BASE DE DONNÉES

### Prisma 7 — Points critiques
- url dans schema.prisma n'existe plus
- La connexion se configure dans gateway/prisma.config.ts via datasource.url
- adapter, earlyAccess, engine sont supprimés en v7
- PrismaLibSQL prend { url: string } directement, pas besoin de createClient()

### Table Conversation
- id : cuid, PK
- channel : "webchat" | "nextcloud"
- channelId : identifiant unique par canal (session, numéro, username)
- title : résumé auto, optionnel
- model : modèle par défaut "main"
- createdAt, updatedAt
- Index unique sur [channel, channelId]

### Table Message
- id : cuid, PK
- conversationId : FK vers Conversation (cascade delete)
- role : "user" | "assistant"
- content : texte
- model : modèle utilisé, optionnel
- createdAt
- Index sur [conversationId, createdAt]

### Table CronJob
- id : cuid, PK
- name : unique
- schedule : expression cron ex "0 9 * * 1-5"
- prompt : instruction à exécuter
- channel + channelId : destinataire
- model : défaut "main"
- enabled : boolean
- lastRun : datetime optionnel

### Table Settings
- key : PK string
- value : string
- updatedAt
- Utilisé pour : system_prompt, persona_name, persona_lang

---

## CANAUX

### WebChat
- Auth : header Authorization: Bearer {WEBCHAT_TOKEN}
- Streaming via Server-Sent Events (ReadableStream)
- Token minimum 32 chars

### Nextcloud Talk Bot
- POST /api/webhook/nextcloud : vérifier signature HMAC-SHA256 obligatoire
- Headers à vérifier : X-Nextcloud-Talk-Random + X-Nextcloud-Talk-Signature
- Secret partagé : NEXTCLOUD_BOT_SECRET
- Envoi : POST {NC_BASE_URL}/ocs/v2.php/apps/spreed/api/v1/bot/{BOT_ID}/message
- Header envoi : OCS-APIRequest: true
- Utiliser crypto.timingSafeEqual pour comparer les signatures

---

## FLUX /api/chat

1. Recevoir { message, conversationId?, model?, channel, channelId }
2. Créer ou récupérer la Conversation (Prisma)
3. Sauvegarder le message user en DB
4. Récupérer les 20 derniers messages (contexte glissant)
5. Récupérer le system prompt depuis Settings
6. Appeler agent Python POST /run avec { message, history, model }
7. Sauvegarder la réponse assistant en DB
8. Retourner la réponse (stream SSE pour webchat, JSON pour les autres)

---

## OUTILS smolagents

### V1 — Actifs (implémentés et validés)
- **FileSystemTool** (TOOL-1) : read/write/create/delete/list/move/search
- **OsExecTool** (TOOL-2) : exécution PowerShell
- **ClipboardTool** (TOOL-3) : lecture/écriture presse-papier
- **ScreenshotTool** (TOOL-8) : capture d'écran Windows
- **VisionTool** (TOOL-7) : analyse d'images locale avec qwen3-vl (100% local, 0 donnée sortante)
- **QwenGroundingTool** (TOOL-11) : GUI grounding avec qwen3-vl
- **ChromeDevTools MCP** (TOOL-10) : pilotage Chrome via Puppeteer (26 outils)

**26 outils Chrome DevTools MCP organisés en 6 catégories :**

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

### V1 — En cours (non validé)
- **MouseKeyboardTool** (TOOL-9) : 🔄 contrôle souris/clavier (nécessite orchestration)

### V1 — Roadmap (À venir)
- **Web Search MCP** (TOOL-4) : ⏳ recherche web Z.ai
- **Web Reader MCP** (TOOL-5) : ⏳ lecture URL Z.ai
- **Zread MCP** (TOOL-6) : ⏳ lecture GitHub Z.ai

### V2 — Bloqués, ne pas implémenter
- run_code sandbox Python/Node
- read_file / write_file dossier whitelist

### Règles de codage outils
- Toujours sous-classe Tool (pas décorateur @tool) pour compatibilité Ollama
- Imports dans forward(), pas au top-level du fichier
- Timeout 10s sur tous les appels HTTP
- max_steps=5 pour tâches simples, 10 pour pilotage PC complexe
- pyautogui.FAILSAFE=False configuré (pas de coin haut-gauche pour arrêter)
- time.sleep(0.5) après chaque action pyautogui pour laisser l'OS réagir
- Logs de debug ajoutés dans mouse_keyboard.py pour diagnostiquer les problèmes

---

## VARIABLES D'ENVIRONNEMENT

### gateway/.env.local
- DATABASE_URL : file:./prisma/dev.db
- WEBCHAT_TOKEN : min 32 chars (openssl rand -hex 32)
- CRON_SECRET : min 32 chars
- AGENT_URL : http://localhost:8000
- NEXTCLOUD_BASE_URL
- NEXTCLOUD_BOT_SECRET
- NEXTCLOUD_BOT_ID
- SCREENSHOT_DIR : C:\tmp\myclawshots (optionnel, défaut: C:\tmp\myclawshots)

### agent/.env
- OLLAMA_BASE_URL : http://localhost:11434
- ZAI_API_KEY : optionnel
- ZAI_BASE_URL : https://api.z.ai/api/coding/paas/v4
- DEFAULT_MODEL : modèle par défaut (optionnel, défaut: reason si ZAI_API_KEY, sinon main)
- SCREENSHOT_DIR : C:\tmp\myclawshots (défaut)

---

## CONVENTIONS DE CODE

### Python
- Python 3.14+, type hints partout
- pyproject.toml + uv.lock — jamais requirements.txt
- uv add <pkg> pour ajouter une dépendance
- uv run <cmd> pour exécuter
- Logging via module logging, pas print()

### TypeScript
- strict: true dans tsconfig
- Exports nommés, pas de default sauf pages Next.js
- unknown + type guard, jamais any

### Sécurité
- Ne jamais logger le contenu des messages
- Logger uniquement : canal, timestamp, durée, modèle
- Valider signature/token sur tous les webhooks
- pyautogui.FAILSAFE=False configuré (pas de coin haut-gauche pour arrêter)
- time.sleep(0.5) après chaque action pyautogui pour laisser l'OS réagir

---

## CE QU'ON NE FAIT PAS

- Pas de multi-utilisateurs
- Pas de Docker pour l'app principale
- Pas de Redis ou message queue
- Pas de pip install ou requirements.txt
- Pas de features V2 sans validation explicite
- Pas de Telegram, Discord, Slack, Signal
- Pas de pilotage PC sans Vision (TOOL-7 requis pour TOOL-9)

---

## CHECKLIST AVANT COMMIT

- npx tsc --noEmit passe sans erreur (gateway)
- Les deux services démarrent sans erreur
- Nouvelles variables d'env dans .env.example
- Pas de secrets dans le code
- Webhooks vérifient leur signature/token
- CHECKPOINT du module validé par l'utilisateur

---

## RÉFÉRENCES

- smolagents : https://huggingface.co/docs/smolagents
- smolagents MCP : https://huggingface.co/docs/smolagents/tutorials/mcp
- Prisma 7 Config : https://pris.ly/d/config-datasource
- Z.ai GLM-4.7 : https://open.bigmodel.cn/dev/api
- Ollama API : https://github.com/ollama/ollama/blob/main/docs/api.md
- Nextcloud Talk Bot : https://nextcloud-talk.readthedocs.io/en/latest/bot-list/
- Prisma 7 Docs : https://www.prisma.io/docs
- Next.js 16 : https://nextjs.org/docs/app
- Gradio : https://www.gradio.app/docs
- FastAPI : https://fastapi.tiangolo.com
- pyautogui : https://pyautogui.readthedocs.io
- Pillow : https://pillow.readthedocs.io
