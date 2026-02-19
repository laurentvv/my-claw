# PROGRESS.md — État d'avancement my-claw

Dernière mise à jour : Février 2026
Repo : https://github.com/laurentvv/my-claw

---

## LÉGENDE
- DONE    : terminé et validé par l'utilisateur
- A FAIRE : prochain à implémenter
- BLOQUE  : ne pas toucher sans validation explicite

---

## MODULE 0 — Socle & Configuration
**Statut : DONE**

- Repo GitHub créé : https://github.com/laurentvv/my-claw
- Structure dossiers : gateway/ (Next.js) + agent/ (Python)
- .gitignore complet (Node, Python, .env, .db, .venv, modèles)
- .env.example avec toutes les variables documentées
- Next.js 16 initialisé avec App Router + TypeScript + Tailwind
- Python uv initialisé avec pyproject.toml
- Ollama opérationnel avec 3 modèles disponibles :
  - qwen3:4b (2.6GB)
  - qwen3:8b (5.2GB)
  - qwen3:14b (9.3GB)
- Bonus déjà présents sur Ollama :
  - nomic-embed-text (utile pour mémoire vectorielle V2)
  - embeddinggemma (utile pour mémoire vectorielle V2)
  - lfm2.5-thinking:1.2b

---

## MODULE 1 — Cerveau Python (smolagents + FastAPI + Gradio)
**Statut : DONE**

- agent/main.py : FastAPI avec POST /run et GET /health
- agent/gradio_app.py : interface Gradio fonctionnelle
- agent/tools/__init__.py : TOOLS = [] prêt à recevoir les outils
- Correction bug Gradio 5 : historique en dicts {role, content} pas en tuples
- Modèles configurés : fast/smart/main (Ollama) + code/reason (Z.ai)
- Fallback automatique Z.ai → main si ZAI_API_KEY absent
- think: false activé pour Qwen3 en mode agent
- num_ctx: 32768 pour tous les modèles Ollama

Aucun outil actif — l'agent répond en langage naturel uniquement.

---

## MODULE 2 — Mémoire (Next.js + Prisma 7 + SQLite)
**Statut : DONE**

- gateway/prisma/schema.prisma : 4 tables (Conversation, Message, CronJob, Settings)
- gateway/prisma.config.ts : configuration Prisma 7 avec datasource.url
- gateway/lib/db.ts : singleton PrismaClient avec PrismaLibSQL
- gateway/lib/memory.ts : helpers getOrCreateConversation, addMessage, getHistory
- gateway/lib/agent-client.ts : appel HTTP vers Python :8000
- Migration init appliquée, dev.db créé
- Dépendances : prisma, @prisma/client, @prisma/adapter-libsql, @libsql/client

Notes Prisma 7 critiques (breaking changes) :
- url retiré de schema.prisma
- PrismaLibSQL prend { url: string } directement (pas createClient())
- prisma.config.ts utilise datasource.url (pas adapter ni earlyAccess)

---

## MODULE 3 — WebChat (Next.js UI)
**Statut : DONE**

- gateway/app/(webchat)/page.tsx : UI React avec Tailwind, mobile-friendly
- gateway/app/api/chat/route.ts : endpoint POST/GET avec auth token
- Authentification via header Authorization: Bearer {WEBCHAT_TOKEN}
- Streaming Server-Sent Events (SSE) pour les réponses agent
- Sauvegarde des messages en DB SQLite via lib/memory.ts
- Chargement historique persistant
- Sélecteur de modèle (fast/smart/main/code/reason)
- Rejet correct des requêtes non authentifiées (401)

Tests validés :
- Gateway Next.js répond sur :3000
- Agent Python répond sur :8000
- POST /api/chat avec token streaming SSE fonctionnel
- Conversation ID généré et persisté en DB
- Messages user et assistant sauvegardés
- GET /api/chat retourne l'historique
- Rejet des requêtes sans token (401)
- UI React affiche les messages et gère le login

Rapport complet : plans/validation-module3.md

---

## DÉCISION — WhatsApp retiré définitivement

WhatsApp supprimé du plan le 2026-02-19.
Raison : Nextcloud Talk suffit pour usage perso, pas de dépendance Meta souhaitée.
Les anciens modules 4 (WhatsApp) et 5 (Nextcloud) sont renumérotés en conséquence.

---

