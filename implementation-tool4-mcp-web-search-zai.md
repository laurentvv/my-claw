# TOOL-4 — MCP Web Search Z.ai — Plan d'implémentation

> Document pour IA de codage (Claude Code, Cursor, Cline…)
> Lire AGENTS.md, LEARNING.md et PROGRESS.md avant de commencer.
> RÈGLE ABSOLUE : un checkpoint validé → commit → étape suivante.

---

## CONTEXTE

### Ce qu'on implémente
TOOL-4 ajoute la recherche web temps réel via le MCP Web Search Z.ai.

**Source officielle** : https://docs.z.ai/devpack/mcp/search-mcp-server

**Outil exposé** : `webSearchPrime` (1 seul outil)
**Type de connexion** : HTTP streamable (pas stdio, pas npx)
**URL** : `https://api.z.ai/api/mcp/web_search_prime/mcp`
**Auth** : `Authorization: Bearer {ZAI_API_KEY}`

### Différence avec TOOL-10 (Chrome DevTools)
- TOOL-10 utilise `StdioServerParameters` (processus local npx)
- TOOL-4 utilise un dict HTTP streamable (service distant Z.ai)
- Pas de processus local à gérer, pas de `npx`

### Quota Z.ai Lite
- 100 appels web search + web reader combinés par mois
- Partagés avec TOOL-5 (webReader) et TOOL-6 (zread) à venir
- **Utiliser avec parcimonie** — ne pas tester en boucle

### Architecture après TOOL-4
TOOL-4 alimente `web_agent` dans l'architecture multi-agent :
```
Manager
└── web_agent (qwen3:8b / Nanbeige4.1-3B) → webSearchPrime
```

---

## ÉTAPE 1 — Vérifier la configuration

### 1A — Vérifier ZAI_API_KEY dans agent/.env
```env
ZAI_API_KEY=ton_token_zai
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
```

Si `ZAI_API_KEY` est absent ou vide → TOOL-4 ne peut pas fonctionner.
Ne pas modifier le code pour ignorer cela — logger un warning et continuer sans le tool.

### 1B — Vérifier que smolagents MCP HTTP est supporté

La connexion HTTP streamable utilise un dict (pas `StdioServerParameters`) :
```python
web_search_params = {
    "url": "https://api.z.ai/api/mcp/web_search_prime/mcp",
    "type": "streamable-http",
    "headers": {
        "Authorization": f"Bearer {os.environ['ZAI_API_KEY']}"
    }
}
```

**IMPORTANT** : Vérifier la version de smolagents installée :
```bash
cd agent
uv run python -c "import smolagents; print(smolagents.__version__)"
```
Smolagents >= 1.9.0 supporte les MCP HTTP streamable via dict.

**Checkpoint 1** : `ZAI_API_KEY` présent dans agent/.env

---

## ÉTAPE 2 — Modifier lifespan dans main.py

### Ce qui existe déjà dans main.py
Le plan de migration multi-agent a déjà prévu ce bloc commenté dans `lifespan` :

```python
# ── Web Search MCP Z.ai (TOOL-4) ─────────────────────────────────────────
# IMPORTANT : décommenter quand ZAI_API_KEY configuré et TOOL-4 implémenté
# logger.info("Initialisation Web Search MCP Z.ai...")
# try:
#     if os.environ.get("ZAI_API_KEY"):
#         web_search_params = {
#             "url": "https://api.z.ai/api/mcp/web_search_prime/mcp",
#             "type": "streamable-http",
#             "headers": {"Authorization": f"Bearer {os.environ['ZAI_API_KEY']}"}
#         }
#         _web_search_context = ToolCollection.from_mcp(web_search_params, trust_remote_code=True)
#         tool_collection = _web_search_context.__enter__()
#         _web_search_tools = list(tool_collection.tools)
#         logger.info(f"✓ Web Search MCP Z.ai: {len(_web_search_tools)} outils")
#     else:
#         logger.warning("✗ ZAI_API_KEY absent, Web Search MCP désactivé")
# except Exception as e:
#     logger.warning(f"✗ Web Search MCP Z.ai: {e}")
```

### Action : Décommenter et ajuster le bloc

Remplacer le bloc commenté par le code suivant dans `lifespan` (section startup) :

