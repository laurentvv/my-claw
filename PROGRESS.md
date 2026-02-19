# PROGRESS.md — État d'avancement my-claw

Dernière mise à jour : Février 2026

---

## LÉGENDE
- DONE : terminé et validé par l'utilisateur
- EN COURS : en cours d'implémentation
- A FAIRE : prochain à implémenter
- BLOQUE : ne pas toucher sans validation explicite

---

## MODULE 0 — Socle & Configuration
**Statut : DONE**

Ce qui a été fait :
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

Checkpoint validé : OUI

---

## MODULE 1 — Cerveau Python (smolagents + FastAPI + Gradio)
**Statut : DONE**

Ce qui a été fait :
- agent/main.py : FastAPI avec POST /run et GET /health
- agent/gradio_app.py : interface Gradio fonctionnelle
- agent/tools/__init__.py : TOOLS = [] prêt à recevoir les outils
- Correction bug Gradio 5 : historique en dicts {role, content} pas en tuples
- Modèles configurés : fast/smart/main (Ollama) + code/reason (Z.ai)
- Fallback automatique Z.ai → main si ZAI_API_KEY absent
- think: false activé pour Qwen3 en mode agent
- num_ctx: 32768 pour tous les modèles Ollama

Aucun outil actif — l'agent répond en langage naturel uniquement.

Checkpoint validé : OUI

---

## MODULE 2 — Mémoire (Next.js + Prisma 7 + SQLite)
**Statut : DONE**

Ce qui a été fait :
- gateway/prisma/schema.prisma : 4 tables (Conversation, Message, CronJob, Settings)
- gateway/prisma.config.ts : configuration Prisma 7 avec datasource.url
- gateway/lib/db.ts : singleton PrismaClient avec PrismaLibSQL
- gateway/lib/memory.ts : helpers getOrCreateConversation, addMessage, getHistory
- gateway/lib/agent-client.ts : appel HTTP vers Python :8000
- Migration init appliquée, dev.db créé
- Dépendances : prisma, @prisma/client, @prisma/adapter-libsql, @libsql/client

Note Prisma 7 importante :
- url retiré de schema.prisma (breaking change v7)
- PrismaLibSQL prend { url: string } directement
- prisma.config.ts utilise datasource.url (pas adapter ni earlyAccess)

Checkpoint validé : OUI

---

## MODULE 3 — WebChat (Next.js UI)
**Statut : DONE**

Ce qui a été fait :
- gateway/app/(webchat)/page.tsx : UI React avec Tailwind, mobile-friendly
- gateway/app/api/chat/route.ts : endpoint POST/GET avec auth token
- Authentification via header Authorization: Bearer {WEBCHAT_TOKEN}
- Streaming Server-Sent Events (SSE) pour les réponses agent
- Sauvegarde des messages en DB SQLite via lib/memory.ts
- Chargement historique persistant (localStorage + DB)
- Sélecteur de modèle (fast/smart/main/code/reason)
- Rejet correct des requêtes non authentifiées (401)

Tests validés :
- ✓ Gateway Next.js répond sur :3000
- ✓ Agent Python répond sur :8000
- ✓ POST /api/chat avec token streaming SSE fonctionnel
- ✓ Conversation ID généré et persisté en DB
- ✓ Messages user et assistant sauvegardés
- ✓ GET /api/chat retourne l'historique
- ✓ Rejet des requêtes sans token (401)
- ✓ UI React affiche les messages et gère le login

Checkpoint validé : OUI (tests automatisés + vérification DB)

---

## MODULE 4 — Canal WhatsApp
**Statut : A FAIRE**

À implémenter :
- gateway/app/api/webhook/whatsapp/route.ts
- gateway/lib/channels/whatsapp.ts
- Vérification token Meta (GET)
- Réception async (POST)
- Envoi via Meta Cloud API

---

## MODULE 5 — Canal Nextcloud Talk
**Statut : A FAIRE**

À implémenter :
- gateway/app/api/webhook/nextcloud/route.ts
- gateway/lib/channels/nextcloud.ts
- Vérification HMAC-SHA256 obligatoire
- Envoi via OCS API

---

## MODULE 6 — Cron & Proactivité
**Statut : A FAIRE**

À implémenter :
- gateway/app/api/cron/route.ts
- Lecture CronJobs actifs depuis DB
- Déclenchement via crontab système

---

## MODULE 7 — Z.ai GLM-4.7 + Health Check
**Statut : A FAIRE**

À implémenter :
- Configuration ZAI_API_KEY
- Test modèles code et reason
- gateway/app/api/health/route.ts : statut Ollama, agent Python, DB

---

## MODULE 8 — Identity & Persona
**Statut : A FAIRE**

À implémenter :
- UI édition system prompt dans WebChat
- Injection system prompt dans chaque appel agent
- Persistance dans table Settings

---

## MODULES V2 — BLOQUES

Ne pas implémenter avant décision explicite de l'utilisateur.

- V2-A : Voice/STT sur Nextcloud Talk (whisper.cpp)
- V2-B : Exécution de code sandbox
- V2-C : Lecture/écriture fichiers whitelist
- V2-D : Browser control Playwright
- V2-E : Mémoire vectorielle (pgvector + nomic-embed-text)
  Note : nomic-embed-text déjà disponible sur Ollama — prêt quand décision prise

---

## STRUCTURE ACTUELLE DU REPO

```
my-claw/
├── AGENTS.md
├── PROGRESS.md
├── COMPARATIF.md
├── README.md
├── .env.example
├── .gitignore
├── setup.ps1
├── agent/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── main.py               DONE module 1
│   ├── gradio_app.py         DONE module 1
│   └── tools/
│       └── __init__.py       DONE module 1 (vide)
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
    ├── app/                  scaffold Next.js — module 3 à faire
    └── ... (fichiers Next.js standard)
```
