# PROGRESS.md — État d'avancement my-claw

Dernière mise à jour : 2026-02-22
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

## MODULE TOOLS — Extensions Smolagents
**Statut : EN COURS — PRIORITAIRE avant Nextcloud Talk**

Objectif : rendre l'agent autonome sur la machine Windows.
Modèle principal : glm-4.7 (Z.ai cloud) ou qwen3:8b (Ollama local).
Règle absolue : un tool validé avant d'implémenter le suivant.

**Outils locaux implémentés :** ✅ TOOL-1, ✅ TOOL-2, ✅ TOOL-3, ✅ TOOL-7, ✅ TOOL-8, 🔄 TOOL-9 (en cours)
**Outils MCP à implémenter :** TOOL-4, TOOL-5, TOOL-6, ✅ TOOL-10 (DONE)

**Améliorations récentes (2026-02-20) :**
- ✅ Fix GLM-4.7 : Nettoyage automatique des balises `</code` générées par GLM-4.7
- ✅ Timeouts augmentés : Gateway 6min, Agent 4min pour l'exécution du code Python (GLM-4.7 screenshot+vision)
- ✅ Guidage de l'agent : `instructions` + `additional_authorized_imports` pour préférer Python natif
- ✅ TOOL-7 Vision : Implémenté avec Ollama local (qwen3-vl:2b) au lieu de Z.ai MCP
- ✅ Skills (patterns de code) : L'agent reçoit des exemples de code réutilisables depuis `agent/skills.txt`
  - Screenshot + vision, OCR, screenshot région, HTTP requests, keyboard automation, clipboard, file operations
  - Plus rapide, plus fiable, moins de tokens consommés
  - Facile à modifier sans toucher au code (juste éditer skills.txt)
  - Documentation : `agent/SKILLS.md`

### TOOL-1 — Fichiers Windows
**Statut : DONE**

Fichiers créés :
- agent/tools/file_system.py : sous-classe Tool, opérations read/write/create/delete/list/move/search
- Pas de whitelist, accès total, machine dédiée mono-utilisateur
- Dépendances : pathlib + shutil (stdlib, rien à ajouter)
- FileSystemTool ajouté dans agent/tools/__init__.py TOOLS

Checkpoint :
- ✅ Gradio avec glm-4.7 : "Crée un fichier C:\tmp\test.txt avec le contenu Bonjour"
- ✅ Vérifier que le fichier existe sur le disque
- ✅ "Lis le fichier C:\tmp\test.txt" → retourne "Bonjour"
- ✅ "Renomme-le en test2.txt" → fichier renommé
- ✅ "Supprime test2.txt" → fichier supprimé
- ✅ Commit : feat: tool-1 — file system windows

### TOOL-2 — Exécution OS Windows (PowerShell)
**Statut : DONE**

Fichiers créés :
- agent/tools/os_exec.py : sous-classe Tool, subprocess.run() PowerShell
- Retourne stdout, stderr, returncode, timeout 30s par défaut
- OsExecTool ajouté dans TOOLS

Checkpoint :
- ✅ "Exécute Get-Date" → date actuelle retournée
- ✅ "Liste les processus actifs (Get-Process | Select -First 5)"
- ✅ "Crée un dossier C:\tmp\testdir via PowerShell"
- ✅ Commit : feat: tool-2 — os powershell

### TOOL-3 — Presse-papier Windows
**Statut : DONE**

Fichiers créés :
- agent/tools/clipboard.py : sous-classe Tool, read_clipboard + write_clipboard
- Dépendance : uv add pyperclip
- ClipboardTool ajouté dans TOOLS

Checkpoint :
- ✅ "Écris 'Hello World' dans le presse-papier"
- ✅ Ctrl+V dans Notepad vérifie manuellement
- ✅ "Lis le contenu du presse-papier" → retourne "Hello World"
- ✅ Commit : feat: tool-3 — clipboard

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

### TOOL-7 — Vision locale (Ollama qwen3-vl:2b)
**Statut : ✅ DONE**

Fichiers créés :
- agent/tools/vision.py : sous-classe Tool, analyse d'images via Ollama qwen3-vl:2b
- Modèle local : qwen3-vl:2b (2.3GB) - 100% local, 0 donnée sortante
- Timeout : 180 secondes (3 minutes) pour l'analyse d'images

Fonctionnalités :
- analyze_image(image_path, prompt) : analyse générale d'image avec prompt personnalisé
- Utilise l'API Ollama /api/chat avec support des images en base64
- Logs détaillés pour le debugging

