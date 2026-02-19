# AGENTS.md — my-claw Assistant Personnel Hybride
> Fichier de guidage pour les IA de codage (Claude Code, Cursor, Codex, Windsurf...)
> Architecture : Next.js 16 (gateway) + Python smolagents (cerveau) + Gradio (UI dev)

---
!! Ne lance pas toi même npm run dev : laisse faire l'utilisateur de le lancer

## COMMANDS ESSENTIELLES

### Démarrage quotidien (2+ terminals)
```bash
# Terminal 1 — Gateway Next.js
cd gateway
npm run dev                              # → http://localhost:3000

# Terminal 2 — Agent Python
cd agent
uv run uvicorn main:app --reload        # → http://localhost:8000

# Terminal 3 — Gradio UI dev (optionnel)
cd agent
uv run python gradio_app.py            # → http://localhost:7860
```

### Base de données (Prisma 7)
```bash
cd gateway
npx prisma generate                     # Régénérer client après changement schema
npx prisma migrate dev --name <nom>     # Créer nouvelle migration
npx prisma migrate reset                 # Reset complet DB (dev uniquement)
npx prisma studio                        # UI pour visualiser/modifier données
npx prisma db push                       # Synchroniser schema sans migration (dev)
```

### Python (uv)
```bash
cd agent
uv add <package>                        # Ajouter dépendance
uv remove <package>                     # Supprimer dépendance
uv sync                                  # Synchroniser après git pull
uv run python -m pytest                  # Lancer tests (quand disponibles)
uv run pyright                           # Vérification types
uv run ruff check                        # Linting
uv run ruff format                       # Formatage
```

### Next.js
```bash
cd gateway
npm run dev                              # Développement
npm run build                            # Production build
npm run start                            # Démarrer production build
npm run lint                             # ESLint
npx tsc --noEmit                         # Vérification types TypeScript
```

---

## RÈGLES IMPÉRATIVES POUR L'IA DE CODAGE

1. **STOP à chaque CHECKPOINT** — attendre validation explicite de l'utilisateur avant de continuer
2. **Un module à la fois** — ne jamais anticiper le module suivant
3. **Lire le skill correspondant** dans `.claude/skills/` avant de coder quoi que ce soit
4. **Ne jamais implémenter un module V2** — ils sont marqués en attente et bloqués intentionnellement
5. **uv uniquement** pour Python — jamais pip install, jamais requirements.txt
6. **Pas de console.log** en prod côté Next.js — logger structuré uniquement
7. **Pas de secrets dans le code** — toujours process.env ou os.environ
8. **Webhooks** : répondre HTTP 200 immédiatement, traiter en async
9. **Valider TypeScript** : npx tsc --noEmit doit passer avant chaque commit

---

## STACK TECHNIQUE

| Couche | Technologie | Version | Notes |
|--------|-------------|---------|-------|
| Gateway | Next.js | 16+ | App Router obligatoire |
| ORM | Prisma | 7+ | SQLite local |
| Runtime JS | Node.js | 22+ | |
| Gestionnaire Python | uv | latest | Jamais pip |
| Agent LLM | smolagents | 1.9+ | CodeAgent |
| API serveur Python | FastAPI | 0.115+ | |
| UI dev | Gradio | 5+ | |
| LLM local | Ollama | latest | Port 11434 |
| LLM cloud | Z.ai GLM-4.7 | — | OpenAI-compatible |
| Language | TypeScript | 5+ | strict: true |

---

## MODÈLES LLM

### Ollama — 100% local, 0 donnée sortante

| ID | Modèle | Taille | Usage |
|----|--------|--------|-------|
| fast | qwen3:4b | 2.6GB | Réponses rapides |
| smart | qwen3:8b | 5.2GB | Usage quotidien |
| main | qwen3:14b | 9.3GB | Modèle principal — défaut |

### Z.ai — Cloud (données envoyées à Z.ai)

| ID | Modèle | Usage |
|----|--------|-------|
| code | glm-4.7-flash | Code, tâches techniques |
| reason | glm-4.7 | Raisonnement profond |

Règles modèles :
- Modèle par défaut : main (qwen3:14b)
- Si ZAI_API_KEY absent : fallback silencieux sur main
- think: false en mode agent (évite verbosité Qwen3)
- num_ctx: 32768 pour tous les modèles Ollama
- Provider Ollama : LiteLLMModel avec prefix ollama_chat/
- Provider Z.ai : LiteLLMModel avec prefix openai/ (compatible OpenAI)

---

## SCHÉMA BASE DE DONNÉES

### Prisma 7 — Points critiques
- url dans schema.prisma n'existe plus
- La connexion se configure dans gateway/prisma.config.ts via datasource.url
- adapter, earlyAccess, engine sont supprimés en v7
- PrismaLibSQL prend { url: string } directement, pas besoin de createClient()

