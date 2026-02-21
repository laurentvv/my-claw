# CHECKPOINT TOOL-7 — Vision locale (Ollama qwen3-vl:2b)

**Date** : 2026-02-20  
**Statut** : ✅ DONE (100% Local)

---

## Résumé

TOOL-7 a été refondu pour être **100% local** en utilisant Ollama avec le modèle `qwen3-vl:2b`. Cette approche garantit la vie privée (aucune donnée sortante) et simplifie grandement l'architecture en évitant les dépendances cloud et les serveurs MCP.

---

## Caractéristiques techniques

- **Modèle** : `qwen3-vl:2b` (Ollama)
- **Architecture** : Intégration directe comme `Tool` smolagents dans `agent/tools/vision.py`.
- **Performance** : Temps de réponse rapide (~10-30s selon la machine).
- **Confidentialité** : 0 donnée sortante, traitement local des images.

---

## Fonctionnalités

1. **analyze_image** : Analyse générale d'une image (screenshot ou fichier).
2. **OCR local** : Extraction de texte à partir d'images via un prompt adapté.
3. **Analyse d'interface** : Compréhension des éléments UI pour assister TOOL-9.

---

## Modifications effectuées

### 1. agent/tools/vision.py
- ✅ Création de la classe `VisionTool`.
- ✅ Encodage base64 des images.
- ✅ Appel à l'API locale Ollama (`/api/generate`).

### 2. agent/main.py
- ✅ Intégration de `VisionTool` dans la liste `TOOLS`.
- ✅ Suppression de la dépendance complexe MCP pour la vision.

---

## Tests effectués

- ✅ **Screenshot + analyse** : "Prends un screenshot de l'écran et analyse-le".
- ✅ **Extraction de texte** : "Prends un screenshot et extrais tout le texte visible".
- ✅ **Diagnostic d'erreur** : "Prends un screenshot et dis-moi s'il y a des erreurs".

---

## Impact sur TOOL-9 (MouseKeyboardTool)

TOOL-7 permet à l'agent de "voir" le résultat de ses actions clavier/souris. Bien que TOOL-9 soit encore "EN COURS" (car nécessitant une orchestration fine), la brique Vision est maintenant solide et locale.

---

## Références

- **Ollama Vision API** : https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-completion
- **smolagents Custom Tools** : https://huggingface.co/docs/smolagents/tutorials/custom_tools
