# AGENTS.md — Assistant Personnel Hybride
> Fichier de guidage pour les IA de codage (Claude Code, Cursor, Codex, Windsurf...)
> Architecture : Next.js 16 (gateway) + Python smolagents (cerveau) + Gradio (UI dev)
> **RÈGLE N°1 : Valider avec l'utilisateur à chaque checkpoint ✅ avant de continuer.**

---

## 🏛️ Architecture Globale

```
┌─────────────────────────────────────────────────────────────┐
│                      Machine dédiée                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Next.js 16  — Gateway & Mémoire  (:3000)           │   │
│  │  /api/webhook/whatsapp   → reçoit, transmet         │   │
│  │  /api/webhook/nextcloud  → reçoit, transmet (HMAC)  │   │
│  │  /api/cron               → déclenche les jobs       │   │
│  │  /api/health             → monitoring               │   │
│  │  Prisma 7 + SQLite       → mémoire conversations    │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │ HTTP interne POST /run                │
│  ┌──────────────────▼──────────────────────────────────┐   │
│  │  Python + smolagents — Cerveau Agent  (:8000)       │   │
│  │  FastAPI  →  POST /run  →  CodeAgent                │   │
│  │                                                     │   │
│  │  agent = CodeAgent(tools=[                          │   │
│  │    web_search_tool,    # SearXNG local              │   │
│  │    # v2: whisper_tool, browser_tool, file_tools     │   │
│  │  ], model=LiteLLMModel("ollama_chat/mistral:7b"))   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Gradio  — UI dev/test  (:7860)                     │   │
│  │  Interface directe avec le CodeAgent Python         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Services locaux :                                          │
│  Ollama :11434 │ SearXNG :8888 │ SQLite (fichier local)    │
└─────────────────────────────────────────────────────────────┘
         │                            │
   WhatsApp (Meta API)      Nextcloud Talk (Bot webhook)
```

---

## 📁 Structure du Projet

```
/
├── AGENTS.md                        ← CE FICHIER
├── .env.example                     ← Template variables d'env
├── .env.local                       ← Secrets (jamais commité)
│
├── gateway/                         ← Next.js 16
│   ├── app/
│   │   ├── (webchat)/               ← UI WebChat
│   │   │   └── page.tsx
│   │   └── api/
│   │       ├── webhook/
│   │       │   ├── whatsapp/route.ts
│   │       │   └── nextcloud/route.ts
│   │       ├── cron/route.ts
│   │       └── health/route.ts
│   ├── lib/
│   │   ├── db.ts                    ← Singleton Prisma
│   │   ├── memory.ts                ← Helpers conversations
│   │   ├── channels/
│   │   │   ├── whatsapp.ts          ← Envoi WA
│   │   │   └── nextcloud.ts        ← Envoi NC Talk
│   │   └── agent-client.ts         ← Appel HTTP vers Python :8000
│   ├── prisma/
│   │   └── schema.prisma
│   └── package.json
│
├── agent/                           ← Python smolagents
│   ├── main.py                      ← FastAPI + CodeAgent
│   ├── tools/
│   │   ├── __init__.py
│   │   └── web_search.py            ← @tool SearXNG
│   ├── gradio_app.py                ← UI Gradio (dev/test)
│   ├── requirements.txt
│   └── .venv/                       ← Environnement virtuel Python
│
└── .claude/
    └── skills/
        ├── smolagents-tools/SKILL.md
        ├── prisma-patterns/SKILL.md
        ├── nextjs-api-routes/SKILL.md
        └── channel-webhooks/SKILL.md
```

---

## 🗺️ Plan d'Implémentation — Modules & Checkpoints

> **CONVENTION IA DE CODAGE :**
> - Chaque module se termine par un `✅ CHECKPOINT` — **STOP, attendre validation utilisateur**
> - Ne pas enchaîner deux modules sans validation intermédiaire
> - Si un test échoue au checkpoint → corriger avant d'avancer
> - Créer des commits git à chaque checkpoint validé

