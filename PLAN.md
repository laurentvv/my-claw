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
│  │  Next.js 16 — Gateway & Mémoire (:3000)             │   │
│  │  Webhooks canaux, Prisma SQLite, WebChat UI         │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │ HTTP interne                          │
│  ┌──────────────────▼──────────────────────────────────┐   │
│  │  Python smolagents — Cerveau (:8000)                │   │
│  │  CodeAgent + 10 tools + MCP Z.ai                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Gradio — UI dev/test (:7860)                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Ollama :11434 — qwen3:4b / 8b / 14b                        │
│  SQLite  — mémoire conversations                            │
└─────────────────────────────────────────────────────────────┘
         │
   Nextcloud Talk (Bot HMAC-SHA256)
```

---

## PLAN V1 — MODULES GATEWAY

### MODULE 0 — Socle & Configuration — DONE
Structure dossiers, Next.js 16, Python uv, Ollama opérationnel.

### MODULE 1 — Cerveau Python — DONE
FastAPI /run, Gradio, factory modèles Ollama + Z.ai, sans outil.

### MODULE 2 — Mémoire Prisma 7 + SQLite — DONE
4 tables, singleton PrismaClient, helpers memory.ts, migration init.

### MODULE 3 — WebChat — DONE
UI React Tailwind, SSE streaming, auth token, historique persistant.

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
Modèle privilégié : glm-4.7 (token Z.ai disponible).
Règle : un tool = un checkpoint = validation avant le suivant.

### Contexte Z.ai Coding Plan Lite
- 100 calls/mois partagés entre web search, web reader et zread
- 5h de pool vision GLM-4.6V/mois
- Stratégie : tools sans quota en priorité, MCP Z.ai à la demande uniquement

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

### TOOL-4 — MCP Web Search Z.ai
Priorité : 4 | Quota : oui (100 calls/mois partagés) | Dépendance : ZAI_API_KEY

Intégration via MCPClient HTTP streamable.
URL : https://api.z.ai/api/mcp/web_search_prime/mcp
Header : Authorization: Bearer {ZAI_API_KEY}
Outil exposé : webSearchPrime

Checkpoint : rechercher "météo Paris aujourd'hui", recevoir des résultats frais.

### TOOL-5 — MCP Web Reader Z.ai
Priorité : 5 | Quota : oui (partagé avec TOOL-4) | Dépendance : ZAI_API_KEY

URL : https://api.z.ai/api/mcp/web_reader/mcp
Outil exposé : webReader — contenu complet d'une URL (titre, body, liens, metadata).

Checkpoint : lire https://example.com, extraire titre et contenu principal.

### TOOL-6 — MCP Zread Z.ai (GitHub)
Priorité : 6 | Quota : oui (partagé) | Dépendance : ZAI_API_KEY

URL : https://api.z.ai/api/mcp/zread/mcp
Outils exposés : search_doc, get_repo_structure, read_file
Repos GitHub publics uniquement.

Checkpoint : explorer la structure de huggingface/smolagents, lire un fichier clé.

### TOOL-7 — MCP Vision Z.ai (GLM-4.6V)
Priorité : 7 | Quota : oui (5h pool vision/mois) | Dépendance : Node.js 22+, ZAI_API_KEY

Intégration via ToolCollection.from_mcp() avec StdioServerParameters.
Commande : npx -y @z_ai/mcp-server@latest
Env : Z_AI_API_KEY + Z_AI_MODE=ZAI

Outils exposés :
- image_analysis : analyse générale d'image
- extract_text_from_screenshot : OCR sur captures écran
- ui_to_artifact : transformer une UI en code/specs
- video_analysis : analyser une vidéo locale (max 8MB, MP4/MOV/M4V)
- diagnose_error_screenshot : analyser une erreur visible à l'écran
- understand_technical_diagram : lire un schéma d'architecture
- ui_diff_check : comparer deux captures UI
- analyze_data_visualization : lire un graphique/dashboard

Bonne pratique : passer le chemin du fichier image, pas coller une image directement.

Checkpoint : analyser un screenshot existant, décrire ce qu'il voit.

### TOOL-8 — Screenshot Windows
Priorité : 8 | Quota : 0 | Dépendance : pyautogui, pillow (uv add pyautogui pillow)

Prendre un screenshot de l'écran entier ou d'une région.
Sauvegarder dans un dossier temporaire configurable (défaut : C:\tmp\myclawshots\).
Retourner le chemin absolu du fichier — utilisé directement avec TOOL-7.

Checkpoint : prendre un screenshot, obtenir le chemin, passer à TOOL-7 pour description.

### TOOL-9 — Contrôle souris et clavier
Priorité : 9 | Quota : 0 | Dépendance : pyautogui (déjà installé avec TOOL-8)

Outils : mouse_click(x, y), mouse_move(x, y), mouse_double_click(x, y),
keyboard_type(text), keyboard_hotkey(*keys), mouse_drag(x1, y1, x2, y2).
S'appuie sur les coordonnées fournies par TOOL-7 Vision.

Checkpoint : ouvrir le menu Démarrer (Win), taper "notepad", Entrée, vérifier via screenshot.

### TOOL-10 — MCP Chrome DevTools (Playwright)
Priorité : 10 | Quota : 0 | Dépendance : npx @playwright/mcp@latest

Piloter Chrome headless ou visible via Playwright MCP.
Stdio local comme le MCP Vision.
Permet : naviguer vers URL, cliquer, extraire texte, remplir formulaires,
screenshot de page web — complémentaire à TOOL-8+TOOL-9 pour le web.

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
    TOOL-7 vision → "bureau Windows visible, Notepad non ouvert"
         ↓
    TOOL-9 keyboard → hotkey("win") → type("notepad") → hotkey("enter")
         ↓
    TOOL-8 screenshot → screen_002.png
         ↓
    TOOL-7 vision → "Notepad ouvert, zone de texte vide, curseur actif"
         ↓
    TOOL-9 keyboard → type("Résumé du 19 février 2026...")
         ↓
    Done
```

