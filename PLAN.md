# PLAN.md — Plan Global my-claw

---

## VISION

Assistant personnel self-hosted, privacy-first, tournant sur une machine dédiée.
Mono-utilisateur, minimaliste, extensible prudemment module par module.
Pas de cloud obligatoire — local-first par défaut, cloud optionnel via Z.ai GLM.

---

## ARCHITECTURE CIBLE

```
┌─────────────────────────────────────────────────────────────┐
│                      Machine dédiée Windows                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Next.js 16.1 — Gateway & Mémoire (:3000)           │   │
│  │  Webhooks canaux, Prisma 7.4, WebChat UI            │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │ HTTP interne                          │
│  ┌──────────────────▼──────────────────────────────────┐   │
│  │  Python 3.14 — Cerveau (:8000)                      │   │
│  │  smolagents + 10 tools + Chrome MCP                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Gradio 6 — UI dev/test (:7860)                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Ollama :11434 — qwen3:8b / 14b / vl:2b                │
│  SQLite  — mémoire conversations                            │
└─────────────────────────────────────────────────────────────┘
         │
   Nextcloud Talk (Bot HMAC-SHA256)
```

---

## PLAN V1 — MODULES GATEWAY

### MODULE 0 — Socle & Configuration — DONE
Structure dossiers, Next.js 16.1, Python 3.14, uv, Ollama opérationnel.

### MODULE 1 — Cerveau Python — DONE
FastAPI /run, Gradio 6, factory modèles Ollama + Z.ai, architecture multi-agent.

### MODULE 2 — Mémoire Prisma 7.4 + SQLite — DONE
4 tables, singleton PrismaClient, helpers memory.ts, migration init.

### MODULE 3 — WebChat — DONE
UI React 19 + Tailwind 4, SSE streaming, auth token, historique persistant.

### MODULE 4 — Canal Nextcloud Talk — A FAIRE (après module tools)
Webhook HMAC-SHA256, envoi OCS API, enregistrement bot admin NC.

### MODULE 5 — Cron & Proactivité — A FAIRE
/api/cron protégé, CronJobs DB, crontab système.

### MODULE 6 — Z.ai GLM-4.7 + Health Check — A FAIRE
ZAI_API_KEY configuré, /api/health, statuts tous services.

### MODULE 7 — Identity & Persona — A FAIRE
System prompt éditable, injection dans chaque appel, persistance Settings.

---

## MODULE TOOLS — Extensions Smolagents (PRIORITAIRE)

Ce module s'implémente AVANT le module 4 (Nextcloud Talk).
Objectif : rendre l'agent autonome sur la machine Windows.
Modèles : qwen3:8b (Ollama local, recommandé) ou glm-4.7 (Z.ai cloud, optionnel).
Règle : un tool = un checkpoint = validation avant le suivant.

### Stratégie Local-First
- Priorité aux outils 100% locaux (Ollama)
- Z.ai cloud uniquement pour ce que le local ne peut pas faire (web search, web reader, zread)
- Vision : qwen3-vl:2b (Ollama local) au lieu de GLM-4.6V (Z.ai cloud)

### TOOL-1 — Fichiers Windows (accès total)
Priorité : 1 | Quota : 0 | Dépendance : pathlib stdlib

Sous-classe Tool smolagents. Opérations : read_file, write_file, create_file,
delete_file, list_directory, move_file, search_files.
Accès total sans whitelist — machine dédiée, mono-utilisateur.
Modèle de test : glm-4.7.

Checkpoint : créer, lire, modifier, renommer, supprimer un fichier via Gradio.

### TOOL-2 — Exécution OS Windows (PowerShell)
Priorité : 2 | Quota : 0 | Dépendance : subprocess stdlib

Sous-classe Tool. Lance des commandes PowerShell via subprocess.run().
Retourne stdout, stderr, code de retour. Timeout configurable (défaut 30s).
Pas de filtre sur les commandes — accès total voulu.

Checkpoint : Get-Process, Get-Date, mkdir, ipconfig via Gradio.

### TOOL-3 — Presse-papier Windows
Priorité : 3 | Quota : 0 | Dépendance : pyperclip (uv add pyperclip)

Lire et écrire le presse-papier Windows.
Fondamental pour injecter du texte dans des applications tierces.

Checkpoint : écrire du texte dans le clipboard, le lire, vérifier la cohérence.

### TOOL-4 — Web Search (DuckDuckGoSearchTool built-in)
Priorité : 4 | Quota : 0 | Dépendance : duckduckgo-search

Recherche web en temps réel intégrée directement au manager.
Basé sur le tool built-in de smolagents. Illimité et gratuit.

