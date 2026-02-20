# IMPLEMENTATION-TOOLS.md — Plan d'implémentation Module Tools

> Document destiné à une IA de codage (Claude Code, Cursor, Cline...)
> Lire AGENTS.md et PROGRESS.md avant de commencer.
> Lire .claude/skills/smolagents-tools/SKILL.md avant chaque tool.
> RÈGLE ABSOLUE : un tool implémenté → testé → validé → commit → tool suivant.

---

## CONTEXTE

On étend l'agent Python smolagents avec 10 tools pour rendre l'assistant
autonome sur Windows. Les tools s'ajoutent dans agent/tools/ et s'enregistrent
dans agent/tools/__init__.py.

Modèle à utiliser pour les tests : glm-4.7 (sélectionner "reason" dans Gradio).
Le modèle par défaut pour les tools dans CodeAgent reste "main" (qwen3:14b local).

---

## STRUCTURE CIBLE agent/tools/

```
agent/tools/
├── __init__.py          ← TOOLS list — ajouter chaque tool au fur et à mesure
├── file_system.py       ← TOOL-1
├── os_exec.py           ← TOOL-2
├── clipboard.py         ← TOOL-3
├── screenshot.py        ← TOOL-8 (avant TOOL-7 car TOOL-7 a besoin de fichiers)
└── mouse_keyboard.py    ← TOOL-9
```

Les tools MCP (TOOL-4, 5, 6, 7, 10) sont chargés dynamiquement dans main.py
via MCPClient ou ToolCollection.from_mcp() au démarrage de FastAPI.

---

## MODIFICATIONS agent/main.py

Le fichier main.py doit être modifié pour :
1. Charger les tools locaux depuis tools/__init__.py
2. Charger les tools MCP Z.ai (HTTP remote) au démarrage
3. Charger les tools MCP stdio (Vision, Playwright) au démarrage
4. Passer tous les tools au CodeAgent

Pattern général à maintenir dans main.py :
- Initialisation des MCP clients à l'import ou via lifespan FastAPI
- Gestion des erreurs si ZAI_API_KEY absent : désactiver les tools MCP silencieusement
- max_steps=10 pour les tâches complexes de pilotage PC (au lieu de 5)
- Logger les tools disponibles au démarrage pour debug

---

## TOOL-1 — Fichiers Windows

Fichier : agent/tools/file_system.py

Opérations à implémenter dans une seule classe FileSystemTool avec un
paramètre "operation" qui dispatch :
- read : lire le contenu d'un fichier texte
- write : écrire/remplacer le contenu d'un fichier
- create : créer un fichier (avec contenu optionnel)
- delete : supprimer un fichier ou dossier vide
- list : lister le contenu d'un dossier
- move : déplacer ou renommer un fichier
- search : chercher des fichiers par pattern glob dans un dossier

Paramètres de l'outil :
- operation (str) : l'opération à effectuer
- path (str) : chemin absolu ou relatif
- content (str, optionnel) : contenu pour write/create
- pattern (str, optionnel) : pattern glob pour search
- destination (str, optionnel) : destination pour move

Comportement :
- Utiliser pathlib.Path pour tous les chemins
- Retourner des messages clairs en cas d'erreur (fichier introuvable, permission refusée...)
- Créer les dossiers parents automatiquement pour write/create
- Encoder en UTF-8 par défaut pour la lecture/écriture

Après implémentation, ajouter dans __init__.py :
  from .file_system import FileSystemTool
  TOOLS = [FileSystemTool()]

Test Gradio avec modèle "reason" (glm-4.7) :
1. "Crée le fichier C:\tmp\myclaw_test.txt avec le contenu : Test TOOL-1 OK"
2. "Lis le fichier C:\tmp\myclaw_test.txt"
3. "Liste le contenu du dossier C:\tmp\"
4. "Déplace C:\tmp\myclaw_test.txt vers C:\tmp\myclaw_test_renamed.txt"
5. "Supprime C:\tmp\myclaw_test_renamed.txt"

Commit message : feat(tools): tool-1 file system windows

---

## TOOL-2 — Exécution OS Windows (PowerShell)

Fichier : agent/tools/os_exec.py

Classe OsExecTool.

Paramètres :
- command (str) : la commande PowerShell à exécuter
- timeout (int, optionnel) : timeout en secondes, défaut 30

