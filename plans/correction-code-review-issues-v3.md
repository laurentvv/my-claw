# Plan de Correction - Code Review Issues

## Résumé

Ce plan corrige 3 problèmes critiques identifiés dans le code de l'agent Python :

1. **Pas de validation de `req.model` avant la construction/cache** - Permet de cacher des agents cassés
2. **Race condition de double-build** - Deux requêtes concurrentes peuvent construire le même agent en parallèle
3. **Échec silencieux de l'auth Z.ai** - L'erreur survient à l'exécution plutôt qu'au démarrage

---

## Problème 1 : Validation de `req.model`

### Localisation
- Fichier : [`agent/main.py`](agent/main.py:280-288)
- Endpoint : `POST /run`
- Ligne 282 : `agent = await get_or_build_agent(req.model)`

### Description
Si un client envoie `model="reason"` ou `model="code"` sans `ZAI_API_KEY` configuré :
- `get_or_build_agent` construit et cache un agent avec `CleanedLiteLLMModel(api_key="ollama")`
- L'agent cassé reste dans le cache en permanence (pas d'éviction sur erreur)
- Toutes les requêtes ultérieures échouent avec une erreur d'auth Z.ai cryptique

### Solution proposée

Ajouter une validation du modèle avant la construction :

```python
# Dans agent/main.py, avant la fonction run()

def validate_model_id(model_id: str | None) -> str:
    """
    Valide l'identifiant du modèle avant construction.
    
    Args:
        model_id: Identifiant du modèle à valider
        
    Returns:
        str: Identifiant du modèle validé
        
    Raises:
        HTTPException: Si le modèle n'est pas valide ou si la clé API est manquante
    """
    if model_id is None:
        model_id = get_default_model()
    
    # Vérifier que le modèle existe
    models = get_models()
    if model_id not in models:
        # Vérifier si c'est un modèle Ollama direct
        ollama_models = get_ollama_models()
        if model_id not in ollama_models:
            raise HTTPException(
                status_code=400,
                detail=f"Modèle '{model_id}' non trouvé. Modèles disponibles: {list(models.keys())}"
            )
    
    # Vérifier que les modèles cloud ont leur clé API
    if model_id in ["code", "reason"]:
        if not os.environ.get("ZAI_API_KEY"):
            raise HTTPException(
                status_code=400,
                detail=f"Modèle cloud '{model_id}' requiert ZAI_API_KEY. Configurez-le dans agent/.env"
            )
    
    return model_id

# Dans @app.post("/run")
@app.post("/run")
async def run(req: RunRequest):
    try:
        # Valider le modèle avant construction
        validated_model = validate_model_id(req.model)
        agent = await get_or_build_agent(validated_model)
        # ... reste du code
```

---

## Problème 2 : Race condition de double-build

### Localisation
- Fichier : [`agent/main.py`](agent/main.py:231-258)
- Fonction : `get_or_build_agent()`
- Lignes 244-258

### Description
Le pattern double-check locking actuel :

```python
if model_id not in _agent_cache:          # Check 1 (sans lock)
    new_agent = build_multi_agent_system(model_id)
    async with _cache_lock:               # Lock seulement pour l'insertion
        if model_id not in _agent_cache:  # Check 2
            _agent_cache[model_id] = new_agent
```

Problèmes :
- Deux requêtes concurrentes peuvent passer le Check 1 simultanément
- `build_multi_agent_system()` est synchrone et coûteux :
  - Spawn MCP subprocesses (Chrome DevTools via `npx`)
  - Appels HTTP à Ollama
- Les deux requêtes construisent le même système en parallèle → gaspillage de ressources

### Solution proposée

Acquérir le lock avant le check pour empêcher le double-build :