```python
# ── Web Search MCP Z.ai (TOOL-4) ─────────────────────────────────────────
logger.info("Initialisation Web Search MCP Z.ai...")
try:
    zai_key = os.environ.get("ZAI_API_KEY", "").strip()
    if not zai_key:
        logger.warning("✗ ZAI_API_KEY absent ou vide → web_agent désactivé")
    else:
        web_search_params = {
            "url": "https://api.z.ai/api/mcp/web_search_prime/mcp",
            "type": "streamable-http",
            "headers": {
                "Authorization": f"Bearer {zai_key}"
            }
        }
        _web_search_context = ToolCollection.from_mcp(
            web_search_params,
            trust_remote_code=True
        )
        tool_collection = _web_search_context.__enter__()
        _web_search_tools = list(tool_collection.tools)
        logger.info(f"✓ Web Search MCP Z.ai: {len(_web_search_tools)} outils")
        logger.info(f"  Outils: {[t.name for t in _web_search_tools]}")
except Exception as e:
    logger.warning(f"✗ Web Search MCP Z.ai non disponible: {e}")
    _web_search_context = None
    _web_search_tools = []
```

Et dans le bloc **shutdown** de `lifespan` :
```python
# Fermeture Web Search MCP Z.ai
if _web_search_context is not None:
    try:
        _web_search_context.__exit__(None, None, None)
        logger.info("✓ Web Search MCP Z.ai fermé")
    except Exception as e:
        logger.error(f"✗ Fermeture Web Search MCP Z.ai: {e}")
```

### Checkpoint 2
Démarrer le serveur :
```bash
cd agent
uv run uvicorn main:app --reload
```

Logs attendus si ZAI_API_KEY configuré :
```
✓ Web Search MCP Z.ai: 1 outils
  Outils: ['webSearchPrime']
✓ web_agent créé (1 tools Z.ai MCP)
```

Logs attendus si ZAI_API_KEY absent :
```
✗ ZAI_API_KEY absent ou vide → web_agent désactivé
✗ web_agent ignoré (aucun tool MCP Z.ai)
```

**Commit** : `feat(tool-4): décommenter bloc Web Search MCP Z.ai dans lifespan`

---

## ÉTAPE 3 — Vérifier web_agent.py

Le fichier `agent/agents/web_agent.py` existe déjà depuis la migration multi-agent.
Vérifier qu'il reçoit bien `_web_search_tools` dans `build_multi_agent_system` :

```python
# Dans main.py — build_multi_agent_system()
if _web_search_tools:
    try:
        managed_web = create_web_managed_agent(ollama_url, _web_search_tools)
        if managed_web:
            managed_agents.append(managed_web)
            logger.info(f"✓ web_agent créé ({len(_web_search_tools)} tools Z.ai MCP)")
    except Exception as e:
        logger.warning(f"✗ web_agent non disponible: {e}")
else:
    logger.info("✗ web_agent ignoré (aucun tool MCP Z.ai)")
```

### Instructions web_agent — ajuster pour webSearchPrime

Dans `agent/agents/web_agent.py`, vérifier que les instructions mentionnent le bon outil et ses paramètres :

```python
_WEB_INSTRUCTIONS = """
Tu es un agent spécialisé dans la recherche web en temps réel via webSearchPrime.

OUTIL DISPONIBLE :
- webSearchPrime(search_query="...", search_recency_filter="...", search_domain_filter="...")
  → Retourne : titres, URLs, résumés, noms de sites, icônes

PARAMÈTRES webSearchPrime :
- search_query (requis) : la requête de recherche (max ~70 caractères)
- search_recency_filter (optionnel) : "oneDay" | "oneWeek" | "oneMonth" | "oneYear"
- search_domain_filter (optionnel) : filtrer sur un domaine ex "huggingface.co"

BONNES PRATIQUES :
- Requêtes courtes et précises (1-6 mots clés max)
- Utiliser search_recency_filter="oneWeek" pour les actualités récentes
- Utiliser search_domain_filter pour cibler un site précis
- Résumer les résultats de manière concise
- QUOTA : 100 calls/mois partagés — appeler UNE SEULE FOIS par tâche

EXEMPLES DE REQUÊTES :
- webSearchPrime(search_query="smolagents latest release", search_recency_filter="oneWeek")
- webSearchPrime(search_query="qwen3 benchmark results", search_domain_filter="huggingface.co")
- webSearchPrime(search_query="prix ethereum aujourd'hui", search_recency_filter="oneDay")
"""
```

