# AGENTS.md — my-claw Assistant Personnel Hybride
> Fichier de guidage pour les IA de codage (Claude Code, Cursor, Codex, Windsurf...)
> Architecture : Next.js 16 (gateway) + Python smolagents (cerveau) + Gradio (UI dev)

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
- Prisma 7 Config : https://pris.ly/d/config-datasource
- Z.ai GLM-4.7 : https://open.bigmodel.cn/dev/api
- Ollama API : https://github.com/ollama/ollama/blob/main/docs/api.md
- WhatsApp Cloud API : https://developers.facebook.com/docs/whatsapp/cloud-api
- Nextcloud Talk Bot : https://nextcloud-talk.readthedocs.io/en/latest/bot-list/
- Prisma 7 Docs : https://www.prisma.io/docs
- Next.js 16 : https://nextjs.org/docs/app
- Gradio : https://www.gradio.app/docs
- FastAPI : https://fastapi.tiangolo.com
