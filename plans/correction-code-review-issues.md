# Plan de Correction - Code Review Issues

**Date:** 2025-02-22
**Statut:** 4 problèmes identifiés (3 WARNING, 1 SUGGESTION)

---

## Vue d'ensemble

| Sévérité | Compte | Problèmes |
|----------|--------|-----------|
| CRITICAL | 0 | - |
| WARNING  | 3 | Rebuild agents, Cache Ollama, Imports inutilisés |
| SUGGESTION | 1 | num_ctx excessif |

---

## Problème 1: WARNING - Rebuild des agents à chaque requête

**Fichier:** `agent/main.py:246`
**Problème:** `build_multi_agent_system()` est appelé à chaque requête `/run`, ce qui reconstruit tous les sous-agents à chaque fois. C'est très coûteux en termes de performance.

### Impact
- Chaque requête `/run` recrée tous les sous-agents (pc_control, vision, browser, web)
- Surcharge inutile du CPU et de la mémoire
- Latence ajoutée à chaque requête

### Solution proposée
Implémenter un cache global du manager et le reconstruire uniquement lorsque le modèle change.

**Architecture actuelle:**
```python
@app.post("/run")
async def run(req: RunRequest):
    agent = build_multi_agent_system(req.model)  # ❌ Rebuild à chaque requête
    ...
```

**Architecture proposée:**
```python
# Cache global
_agent_cache: dict[str, CodeAgent] = {}
_cache_lock = asyncio.Lock()

@app.post("/run")
async def run(req: RunRequest):
    async with _cache_lock:
        if req.model not in _agent_cache:
            _agent_cache[req.model] = build_multi_agent_system(req.model)
    agent = _agent_cache[req.model]
    ...
```

### Avantages
- ✅ Réduction drastique de la latence des requêtes
- ✅ Moins de charge CPU/mémoire
- ✅ Les agents sont reconstruits uniquement si nécessaire (changement de modèle)

### Inconvénients
- ⚠️ Plus de complexité (cache + lock)
- ⚠️ Nécessite un mécanisme d'invalidation si les agents doivent être reconstruits (ex: changement de configuration)

### Implémentation
1. Ajouter un dictionnaire global `_agent_cache` et un `_cache_lock`
2. Dans `/run`, vérifier si le modèle est en cache
3. Si non, construire l'agent et le mettre en cache
4. Utiliser `asyncio.Lock()` pour éviter les conditions de course

---

## Problème 2: WARNING - Détection modèles au moment de l'import

**Fichier:** `agent/models.py:78`
**Problème:** `MODELS = detect_models()` est exécuté au moment de l'import du module. Cela fait un appel HTTP à Ollama, et si Ollama est down à ce moment, le cache sera définitivement périmé.

### Impact
- Si Ollama est down au démarrage du serveur, `MODELS` sera vide ou incomplet
- Le cache `_detected_models` ne sera jamais rafraîchi
- Le serveur doit être redémarré pour détecter les nouveaux modèles

### Solution proposée
Utiliser une approche "lazy initialization" avec rafraîchissement périodique.

**Architecture actuelle:**
```python
def detect_models() -> dict[str, tuple[str, str]]:
    global _detected_models
    if _detected_models is not None:
        return _detected_models
    # Appel HTTP à Ollama
    ...
    _detected_models = detected
    return detected

MODELS = detect_models()  # ❌ Exécuté à l'import
```

**Architecture proposée:**
```python
def get_models() -> dict[str, tuple[str, str]]:
    """Retourne les modèles détectés avec cache lazy."""
    global _detected_models
    if _detected_models is None:
        _detected_models = _detect_models_impl()
    return _detected_models

# Remplacer MODELS par get_models() partout
```

### Avantages
- ✅ L'appel HTTP n'est fait qu'à la première utilisation
- ✅ Possibilité d'ajouter un rafraîchissement périodique
- ✅ Le serveur démarre même si Ollama est down (erreur différée)

### Inconvénients
- ⚠️ Changement d'API (MODELS → get_models())
- ⚠️ Nécessite de mettre à jour tous les imports de MODELS

### Implémentation
1. Renommer `MODELS` en `_MODELS_CACHE` (privé)
2. Créer une fonction `get_models()` qui retourne le cache
3. Remplacer tous les accès à `MODELS` par des appels à `get_models()`
4. Ajouter un mécanisme de rafraîchissement optionnel (ex: `refresh_models()`)