### Checkpoint 3
Vérifier l'import sans erreur :
```bash
cd agent
uv run python -c "from agents.web_agent import create_web_managed_agent; print('OK')"
```

---

## ÉTAPE 4 — Ajouter le skill webSearchPrime dans skills.txt

Ajouter à la fin de `agent/skills.txt` :

```
11. Recherche web avec webSearchPrime (QUOTA: 100/mois - utiliser avec parcimonie):
Délègue au web_agent qui appelle webSearchPrime. Formuler des requêtes courtes et précises.
Exemples de prompts:
- "Recherche les dernières nouveautés sur smolagents"
- "Quelle est la météo à Paris cette semaine ?"
- "Trouve les benchmarks récents de Nanbeige4.1-3B"

IMPORTANT: Le web_agent gère webSearchPrime automatiquement.
Le manager n'a pas besoin de coder l'appel directement.
```

---

## ÉTAPE 5 — Tests de validation

### 5A — Test basique (1 call quota)
Via Gradio avec modèle `smart` ou `main` :

**Prompt** : `"Quelles sont les dernières nouvelles sur smolagents ?"`

**Attendu dans les logs** :
```
Manager → délègue à web_agent
web_agent → webSearchPrime(search_query="smolagents latest news", search_recency_filter="oneWeek")
→ résultats retournés
→ final_answer(résumé structuré)
```

**Attendu dans Gradio** : liste de résultats avec titres et résumés, provenant de sources récentes.

### 5B — Test avec filtre domaine (1 call quota)
**Prompt** : `"Cherche des informations sur qwen3-vl sur huggingface"`

**Attendu** : Résultats filtrés sur huggingface.co uniquement.

### 5C — Test délégation correcte
**Prompt** : `"Liste les fichiers dans C:/tmp puis cherche les nouveautés Python 3.14"`

**Attendu** :
- Manager → `file_system` pour la liste (outil direct)
- Manager → `web_agent` pour la recherche Python (délégation)
- Deux réponses consolidées

### 5D — Test fallback sans ZAI_API_KEY
Commenter temporairement `ZAI_API_KEY` dans `.env`, redémarrer :

**Attendu dans les logs** :
```
✗ ZAI_API_KEY absent ou vide → web_agent désactivé
✗ web_agent ignoré (aucun tool MCP Z.ai)
```

**Attendu si on demande une recherche web** : Le manager répond qu'il ne peut pas accéder au web (pas de crash).

**Commit** : `feat: tool-4 — mcp web search zai validé`

---

## ÉTAPE 6 — Mettre à jour /health et /models

### Endpoint /health
Ajouter l'état du web search dans la réponse :

```python
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "module": "2-multi-agent",
        "chrome_mcp": len(_chrome_mcp_tools),
        "web_mcp": len(_web_search_tools),         # ← déjà présent
        "web_search_active": len(_web_search_tools) > 0,  # ← ajouter
    }
```

### Endpoint /models
Vérifier que la section `sub_agents` reflète l'état réel :
```python
"sub_agents": {
    "pc_control": "qwen3-vl:8b + screenshot/vision/ui_grounding/mouse_keyboard",
    "browser": f"Nanbeige4.1-3B + {len(_chrome_mcp_tools)} tools Chrome DevTools",
    "web_search": f"Nanbeige4.1-3B + {len(_web_search_tools)} tools Z.ai MCP",
},
```

---

## ÉTAPE 7 — Mettre à jour PROGRESS.md et LEARNING.md

### PROGRESS.md — Modifier la section TOOL-4

```markdown
### TOOL-4 — MCP Web Search Z.ai
**Statut : ✅ DONE**

Intégration :
- ToolCollection.from_mcp() avec dict HTTP streamable (pas StdioServerParameters)
- URL : https://api.z.ai/api/mcp/web_search_prime/mcp
- Header : Authorization: Bearer {ZAI_API_KEY}
- Outil exposé : webSearchPrime (1 outil)
- Chargé dans lifespan FastAPI → alimenté dans web_agent (ManagedAgent)
- Fallback silencieux si ZAI_API_KEY absent

Checkpoint :
- ✅ ZAI_API_KEY configuré dans agent/.env
- ✅ "Quelles sont les dernières nouvelles sur smolagents ?" → résultats temps réel
- ✅ Logs : webSearchPrime appelé via web_agent
- ✅ Fallback sans ZAI_API_KEY validé (pas de crash)
- ✅ Commit : feat: tool-4 — mcp web search zai
```

