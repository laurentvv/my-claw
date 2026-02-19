# PLAN.md — Plan Global my-claw

---

## VISION

Assistant personnel self-hosted, privacy-first, tournant sur une machine dédiée.
Mono-utilisateur, minimaliste, extensible prudemment module par module.
Pas de cloud obligatoire — local-first par défaut, cloud optionnel.

---

## ARCHITECTURE CIBLE

```
┌─────────────────────────────────────────────────────────────┐
│                      Machine dédiée                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Next.js 16 — Gateway & Mémoire (:3000)             │   │
│  │  Webhooks canaux, Prisma SQLite, WebChat UI         │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │ HTTP interne                          │
│  ┌──────────────────▼──────────────────────────────────┐   │
│  │  Python smolagents — Cerveau (:8000)                │   │
│  │  CodeAgent, outils, multi-modèles                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Gradio — UI dev/test (:7860)                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Ollama :11434 — modèles locaux                             │
│  SQLite  — mémoire conversations                            │
└─────────────────────────────────────────────────────────────┘
         │                        │
   WhatsApp                 Nextcloud Talk
   (Meta Cloud API)         (Bot HMAC-SHA256)
```

---

## PLAN V1 — 8 MODULES

### MODULE 0 — Socle & Configuration
**But :** Repo propre, deux services qui démarrent, Ollama opérationnel.

Périmètre :
- Structure dossiers gateway/ + agent/
- .gitignore, .env.example, README
- Next.js 16 initialisé (App Router, TypeScript, Tailwind)
- Python uv initialisé avec pyproject.toml
- Ollama avec qwen3:4b / 8b / 14b

Livrable : les deux services démarrent, ollama list répond.

---

### MODULE 1 — Cerveau Python
**But :** Agent smolagents accessible via HTTP, testable dans Gradio.

Périmètre :
- agent/main.py : FastAPI avec POST /run et GET /health
- agent/gradio_app.py : interface Gradio avec sélecteur de modèle
- agent/tools/__init__.py : liste vide prête à recevoir les outils
- Factory de modèles : fast/smart/main (Ollama) + code/reason (Z.ai)
- Fallback automatique Z.ai → main si clé absente
- Gestion historique de conversation injectée dans le prompt
- Qwen3 : think=false, num_ctx=32768

Livrable : Gradio répond à une question, /health retourne ok.

---

### MODULE 2 — Mémoire
**But :** Persister les conversations, passer l'historique à l'agent.

Périmètre :
- gateway/prisma/schema.prisma : tables Conversation, Message, CronJob, Settings
- gateway/prisma.config.ts : configuration Prisma 7 (datasource.url)
- gateway/lib/db.ts : singleton PrismaClient avec PrismaLibSQL
- gateway/lib/memory.ts : getOrCreateConversation, addMessage, getHistory
- gateway/lib/agent-client.ts : appel HTTP vers Python :8000
- Migration SQLite init

Livrable : Prisma Studio montre les tables, helpers fonctionnent.

---

### MODULE 3 — WebChat
**But :** Interface web fonctionnelle avec streaming et authentification.

Périmètre :
- gateway/app/(webchat)/page.tsx : UI chat sobre, mobile-friendly
- gateway/app/api/chat/route.ts : endpoint SSE, auth token, mémoire, appel agent
- Authentification par header Authorization: Bearer {WEBCHAT_TOKEN}
- Streaming Server-Sent Events
- Historique affiché au chargement
- Sélecteur de modèle

Livrable : chat fonctionnel dans le navigateur, historique persistant.

---

### MODULE 4 — Canal WhatsApp
**But :** Recevoir et envoyer des messages via Meta Cloud API.

Périmètre :
- gateway/app/api/webhook/whatsapp/route.ts : GET (vérif) + POST (réception async)
- gateway/lib/channels/whatsapp.ts : fonction send(to, text)
- Flux complet : webhook → mémoire → agent → réponse WA
- Exposition publique du webhook pour Meta (ngrok en dev)

Livrable : envoyer un WhatsApp → recevoir la réponse de l'agent.

---

### MODULE 5 — Canal Nextcloud Talk
**But :** Bot Nextcloud Talk avec sécurité HMAC.

Périmètre :
- gateway/app/api/webhook/nextcloud/route.ts : vérification HMAC-SHA256
- gateway/lib/channels/nextcloud.ts : fonction send(token, message)
- Enregistrement du bot dans l'admin Nextcloud

Livrable : message dans Nextcloud Talk → réponse de l'agent.

---

### MODULE 6 — Cron & Proactivité
**But :** L'assistant peut initier des messages selon un planning.