## MODULE 4 — Canal Nextcloud Talk
**Statut : A FAIRE — PROCHAIN MODULE**

À implémenter :
- gateway/app/api/webhook/nextcloud/route.ts
  - Vérification signature HMAC-SHA256 obligatoire
  - Headers : X-Nextcloud-Talk-Random + X-Nextcloud-Talk-Signature
  - Utiliser crypto.timingSafeEqual pour comparer les signatures
  - Répondre HTTP 200 immédiatement, traiter en async
- gateway/lib/channels/nextcloud.ts
  - Fonction send(token, message)
  - POST vers {NC_BASE_URL}/ocs/v2.php/apps/spreed/api/v1/bot/{BOT_ID}/message
  - Header OCS-APIRequest: true
- Enregistrer le bot dans l'admin Nextcloud, récupérer le secret NEXTCLOUD_BOT_SECRET

Variables d'env à remplir dans gateway/.env.local :
- NEXTCLOUD_BASE_URL
- NEXTCLOUD_BOT_SECRET
- NEXTCLOUD_BOT_ID

Checkpoint attendu :
- Envoyer un message au bot dans Nextcloud Talk → réponse de l'agent
- Mauvaise signature → HTTP 401
- Historique de la conversation visible dans Prisma Studio
- Commit : feat: module 4 — nextcloud talk

---

## MODULE 5 — Cron & Proactivité
**Statut : A FAIRE**

À implémenter :
- gateway/app/api/cron/route.ts
  - Protégé par header X-Cron-Secret
  - Lit les CronJobs actifs en DB
  - Exécute via agent Python et envoie la réponse sur Nextcloud Talk
- Configuration crontab système : appel chaque minute vers /api/cron
- UI minimaliste pour créer/activer/désactiver des CronJobs

---

## MODULE 6 — Z.ai GLM-4.7 + Health Check
**Statut : A FAIRE**

À implémenter :
- Configuration ZAI_API_KEY dans agent/.env
- Test modèles code (glm-4.7-flash) et reason (glm-4.7) via Gradio
- gateway/app/api/health/route.ts
  - Statut Ollama (:11434)
  - Statut agent Python (:8000)
  - Statut DB SQLite (ping Prisma)

---

## MODULE 7 — Identity & Persona
**Statut : A FAIRE**

À implémenter :
- UI d'édition du system prompt dans WebChat
- Injection du system prompt dans chaque appel à l'agent Python
- Persistance dans la table Settings (clés : system_prompt, persona_name)

---

## MODULES V2 — BLOQUES

Ne pas implémenter avant décision explicite de l'utilisateur dans ce fichier.

- V2-A : Voice/STT sur Nextcloud Talk (whisper.cpp + ffmpeg)
  Note : l'API bot NC Talk ne supporte pas l'envoi audio — STT entrant uniquement
- V2-B : Exécution de code sandbox (Pyodide ou Docker)
- V2-C : Lecture/écriture fichiers whitelist /data/allowed/
- V2-D : Browser control Playwright headless
- V2-E : Mémoire vectorielle — nomic-embed-text déjà dispo sur Ollama, prêt quand décidé

---

## STRUCTURE ACTUELLE DU REPO

```
my-claw/
├── AGENTS.md
├── PLAN.md
├── PROGRESS.md               ← CE FICHIER
├── COMPARATIF.md
├── README.md
├── .env.example
├── .gitignore
├── setup.ps1
├── .claude/
│   └── skills/
│       ├── smolagents-tools/SKILL.md
│       ├── prisma-patterns/SKILL.md
│       ├── nextjs-api-routes/SKILL.md
│       └── channel-webhooks/SKILL.md
├── plans/
│   └── validation-module3.md
├── agent/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── main.py               DONE module 1
│   ├── gradio_app.py         DONE module 1
│   └── tools/
│       └── __init__.py       DONE module 1
└── gateway/
    ├── prisma.config.ts      DONE module 2
    ├── prisma/
    │   ├── schema.prisma     DONE module 2
    │   ├── dev.db            DONE module 2 (gitignored)
    │   └── migrations/       DONE module 2
    ├── lib/
    │   ├── db.ts             DONE module 2
    │   ├── memory.ts         DONE module 2
    │   └── agent-client.ts   DONE module 2
    └── app/
        ├── (webchat)/
        │   └── page.tsx      DONE module 3
        └── api/
            └── chat/
                └── route.ts  DONE module 3
```