Checkpoint : rechercher "météo Paris aujourd'hui", recevoir des résultats frais.
**Statut : ✅ DONE**

### TOOL-5 — Web Reader (VisitWebpageTool built-in)
Priorité : 5 | Quota : 0 | Dépendance : markdownify

Lecture de pages web et conversion en Markdown. Intégré au manager.
Validation SSRF incluse (blocage localhost/internal).

Checkpoint : lire https://example.com, extraire titre et contenu principal en MD.
**Statut : ✅ DONE**

### TOOL-6 — MCP Zread Z.ai (GitHub)
Priorité : 6 | Quota : oui (partagé) | Dépendance : ZAI_API_KEY

URL : https://api.z.ai/api/mcp/zread/mcp
Outils exposés : search_doc, get_repo_structure, read_file
Repos GitHub publics uniquement.

Checkpoint : explorer la structure de huggingface/smolagents, lire un fichier clé.

### TOOL-7 — Vision locale (Ollama qwen3-vl:2b)
Priorité : 7 | Quota : 0 (100% local) | Dépendance : Ollama + qwen3-vl:2b

Sous-classe Tool smolagents. Analyse d'images via Ollama qwen3-vl:2b.
Modèle : qwen3-vl:2b (2.3GB) - vision locale, 0 donnée sortante.
API : Ollama /api/chat avec support des images en base64.
Timeout : 180 secondes (3 minutes) pour l'analyse.

Fonctionnalités :
- analyze_image(image_path, prompt) : analyse générale d'image avec prompt personnalisé
- OCR : extraction de texte depuis des screenshots
- Compréhension de diagrammes, graphiques, interfaces

Installation : `ollama pull qwen3-vl:2b`

Checkpoint : analyser un screenshot existant, décrire ce qu'il voit, extraire du texte.

### TOOL-8 — Screenshot Windows
Priorité : 8 | Quota : 0 | Dépendance : pyautogui, pillow (uv add pyautogui pillow)

Prendre un screenshot de l'écran entier ou d'une région.
Sauvegarder dans un dossier temporaire configurable (défaut : C:\tmp\myclawshots\).
Retourner le chemin absolu du fichier — utilisé directement avec TOOL-7.

Checkpoint : prendre un screenshot, obtenir le chemin, passer à TOOL-7 pour description.
**Statut : ✅ DONE** - Fonctionne parfaitement avec TOOL-7 (qwen3-vl:2b).

### TOOL-9 — Contrôle souris et clavier
Priorité : 9 | Quota : 0 | Dépendance : pyautogui (déjà installé avec TOOL-8)

Outils : mouse_click(x, y), mouse_move(x, y), mouse_double_click(x, y),
keyboard_type(text), keyboard_hotkey(*keys), mouse_drag(x1, y1, x2, y2).
S'appuie sur les coordonnées fournies par TOOL-7 Vision ou TOOL-11 Grounding.

Checkpoint : ouvrir le menu Démarrer (Win), taper "notepad", Entrée, vérifier via screenshot.
**Statut : ✅ DONE**

### TOOL-10 — MCP Chrome DevTools (Puppeteer)
Priorité : 10 | Quota : 0 | Dépendance : npx chrome-devtools-mcp@latest | **Statut : ✅ DONE**

Piloter Chrome headless ou visible via Chrome DevTools MCP (basé sur Puppeteer).
Stdio local comme le MCP Vision.
Permet : naviguer vers URL, cliquer, extraire texte, remplir formulaires,
screenshot de page web — complémentaire à TOOL-8+TOOL-9 pour le web.

**26 outils disponibles organisés en 6 catégories** :
- Input automation (8) : click, drag, fill, fill_form, handle_dialog, hover, press_key, upload_file
- Navigation automation (6) : close_page, list_pages, navigate_page, new_page, select_page, wait_for
- Emulation (2) : emulate, resize_page
- Performance (3) : performance_analyze_insight, performance_start_trace, performance_stop_trace
- Network (2) : get_network_request, list_network_requests
- Debugging (5) : evaluate_script, get_console_message, list_console_messages, take_screenshot, take_snapshot

**Options de configuration** :
- --headless=true : mode sans interface (défaut : false)
- --channel=canary|beta|dev : utiliser une autre version de Chrome
- --viewport=1280x720 : taille initiale du viewport
- --isolated=true : utiliser un profil temporaire
- --category-performance=false : désactiver les outils de performance
- --category-network=false : désactiver les outils réseau
- --category-emulation=false : désactiver les outils d'émulation

Checkpoint : ouvrir https://example.com, extraire le titre H1, prendre un screenshot.

---