---

### MODULE 0 — Socle & Configuration
**But :** Avoir un repo propre, les deux projets qui démarrent, les services locaux actifs.

Tâches :
- Initialiser le repo git avec `.gitignore` (`.env.local`, `.venv/`, `*.db`, `node_modules/`)
- Créer `.env.example` avec toutes les variables commentées
- Créer `gateway/` avec `npx create-next-app@latest` (App Router, TypeScript, Tailwind)
- Créer `agent/` avec `uv init` + `uv add smolagents[litellm] fastapi uvicorn gradio python-dotenv`
- Vérifier qu'Ollama tourne : `curl http://localhost:11434/api/tags`
- Vérifier que le modèle de base est disponible : `ollama pull mistral:7b`

**✅ CHECKPOINT 0** — L'utilisateur confirme :
- `cd gateway && npm run dev` → Next.js démarre sur :3000
- `cd agent && uv run uvicorn main:app --reload` → FastAPI démarre sur :8000
- `ollama list` → au moins un modèle visible
- Commit : `feat: initial project structure`

---

### MODULE 1 — Cerveau Python (smolagents + FastAPI)
**But :** Un agent fonctionnel accessible via HTTP, testable avec Gradio.

Tâches :
- `agent/main.py` : FastAPI avec `POST /run` qui prend `{ message, history?, model? }`
- `agent/tools/web_search.py` : `@tool` SearXNG (mock si SearXNG pas encore installé)
- Modèles disponibles via `LiteLLMModel` :

```python
MODELS = {
    "fast":   "ollama_chat/qwen3:4b",      # 2.6GB — réponses rapides
    "smart":  "ollama_chat/qwen3:8b",      # 5.2GB — usage quotidien
    "main":   "ollama_chat/qwen3:14b",     # 9.3GB — modèle principal
    "code":   "openai/glm-4.7-flash",      # Z.ai — code léger
    "reason": "openai/glm-4.7",            # Z.ai — raisonnement profond
}
```

- Fallback automatique : si `ZAI_API_KEY` absent → utiliser `smart`
- `agent/gradio_app.py` : interface Gradio simple (chatbox + sélecteur de modèle)
- **Note sur les tools Ollama** : avec Ollama, utiliser `Tool` (sous-classe) plutôt que `@tool` décorateur si des problèmes apparaissent (quirk connu de smolagents)

**✅ CHECKPOINT 1** — L'utilisateur confirme via Gradio :
- Envoyer "Quelle heure est-il ?" → réponse cohérente
- Envoyer "Cherche des infos sur Python 3.13" → web_search appelé
- `curl -X POST http://localhost:8000/run -H "Content-Type: application/json" -d '{"message":"Hello"}'` → JSON de réponse
- Commit : `feat: smolagents brain + fastapi endpoint + gradio ui`

---

### MODULE 2 — Mémoire (Next.js + Prisma)
**But :** Persister les conversations, passer l'historique à l'agent.

Schéma Prisma :

```prisma
model Conversation {
  id         String    @id @default(cuid())
  channel    String    // "webchat" | "whatsapp" | "nextcloud"
  channelId  String    // session/numéro/username
  title      String?
  model      String    @default("smart")
  createdAt  DateTime  @default(now())
  updatedAt  DateTime  @updatedAt
  messages   Message[]
  @@index([channel, channelId])
}

model Message {
  id             String       @id @default(cuid())
  conversationId String
  conversation   Conversation @relation(fields: [conversationId], references: [id], onDelete: Cascade)
  role           String       // "user" | "assistant"
  content        String
  model          String?
  createdAt      DateTime     @default(now())
  @@index([conversationId, createdAt])
}

model CronJob {
  id         String    @id @default(cuid())
  name       String    @unique
  schedule   String    // "0 9 * * 1-5"
  prompt     String
  channel    String
  channelId  String
  model      String    @default("smart")
  enabled    Boolean   @default(true)
  lastRun    DateTime?
  createdAt  DateTime  @default(now())
}
```

