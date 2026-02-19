# my-claw 🦞

Assistant personnel minimaliste, self-hosted, privacy-first.

## Architecture

```
gateway/    → Next.js 16 — webhooks canaux, mémoire Prisma, WebChat
agent/      → Python smolagents — cerveau LLM, outils, Gradio dev UI
```

## Prérequis

- Node.js 24+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (gestionnaire Python)
- [Ollama](https://ollama.ai) avec Qwen3 : `ollama pull qwen3:14b` (9.3GB — modèle principal)

## Démarrage rapide

```bash
# 1. Variables d'environnement
cp .env.example .env.local
# Remplir les valeurs dans .env.local

# 2. Gateway (Next.js)
cd gateway
npm install
npx prisma migrate dev --name init
npm run dev                          # → http://localhost:3000

# 3. Agent (Python — uv)
cd agent
uv sync                              # installe les dépendances
uv run uvicorn main:app --reload     # → http://localhost:8000

# 4. Gradio dev UI (optionnel)
cd agent
uv run python gradio_app.py          # → http://localhost:7860
```

> Pour ajouter une dépendance Python : `uv add <package>` (jamais pip)

## Modules

| Module | Status | Description |
|--------|--------|-------------|
| 0 — Socle | ✅ | Structure, config, services locaux |
| 1 — Agent | ⏳ | smolagents + FastAPI + Gradio |
| 2 — Mémoire | ⏳ | Prisma + historique conversations |
| 3 — WebChat | ⏳ | UI web + streaming + auth |
| 4 — WhatsApp | ⏳ | Meta Cloud API webhook |
| 5 — Nextcloud Talk | ⏳ | Bot HMAC-SHA256 |
| 6 — Cron | ⏳ | Tâches proactives |
| 7 — Z.ai + Health | ⏳ | GLM-4.7 + monitoring |
| 8 — Identity | ⏳ | Persona + system prompt |

## Documentation

Voir [AGENTS.md](./AGENTS.md) pour le guide complet d'architecture et d'implémentation.