Périmètre :
- gateway/app/api/cron/route.ts : lecture CronJobs actifs, exécution, protégé X-Cron-Secret
- Configuration crontab système pour appeler /api/cron chaque minute
- UI minimaliste pour créer/activer/désactiver des CronJobs

Livrable : un CronJob créé déclenche un message au bon moment.

---

### MODULE 7 — Z.ai GLM-4.7 + Health Check
**But :** Provider cloud opérationnel + monitoring de l'ensemble.

Périmètre :
- Configuration ZAI_API_KEY et test des modèles code et reason
- gateway/app/api/health/route.ts : statut Ollama, agent Python, DB SQLite

Livrable : GLM-4.7 répond via Gradio, /api/health retourne tous les statuts.

---

### MODULE 8 — Identity & Persona
**But :** L'assistant a une personnalité persistante configurable.

Périmètre :
- UI d'édition du system prompt dans WebChat
- Injection du system prompt dans chaque appel à l'agent Python
- Persistance dans la table Settings (clés : system_prompt, persona_name)

Livrable : changer le system prompt → l'assistant change de personnalité.

---

## PLAN V2 — OUTILS AVANCÉS

Ces modules sont bloqués et ne doivent pas être implémentés avant décision explicite.
Chaque item nécessite un feu vert de l'utilisateur dans PROGRESS.md avant de commencer.

### V2-A — Voice / STT sur Nextcloud Talk
Flux : message vocal Nextcloud → téléchargement fichier audio → transcription whisper.cpp local → réponse texte.
Dépendances : whisper.cpp (binaire compilé), nodejs-whisper, ffmpeg.
Limitation connue : l'API bot Nextcloud ne supporte pas l'envoi audio — réponse texte uniquement.

### V2-B — Exécution de code
Sandbox isolé pour exécuter du Python ou du Node.js à la demande de l'agent.
Option légère : Pyodide (WASM) ou Deno sandbox.
Option robuste : container Docker dédié.

### V2-C — Lecture et écriture de fichiers
Outil smolagents read_file / write_file sur un dossier /data/allowed/ en whitelist stricte.
Aucun accès système, chemin absolu uniquement dans le dossier autorisé.

### V2-D — Browser control
Playwright headless piloté comme outil smolagents.
Utile pour scraping, remplissage de formulaires, automatisation web sans API.

### V2-E — Mémoire vectorielle
pgvector + embeddings via nomic-embed-text (déjà disponible sur Ollama).
Permet de retrouver des souvenirs pertinents dans de longues histoires de conversation.
Complète (ne remplace pas) l'historique glissant de 20 messages.

---

## DÉCISIONS PRISES

| Sujet | Décision | Raison |
|-------|----------|--------|
| WhatsApp | Meta Cloud API (officiel) | Plus stable que Baileys (reverse-engineering) |
| Nextcloud Talk | Ajouté comme canal prioritaire | Privacy, déjà dans l'infra |
| Docker | Non pour l'app | Complexité inutile, machine dédiée |
| Redis | Non | Pas de besoin de queue pour mono-utilisateur |
| Mémoire vectorielle | V2 | Commencer simple, ajouter si besoin ressenti |
| SearXNG | Retiré du V1 | Solution alternative à décider |
| Telegram/Discord/Slack | Exclus | Non voulu |
| Voice TTS sortante | Impossible via bot NC Talk | API bot ne supporte pas l'upload audio |

---

## CONTRAINTES PERMANENTES

- Machine dédiée séparée de la machine personnelle (vie privée)
- Mono-utilisateur — pas d'auth complexe
- Local-first — Ollama prioritaire, Z.ai optionnel
- 14B max sur la config actuelle (qwen3:14b = modèle principal)
- Pas de Docker obligatoire pour l'application principale
- Toutes les dépendances justifiées dans AGENTS.md avant d'être ajoutées

---

## ORDRE D'IMPLÉMENTATION RECOMMANDÉ

```
MODULE 0  DONE  Socle
MODULE 1  DONE  Cerveau Python
MODULE 2  DONE  Mémoire Prisma
MODULE 3  TODO  WebChat          ← PROCHAIN
MODULE 4  TODO  WhatsApp
MODULE 5  TODO  Nextcloud Talk
MODULE 6  TODO  Cron
MODULE 7  TODO  Z.ai + Health
MODULE 8  TODO  Identity
─────────────────────────────────
V2-A      HOLD  Voice STT
V2-B      HOLD  Code sandbox
V2-C      HOLD  Fichiers
V2-D      HOLD  Browser
V2-E      HOLD  Mémoire vectorielle
```