---

## DÉCISIONS PRISES

| Sujet | Décision | Raison |
|-------|----------|--------|
| WhatsApp | Retiré définitivement | Dépendance Meta inutile pour usage perso |
| SearXNG | Remplacé par MCP Web Search Z.ai | Déjà dans le token, zéro infra supplémentaire |
| Modèle principal tools | glm-4.7 | Token disponible, meilleur pour l'orchestration |
| Quota Z.ai Lite | Outils sans quota en priorité | 100 calls/mois partagés — utiliser avec parcimonie |
| Docker | Non pour l'app | Complexité inutile, machine dédiée |
| Redis | Non | Pas de besoin de queue pour mono-utilisateur |

---

## CONTRAINTES PERMANENTES

- Machine dédiée Windows, mono-utilisateur
- Local-first — Ollama prioritaire, Z.ai pour ce que le local ne peut pas faire
- 14B max Ollama (qwen3:14b = modèle secondaire)
- glm-4.7 = modèle principal pour les tools
- Z.ai Lite : 100 calls web/reader/zread + 5h vision par mois
- uv uniquement pour Python, jamais pip
- Un tool validé avant d'implémenter le suivant

---

## ORDRE D'IMPLÉMENTATION GLOBAL

```
MODULE 0   DONE   Socle
MODULE 1   DONE   Cerveau Python
MODULE 2   DONE   Mémoire Prisma
MODULE 3   DONE   WebChat
─────────────────────────────────── ← On est ici
TOOL-1     TODO   Fichiers Windows          ← PROCHAIN
TOOL-2     TODO   OS PowerShell
TOOL-3     TODO   Clipboard
TOOL-4     TODO   MCP Web Search Z.ai
TOOL-5     TODO   MCP Web Reader Z.ai
TOOL-6     TODO   MCP Zread GitHub
TOOL-7     TODO   MCP Vision GLM-4.6V
TOOL-8     TODO   Screenshot Windows
TOOL-9     TODO   Souris/Clavier
TOOL-10    TODO   MCP Chrome Playwright
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
