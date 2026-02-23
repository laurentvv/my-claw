# STATUS — Vue rapide my-claw

> Dernière mise à jour : 2026-02-23
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
| **Tools** | ✅ **8/10** | TOOL-1,2,3,4,5,7,8,9,10,11 DONE / TOOL-6 TODO |
| **4 — Nextcloud Talk** | ⏳ TODO | Bot HMAC-SHA256 |
| **5 — Cron** | ⏳ TODO | Tâches proactives |
| **6 — Z.ai + Health** | ⏳ TODO | GLM-4.7 + monitoring |
| **7 — Identity** | ⏳ TODO | Persona + system prompt |

---

## 🛠️ Outils smolagents (8/10)

| Tool | Statut | Description | Tests |
|------|--------|-------------|-------|
| **TOOL-1** | ✅ | Fichiers Windows (read/write/create/delete/list/move/search) | ✅ Validé |
| **TOOL-2** | ✅ | OS PowerShell (fix curl alias + encodage cp1252) | ✅ Validé |
| **TOOL-3** | ✅ | Presse-papier Windows | ✅ Validé |
| **TOOL-4** | ✅ | DuckDuckGoSearchTool (built-in smolagents, illimité) | ✅ Validé |
| **TOOL-5** | ✅ | VisitWebpageTool (built-in smolagents, illimité) | ✅ Validé |
| **TOOL-7** | ✅ | Vision locale (Ollama qwen3-vl:2b) - 100% local | ✅ Validé via délégation |
| **TOOL-8** | ✅ | Screenshot Windows | ✅ Validé via délégation |
| **TOOL-9** | ✅ | Souris/Clavier (contrôle direct OS via pyautogui) | ✅ Validé via délégation |
| **TOOL-11** | ✅ | GUI Grounding (qwen3-vl:2b pour localisation UI) | ✅ Validé via délégation |
| **TOOL-10** | ✅ | MCP Chrome DevTools (26 outils Puppeteer) - TESTÉ & VALIDÉ | ✅ Validé |
| **TOOL-6** | ⏳ | MCP Zread GitHub (Z.ai) | TODO |

---

## 🚀 Améliorations récentes (2026-02-23)

- ✅ **TOOL-4 Web Search** : DuckDuckGoSearchTool validé (built-in smolagents, illimité)
- ✅ **TOOL-5 Web Reader** : VisitWebpageTool validé (built-in smolagents, illimité)
- ✅ **TOOL-8+7 Screenshot + Vision** : Délégation pc_control → vision validée
- ✅ **Fix encodage PowerShell** : cp1252 au lieu de utf-8 dans os_exec.py
- ✅ **Graceful degradation** : Imports conditionnels pour ddgs/markdownify
- ✅ **Sécurité URL** : Validation SSRF dans WebVisitTool
- ✅ **Skills mis à jour** : Architecture directe vs délégation clarifiée
- ✅ **Timeouts ajustés** : Agent 300s (5min) pour tâches complexes

---

## 🧪 Résultats des tests (2026-02-23)

| Test | Prompt | Résultat | Temps |
|------|--------|----------|-------|
| TOOL-1.1 | Créer fichier | ✅ OK | ~5s |
| TOOL-1.2 | Lire fichier | ✅ OK | ~5s |
| TOOL-2.1 | PowerShell Get-Date | ✅ OK | ~5s |
| TOOL-3.1 | Write clipboard | ✅ OK | ~5s |
| TOOL-3.2 | Read clipboard | ✅ OK | ~5s |
| TOOL-4.1 | Search smolagents | ✅ OK | ~10s |
| TOOL-5.1 | Visit example.com | ✅ OK | ~10s |
| TOOL-8+7 | Screenshot + Vision | ✅ OK | ~240s |

**Taux de réussite : 8/8 = 100%** ✅

---

## 🧠 Modèles LLM

### Ollama (100% local)
- **main** : qwen3:8b (5.2GB) — Modèle principal
- **fast** : gemma3:latest (3.3GB) — Réponses rapides
- **vision** : qwen3-vl:2b (2.3GB) — Vision locale

### Z.ai (cloud, optionnel)
- **code** : glm-4.7-flash — Tâches techniques
- **reason** : glm-4.7 — Raisonnement profond (défaut avec ZAI_API_KEY)

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
│   ├── tools/           9 outils locaux
│   └── agents/          3 sous-agents (pc_control, vision, browser)
│
├── PROGRESS.md          📋 Détails complets
├── STATUS.md            ⚡ Vue rapide (ce fichier)
├── PLAN.md              🗺️ Architecture globale
└── LEARNING.md          📚 Découvertes techniques
```

---

## 🎯 Prochain objectif

**TOOL-6** : MCP Zread GitHub (lecture de repos GitHub via Z.ai API)

---

## 🔗 Liens rapides

- **Démarrage** : Voir `README.md`
- **Détails** : Voir `PROGRESS.md`
- **Architecture** : Voir `PLAN.md`
- **Techniques** : Voir `LEARNING.md`
- **Skills** : Voir `agent/skills.txt`
- **Tests** : Voir `TEST-RESULTS.md`