Checkpoint :
- ✅ Installer le modèle : `ollama pull qwen3-vl:2b`
- ✅ Démarrer le serveur : `uv run uvicorn main:app --reload`
- ✅ Vérifier logs : "✓ vision: qwen3-vl:2b"
- ✅ Test Gradio : "Prends un screenshot et décris ce que tu vois"
- ✅ Test OCR : "Prends un screenshot et extrait le texte visible"
- ✅ Commit : feat: tool-7 — vision locale ollama qwen3-vl

Impact :
- ✅ 100% local, pas de dépendance cloud pour la vision
- ✅ Permet l'analyse d'images, OCR, compréhension de diagrammes
- ⚠️ TOOL-9 reste bloqué : qwen3-vl:2b seul ne suffit pas pour le pilotage PC autonome
  - L'agent a besoin d'un modèle plus puissant (GLM-4.6V via Z.ai MCP) pour coordonner screenshot + vision + actions
  - Alternative : Utiliser glm-4.7 comme orchestrateur avec qwen3-vl:2b comme outil vision

### TOOL-8 — Screenshot Windows
**Statut : DONE**

Fichiers créés :
- agent/tools/screenshot.py : sous-classe Tool
- pyautogui.screenshot() → sauvegarde C:\tmp\myclawshots\screen_{timestamp}.png
- Retourne le chemin absolu
- Dépendances : uv add pyautogui pillow
- Option région : screenshot(region=(x, y, w, h))

Checkpoint :
- ✅ "Prends un screenshot de l'écran" → chemin retourné
- ✅ Vérifier que le fichier PNG existe et est lisible
- ✅ Enchaîner avec TOOL-7 : "Prends un screenshot et décris ce que tu vois" → Fonctionne avec qwen3-vl:2b
- ✅ Commit : feat: tool-8 — screenshot windows

### TOOL-9 — Contrôle souris et clavier
**Statut : 🔄 EN COURS (partiellement validé)**

Fichiers créés :
- agent/tools/mouse_keyboard.py : sous-classe Tool
- Opérations : click, double_click, move, type, hotkey, drag, scroll
- pyautogui déjà installé avec TOOL-8
- Logs de debug ajoutés pour diagnostiquer les problèmes

Checkpoint :
- ✅ "Ouvre Notepad via le menu Démarrer et tape 'Test migration multi-agent OK'" → **SUCCÈS** (2026-02-22)
  - Utilise correctement `hotkey("win")` pour ouvrir le menu Démarrer
  - Tape "notepad" et appuie sur Entrée
  - Tape le texte demandé
  - Prend des screenshots pour vérification
- ❌ Anciens tests (2026-02-20) : LLM cliquait sur (0,0) au lieu d'utiliser hotkey
- ✅ Commit : feat: tool-9 — mouse keyboard control

**Validation partielle (2026-02-22)** :
- ✅ Architecture multi-agent avec `pc_control_agent` fonctionne correctement
- ✅ Modèle GLM-4.7 (reason) orchestre correctement les actions
- ✅ Séquencement des opérations : hotkey → type → hotkey → screenshot → type
- ✅ L'agent comprend l'ordre des opérations et gère les délais

**Problème résolu (2026-02-20 → 2026-02-22)** :
- ✅ L'agent LLM sait maintenant comment utiliser correctement mouse_keyboard
- ✅ Il utilise les bonnes opérations (hotkey) au lieu d'inventer des coordonnées
- ✅ La combinaison glm-4.7 + qwen3-vl:2b + mouse_keyboard fonctionne

**Tests supplémentaires requis** :
- Plan de tests complet créé : `plans/validation-tool9-mouse-keyboard.md`
- 21 tests organisés en 8 catégories (hotkey, navigation, copie-coller, scroll, drag-drop, clic droit, séquences complexes, robustesse)
- Tests à effectuer pour validation complète :
  - Raccourcis clavier (4 tests)
  - Navigation et clics (3 tests)
  - Sélection, copie et collage (2 tests)
  - Scroll (2 tests)
  - Drag-and-drop (2 tests)
  - Séquences complexes (4 tests)
  - Tests de robustesse (3 tests)

**Prochaine étape** :
Exécuter les tests du plan `plans/validation-tool9-mouse-keyboard.md` pour valider complètement TOOL-9

### TOOL-10 — MCP Chrome DevTools (Puppeteer)
**Statut : ✅ DONE (Testé & Validé)**

Intégration :
- StdioServerParameters : npx chrome-devtools-mcp@latest
- Piloter Chrome headless ou visible via Chrome DevTools MCP (basé sur Puppeteer)
- 26 outils disponibles organisés en 6 catégories :
  - Input automation (8) : click, drag, fill, fill_form, handle_dialog, hover, press_key, upload_file
  - Navigation automation (6) : close_page, list_pages, navigate_page, new_page, select_page, wait_for
  - Emulation (2) : emulate, resize_page
  - Performance (3) : performance_analyze_insight, performance_start_trace, performance_stop_trace
  - Network (2) : get_network_request, list_network_requests
  - Debugging (5) : evaluate_script, get_console_message, list_console_messages, take_screenshot, take_snapshot

