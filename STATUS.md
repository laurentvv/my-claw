# STATUS — Vue rapide my-claw

> Dernière mise à jour : 2026-02-20  
> Repo : https://github.com/laurentvv/my-claw

---

## 🎯 Vision

Assistant personnel hybride 100% local (Ollama) avec capacités cloud optionnelles (Z.ai).  
Architecture : Next.js 16 (gateway) + Python smolagents (agent) + Gradio (UI dev).

---

## 📊 Progression globale

| Module | Statut | Commentaire |
|--------|--------|-------------|
| **0 — Socle** | ✅ DONE | Structure, Next.js 16, Python uv, Ollama |
| **1 — Agent** | ✅ DONE | smolagents + FastAPI + Gradio + GLM-4.7 fix + skills |
| **2 — Mémoire** | ✅ DONE | Prisma 7 + SQLite + historique conversations |
| **3 — WebChat** | ✅ DONE | UI React + SSE streaming + auth Bearer |
| **Tools** | 🔄 **6/10** | TOOL-1,2,3,7,8,9 DONE / TOOL-4,5,6,10 TODO |
| **4 — Nextcloud Talk** | ⏳ TODO | Bot HMAC-SHA256 |
| **5 — Cron** | ⏳ TODO | Tâches proactives |
| **6 — Z.ai + Health** | ⏳ TODO | GLM-4.7 + monitoring |
| **7 — Identity** | ⏳ TODO | Persona + system prompt |

---

## 🛠️ Outils smolagents (6/10)

| Tool | Statut | Description |
|------|--------|-------------|
| **TOOL-1** | ✅ | Fichiers Windows (read/write/create/delete/list/move/search) |
| **TOOL-2** | ✅ | OS PowerShell (fix curl alias) |
| **TOOL-3** | ✅ | Presse-papier Windows |
| **TOOL-7** | ✅ | Vision locale (Ollama qwen3-vl:2b) - 100% local |
| **TOOL-8** | ✅ | Screenshot Windows |
| **TOOL-9** | ⚠️ | Souris/Clavier (bloqué par orchestration) |
| **TOOL-4** | ⏳ | MCP Web Search Z.ai |
| **TOOL-5** | ⏳ | MCP Web Reader Z.ai |
| **TOOL-6** | ⏳ | MCP Zread GitHub |
| **TOOL-10** | ⏳ | MCP Chrome DevTools |

---

## 🚀 Améliorations récentes (2026-02-20)

- ✅ **Fix GLM-4.7** : Nettoyage automatique des balises `</code` (SyntaxError résolu)
- ✅ **Timeouts augmentés** : Gateway 6min, Agent 4min (GLM-4.7 screenshot+vision)
- ✅ **Guidage agent** : `instructions` + `additional_authorized_imports` (Python natif)
- ✅ **TOOL-7 Vision** : Ollama qwen3-vl:2b au lieu de Z.ai MCP (100% local)
- ✅ **Skills externalisés** : `agent/skills.txt` avec patterns de code + `final_answer()`

---

## 🔧 Stack technique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Gateway | Next.js | 16+ |
| ORM | Prisma | 7+ |
| Agent | smolagents | 1.9+ |
| API Python | FastAPI | 0.115+ |
| UI dev | Gradio | 5+ |
| LLM local | Ollama | latest |
| LLM cloud | Z.ai GLM-4.7 | optionnel |

---

## 🧠 Modèles LLM

### Ollama (100% local)
- **main** : qwen3:8b (5.2GB) — Modèle principal
- **fast** : gemma3:latest (3.3GB) — Réponses rapides
- **vision** : qwen3-vl:2b (2.3GB) — Vision locale

### Z.ai (cloud, optionnel)
- **code** : glm-4.7-flash — Tâches techniques
- **reason** : glm-4.7 — Raisonnement profond

---

## 📂 Structure

```
my-claw/
├── gateway/              Next.js 16 + Prisma 7
│   ├── app/             App Router
│   ├── lib/             DB + agent client
│   └── prisma/          Schema + migrations
│
├── agent/               Python smolagents
│   ├── main.py          FastAPI server
│   ├── gradio_app.py    UI dev
│   ├── skills.txt       Patterns de code
│   └── tools/           6 outils locaux
│
├── PROGRESS.md          📋 Détails complets
├── STATUS.md            ⚡ Vue rapide (ce fichier)
├── PLAN.md              🗺️ Architecture globale
└── LEARNING.md          📚 Découvertes techniques
```

---

## 🎯 Prochain objectif

**TOOL-4** : MCP Web Search Z.ai (recherche web via Z.ai)

---

## 🔗 Liens rapides

- **Démarrage** : Voir `README.md`
- **Détails** : Voir `PROGRESS.md`
- **Architecture** : Voir `PLAN.md`
- **Techniques** : Voir `LEARNING.md`
- **Skills** : Voir `agent/SKILLS.md`