Implémentation :
- subprocess.run() avec shell=False
- Lancer via ["powershell", "-Command", command]
- Capturer stdout et stderr en UTF-8
- Retourner un dict formaté : stdout, stderr, returncode
- Si timeout dépassé : retourner un message d'erreur clair
- Ne pas filtrer les commandes — accès total voulu

Ajouter dans __init__.py :
  from .os_exec import OsExecTool
  TOOLS = [FileSystemTool(), OsExecTool()]

Test Gradio :
1. "Exécute la commande PowerShell : Get-Date"
2. "Liste les 5 premiers processus avec Get-Process | Select-Object -First 5"
3. "Crée le dossier C:\tmp\testdir_powershell via PowerShell"
4. "Supprime le dossier C:\tmp\testdir_powershell"

Commit message : feat(tools): tool-2 os powershell exec

---

## TOOL-3 — Presse-papier Windows

Fichier : agent/tools/clipboard.py

Classe ClipboardTool.

Dépendance à ajouter : uv add pyperclip

Paramètres :
- operation (str) : "read" ou "write"
- content (str, optionnel) : texte à écrire (requis si operation="write")

Implémentation :
- pyperclip.copy() pour écrire
- pyperclip.paste() pour lire
- Gérer l'exception si pas de gestionnaire de clipboard disponible

Ajouter dans __init__.py :
  from .clipboard import ClipboardTool
  TOOLS = [FileSystemTool(), OsExecTool(), ClipboardTool()]

Test Gradio :
1. "Écris 'Bonjour depuis my-claw !' dans le presse-papier"
2. Vérifier manuellement avec Ctrl+V dans Notepad
3. "Lis le contenu actuel du presse-papier"

Commit message : feat(tools): tool-3 clipboard windows

---

## TOOL-4 — MCP Web Search Z.ai (HTTP Remote)

Pas de fichier tools/ — intégration dans main.py.

Dépendances à ajouter : uv add mcp (ou smolagents gère via ToolCollection)
Vérifier la version smolagents installée — MCP HTTP disponible depuis v1.4.1.

Variable d'env requise : ZAI_API_KEY dans agent/.env

Pattern d'intégration dans main.py :

La documentation smolagents pour MCP HTTP remote utilise MCPClient avec
type "streamable-http" et un header d'authentification.

Configuration :
  url : https://api.z.ai/api/mcp/web_search_prime/mcp
  type : streamable-http (ou http selon version smolagents)
  headers : {"Authorization": f"Bearer {os.environ['ZAI_API_KEY']}"}

Outils chargés : webSearchPrime

Logique de démarrage dans main.py :
- Si ZAI_API_KEY présent → charger le client MCP web search
- Si absent → logger un warning, continuer sans ce tool
- Ajouter les tools MCP à la liste TOOLS avant de créer le CodeAgent

Test Gradio avec modèle "reason" :
1. "Quelle est la météo à Paris aujourd'hui ?"
2. "Quelles sont les dernières nouvelles sur l'IA en France ?"
3. Vérifier dans les logs FastAPI que webSearchPrime a été appelé

Commit message : feat(tools): tool-4 mcp web search zai

---

## TOOL-5 — MCP Web Reader Z.ai (HTTP Remote)

Même pattern que TOOL-4.

Configuration :
  url : https://api.z.ai/api/mcp/web_reader/mcp
  type : streamable-http
  headers : {"Authorization": f"Bearer {os.environ['ZAI_API_KEY']}"}

Outils chargés : webReader

Test Gradio :
1. "Lis la page https://example.com et résume son contenu"
2. "Lis https://huggingface.co/docs/smolagents et liste les sections principales"

Commit message : feat(tools): tool-5 mcp web reader zai

---

## TOOL-6 — MCP Zread Z.ai (GitHub, HTTP Remote)

Même pattern que TOOL-4 et TOOL-5.

Configuration :
  url : https://api.z.ai/api/mcp/zread/mcp
  type : streamable-http
  headers : {"Authorization": f"Bearer {os.environ['ZAI_API_KEY']}"}

Outils chargés : search_doc, get_repo_structure, read_file

Test Gradio :
1. "Donne-moi la structure du repo GitHub huggingface/smolagents"
2. "Lis le fichier README.md du repo huggingface/smolagents"
3. "Cherche des informations sur le MCP dans la documentation de smolagents"

