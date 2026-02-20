# Test TOOL-7 — MCP Vision Z.ai

**Date** : 2026-02-20  
**Statut** : Prêt pour test utilisateur

---

## ✅ Configuration validée

- ✅ Serveur démarré avec succès
- ✅ MCP Vision Z.ai connecté - 8 outils disponibles
- ✅ Total 13 outils (5 locaux + 8 MCP)
- ✅ Pas d'erreur "Event loop is closed"

---

## ⚠️ Problème identifié : GLM-4.7 incompatible

**Le modèle GLM-4.7 (reason) génère des balises `</code>` invalides** causant des `SyntaxError`.

**Solution** : Utiliser les modèles Ollama locaux (qwen3, gemma3).

---

## 🎯 Modèles disponibles sur cette machine

| ID | Modèle Ollama | Taille | Usage |
|----|---------------|--------|-------|
| **fast** | gemma3:latest | 3.3GB | Réponses rapides |
| **smart** | qwen3:latest (8b) | 5.2GB | ⭐ **RECOMMANDÉ** pour TOOL-7 |
| **main** | qwen3:latest (8b) | 5.2GB | Par défaut |
| **vision** | qwen3-vl:4b | 3.3GB | Vision locale (alternative MCP) |
| code | glm-4.7-flash | Cloud | ❌ Incompatible smolagents |
| reason | glm-4.7 | Cloud | ❌ Incompatible smolagents |

---

## 🧪 Test à effectuer

### 1. Relancer Gradio

```bash
cd agent
uv run python gradio_app.py
```

### 2. Sélectionner le modèle **`smart`** (qwen3:8b)

Dans l'interface Gradio, choisir **`smart`** dans le dropdown.

### 3. Tester les scénarios

#### Scénario 1 : Screenshot + Analyse
```
Prends un screenshot et décris ce que tu vois
```

**Résultat attendu** :
- ✅ L'agent utilise `ScreenshotTool`
- ✅ L'agent utilise `analyze_image` (MCP Vision)
- ✅ Retour : description détaillée de l'écran

#### Scénario 2 : Screenshot + OCR
```
Prends un screenshot et extrait tout le texte visible
```

**Résultat attendu** :
- ✅ L'agent utilise `ScreenshotTool`
- ✅ L'agent utilise `extract_text_from_screenshot` (MCP Vision)
- ✅ Retour : texte extrait

#### Scénario 3 : Pilotage PC avec Vision (TOOL-9)
```
Ouvre le menu Démarrer Windows, prends un screenshot et vérifie qu'il est ouvert
```

**Résultat attendu** :
- ✅ L'agent utilise `MouseKeyboardTool.hotkey("win")`
- ✅ L'agent utilise `ScreenshotTool`
- ✅ L'agent utilise `analyze_image` pour vérifier
- ✅ Retour : confirmation que le menu est ouvert

#### Scénario 4 : Ouvrir Notepad (test complet)
```
Ouvre Notepad
```

**Résultat attendu** :
- ✅ L'agent ouvre le menu Démarrer
- ✅ L'agent vérifie visuellement que le menu est ouvert
- ✅ L'agent tape "notepad"
- ✅ L'agent appuie sur Entrée
- ✅ L'agent vérifie visuellement que Notepad est ouvert
- ✅ Retour : confirmation que Notepad est ouvert

---

## 📊 Logs attendus dans le terminal du serveur

```
INFO:main:Tools disponibles: 13 (5 locaux, 8 MCP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Step 1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LiteLLM completion() model= qwen3:latest; provider = ollama_chat
 ─ Executing parsed code: ─────────────────────────────────────────────────────────────────────────────────────────────────
  screenshot_path = screenshot()
  print(f"Screenshot saved to: {screenshot_path}")
 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Out: Screenshot saved to: C:\tmp\myclawshots\screen_001.png
[Step 1: Duration X.XX seconds| Input tokens: XXX | Output tokens: XXX]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Step 2 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LiteLLM completion() model= qwen3:latest; provider = ollama_chat
 ─ Executing parsed code: ─────────────────────────────────────────────────────────────────────────────────────────────────
  result = analyze_image(image_path="C:\\tmp\\myclawshots\\screen_001.png", query="Describe what you see")
  print(result)
 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Out: [Description de l'écran]
[Step 2: Duration X.XX seconds| Input tokens: XXX | Output tokens: XXX]
```

---

## ✅ Critères de validation

- [ ] Le modèle `smart` (qwen3:8b) ne génère pas de balises `</code>`
- [ ] L'agent réussit à prendre un screenshot
- [ ] L'agent réussit à analyser l'image avec MCP Vision
- [ ] L'agent retourne une description cohérente
- [ ] Pas d'erreur "SyntaxError: invalid syntax"
- [ ] Pas d'erreur "Event loop is closed"
- [ ] L'agent atteint son objectif en moins de 10 steps

---

## 🎯 Si le test réussit

**TOOL-7 est validé !** Vous pouvez alors :

1. Commiter les changements :
   ```bash
   git add agent/main.py agent/gradio_app.py agent/test_mcp_vision.py .env.example plans/validation-tool7-mcp-vision.md LEARNING.md PROGRESS.md CHECKPOINT-TOOL7.md AGENTS.md TEST-TOOL7.md
   git commit -m "feat(tools): tool-7 mcp vision z.ai glm-4.6v

   - Intégration MCP Vision Z.ai via FastAPI lifespan
   - 8 outils disponibles: analyze_image, OCR, diagrammes, etc.
   - Résolution du bug 'Event loop is closed'
   - Client MCP actif pendant toute la durée de vie de l'app
   - Débloque TOOL-9 (contrôle souris/clavier avec vision)
   - Configuration adaptée aux modèles Ollama disponibles
   - Modèle recommandé: smart (qwen3:8b)
   "
   ```

2. Passer au module suivant (MODULE-4 : Nextcloud Talk Bot)

---

## 🔧 Si le test échoue

Communiquez-moi les logs du serveur et je vous aiderai à diagnostiquer le problème.