### Changer le schéma
1. Modifier `gateway/prisma/schema.prisma`
2. `cd gateway && npx prisma migrate dev --name <description>`
3. Le client Prisma est régénéré automatiquement
4. Si changement cassant (suppression colonne/table) : `npx prisma migrate reset`
5. Jamais de modifications manuelles sur `dev.db` — utiliser Prisma Studio ou migrations

### Table Conversation
- id : cuid, PK
- channel : "webchat" | "whatsapp" | "nextcloud"
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

### WhatsApp (Meta Cloud API)
- GET /api/webhook/whatsapp : vérification token Meta
- POST /api/webhook/whatsapp : répondre 200 immédiatement, traiter async
- Envoi via https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages
- Critique : Meta renvoie le message si pas de 200 dans les 20 secondes

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

### V1 — Actifs
Aucun outil pour l'instant — l'agent répond en langage naturel uniquement.

### V2 — Bloqués, ne pas implémenter
- web_search via SearXNG local
- run_code sandbox Python/Node
- read_file / write_file dossier whitelist
- Browser control Playwright

### Règles de codage outils
- Toujours sous-classe Tool (pas décorateur @tool) pour compatibilité Ollama
- Imports dans forward(), pas au top-level du fichier
- Timeout 10s sur tous les appels HTTP
- max_steps=5 obligatoire sur CodeAgent

---

## VARIABLES D'ENVIRONNEMENT

### gateway/.env.local
- DATABASE_URL : file:./prisma/dev.db
- WEBCHAT_TOKEN : min 32 chars (openssl rand -hex 32)
- CRON_SECRET : min 32 chars
- AGENT_URL : http://localhost:8000
- WHATSAPP_VERIFY_TOKEN
- WHATSAPP_ACCESS_TOKEN
- WHATSAPP_PHONE_NUMBER_ID
- NEXTCLOUD_BASE_URL
- NEXTCLOUD_BOT_SECRET
- NEXTCLOUD_BOT_ID

### agent/.env
- OLLAMA_BASE_URL : http://localhost:11434
- ZAI_API_KEY : optionnel
- ZAI_BASE_URL : https://open.bigmodel.cn/api/paas/v4

---

## WORKFLOW DE DÉVELOPPEMENT

### Ajouter une nouvelle route API Next.js
1. Lire skill `nextjs-api-routes`
2. Créer fichier `gateway/app/api/<endpoint>/route.ts`
3. Suivre pattern standard : try/catch, validation, NextResponse.json
4. Si webhook : réponse 200 immédiatement, traitement async
5. Tester avec curl ou Postman avant de construire UI

### Ajouter un nouvel outil smolagents
1. Lire skill `smolagents-tools`
2. Créer fichier `agent/tools/<outil>.py`
3. TOUJOURS sous-classe `Tool`, jamais décorateur `@tool`
4. Imports dans `forward()`, pas au top-level
5. Timeout 10s sur tous les appels HTTP
6. Ajouter à `agent/tools/__init__.py` dans la liste TOOLS
7. Tester dans Gradio avant l'intégration

### Modification base de données
1. Lire skill `prisma-patterns`
2. Modifier `gateway/prisma/schema.prisma`
3. Créer migration : `npx prisma migrate dev --name <description>`
4. Mettre à jour les helpers dans `gateway/lib/memory.ts` si nécessaire
5. Vérifier les index et contraintes

### Workflow typique pour un nouveau module
1. LIRE le skill correspondant (webhook, api-route, prisma, smolagents-tools)
2. Créer/modifier les fichiers nécessaires
3. `cd gateway && npx tsc --noEmit` → corriger les erreurs TypeScript
4. `cd agent && uv run ruff check` → corriger les warnings Python
5. Tester manuellement via Gradio (agent) ou curl (gateway)
6. Vérifier que les deux services tournent
7. Valider CHECKPOINT avec l'utilisateur
8. Commit : `feat(module): description`

---

## DÉPANNAGE

### Gateway Next.js ne démarre pas
- Vérifier que `node_modules` existe : `npm install` si absent
- Vérifier que `dev.db` existe : `npx prisma migrate dev` si absent
- Vérifier les variables d'env dans `gateway/.env.local`
- Erreur "PrismaClient initialization error" → problème configuration DB

### Agent Python ne démarre pas
- Vérifier que l'environnement uv existe : `uv sync` si erreur module
- Vérifier que Ollama tourne : `curl http://localhost:11434/api/tags`
- Vérifier que les modèles sont téléchargés : `ollama list`
- Erreur "ModuleNotFoundError" → `uv sync` dans dossier agent

### Erreur TypeScript "Cannot find module"
- Vérifier imports relatifs (commencer par `./` ou `../`)
- Vérifier que le fichier existe
- `npx tsc --noEmit` pour voir l'erreur complète

### Webhook ne reçoit pas les messages
- Vérifier que ngrok (ou tunnel public) est actif en dev
- Vérifier l'URL enregistrée dans Meta/Nextcloud
- Tester avec curl sur le endpoint GET pour vérifier la route
- Vérifier les logs : terminal gateway + logs Meta/Nextcloud