Commit message : feat(tools): tool-6 mcp zread github

---

## TOOL-7 — MCP Vision Z.ai (GLM-4.6V, stdio local)

Pas de fichier tools/ — intégration dans main.py via ToolCollection.from_mcp().

Prérequis : Node.js 22+ installé (déjà présent d'après setup).

Configuration StdioServerParameters :
  command : "npx"
  args : ["-y", "@z_ai/mcp-server@latest"]
  env : {"Z_AI_API_KEY": ZAI_API_KEY, "Z_AI_MODE": "ZAI", ...os.environ}

Important : passer tout os.environ dans env pour que npx trouve Node.js sur Windows.

Outils chargés (8 au total) :
  image_analysis, extract_text_from_screenshot, ui_to_artifact,
  video_analysis, diagnose_error_screenshot, understand_technical_diagram,
  ui_diff_check, analyze_data_visualization

Bonne pratique Z.ai : référencer les images par chemin de fichier dans le prompt,
ne pas coller d'image directement. Ex : "Analyse l'image C:\tmp\screen.png"

Délai de démarrage : npx télécharge le package au premier lancement (~5-10s).
Gérer avec un timeout approprié à l'initialisation.

Test Gradio (nécessite d'avoir TOOL-8 ou un PNG existant) :
1. Préparer un screenshot PNG quelconque dans C:\tmp\capture.png
2. "Analyse l'image C:\tmp\capture.png et décris précisément ce que tu vois"
3. "Extrait tout le texte visible dans C:\tmp\capture.png"
4. Si une image d'erreur existe : "Analyse cette erreur : C:\tmp\error.png et propose un fix"

Commit message : feat(tools): tool-7 mcp vision glm46v

---

## TOOL-8 — Screenshot Windows

Fichier : agent/tools/screenshot.py

Dépendances : uv add pyautogui pillow

Classe ScreenshotTool.

Paramètres :
- region (str, optionnel) : "x,y,width,height" pour une région spécifique
  Si absent : screenshot de l'écran entier

Implémentation :
- Créer le dossier C:\tmp\myclawshots\ s'il n'existe pas (configurable via env SCREENSHOT_DIR)
- Nommer le fichier : screen_{timestamp}.png (ex: screen_20260219_143022.png)
- pyautogui.screenshot() ou pyautogui.screenshot(region=(x,y,w,h))
- Sauvegarder avec Pillow
- Retourner le chemin absolu Windows du fichier

Ajouter dans __init__.py :
  from .screenshot import ScreenshotTool
  TOOLS = [FileSystemTool(), OsExecTool(), ClipboardTool(), ScreenshotTool()]

Test Gradio :
1. "Prends un screenshot de l'écran entier"
2. Vérifier que le fichier PNG existe dans C:\tmp\myclawshots\
3. "Prends un screenshot et analyse-le" → enchaîne automatiquement avec TOOL-7
4. (Optionnel) "Prends un screenshot de la région 0,0,800,600"

Commit message : feat(tools): tool-8 screenshot windows

---

## TOOL-9 — Contrôle souris et clavier

Fichier : agent/tools/mouse_keyboard.py

pyautogui déjà installé avec TOOL-8.

Classe MouseKeyboardTool.

Paramètre "operation" qui dispatch :
- click : cliquer à des coordonnées (x, y)
- double_click : double-cliquer à des coordonnées (x, y)
- move : déplacer la souris sans cliquer
- right_click : clic droit à des coordonnées
- type : taper du texte (avec délai configurable entre les touches)
- hotkey : combinaison de touches (ex: "ctrl,c" ou "win" ou "alt,f4")
- drag : glisser de (x1,y1) à (x2,y2)
- scroll : scroller à une position (x, y, clicks)

Paramètres :
- operation (str)
- x, y (int, optionnel) : coordonnées
- x2, y2 (int, optionnel) : coordonnées destination pour drag
- text (str, optionnel) : texte à taper
- keys (str, optionnel) : touches séparées par virgule pour hotkey
- clicks (int, optionnel) : nombre de clics pour scroll

Important : ajouter pyautogui.FAILSAFE = True (déplacer souris coin haut-gauche pour arrêter)
et un sleep de 0.5s après chaque action pour laisser l'OS réagir.

Ajouter dans __init__.py :
  from .mouse_keyboard import MouseKeyboardTool
  TOOLS = [FileSystemTool(), OsExecTool(), ClipboardTool(), ScreenshotTool(), MouseKeyboardTool()]

Test Gradio (scénario complet) :
1. "Ouvre le menu Démarrer"
2. "Tape 'notepad' et appuie sur Entrée"
3. "Prends un screenshot et vérifie que Notepad est ouvert"
4. "Tape 'Bonjour depuis my-claw !' dans Notepad"
5. "Ferme Notepad sans sauvegarder (Alt+F4 puis ne pas sauvegarder)"

Commit message : feat(tools): tool-9 mouse keyboard control

---

## TOOL-10 — MCP Chrome DevTools (Playwright)

Pas de fichier tools/ — intégration dans main.py via ToolCollection.from_mcp().

Dépendance : npx @playwright/mcp@latest (pas d'installation locale requise)
Chrome doit être installé sur la machine Windows.

Configuration StdioServerParameters :
  command : "npx"
  args : ["@playwright/mcp@latest"]
  env : os.environ (pour trouver Chrome)

Optionnel : passer --headed pour voir Chrome s'ouvrir (utile pour debug).
En production : headless par défaut.

Outils chargés (dépend de la version Playwright MCP) :
  navigate, click, fill, select, press_key, screenshot, get_text, get_html,
  wait_for_element, scroll, hover, new_tab, close_tab...

Test Gradio :
1. "Ouvre https://example.com dans Chrome"
2. "Récupère le titre H1 de la page"
3. "Prends un screenshot de la page entière"
4. "Va sur https://huggingface.co et cherche smolagents dans la barre de recherche"

Commit message : feat(tools): tool-10 mcp chrome playwright

---

## RÉCAPITULATIF ORDRE D'IMPLÉMENTATION

```
TOOL-1   Fichiers Windows          ← COMMENCER ICI
TOOL-2   OS PowerShell
TOOL-3   Clipboard
         → Checkpoint intermédiaire : les 3 tools locaux fonctionnent ensemble
TOOL-4   MCP Web Search Z.ai
TOOL-5   MCP Web Reader Z.ai
TOOL-6   MCP Zread GitHub
         → Checkpoint intermédiaire : MCP HTTP remote fonctionnels
TOOL-7   MCP Vision GLM-4.6V
TOOL-8   Screenshot Windows
TOOL-9   Souris/Clavier
         → Checkpoint intermédiaire : pilotage PC complet fonctionnel
TOOL-10  MCP Chrome Playwright
         → CHECKPOINT FINAL : tous les tools validés → passer au MODULE 4
```

---

## GESTION DES ERREURS — RÈGLES GÉNÉRALES

- Tous les tools doivent capturer les exceptions et retourner un message lisible
- Ne jamais faire crasher le CodeAgent avec une exception non gérée
- Logger l'erreur avec logging.error() côté Python
- Retourner une string d'erreur préfixée par "ERROR: " pour que l'agent comprenne
- Pour les tools MCP : si la connexion échoue au démarrage, désactiver silencieusement

---

## VARIABLES D'ENV À AJOUTER (agent/.env)

ZAI_API_KEY=ton_token_zai
ZAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
SCREENSHOT_DIR=C:\tmp\myclawshots

---

## NOTES IMPORTANTES

Qwen3 vs GLM-4.7 pour les tools :
- Qwen3:14b (main) : bon pour les tools simples (fichiers, OS, clipboard)
- GLM-4.7 (reason) : meilleur pour orchestrer des tâches complexes multi-tools
- GLM-4.6V (via Vision MCP) : uniquement pour l'analyse d'images

pyautogui sur Windows :
- FAILSAFE=True obligatoire — déplacer la souris en haut à gauche pour stopper
- Peut nécessiter des droits admin pour certaines actions (UAC)
- Un délai de 0.5s entre les actions évite les problèmes de timing Windows

MCP stdio sur Windows :
- Passer os.environ complet dans env de StdioServerParameters
- Vérifier que npx est dans le PATH Windows
- Le premier lancement télécharge le package — peut être lent

Quota Z.ai Lite à surveiller :
- TOOL-4, 5, 6 partagent les 100 calls/mois
- TOOL-7 consomme le pool de 5h vision
- L'agent ne doit pas appeler ces tools inutilement — max_steps=10 aide à limiter
