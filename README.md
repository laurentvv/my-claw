# my-claw 🦞

Assistant personnel minimaliste, self-hosted, privacy-first.

📊 **Vue rapide** : [STATUS.md](STATUS.md) | 📋 **Détails complets** : [PROGRESS.md](PROGRESS.md)

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

Lancer le script d'installation automatique :

```powershell
./setup.ps1
```

> Pour ajouter une dépendance Python : `uv add <package>` (jamais pip)

## Modules

| Module | Status | Description |
|--------|--------|-------------|
| 0 — Socle | ✅ | Structure, config, services locaux |
| 1 — Agent | ✅ | smolagents + FastAPI + Gradio + GLM-4.7 fix |
| 2 — Mémoire | ✅ | Prisma + historique conversations |
| 3 — WebChat | ✅ | UI web + streaming + auth |
| Tools | 🔄 | 7/10 outils implémentés (1,2,3,7,8,10 DONE / 9 EN COURS / 4,5,6 TODO) |
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
| TOOL-9 | 🔄 | Contrôle souris/clavier (en cours - nécessite orchestration avancée) |
| TOOL-10 | ✅ | MCP Chrome DevTools (26 outils Puppeteer) - TESTÉ & VALIDÉ |

### Améliorations récentes (2026-02-20)

- ✅ **Fix GLM-4.7** : Nettoyage automatique des balises `</code` générées par GLM-4.7 (SyntaxError résolu)
- ✅ **Timeouts augmentés** : Gateway 5min, Agent 3min pour l'exécution du code Python
- ✅ **Guidage de l'agent** : `instructions` + `additional_authorized_imports` pour préférer Python natif (requests, urllib, json, etc.)
- ✅ **TOOL-7 Vision** : Implémenté avec Ollama local (qwen3-vl:2b) au lieu de Z.ai MCP - 100% local, 0 donnée sortante
- ✅ **TOOL-10 Chrome DevTools** : MCP chargé avec 26 outils Puppeteer - Tests validés

## Documentation

### Vue d'ensemble
- 📊 [STATUS.md](./STATUS.md) — **Vue rapide** du projet (statut, progression, stack)
- 📋 [PROGRESS.md](./PROGRESS.md) — État d'avancement détaillé (checkpoints, validations)

### Architecture et plan
- 🏗️ [AGENTS.md](./AGENTS.md) — Guide complet d'architecture et d'implémentation
- 🗺️ [PLAN.md](./PLAN.md) — Plan global et architecture cible
- 🛠️ [IMPLEMENTATION-TOOLS.md](./IMPLEMENTATION-TOOLS.md) — Plan d'implémentation des outils smolagents

### Techniques et apprentissages
- 📚 [LEARNING.md](./LEARNING.md) — Découvertes techniques et solutions
- 🎯 [agent/SKILLS.md](./agent/SKILLS.md) — Patterns de code réutilisables pour l'agent