### Erreur Prisma "Unique constraint failed"
- `npx prisma studio` pour voir les données existantes
- Vérifier la constraint `@@unique` dans schema.prisma
- `npx prisma migrate reset` si données de test acceptable

---

## CONVENTIONS DE CODE

### Python
- Python 3.11+, type hints partout
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

---

## CE QU'ON NE FAIT PAS

- Pas de multi-utilisateurs
- Pas de Docker pour l'app principale
- Pas de Redis ou message queue
- Pas de pip install ou requirements.txt
- Pas de features V2 sans validation explicite
- Pas de Telegram, Discord, Slack, Signal

---

## PROGRESSION MODULES

### Modules V1 — À implémenter séquentiellement
- ✅ Module 0 — Socle & Configuration
- ✅ Module 1 — Cerveau Python (smolagents + FastAPI + Gradio)
- ✅ Module 2 — Mémoire (Next.js + Prisma 7 + SQLite)
- ⏳ Module 3 — WebChat (UI + streaming + auth) — PROCHAIN
- ⏳ Module 4 — Canal WhatsApp
- ⏳ Module 5 — Canal Nextcloud Talk
- ⏳ Module 6 — Cron & Proactivité
- ⏳ Module 7 — Z.ai GLM-4.7 + Health Check
- ⏳ Module 8 — Identity & Persona

### Modules V2 — BLOQUÉS
- V2-A — Voice/STT sur Nextcloud Talk (whisper.cpp)
- V2-B — Exécution de code sandbox
- V2-C — Lecture/écriture fichiers whitelist
- V2-D — Browser control Playwright
- V2-E — Mémoire vectorielle (pgvector + nomic-embed-text)

**Règle** : JAMAIS implémenter V2 sans validation explicite utilisateur dans PROGRESS.md

### Gestion des CHECKPOINTS
- Chaque module se termine par un CHECKPOINT
- STOP et attendre validation utilisateur avant de continuer
- Le CHECKPOINT est validé dans PROGRESS.md
- Une fois validé, passer au module suivant

### Comment savoir quel module faire
1. Lire `PROGRESS.md` → repérer le module en cours
2. Lire le skill correspondant dans `.claude/skills/`
3. Implémenter selon PLAN.md pour ce module
4. Valider avec CHECKPOINT dans PROGRESS.md

---

## TESTS ET QUALITÉ CODE

### État actuel
- Aucun test unitaire ou d'intégration implémenté
- Tests manuels via Gradio (agent) et curl (gateway)
- Linting configuré mais pas obligatoire avant commit

### TypeScript (Gateway)
- `npx tsc --noEmit` → validation types avant commit
- `npm run lint` → ESLint (configuré avec @typescript-eslint)
- strict: true dans tsconfig.json → pas de `any`, type guards obligatoires

### Python (Agent)
- `uv run ruff check` → linting (E, F, I activés)
- `uv run ruff format` → formatage
- `uv run pyright` → vérification types (basic mode)
- Python 3.11+ exigé, type hints partout

### À faire
- Tests unitaires pour helpers lib/memory.ts
- Tests d'intégration pour routes API
- Tests pour outils smolagents
- Setup pytest si tests ajoutés

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

### Skills internes — LIRES AVANT DE CODER
- `.claude/skills/prisma-patterns/SKILL.md` — Patterns Prisma 7 et opérations DB
- `.claude/skills/nextjs-api-routes/SKILL.md` — Routes API Next.js et handlers
- `.claude/skills/channel-webhooks/SKILL.md` — WhatsApp + Nextcloud Talk Bot
- `.claude/skills/smolagents-tools/SKILL.md` — Création d'outils smolagents

### Documentation externe
- smolagents : https://huggingface.co/docs/smolagents
- Prisma 7 Config : https://pris.ly/d/config-datasource
- Z.ai GLM-4.7 : https://open.bigmodel.cn/dev/api
- Ollama API : https://github.com/ollama/ollama/blob/main/docs/api.md
- WhatsApp Cloud API : https://developers.facebook.com/docs/whatsapp/cloud-api
- Nextcloud Talk Bot : https://nextcloud-talk.readthedocs.io/en/latest/bot-list/
- Prisma 7 Docs : https://www.prisma.io/docs
- Next.js 16 : https://nextjs.org/docs/app
- Gradio : https://www.gradio.app/docs
- FastAPI : https://fastapi.tiangolo.com

### Documentation projet
- `README.md` — Vue d'ensemble et démarrage rapide
- `PLAN.md` — Plan d'implémentation complet (V1 + V2)
- `PROGRESS.md` — État d'avancement module par module
- `COMPARATIF.md` — Choix technologiques et alternatives

### Connaissances clés
- LLM Qwen3 supporte `think` mode → désactivé en agent (`think: False`)
- Prisma 7 change : `url` supprimé du schema, config via `prisma.config.ts`
- smolagents + Ollama → toujours sous-classe `Tool`, jamais décorateur `@tool`
- Webhooks → HTTP 200 immédiatement, traitement async
- uv gestionnaire Python → jamais pip, jamais requirements.txt
