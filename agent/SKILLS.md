# Skills — Patterns de code pour l'agent smolagents

Ce fichier documente les **skills** (patterns de code réutilisables) fournis à l'agent via le paramètre `instructions` de `CodeAgent`.

Les skills sont définis dans **`agent/skills.txt`** et chargés automatiquement au démarrage du serveur.

## Pourquoi des skills ?

Les LLM ont tendance à **régénérer le code à chaque fois**, ce qui :
- ❌ Prend du temps (génération LLM)
- ❌ Consomme des tokens inutilement
- ❌ Peut introduire des erreurs ou variations
- ❌ Nécessite de "réapprendre" les patterns à chaque fois

En fournissant des **patterns de code concrets** dans `instructions`, l'agent peut :
- ✅ **Copier directement** le code sans le régénérer
- ✅ Exécuter plus rapidement
- ✅ Être plus fiable et cohérent
- ✅ Économiser des tokens

---

## Skills disponibles (2026-02-20)

### 1. Screenshot + Vision

**Usage** : Prendre un screenshot et l'analyser avec qwen3-vl:2b

```python
screenshot_path = screenshot()
print(f"Screenshot saved: {screenshot_path}")
analysis = analyze_image(image_path=screenshot_path, prompt="Describe what you see in this screenshot")
print(f"Analysis: {analysis}")
```

**Cas d'usage** :
- "Prends un screenshot et décris ce que tu vois"
- "Qu'est-ce qui est affiché à l'écran ?"
- "Analyse l'écran actuel"

---

### 2. OCR (Extraction de texte)

**Usage** : Extraire le texte visible depuis un screenshot

```python
screenshot_path = screenshot()
text = analyze_image(image_path=screenshot_path, prompt="Extract all visible text from this image. Return only the text, nothing else.")
print(f"Extracted text: {text}")
```

**Cas d'usage** :
- "Lis le texte affiché à l'écran"
- "Extrait le texte de cette fenêtre"
- "Qu'est-ce qui est écrit ?"

---

### 3. Screenshot d'une région spécifique

**Usage** : Capturer seulement une partie de l'écran

```python
# Region format: (x, y, width, height)
screenshot_path = screenshot(region=(100, 100, 800, 600))
print(f"Region screenshot saved: {screenshot_path}")
```

**Cas d'usage** :
- "Prends un screenshot de la zone en haut à gauche"
- "Capture seulement la fenêtre active"

---

### 4. Requête HTTP avec Python

**Usage** : Faire une requête HTTP (PAS avec os_exec + curl)

```python
import requests
response = requests.get("https://wttr.in/Nancy?format=3")
print(response.text)
```

**Cas d'usage** :
- "Quel temps fait-il à Nancy ?"
- "Récupère les données de cette API"
- "Télécharge ce fichier"

---

### 5. Ouvrir une application avec le clavier

**Usage** : Ouvrir une application Windows via le menu Démarrer

```python
keyboard_hotkey("win")
import time
time.sleep(0.5)
keyboard_type("notepad")
time.sleep(0.5)
keyboard_hotkey("enter")
```

**Cas d'usage** :
- "Ouvre Notepad"
- "Lance Calculator"
- "Démarre Chrome"

---

## Comment ajouter un nouveau skill ?

1. **Identifier un pattern répétitif** : Si l'agent régénère souvent le même type de code
2. **Créer un exemple concret** : Code minimal et fonctionnel
3. **Ajouter dans `agent/skills.txt`** : Ajouter le pattern à la fin du fichier
4. **Redémarrer le serveur** : `uv run uvicorn main:app --reload` pour recharger les skills
5. **Documenter ici** : Ajouter le pattern dans ce fichier pour référence
6. **Tester** : Vérifier que l'agent copie bien le pattern au lieu de le régénérer

**Avantage** : Pas besoin de modifier le code Python, juste éditer `skills.txt` !

---

## Bonnes pratiques

- ✅ **Patterns courts** : 3-5 lignes max par skill
- ✅ **Code fonctionnel** : Doit marcher tel quel, sans modification
- ✅ **Commentaires clairs** : Expliquer ce que fait chaque ligne si nécessaire
- ✅ **Cas d'usage explicites** : Donner des exemples de questions utilisateur
- ❌ **Pas de code complexe** : Les skills sont des raccourcis, pas des bibliothèques
- ❌ **Pas de duplication** : Un skill = un cas d'usage précis

---

## Architecture

```
agent/
├── skills.txt          ← Patterns de code chargés au démarrage
├── SKILLS.md           ← Documentation (ce fichier)
└── main.py             ← Charge skills.txt via load_skills()
```

**Flux** :
1. Au démarrage, `main.py` appelle `load_skills()`
2. `load_skills()` lit `agent/skills.txt`
3. Le contenu est stocké dans la variable `SKILLS`
4. `SKILLS` est passé au paramètre `instructions` de `CodeAgent`
5. L'agent reçoit les patterns et peut les copier directement

---

## Références

- **smolagents documentation** : https://huggingface.co/docs/smolagents/tutorials/building_good_agents
- **CodeAgent.instructions** : https://huggingface.co/docs/smolagents/reference/agents#smolagents.CodeAgent
- **LEARNING.md** : Section "Guidage de l'agent CodeAgent"
- **skills.txt** : Fichier source des patterns de code