- `gateway/lib/db.ts` : singleton Prisma
- `gateway/lib/memory.ts` : `getOrCreate()`, `addMessage()`, `getHistory(limit=20)`
- `gateway/lib/agent-client.ts` : `POST http://localhost:8000/run` avec `{ message, history }`
- Migrer : `npx prisma migrate dev --name init`

**✅ CHECKPOINT 2** — L'utilisateur confirme :
- `npx prisma studio` → tables visibles et vides
- Appel à `agent-client.ts` avec historique → réponse contextuelle
- Commit : `feat: prisma memory + agent client`

---

### MODULE 3 — WebChat (Next.js UI)
**But :** Interface web minimaliste, streaming, token auth.

Tâches :
- Page `/` : chatbox avec historique, sélecteur de modèle, streaming SSE
- Auth : header `Authorization: Bearer {WEBCHAT_TOKEN}` (token dans `.env.local`)
- Route `POST /api/chat` : récupère historique Prisma → appelle agent Python → sauvegarde → stream la réponse
- UI sobre : Tailwind, pas de lib de composants externes, mobile-friendly

**✅ CHECKPOINT 3** — L'utilisateur confirme dans le navigateur :
- Login avec le token → accès au chat
- Envoyer un message → réponse en streaming visible
- Rafraîchir la page → historique de la conversation toujours là
- Commit : `feat: webchat ui + streaming + auth`

---

### MODULE 4 — Canal WhatsApp
**But :** Recevoir et envoyer des messages via Meta Cloud API.

Tâches :
- `gateway/app/api/webhook/whatsapp/route.ts` :
  - `GET` → vérification token Meta
  - `POST` → répondre 200 immédiatement, traiter en async
- `gateway/lib/channels/whatsapp.ts` : fonction `send(to, text)`
- Flux : webhook → Prisma (getOrCreate conversation) → agent Python → Prisma (save) → send WA
- Exposer le webhook publiquement pour Meta : `ngrok http 3000` en dev

**✅ CHECKPOINT 4** — L'utilisateur confirme :
- Envoyer un WhatsApp → recevoir une réponse de l'agent
- L'historique de la conversation WA est visible dans Prisma Studio
- Commit : `feat: whatsapp channel`

---

### MODULE 5 — Canal Nextcloud Talk
**But :** Bot Nextcloud Talk avec vérification HMAC-SHA256.

Tâches :
- `gateway/app/api/webhook/nextcloud/route.ts` :
  - Vérifier signature `X-Nextcloud-Talk-Random` + `X-Nextcloud-Talk-Signature`
  - Répondre 200, traiter en async
- `gateway/lib/channels/nextcloud.ts` : fonction `send(token, message)`
- Enregistrer le bot dans Nextcloud Admin → copier le secret dans `.env.local`

**✅ CHECKPOINT 5** — L'utilisateur confirme :
- Envoyer un message au bot dans Nextcloud Talk → recevoir une réponse
- Tester avec une mauvaise signature → HTTP 401 retourné
- Commit : `feat: nextcloud talk channel`

---

### MODULE 6 — Cron & Proactivité
**But :** L'assistant peut initier des messages selon un planning.

Tâches :
- `gateway/app/api/cron/route.ts` : protégé par `X-Cron-Secret`, lit les CronJobs actifs, exécute
- Ajouter dans `crontab -e` : `* * * * * curl -s -H "X-Cron-Secret: $TOKEN" http://localhost:3000/api/cron`
- UI minimaliste pour gérer les CronJobs (liste, activer/désactiver)

**✅ CHECKPOINT 6** — L'utilisateur confirme :
- Créer un CronJob "Bonjour quotidien" → recevoir le message au bon moment
- Commit : `feat: cron proactive messaging`

---

### MODULE 7 — Z.ai GLM-4.7 + Health Check
**But :** Provider cloud opérationnel + monitoring de l'ensemble.