### Alternative: Lazy initialization avec fallback
```python
def get_models() -> dict[str, tuple[str, str]]:
    """Retourne les modèles détectés avec cache et retry."""
    global _detected_models
    if _detected_models is None:
        try:
            _detected_models = _detect_models_impl()
        except Exception as e:
            logger.warning(f"Échec détection modèles: {e}")
            _detected_models = {}  # Fallback vide
    return _detected_models
```

---

## Problème 3: WARNING - Imports inutilisés dans browser_agent.py

**Fichier:** `agent/agents/browser_agent.py:11`
**Problème:** Imports inutilisés: `contextmanager`, `ToolCollection`, `StdioServerParameters`, `os`. C'est du code mort suite au refactoring.

### Impact
- Code mort qui encombre le fichier
- Confusion sur les dépendances réelles du module

### Solution proposée
Supprimer les imports inutilisés.

**Code actuel:**
```python
import os
import logging
from contextlib import contextmanager  # ❌ Inutilisé
from smolagents import CodeAgent, ToolCollection  # ❌ ToolCollection inutilisé
from mcp import StdioServerParameters  # ❌ Inutilisé
```

**Code corrigé:**
```python
import logging
from smolagents import CodeAgent
```

### Avantages
- ✅ Code plus propre
- ✅ Moins de confusion sur les dépendances

### Inconvénients
- Aucun

### Implémentation
1. Analyser les imports utilisés dans le fichier
2. Supprimer `contextmanager`, `ToolCollection`, `StdioServerParameters`, `os`
3. Garder `logging` et `CodeAgent` qui sont utilisés

---

## Problème 4: SUGGESTION - num_ctx excessif dans grounding.py

**Fichier:** `agent/tools/grounding.py:167`
**Problème:** `num_ctx: 32768` est excessif pour qwen3-vl:2b grounding. L'original utilisait 4096, ce qui est plus approprié pour cette tâche.

### Impact
- Utilisation de mémoire inutilement élevée
- Latence potentielle augmentée pour une tâche simple (grounding)

### Solution proposée
Réduire `num_ctx` de 32768 à 4096.

**Code actuel:**
```python
"options": {
    "temperature": 0.0,
    "num_ctx": 32768,  # ❌ Excessif pour grounding
},
```

**Code corrigé:**
```python
"options": {
    "temperature": 0.0,
    "num_ctx": 4096,  # ✅ Suffisant pour grounding
},
```

### Avantages
- ✅ Moins de mémoire utilisée
- ✅ Potentiellement plus rapide
- ✅ Aligné avec l'implémentation originale

### Inconvénients
- Aucun (4096 est suffisant pour la tâche de grounding)

### Implémentation
1. Changer la valeur de `num_ctx` de 32768 à 4096
2. Vérifier que cela n'impacte pas d'autres utilisations de qwen3-vl

---

## Ordre de correction recommandé

1. **Problème 3** (Imports inutilisés) - Le plus simple, sans risque
2. **Problème 4** (num_ctx) - Simple, changement de valeur unique
3. **Problème 2** (MODELS lazy) - Impacte plusieurs fichiers, mais changement d'API bien défini
4. **Problème 1** (Cache agents) - Le plus complexe, nécessite une architecture de cache

---

## Tests à effectuer après correction

### Pour Problème 1 (Cache agents)
- [ ] Vérifier que le cache fonctionne (première requête lente, suivantes rapides)
- [ ] Tester avec plusieurs modèles différents
- [ ] Vérifier qu'il n'y a pas de condition de course (requêtes concurrentes)

### Pour Problème 2 (MODELS lazy)
- [ ] Démarrer le serveur sans Ollama (ne devrait pas planter)
- [ ] Démarrer Ollama après le serveur (devrait détecter les modèles)
- [ ] Tester l'endpoint `/models`

### Pour Problème 3 (Imports)
- [ ] Vérifier que le module s'importe toujours correctement
- [ ] Tester que browser_agent fonctionne toujours

### Pour Problème 4 (num_ctx)
- [ ] Tester le grounding avec qwen3-vl:2b
- [ ] Vérifier que les coordonnées sont toujours précises
- [ ] Comparer la latence avant/après

---

## Références

- Code review original: 4 issues found
- Fichiers concernés:
  - `agent/main.py` (ligne 246)
  - `agent/models.py` (ligne 78)
  - `agent/agents/browser_agent.py` (ligne 11)
  - `agent/tools/grounding.py` (ligne 167)