### LEARNING.md — Ajouter section TOOL-4

```markdown
## TOOL-4 — MCP Web Search Z.ai (2026-02-22)

### Différence HTTP streamable vs StdioServerParameters

**TOOL-10 (Chrome DevTools)** utilise un processus local :
```python
StdioServerParameters(command="npx", args=["-y", "chrome-devtools-mcp@latest"])
```

**TOOL-4 (Web Search Z.ai)** utilise un service HTTP distant :
```python
{
    "url": "https://api.z.ai/api/mcp/web_search_prime/mcp",
    "type": "streamable-http",
    "headers": {"Authorization": f"Bearer {ZAI_API_KEY}"}
}
```

Même interface `ToolCollection.from_mcp()` → même pattern `__enter__()` / `__exit__()`.

### Paramètres webSearchPrime
- `search_query` : requête courte (max ~70 chars)
- `search_recency_filter` : "oneDay" | "oneWeek" | "oneMonth" | "oneYear"
- `search_domain_filter` : filtrer sur un domaine précis

### Quota Lite
- 100 appels/mois partagés TOOL-4 + TOOL-5 + TOOL-6
- Ne tester qu'avec des prompts ciblés, pas en boucle
- Logger un compteur d'usage si besoin
```

---

## RÉCAPITULATIF ORDRE D'IMPLÉMENTATION

```
ÉTAPE 1  Vérifier ZAI_API_KEY dans agent/.env
ÉTAPE 2  Décommenter bloc Web Search dans lifespan main.py
ÉTAPE 3  Vérifier web_agent.py + instructions webSearchPrime
ÉTAPE 4  Ajouter skill webSearchPrime dans skills.txt
ÉTAPE 5  Tests validation (5A → 5D) — MAX 3 calls quota
ÉTAPE 6  Mettre à jour /health et /models
ÉTAPE 7  Mettre à jour PROGRESS.md et LEARNING.md
─────────────────────────────────────────────────────
→ CHECKPOINT FINAL validé → commit → passer TOOL-5 (Web Reader)
```

---

## STRUCTURE FICHIERS MODIFIÉS

```
agent/
├── main.py          ← Décommenter bloc Web Search MCP dans lifespan + shutdown
├── skills.txt       ← Ajouter skill webSearchPrime
└── agents/
    └── web_agent.py ← Vérifier/ajuster instructions webSearchPrime
```

Aucun nouveau fichier à créer — tout est déjà en place depuis la migration multi-agent.

---

## NOTES IMPORTANTES POUR L'IA DE CODAGE

1. **Ne pas créer** de nouveau fichier `web_search_tool.py` — le tool est MCP, pas local
2. **Ne pas modifier** `agent/tools/__init__.py` — webSearchPrime n'est pas un tool local
3. **Ne pas appeler** webSearchPrime directement dans le Manager — toujours via web_agent
4. **Le type MCP** pour Z.ai est `"streamable-http"` (avec tiret) — vérifier la compatibilité smolagents
5. **Si smolagents ne supporte pas** `"streamable-http"`, essayer `"sse"` avec l'URL SSE alternative :
   `https://api.z.ai/api/mcp/web_search_prime/sse?Authorization=YOUR_KEY`
6. **Fallback SSE** (si streamable-http échoue) :
   ```python
   web_search_params_sse = {
       "url": f"https://api.z.ai/api/mcp/web_search_prime/sse?Authorization={zai_key}",
       "type": "sse",
   }
   ```
7. **Quota** : Maximum 3 appels pour les tests — ne pas tester en boucle
8. **Ne pas modifier** les fichiers TOOL-1, TOOL-2, TOOL-3, TOOL-7, TOOL-8, TOOL-9, TOOL-10 — ils sont validés

---

## RÉFÉRENCE DOC OFFICIELLE Z.AI

- URL MCP : `https://api.z.ai/api/mcp/web_search_prime/mcp`
- URL SSE (fallback) : `https://api.z.ai/api/mcp/web_search_prime/sse?Authorization=YOUR_KEY`
- Type smolagents : `"streamable-http"` (ou `"sse"` pour fallback)
- Auth : header `Authorization: Bearer YOUR_KEY`
- Outil : `webSearchPrime`
- Quota Lite : 100 calls/mois (partagé avec web reader et zread)
- Doc : https://docs.z.ai/devpack/mcp/search-mcp-server
