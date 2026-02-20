# Validation TOOL-7 — MCP Vision Z.ai (GLM-4.6V)

**Date** : 2026-02-20  
**Statut** : EN ATTENTE DE VALIDATION UTILISATEUR

---

## Objectif

Implémenter TOOL-7 (MCP Vision Z.ai) pour permettre à l'agent d'analyser des images, faire de l'OCR, comprendre des diagrammes techniques, et débloquer TOOL-9 (contrôle souris/clavier).

---

## Modifications apportées

### 1. agent/main.py

**Problème résolu** : Le bug "Event loop is closed" était causé par la fermeture prématurée du contexte MCP.

**Solution** : Utilisation de FastAPI `lifespan` pour garder le client MCP actif pendant toute la durée de vie de l'application.

**Changements** :
- Ajout de `@asynccontextmanager async def lifespan(app: FastAPI)`
- Initialisation du client MCP au startup (ligne 47-51)
- Fermeture propre au shutdown (ligne 64-69)
- Variables globales `_mcp_client` et `_mcp_tools` pour stocker les outils MCP
- Fusion dynamique des tools locaux + MCP dans `/run` (ligne 117)

### 2. .env.example

**Changements** :
- Réactivation des variables `ZAI_API_KEY` et `ZAI_BASE_URL`
- Documentation mise à jour pour indiquer que c'est requis pour TOOL-7

---

## Prérequis

1. **Node.js 24+** : Requis pour `npx @z_ai/mcp-server@latest`
2. **Clé API Z.ai** : Obtenir sur https://open.bigmodel.cn/dev/api
3. **Dépendances Python** : Déjà installées (`mcp>=0.9.0`, `smolagents[mcp]>=1.9.0`)

---

## Configuration

### 1. Créer agent/.env

```bash
cd agent
cp ../.env.example .env
```

### 2. Remplir ZAI_API_KEY dans agent/.env

```env
ZAI_API_KEY="votre_clé_api_z_ai_ici"
ZAI_BASE_URL="https://api.z.ai/api/coding/paas/v4"
```

---

## Tests à effectuer

### Test 1 : Vérifier le démarrage du serveur

```bash
cd agent
uv run uvicorn main:app --reload
```

**Résultat attendu** :
```
INFO:     Started server process
INFO:__main__:MCP Vision Z.ai connecté - 8 outils disponibles
INFO:__main__:Outils MCP: ['ui_to_artifact', 'extract_text_from_screenshot', 'diagnose_error_screenshot', 'understand_technical_diagram', 'analyze_data_visualization', 'ui_diff_check', 'analyze_image', 'analyze_video']
INFO:__main__:Total tools disponibles: 13 (5 locaux, 8 MCP)
INFO:     Application startup complete.
```

### Test 2 : Analyser une image via Gradio

```bash
cd agent
uv run python gradio_app.py
```

**Scénario** :
1. Prendre un screenshot : "Prends un screenshot de l'écran"
2. Analyser le screenshot : "Analyse le dernier screenshot pris et décris ce que tu vois"

**Résultat attendu** :
- L'agent utilise `ScreenshotTool` pour capturer l'écran
- L'agent utilise `analyze_image` (MCP Vision) pour analyser l'image
- Retour : description détaillée de ce qui est visible à l'écran

### Test 3 : OCR sur une capture d'écran

**Scénario** :
1. Ouvrir un document texte ou une page web avec du texte
2. "Prends un screenshot et extrait tout le texte visible"

**Résultat attendu** :
- L'agent utilise `ScreenshotTool`
- L'agent utilise `extract_text_from_screenshot` (MCP Vision)
- Retour : texte extrait de l'image

### Test 4 : Comprendre un diagramme technique

**Scénario** :
1. Afficher un diagramme d'architecture (ex: PLAN.md ouvert dans un éditeur)
2. "Prends un screenshot et explique-moi le diagramme d'architecture visible"

**Résultat attendu** :
- L'agent utilise `ScreenshotTool`
- L'agent utilise `understand_technical_diagram` (MCP Vision)
- Retour : explication du diagramme

### Test 5 : Débloquer TOOL-9 (contrôle souris/clavier)

**Scénario** :
1. "Ouvre le menu Démarrer Windows"
2. "Prends un screenshot et vérifie que le menu est ouvert"
3. "Tape 'notepad' et appuie sur Entrée"
4. "Prends un screenshot et vérifie que Notepad est ouvert"

**Résultat attendu** :
- L'agent utilise `MouseKeyboardTool` pour ouvrir le menu (hotkey "win")
- L'agent utilise `ScreenshotTool` + `analyze_image` pour vérifier
- L'agent utilise `MouseKeyboardTool` pour taper et valider
- L'agent utilise `ScreenshotTool` + `analyze_image` pour confirmer
- Notepad est ouvert et visible

---

## Outils MCP Vision disponibles

| Outil | Description |
|-------|-------------|
| `analyze_image` | Analyse générale d'une image |
| `extract_text_from_screenshot` | OCR sur captures d'écran |
| `ui_to_artifact` | Transformer une UI en code/specs |
| `analyze_video` | Analyser une vidéo locale (max 8MB, MP4/MOV/M4V) |
| `diagnose_error_screenshot` | Analyser une erreur visible à l'écran |
| `understand_technical_diagram` | Lire un schéma d'architecture |
| `ui_diff_check` | Comparer deux captures UI |
| `analyze_data_visualization` | Lire un graphique/dashboard |

---

## Checklist de validation

- [ ] Le serveur démarre sans erreur
- [ ] Les 8 outils MCP Vision sont chargés
- [ ] Test 1 : Analyse d'image fonctionne
- [ ] Test 2 : OCR fonctionne
- [ ] Test 3 : Compréhension de diagramme fonctionne
- [ ] Test 4 : Pilotage PC avec Vision fonctionne (TOOL-9 débloqué)
- [ ] Pas d'erreur "Event loop is closed"
- [ ] Fermeture propre du serveur (Ctrl+C)

---

## Commit

Une fois validé :

```bash
git add agent/main.py .env.example plans/validation-tool7-mcp-vision.md
git commit -m "feat(tools): tool-7 mcp vision z.ai glm-4.6v

- Intégration MCP Vision Z.ai via FastAPI lifespan
- 8 outils disponibles: image_analysis, OCR, diagrammes, etc.
- Résolution du bug 'Event loop is closed'
- Client MCP actif pendant toute la durée de vie de l'app
- Débloque TOOL-9 (contrôle souris/clavier avec vision)
"
```

---

## Références

- Bug GitHub smolagents #1159 : https://github.com/huggingface/smolagents/issues/1159
- Documentation Z.ai MCP Vision : https://docs.z.ai/devpack/mcp/vision-mcp-server
- Documentation smolagents MCP : https://huggingface.co/docs/smolagents/tutorials/mcp