Tâches :
- Configurer `ZAI_API_KEY` dans `.env.local`
- Tester `model="code"` et `model="reason"` dans Gradio
- `GET /api/health` : vérifie Ollama (:11434), agent Python (:8000), DB (Prisma ping), SearXNG (:8888)

**✅ CHECKPOINT 7** — L'utilisateur confirme :
- GLM-4.7-Flash répond via Gradio
- `/api/health` retourne `{ ollama: ok, agent: ok, db: ok, searxng: ok }`
- Commit : `feat: zai provider + health check`

---

### MODULE 8 — Identity & Persona
**But :** L'assistant a une personnalité persistante et un nom.

Tâches :
- Table `Settings` dans Prisma : clé/valeur (system_prompt, persona_name, persona_lang)
- UI dans WebChat pour éditer le system prompt
- Injecter le system prompt dans chaque appel à l'agent Python

**✅ CHECKPOINT 8** — L'utilisateur confirme :
- Changer le system prompt → l'assistant adopte la nouvelle personnalité
- Commit : `feat: identity and persona`

---

### MODULE V2 — Outils Avancés (ne pas implémenter avant décision explicite)

> ⚠️ Ces modules ne doivent PAS être codés tant qu'il n'y a pas de ✅ explicite ici.

- ⏳ **V2-A** Voice/STT sur Nextcloud Talk (whisper.cpp + nodejs-whisper + ffmpeg)
- ⏳ **V2-B** Exécution de code (sandbox Docker ou Pyodide/Deno)
- ⏳ **V2-C** Lecture/écriture de fichiers (whitelist `/data/allowed/`)
- ⏳ **V2-D** Browser control (Playwright headless via `webagent` smolagents)
- ⏳ **V2-E** Mémoire vectorielle (pgvector + `nomic-embed-text` via Ollama)

---

## ⚙️ Variables d'Environnement

```bash
# === GATEWAY (Next.js) ===
DATABASE_URL="file:./dev.db"
WEBCHAT_TOKEN=""                  # min 32 chars aléatoires
CRON_SECRET=""                    # min 32 chars aléatoires
AGENT_URL="http://localhost:8000" # URL interne Python agent

# === CANAUX ===
# WhatsApp Meta Cloud API
WHATSAPP_VERIFY_TOKEN=""
WHATSAPP_ACCESS_TOKEN=""
WHATSAPP_PHONE_NUMBER_ID=""

# Nextcloud Talk Bot
NEXTCLOUD_BASE_URL=""             # https://nextcloud.mondomaine.fr
NEXTCLOUD_BOT_SECRET=""
NEXTCLOUD_BOT_ID=""

# === AGENT (Python) ===
# Ollama (local — 0 donnée sortante)
OLLAMA_BASE_URL="http://localhost:11434"

# Z.ai / GLM-4.7 (optionnel — cloud)
ZAI_API_KEY=""
ZAI_BASE_URL="https://open.bigmodel.cn/api/paas/v4"

# SearXNG (local)
SEARXNG_URL="http://localhost:8888"
```

---

## 🤖 smolagents — Règles & Patterns

### Modèles Ollama
```python
# Toujours utiliser LiteLLMModel avec ollama_chat/ prefix
model = LiteLLMModel(
    model_id="ollama_chat/mistral:7b",
    api_base="http://localhost:11434",
    api_key="ollama",             # valeur factice, obligatoire
    num_ctx=8192,
)
```

### Modèles Z.ai (OpenAI-compatible)
```python
model = LiteLLMModel(
    model_id="openai/glm-4.7-flash",
    api_base="https://open.bigmodel.cn/api/paas/v4",
    api_key=os.environ["ZAI_API_KEY"],
)
```