## ARCHITECTURE PILOTAGE PC (TOOL-7 + TOOL-8 + TOOL-9)

```
User: "Ouvre Notepad et écris un résumé de ma journée"
         ↓
    glm-4.7 (orchestrateur, max_steps=10 pour tâches complexes)
         ↓
    TOOL-8 screenshot → C:\tmp\myclawshots\screen_001.png
         ↓
    TOOL-7 vision (qwen3-vl:2b) → "bureau Windows visible, Notepad non ouvert"
         ↓
    TOOL-9 keyboard → hotkey("win") → type("notepad") → hotkey("enter")
         ↓
    TOOL-8 screenshot → screen_002.png
         ↓
    TOOL-7 vision (qwen3-vl:2b) → "Notepad ouvert, zone de texte vide, curseur actif"
         ↓
    TOOL-9 keyboard → type("Résumé du 20 février 2026...")
         ↓
    Done
```

**Note** : Cette architecture nécessite un modèle orchestrateur puissant (glm-4.7 recommandé) pour coordonner les outils de manière autonome. qwen3:8b seul ne suffit pas pour ce niveau de complexité.

---

## DÉCISIONS PRISES

| Sujet | Décision | Raison |
|-------|----------|--------|
| SearXNG | Remplacé par MCP Web Search Z.ai | Déjà dans le token, zéro infra supplémentaire |
| Modèle principal | qwen3:8b (Ollama local) | 100% local, 0 donnée sortante, performant |
| Modèle orchestrateur | glm-4.7 (Z.ai cloud, optionnel) | Meilleur pour l'orchestration complexe (TOOL-9) |
| Vision | qwen3-vl:2b (Ollama local) | 100% local au lieu de GLM-4.6V (Z.ai cloud) |
| Quota Z.ai | Outils sans quota en priorité | 100 calls/mois partagés — utiliser avec parcimonie |
| Docker | Non pour l'app | Complexité inutile, machine dédiée |
| Redis | Non | Pas de besoin de queue pour mono-utilisateur |

---

## CONTRAINTES PERMANENTES

- Machine dédiée Windows, mono-utilisateur
- Local-first — Ollama prioritaire, Z.ai pour ce que le local ne peut pas faire
- Modèles Ollama : qwen3:8b (principal), qwen3-vl:2b (vision), gemma3 (rapide)
- glm-4.7 (Z.ai cloud) = optionnel pour orchestration complexe
- Z.ai Lite : 100 calls web/reader/zread par mois (vision locale avec qwen3-vl:2b)
- uv uniquement pour Python, jamais pip
- Un tool validé avant d'implémenter le suivant

---

## ORDRE D'IMPLÉMENTATION GLOBAL

```
MODULE 0   DONE   Socle
MODULE 1   DONE   Cerveau Python + GLM-4.7 fix + multi-agent
MODULE 2   DONE   Mémoire Prisma 7.4
MODULE 3   DONE   WebChat (SSE streaming)
TOOL-1     DONE   Fichiers Windows
TOOL-2     DONE   OS PowerShell + fix encodage
TOOL-3     DONE   Clipboard
TOOL-7     DONE   Vision locale (qwen3-vl)
TOOL-8     DONE   Screenshot Windows
TOOL-10    DONE   MCP Chrome DevTools
TOOL-9     DONE   Souris/Clavier
TOOL-11    DONE   GUI Grounding
TOOL-4     DONE   Web Search (DuckDuckGo)
TOOL-5     DONE   Web Reader (Built-in)
─────────────────────────────────── ← On est ici
TOOL-6     TODO   MCP Zread GitHub          ← PROCHAIN
─────────────────────────────────── ← Après tools validés
MODULE 4   TODO   Nextcloud Talk
MODULE 5   TODO   Cron
MODULE 6   TODO   Z.ai + Health
MODULE 7   TODO   Identity
─────────────────────────────────── ← V2 bloquée
V2-A       HOLD   Voice STT
V2-B       HOLD   Code sandbox
V2-C       HOLD   Fichiers whitelist (remplacé par TOOL-1 accès total)
V2-D       HOLD   Browser (remplacé par TOOL-10)
V2-E       HOLD   Mémoire vectorielle
```

---

## RÉFÉRENCES Z.AI MCP

- Vision MCP : https://docs.z.ai/devpack/mcp/vision-mcp-server
- Web Search MCP : https://docs.z.ai/devpack/mcp/search-mcp-server
- Web Reader MCP : https://docs.z.ai/devpack/mcp/reader-mcp-server
- Zread MCP : https://docs.z.ai/devpack/mcp/zread-mcp-server
- smolagents MCP : https://huggingface.co/docs/smolagents/tutorials/mcp