Options de configuration :
- --headless=true : mode sans interface (défaut : false)
- --channel=canary|beta|dev : utiliser une autre version de Chrome
- --viewport=1280x720 : taille initiale du viewport
- --isolated=true : utiliser un profil temporaire
- --category-performance=false : désactiver les outils de performance
- --category-network=false : désactiver les outils réseau
- --category-emulation=false : désactiver les outils d'émulation

Bonnes pratiques :
- Toujours utiliser take_snapshot() avant d'interagir avec la page pour connaître les uid des éléments
- Privilégier take_snapshot() à take_screenshot() pour obtenir des uid exploitables
- Utiliser wait_for() ou laisser le tool gérer automatiquement les attentes

Checkpoint :
- "Ouvre https://example.com dans Chrome"
- "Prends un snapshot de la page et liste les éléments visibles"
- "Récupère le titre H1 de la page via evaluate_script"
- "Prends un screenshot de la page entière"
- "Va sur https://huggingface.co et prends un snapshot"
- "Cherche 'smolagents' dans la barre de recherche et valide avec Enter"
- "Liste les requêtes réseau de la page"
- "Vérifie les messages console de la page"
- Commit : feat: tool-10 — mcp chrome devtools

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

## ARCHITECTURE MULTI-AGENT — DONE

Migration vers architecture Manager + 3 sous-agents spécialisés (2026-02-21)

Manager (glm-4.7 / qwen3:8b) → tools directs : file_system, os_exec, clipboard
├── pc_control_agent (qwen3-vl:2b) → screenshot, analyze_image, ui_grounding, mouse_keyboard
├── browser_agent (qwen3:8b) → 26 tools Chrome DevTools MCP
└── web_agent (qwen3:8b) → webSearchPrime, webReader, zread (activer avec ZAI_API_KEY)

## TOOL-11 — QwenGroundingTool (anciennement UITarsGroundingTool)
**Statut : DONE**

Fichiers créés :
- agent/tools/grounding.py : sous-classe Tool, grounding GUI avec qwen3-vl
- Modèle : qwen3-vl:2b (détecté automatiquement)
- Retourne coordonnées pixel absolues depuis description textuelle + screenshot

Modifications :
- Renommage : ui_tars_grounding.py → grounding.py
- Classe : UITarsGroundingTool → QwenGroundingTool
- Modèle : UI-TARS-2B-SFT → qwen3-vl:2b
- Prompt système spécialisé pour grounding déterministe (temperature: 0.0)
- Détection automatique du modèle qwen3-vl disponible (2b, 4b, 8b)

Checkpoint :
- ✅ Installer qwen3-vl:2b : `ollama pull qwen3-vl:2b`
- ✅ Test grounding : "Trouve le bouton Démarrer dans ce screenshot"
- ✅ Vérification coordonnées : Retourne [x, y] relatifs → conversion en absolus
- ✅ Commit : feat: tool-11 — qwen3-vl grounding tool

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
│   ├── main.py                    DONE module 1 + GLM-4.7 fix + timeouts + skills loader + multi-agent
│   ├── gradio_app.py              DONE module 1 + Gradio 6.6.0
│   ├── skills.txt                 Patterns de code réutilisables (chargés au démarrage)
│   ├── SKILLS.md                  Documentation des skills
│   ├── agents/
│   │   ├── __init__.py            DONE — package sous-agents
│   │   ├── pc_control_agent.py    DONE — qwen3-vl:2b + screenshot/vision/ui_tars/mouse
│   │   ├── browser_agent.py       DONE — qwen3:8b + Chrome DevTools MCP
│   │   └── web_agent.py           DONE — qwen3:8b + MCP Z.ai (optionnel)
│   └── tools/
│       ├── __init__.py            DONE — contient TOOLS = [7 outils dont UITarsGroundingTool]
│       ├── file_system.py          ✅ DONE — TOOL-1
│       ├── os_exec.py             ✅ DONE — TOOL-2 (fix curl PowerShell)
│       ├── clipboard.py           ✅ DONE — TOOL-3
│       ├── vision.py              ✅ DONE — TOOL-7 (Ollama qwen3-vl:2b)
│       ├── screenshot.py          ✅ DONE — TOOL-8
│       ├── mouse_keyboard.py      🔄 EN COURS — TOOL-9
│       └── ui_tars_grounding.py   ✅ DONE — TOOL-11
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