### Outils — Décorateur vs Sous-classe
```python
# Décorateur (simple, fonctionne bien avec Z.ai)
from smolagents import tool

@tool
def web_search(query: str) -> str:
    """Searches the web via local SearXNG.
    Args:
        query: The search query.
    """
    ...

# Sous-classe (préférer avec Ollama si le décorateur pose problème)
from smolagents import Tool

class WebSearchTool(Tool):
    name = "web_search"
    description = "Searches the web via local SearXNG."
    inputs = {"query": {"type": "string", "description": "The search query."}}
    output_type = "string"

    def forward(self, query: str) -> str:
        ...
```

### Historique de conversation
```python
# smolagents n'a pas de mémoire native entre runs
# Injecter l'historique dans le message initial
def build_prompt_with_history(message: str, history: list[dict]) -> str:
    if not history:
        return message
    context = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in history[-10:]  # 10 derniers messages
    )
    return f"Conversation history:\n{context}\n\nUser: {message}"
```

### FastAPI endpoint
```python
# agent/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from smolagents import CodeAgent, LiteLLMModel
from tools import WebSearchTool

app = FastAPI()

class RunRequest(BaseModel):
    message: str
    history: list[dict] = []
    model: str = "smart"

@app.post("/run")
async def run(req: RunRequest):
    model = get_model(req.model)  # factory selon req.model
    agent = CodeAgent(tools=[WebSearchTool()], model=model)
    prompt = build_prompt_with_history(req.message, req.history)
    result = agent.run(prompt)
    return {"response": str(result)}

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## 📏 Conventions de Code

### Python (agent/)
- Python 3.11+
- `pyproject.toml` + `uv.lock` versionnés (jamais de `requirements.txt`)
- Type hints partout
- Pas de `print()` en prod → `logging`
- Variables d'env via `os.environ` avec fallback explicite
- Commandes : `uv add <pkg>` (pas pip), `uv run <cmd>` (pas d'activation manuelle du venv)

### TypeScript (gateway/)
- `strict: true` dans `tsconfig.json`
- Pas de `any` implicite → `unknown` + type guard
- Exports nommés (pas de default sauf pages Next.js)
- Pas de `console.log` en prod → logger structuré

### Sécurité (les deux)
- Valider toutes les entrées des webhooks (signature, token)
- Ne jamais logger le contenu des messages
- Logger uniquement métadonnées (canal, timestamp, durée, modèle)
- WEBCHAT_TOKEN et CRON_SECRET : minimum 32 chars générés avec `openssl rand -hex 32`

---

## 🚫 Ce Qu'on NE Fait PAS

- ❌ Pas de multi-utilisateurs
- ❌ Pas de Docker pour l'app elle-même (juste SearXNG si voulu)
- ❌ Pas de Redis / message queue
- ❌ Pas de micro-services supplémentaires
- ❌ Pas de dépendances sans justification dans ce fichier
- ❌ Pas de features V2 sans ✅ explicite dans ce fichier

---

## ✅ Checklist avant chaque Commit

- [ ] Les deux services démarrent sans erreur
- [ ] `npx tsc --noEmit` passe (gateway)
- [ ] Les nouvelles variables sont dans `.env.example`
- [ ] Pas de secrets dans le code
- [ ] Les webhooks vérifient bien leur token/signature
- [ ] Le CHECKPOINT du module est validé par l'utilisateur

---

## 📚 Références

- [smolagents docs](https://huggingface.co/docs/smolagents)
- [smolagents GitHub](https://github.com/huggingface/smolagents)
- [LiteLLM providers](https://docs.litellm.ai/docs/providers)
- [Z.ai GLM-4.7 API](https://open.bigmodel.cn/dev/api)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Nextcloud Talk Bot API](https://nextcloud-talk.readthedocs.io/en/latest/bot-list/)
- [SearXNG API](https://docs.searxng.org/dev/search_api.html)
- [Prisma 7 Docs](https://www.prisma.io/docs)
- [Next.js 16 App Router](https://nextjs.org/docs/app)
- [Gradio Docs](https://www.gradio.app/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com)
