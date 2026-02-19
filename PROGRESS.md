# PROGRESS.md — État d'avancement my-claw

Dernière mise à jour : Février 2026
Repo : https://github.com/laurentvv/my-claw

---

## LÉGENDE
- DONE    : terminé et validé par l'utilisateur
- A FAIRE : prochain à implémenter
- BLOQUE  : ne pas toucher sans validation explicite

---

## MODULE 0 — Socle & Configuration — DONE

- Repo GitHub, structure gateway/ + agent/, .gitignore, .env.example, setup.ps1
- Next.js 16 App Router + TypeScript + Tailwind
- Python uv + pyproject.toml
- Ollama : qwen3:4b / qwen3:8b / qwen3:14b + nomic-embed-text + embeddinggemma

---

## MODULE 1 — Cerveau Python — DONE

- agent/main.py : FastAPI POST /run + GET /health
- agent/gradio_app.py : Gradio fonctionnel, bug Gradio 5 corrigé
- agent/tools/__init__.py : TOOLS = [] prêt
- Modèles : fast/smart/main (Ollama) + code/reason (Z.ai), fallback auto
- think: false, num_ctx: 32768 pour Qwen3

---

## MODULE 2 — Mémoire Prisma 7 + SQLite — DONE

- gateway/prisma/schema.prisma : Conversation, Message, CronJob, Settings
- gateway/prisma.config.ts : datasource.url (Prisma 7, pas de url dans schema)
- gateway/lib/db.ts : PrismaLibSQL({ url: string }) directement
- gateway/lib/memory.ts : getOrCreateConversation, addMessage, getHistory
- gateway/lib/agent-client.ts : appel HTTP :8000
- Migration init appliquée, dev.db créé

---

## MODULE 3 — WebChat — DONE

- gateway/app/(webchat)/page.tsx : UI React Tailwind mobile-friendly
- gateway/app/api/chat/route.ts : SSE streaming, auth Bearer token, mémoire
- Sélecteur modèle, historique persistant, rejet 401 sans token
- Rapport complet : plans/validation-module3.md

---

## DÉCISION — WhatsApp retiré (2026-02-19)

Retiré définitivement. Nextcloud Talk suffit, pas de dépendance Meta souhaitée.
Les modules 4/5/6/7/8 originaux ont été renumérotés en conséquence.

---

## MODULE TOOLS — Extensions Smolagents
**Statut : EN COURS — PRIORITAIRE avant Nextcloud Talk**

Objectif : rendre l'agent autonome sur la machine Windows.
Modèle principal : glm-4.7 (token Z.ai Coding Plan Lite).
Z.ai Lite : 100 calls/mois web search+reader+zread, 5h pool vision.
Règle absolue : un tool validé avant d'implémenter le suivant.

### TOOL-1 — Fichiers Windows
**Statut : A FAIRE — PROCHAIN**

Fichiers à créer :
- agent/tools/file_system.py : sous-classe Tool, opérations read/write/create/delete/list/move/search
- Pas de whitelist, accès total, machine dédiée mono-utilisateur
- Dépendances : pathlib + shutil (stdlib, rien à ajouter)
- Ajouter FileSystemTool dans agent/tools/__init__.py TOOLS

Checkpoint :
- Gradio avec glm-4.7 : "Crée un fichier C:\tmp\test.txt avec le contenu Bonjour"
- Vérifier que le fichier existe sur le disque
- "Lis le fichier C:\tmp\test.txt" → retourne "Bonjour"
- "Renomme-le en test2.txt" → fichier renommé
- "Supprime test2.txt" → fichier supprimé
- Commit : feat: tool-1 — file system windows

### TOOL-2 — Exécution OS Windows (PowerShell)
**Statut : A FAIRE**

Fichiers à créer :
- agent/tools/os_exec.py : sous-classe Tool, subprocess.run() PowerShell
- Retourne stdout, stderr, returncode, timeout 30s par défaut
- Ajouter OsExecTool dans TOOLS

Checkpoint :
- "Exécute Get-Date" → date actuelle retournée
- "Liste les processus actifs (Get-Process | Select -First 5)"
- "Crée un dossier C:\tmp\testdir via PowerShell"
- Commit : feat: tool-2 — os powershell

### TOOL-3 — Presse-papier Windows
**Statut : A FAIRE**

Fichiers à créer :
- agent/tools/clipboard.py : sous-classe Tool, read_clipboard + write_clipboard
- Dépendance : uv add pyperclip
- Ajouter ClipboardTool dans TOOLS

Checkpoint :
- "Écris 'Hello World' dans le presse-papier"
- Ctrl+V dans Notepad vérifie manuellement
- "Lis le contenu du presse-papier" → retourne "Hello World"
- Commit : feat: tool-3 — clipboard

### TOOL-4 — MCP Web Search Z.ai
**Statut : A FAIRE**

Intégration :
- MCPClient HTTP streamable vers https://api.z.ai/api/mcp/web_search_prime/mcp
- Header Authorization: Bearer {ZAI_API_KEY}
- Outil exposé : webSearchPrime
- Initialisation dans agent/main.py au démarrage
- Ajouter à TOOLS

Checkpoint :
- ZAI_API_KEY configuré dans agent/.env
- "Quelle est la météo à Paris aujourd'hui ?" → résultats temps réel
- Vérifier dans les logs que webSearchPrime a bien été appelé
- Commit : feat: tool-4 — mcp web search zai

### TOOL-5 — MCP Web Reader Z.ai
**Statut : A FAIRE**

Intégration :
- URL : https://api.z.ai/api/mcp/web_reader/mcp
- Outil exposé : webReader
- Même pattern que TOOL-4