```python
# Dans agent/main.py, remplacer get_or_build_agent()

async def get_or_build_agent(model_id: str | None = None) -> CodeAgent:
    """
    Récupère l'agent depuis le cache ou le construit si nécessaire.
    
    Thread-safe : empêche le double-build avec un lock global.
    
    Args:
        model_id: Identifiant du modèle (optionnel, utilise le défaut sinon)
    
    Returns:
        CodeAgent: L'agent manager avec ses sous-agents
    """
    if model_id is None:
        model_id = get_default_model()
    
    # Acquérir le lock AVANT le check pour empêcher le double-build
    async with _cache_lock:
        if model_id not in _agent_cache:
            logger.info(f"Construction du système multi-agent pour modèle {model_id}")
            # Construire l'agent dans un thread séparé (appel bloquant)
            loop = asyncio.get_event_loop()
            new_agent = await loop.run_in_executor(
                None, build_multi_agent_system, model_id
            )
            _agent_cache[model_id] = new_agent
        else:
            logger.info(f"Utilisation du cache pour modèle {model_id}")
    
    return _agent_cache[model_id]
```

**Avantages :**
- ✅ Une seule construction par `model_id`
- ✅ `build_multi_agent_system()` exécuté dans un thread séparé (non bloquant pour l'event loop)
- ✅ Lock minimal (uniquement pendant la construction)

**Inconvénients :**
- ⚠️ Toutes les requêtes pour un modèle en construction attendent la fin de la construction
- ⚠️ Si la construction échoue, toutes les requêtes en attente échouent

**Alternative (sémaphore par modèle) :**
Pour éviter de bloquer toutes les requêtes, on pourrait utiliser un dictionnaire de sémaphores :

```python
_build_semaphores: dict[str, asyncio.Semaphore] = {}
_build_semaphores_lock = asyncio.Lock()

async def get_or_build_agent(model_id: str | None = None) -> CodeAgent:
    if model_id is None:
        model_id = get_default_model()
    
    # Check rapide sans lock
    if model_id in _agent_cache:
        return _agent_cache[model_id]
    
    # Obtenir ou créer le sémaphore pour ce modèle
    async with _build_semaphores_lock:
        if model_id not in _build_semaphores:
            _build_semaphores[model_id] = asyncio.Semaphore(1)
        semaphore = _build_semaphores[model_id]
    
    # Construire avec le sémaphore (une seule construction par modèle)
    async with semaphore:
        if model_id not in _agent_cache:
            logger.info(f"Construction du système multi-agent pour modèle {model_id}")
            loop = asyncio.get_event_loop()
            new_agent = await loop.run_in_executor(
                None, build_multi_agent_system, model_id
            )
            _agent_cache[model_id] = new_agent
    
    return _agent_cache[model_id]
```

**Recommandation :** Commencer avec la solution simple (lock global), car la construction d'agent est rare (une fois par modèle au démarrage).

---

## Problème 3 : Échec silencieux de l'auth Z.ai

### Localisation
- Fichier : [`agent/models.py`](agent/models.py:167-173)
- Fonction : `get_model()`
- Ligne 171 : `api_key=os.environ.get("ZAI_API_KEY", "ollama")`

### Description

Code actuel :
```python
if is_glm:
    return CleanedLiteLLMModel(
        model_id=model_name,
        api_base=base_url,
        api_key=os.environ.get("ZAI_API_KEY", "ollama"),  # ← Fallback "ollama"
        stop=["</code>", "</code", "</s>"],
    )
```

Problèmes :
- Si `ZAI_API_KEY` n'est pas défini, `api_key="ollama"`
- Z.ai rejette avec 401/403 à l'**exécution**, pas à la création du modèle
- L'erreur survient profondément dans l'exécution de l'agent → message cryptique
- Pas de warning au démarrage du serveur

### Solution proposée

Échouer rapidement avec un message clair :

```python
# Dans agent/models.py, fonction get_model()

def get_model(model_id: str = "main") -> LiteLLMModel:
    """
    Crée un modèle LiteLLMModel à partir d'un identifiant.

    Args:
        model_id: Identifiant du modèle (main, smart, fast, vision, code, reason)
                   OU nom direct d'un modèle Ollama (ex: hf.co/tantk/Nanbeige4.1-3B-GGUF:Q4_K_M)

    Returns:
        LiteLLMModel configuré correctement

    Raises:
        RuntimeError: Si aucun modèle n'est disponible ou si ZAI_API_KEY est manquant
    """
    models = get_models()
    
    # Vérifier si c'est une catégorie
    if model_id in models:
        model_name, base_url = models[model_id]
    else:
        # Vérifier si c'est un modèle Ollama direct
        ollama_models = get_ollama_models()
        if model_id in ollama_models:
            # Créer le modèle Ollama directement
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            model_name = f"ollama_chat/{model_id}"
            base_url = ollama_url
            logger.info(f"✓ Utilisation du modèle Ollama direct: {model_id}")
        else:
            # Fallback sur main ou le premier modèle disponible
            if "main" in models:
                model_name, base_url = models["main"]
            elif models:
                model_name, base_url = next(iter(models.values()))
                logger.warning(f"Modèle '{model_id}' non trouvé, fallback")
            else:
                raise RuntimeError("Aucun modèle disponible.")

    is_glm = "z.ai" in base_url.lower() or model_id in ["code", "reason"]

    if is_glm:
        # Vérifier que ZAI_API_KEY est configuré
        api_key = os.environ.get("ZAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ZAI_API_KEY est requis pour les modèles cloud (code, reason). "
                "Configurez-le dans agent/.env ou utilisez un modèle local (main, smart, fast)."
            )
        
        return CleanedLiteLLMModel(
            model_id=model_name,
            api_base=base_url,
            api_key=api_key,
            stop=["</code>", "</code", "</s>"],
        )
    else:
        return LiteLLMModel(
            model_id=model_name,
            api_base=base_url,
            api_key="ollama",
            num_ctx=32768,
            extra_body={"think": False},
        )
```

**Avantages :**
- ✅ Échoue rapidement à la création du modèle (pas à l'exécution)
- ✅ Message d'erreur clair avec instructions
- ✅ Le serveur ne démarre pas avec une configuration invalide

---

## Implémentation

### Ordre des modifications

1. **[`agent/models.py`](agent/models.py)** - Corriger le problème 3 (validation ZAI_API_KEY)
   - Modifier `get_model()` pour vérifier `ZAI_API_KEY` avant de créer le modèle
   - Ajouter un message d'erreur clair

2. **[`agent/main.py`](agent/main.py)** - Corriger le problème 2 (race condition)
   - Modifier `get_or_build_agent()` pour acquérir le lock avant le check
   - Exécuter `build_multi_agent_system()` dans un thread séparé

3. **[`agent/main.py`](agent/main.py)** - Corriger le problème 1 (validation req.model)
   - Ajouter la fonction `validate_model_id()`
   - Modifier l'endpoint `/run` pour valider le modèle avant construction

### Tests à effectuer

1. **Test 1 : Validation du modèle**
   - Envoyer `model="invalid"` → 400 avec liste des modèles disponibles
   - Envoyer `model="code"` sans `ZAI_API_KEY` → 400 avec message d'erreur
   - Envoyer `model="main"` → OK si modèle local disponible

2. **Test 2 : Race condition**
   - Lancer 10 requêtes simultanées pour un nouveau modèle
   - Vérifier que `build_multi_agent_system()` n'est appelé qu'une fois
   - Vérifier que toutes les requêtes reçoivent la même instance d'agent

3. **Test 3 : Échec rapide Z.ai**
   - Démarrer le serveur sans `ZAI_API_KEY`
   - Essayer de créer un agent avec `model="code"`
   - Vérifier que l'erreur survient immédiatement (pas à l'exécution)

---

## Références

- [`agent/main.py`](agent/main.py) - Endpoint `/run` et fonction `get_or_build_agent()`
- [`agent/models.py`](agent/models.py) - Fonction `get_model()`
- [`AGENTS.md`](AGENTS.md) - Documentation de l'architecture multi-agent
- [`LEARNING.md`](LEARNING.md) - Apprentissages sur le projet
