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
- [Ollama](https://ollama.ai) avec les modèles suivants :
  - `ollama pull qwen3:8b` (5.2GB — modèle principal, recommandé)
  - `ollama pull qwen3-vl:2b` (2.3GB — vision locale pour TOOL-7)
  - `ollama pull gemma3:latest` (3.3GB — modèle rapide)
- Python 3.11+ (via uv)
- (Optionnel) Token Z.ai pour GLM-4.7 cloud (code/reason)

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
uv sync                              # installe les dépendances (pyautogui, pillow, pyperclip, etc.)
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
| 1 — Agent | ✅ | smolagents + FastAPI + Gradio + GLM-4.7 fix |
| 2 — Mémoire | ✅ | Prisma + historique conversations |
| 3 — WebChat | ✅ | UI web + streaming + auth |
| Tools | 🔄 | 6/10 outils implémentés (1,2,3,7,8,9 DONE / 4,5,6,10 TODO) |
| 4 — Nextcloud Talk | ⏳ | Bot HMAC-SHA256 |
| 5 — Cron | ⏳ | Tâches proactives |
| 6 — Z.ai + Health | ⏳ | GLM-4.7 + monitoring |
| 7 — Identity | ⏳ | Persona + system prompt |

### Outils smolagents implémentés

| Tool | Status | Description |
|------|--------|-------------|
| TOOL-1 | ✅ | Fichiers Windows (read/write/create/delete/list/move/search) |
| TOOL-2 | ✅ | Exécution OS Windows (PowerShell + fix curl alias) |
| TOOL-3 | ✅ | Presse-papier Windows |
| TOOL-7 | ✅ | Vision locale (Ollama qwen3-vl:2b) - 100% local |
| TOOL-8 | ✅ | Screenshot Windows |
| TOOL-9 | ⚠️ | Contrôle souris/clavier (implémenté mais nécessite orchestration avancée) |

### Améliorations récentes (2026-02-20)

- ✅ **Fix GLM-4.7** : Nettoyage automatique des balises `</code` générées par GLM-4.7 (SyntaxError résolu)
- ✅ **Timeouts augmentés** : Gateway 5min, Agent 3min pour l'exécution du code Python
- ✅ **Guidage de l'agent** : `instructions` + `additional_authorized_imports` pour préférer Python natif (requests, urllib, json, etc.)
- ✅ **TOOL-7 Vision** : Implémenté avec Ollama local (qwen3-vl:2b) au lieu de Z.ai MCP - 100% local, 0 donnée sortante

> **Note** : WhatsApp a été retiré du projet (2026-02-19). Nextcloud Talk suffit pour les besoins actuels.

## Documentation

- [AGENTS.md](./AGENTS.md) — Guide complet d'architecture et d'implémentation
- [PROGRESS.md](./PROGRESS.md) — État d'avancement du projet
- [LEARNING.md](./LEARNING.md) — Découvertes techniques et apprentissages
- [PLAN.md](./PLAN.md) — Plan global et architecture cible
- [IMPLEMENTATION-TOOLS.md](./IMPLEMENTATION-TOOLS.md) — Plan d'implémentation des outils smolagents
