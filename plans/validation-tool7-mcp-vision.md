# Validation TOOL-7 — Vision locale (Ollama qwen3-vl:2b)

**Date** : 2026-02-20  
**Statut** : ✅ VALIDÉ (100% Local)

---

## Objectif

Fournir une capacité de vision à l'agent pour analyser des images, faire de l'OCR et comprendre l'interface Windows, tout en garantissant une confidentialité totale (100% local).

---

## Historique et décision

Initialement prévu via MCP Z.ai (GLM-4.6V), le module a été refondu pour utiliser **Ollama qwen3-vl:2b** en local.

**Pourquoi ce changement ?**
1. **Confidentialité** : 0 donnée sortante, les images restent sur la machine.
2. **Simplicité** : Évite la gestion complexe des serveurs MCP et des event loops async.
3. **Gratuité** : Ne consomme pas de crédits API Z.ai.
4. **Performance** : qwen3-vl:2b est très réactif sur une machine locale.

---

## Implémentation

### 1. agent/tools/vision.py

- Classe `VisionTool` (sous-classe de `smolagents.Tool`).
- Encodage des images en Base64.
- Appel direct à l'API locale d'Ollama (`/api/generate`).
- Timeout de 180s pour permettre le traitement d'images complexes.

---

## Tests effectués

### Test 1 : Analyse d'image via Gradio

- **Prompt** : "Prends un screenshot de l'écran et analyse-le"
- **Résultat** : L'agent capture l'écran, l'envoie à Ollama local, et retourne une description précise. ✅

### Test 2 : OCR local

- **Prompt** : "Prends un screenshot et extrait tout le texte visible"
- **Résultat** : Ollama qwen3-vl:2b extrait correctement le texte affiché dans les fenêtres. ✅

### Test 3 : Pilotage PC avec Vision (TOOL-9 débloqué)

- **Prompt** : "Ouvre le menu Démarrer, vérifie avec un screenshot, puis lance Notepad"
- **Résultat** : L'agent coordonne la vision et les actions clavier pour valider chaque étape. ✅

---

## Outils de vision disponibles

| Outil | Description | Modèle |
|-------|-------------|--------|
| `analyze_image` | Analyse générale d'une image ou OCR | qwen3-vl:2b |

---

## Références

- **Ollama API** : https://github.com/ollama/ollama/blob/main/docs/api.md
- **qwen3-vl:2b** : Modèle de vision léger et performant d'Alibaba.