Checkpoint :
- "Lis la page https://example.com et résume-la"
- Retour : titre + contenu principal + liens
- Commit : feat: tool-5 — mcp web reader zai

### TOOL-6 — MCP Zread Z.ai (GitHub)
**Statut : A FAIRE**

Intégration :
- URL : https://api.z.ai/api/mcp/zread/mcp
- Outils exposés : search_doc, get_repo_structure, read_file
- Repos GitHub publics uniquement

Checkpoint :
- "Donne-moi la structure du repo huggingface/smolagents"
- "Lis le fichier README.md de ce repo"
- Commit : feat: tool-6 — mcp zread github

### TOOL-7 — MCP Vision Z.ai (GLM-4.6V)
**Statut : A FAIRE**

Intégration :
- ToolCollection.from_mcp() avec StdioServerParameters
- command: npx, args: ["-y", "@z_ai/mcp-server@latest"]
- env: Z_AI_API_KEY + Z_AI_MODE=ZAI
- Node.js 22+ requis (déjà installé)
- 8 outils exposés (image_analysis, extract_text_from_screenshot, etc.)

Checkpoint :
- Préparer un screenshot PNG dans C:\tmp\
- "Analyse l'image C:\tmp\capture.png et décris ce que tu vois"
- Vérifier que GLM-4.6V répond via le MCP
- Commit : feat: tool-7 — mcp vision glm46v

### TOOL-8 — Screenshot Windows
**Statut : A FAIRE**

Fichiers à créer :
- agent/tools/screenshot.py : sous-classe Tool
- pyautogui.screenshot() → sauvegarde C:\tmp\myclawshots\screen_{timestamp}.png
- Retourne le chemin absolu
- Dépendances : uv add pyautogui pillow
- Option région : screenshot(region=(x, y, w, h))

Checkpoint :
- "Prends un screenshot de l'écran" → chemin retourné
- Vérifier que le fichier PNG existe et est lisible
- Enchaîner avec TOOL-7 : "Prends un screenshot et décris ce que tu vois"
- Commit : feat: tool-8 — screenshot windows

### TOOL-9 — Contrôle souris et clavier
**Statut : A FAIRE**

Fichiers à créer :
- agent/tools/mouse_keyboard.py : sous-classe Tool
- Opérations : click, double_click, move, type, hotkey, drag
- pyautogui déjà installé avec TOOL-8

Checkpoint :
- "Ouvre le menu Démarrer" → hotkey Win
- "Tape notepad et appuie sur Entrée"
- Screenshot pour vérifier que Notepad s'est ouvert
- Commit : feat: tool-9 — mouse keyboard control

### TOOL-10 — MCP Chrome DevTools (Playwright)
**Statut : A FAIRE**

Intégration :
- StdioServerParameters : npx @playwright/mcp@latest
- Piloter Chrome headless ou visible
- Outils : navigate, click, fill, extract_text, screenshot_page

Checkpoint :
- "Ouvre https://example.com dans Chrome"
- "Extrait le titre H1 de la page"
- "Prends un screenshot de la page"
- Commit : feat: tool-10 — mcp chrome playwright

---

## MODULE 4 — Canal Nextcloud Talk — A FAIRE (après tous les tools)

- gateway/app/api/webhook/nextcloud/route.ts : HMAC-SHA256
- gateway/lib/channels/nextcloud.ts : send(token, message)
- Variables : NEXTCLOUD_BASE_URL, NEXTCLOUD_BOT_SECRET, NEXTCLOUD_BOT_ID

---

## MODULE 5 — Cron & Proactivité — A FAIRE

- /api/cron protégé X-Cron-Secret, CronJobs DB, crontab système

---

## MODULE 6 — Z.ai + Health Check — A FAIRE

- ZAI_API_KEY agent/.env, /api/health tous services

---

## MODULE 7 — Identity & Persona — A FAIRE

- System prompt éditable WebChat, injection chaque appel, Settings DB

---

## MODULES V2 — BLOQUES

- V2-A : Voice STT Nextcloud Talk (whisper.cpp)
- V2-B : Code sandbox (remplacé en partie par TOOL-2)
- V2-C : Fichiers whitelist (remplacé par TOOL-1 accès total)
- V2-D : Browser control (remplacé par TOOL-10)
- V2-E : Mémoire vectorielle (nomic-embed-text prêt sur Ollama)

---

## STRUCTURE REPO (état actuel)

```
my-claw/
├── AGENTS.md
├── PLAN.md
├── PROGRESS.md
├── COMPARATIF.md
├── README.md
├── .env.example
├── .gitignore
├── setup.ps1
├── .claude/skills/
│   ├── smolagents-tools/SKILL.md
│   ├── prisma-patterns/SKILL.md
│   ├── nextjs-api-routes/SKILL.md
│   └── channel-webhooks/SKILL.md
├── plans/
│   └── validation-module3.md
├── agent/
│   ├── pyproject.toml + uv.lock
│   ├── main.py                    DONE module 1
│   ├── gradio_app.py              DONE module 1
│   └── tools/
│       └── __init__.py            DONE module 1 — à compléter avec chaque tool
└── gateway/
    ├── prisma.config.ts           DONE module 2
    ├── prisma/schema.prisma       DONE module 2
    ├── lib/db.ts                  DONE module 2
    ├── lib/memory.ts              DONE module 2
    ├── lib/agent-client.ts        DONE module 2
    └── app/
        ├── (webchat)/page.tsx     DONE module 3
        └── api/chat/route.ts      DONE module 3
```
