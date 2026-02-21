# Tests de validation — TOOL-10: MCP Chrome DevTools

> Date : 2026-02-20
> Module : TOOL-10 — MCP Chrome DevTools (Puppeteer)
> Statut : ✅ **VALIDÉ**

---

## PRÉREQUIS

### Système
- Node.js 20.19+ installé
- npm/npx disponible
- Chrome stable installé

### Vérification
```bash
node --version  # Doit être >= 20.19
npx --version
chrome --version  # Windows
google-chrome --version  # Linux
```

---

## TESTS DE DÉMARRAGE

### Test 1 : Démarrage du serveur

**Commande** :
```bash
cd agent
uv run uvicorn main:app --reload
```

**Attendu dans les logs** :
```
Démarrage Chrome DevTools MCP...
✓ Chrome DevTools MCP chargé : 26 outils
  Outils Chrome DevTools: ['click', 'drag', 'fill', 'fill_form', 'handle_dialog', 'hover', 'press_key', 'upload_file', 'close_page', 'list_pages', 'navigate_page', 'new_page', 'select_page', 'wait_for', 'emulate', 'resize_page', 'performance_analyze_insight', 'performance_start_trace', 'performance_stop_trace', 'get_network_request', 'list_network_requests', 'evaluate_script', 'get_console_message', 'list_console_messages', 'take_screenshot', 'take_snapshot']
Tools disponibles: 6 outils locaux
Outils locaux: ['file_system', 'os_exec', 'clipboard', 'screenshot', 'mouse_keyboard', 'vision']
```

**Critère de succès** : ✅ Chrome DevTools MCP chargé avec 26 outils

---

## TESTS DE BASE

### Test 2 : Navigation simple

**Prompt** :
```
Ouvre https://example.com dans Chrome
```

**Attendu** :
- Chrome s'ouvre avec example.com
- L'agent utilise l'outil `navigate_page`

**Critère de succès** : ✅ Navigation réussie

---

### Test 3 : Snapshot de la page

**Prompt** :
```
Prends un snapshot de la page et liste les éléments visibles
```

**Attendu** :
- Snapshot textuel retourné avec uid des éléments
- L'agent utilise l'outil `take_snapshot`

**Critère de succès** : ✅ Snapshot retourné avec uid des éléments

---

### Test 4 : Évaluation JavaScript

**Prompt** :
```
Récupère le titre H1 de la page via evaluate_script
```

**Attendu** :
- Titre H1 retourné
- L'agent utilise l'outil `evaluate_script`

**Critère de succès** : ✅ Titre H1 retourné

---

### Test 5 : Screenshot

**Prompt** :
```
Prends un screenshot de la page entière
```

**Attendu** :
- Screenshot PNG sauvegardé dans SCREENSHOT_DIR
- L'agent utilise l'outil `take_screenshot`

**Critère de succès** : ✅ Screenshot sauvegardé

---

### Test 6 : Navigation multi-pages

**Prompt** :
```
Va sur https://huggingface.co et prends un snapshot
```

**Attendu** :
- Navigation vers huggingface.co
- Snapshot retourné

**Critère de succès** : ✅ Navigation + snapshot réussis

---

### Test 7 : Recherche

**Prompt** :
```
Cherche 'smolagents' dans la barre de recherche et valide avec Enter
```

**Attendu** :
- Recherche effectuée
- Résultats affichés
- L'agent utilise `fill` ou `fill_form` + `press_key`

**Critère de succès** : ✅ Recherche effectuée

---

### Test 8 : Requêtes réseau

**Prompt** :
```
Liste les requêtes réseau de la page
```

**Attendu** :
- Liste des requêtes réseau retournée
- L'agent utilise l'outil `list_network_requests`

**Critère de succès** : ✅ Liste des requêtes retournée

---

### Test 9 : Messages console

**Prompt** :
```
Vérifie les messages console de la page
```

**Attendu** :
- Liste des messages console retournée
- L'agent utilise l'outil `list_console_messages`

**Critère de succès** : ✅ Liste des messages console retournée

---

## SCÉNARIOS AVANCÉS

### Test 10 : Performance trace

**Séquence de prompts** :
1. "Ouvre https://developers.chrome.com"
2. "Lance un enregistrement de performance trace avec autoStop et reload"
3. "Analyse les insights de performance"

**Attendu** :
- Navigation vers developers.chrome.com
- Trace de performance enregistrée
- Insights de performance analysées

**Critère de succès** : ✅ Performance trace complète

---

### Test 11 : Navigation multi-pages

**Séquence de prompts** :
1. "Crée une nouvelle page sur https://example.com"
2. "Crée une deuxième page sur https://huggingface.co"
3. "Liste toutes les pages ouvertes"
4. "Sélectionne la première page"
5. "Ferme la deuxième page"

**Attendu** :
- Deux pages créées
- Liste des pages affichée
- Première page sélectionnée
- Deuxième page fermée

**Critère de succès** : ✅ Gestion multi-pages réussie

---

### Test 12 : Formulaire

**Séquence de prompts** :
1. "Ouvre un site avec un formulaire de contact"
2. "Prends un snapshot pour identifier les champs"
3. "Remplis le formulaire avec fill_form"
4. "Soumets le formulaire"

**Attendu** :
- Page avec formulaire ouverte
- Snapshot retourné avec uid des champs
- Formulaire rempli
- Formulaire soumis

**Critère de succès** : ✅ Formulaire rempli et soumis

---

## CHECKPOINT DE VALIDATION

### Critères de succès
- ✅ Le serveur FastAPI démarre sans erreur
- ✅ Chrome DevTools MCP est chargé avec 26 outils
- ✅ Les logs affichent les outils Chrome DevTools disponibles
- ✅ L'agent peut naviguer vers une URL
- ✅ L'agent peut prendre un snapshot de la page
- ✅ L'agent peut exécuter du JavaScript
- ✅ L'agent peut prendre un screenshot
- ✅ L'agent peut gérer plusieurs pages
- ✅ L'agent peut remplir des formulaires
- ✅ Le client MCP se ferme proprement à l'arrêt

### Commit message
```
feat(tools): tool-10 mcp chrome devtools

- Ajout de la dépendance MCP (smolagents[litellm,mcp], mcp>=0.9.0)
- Intégration de Chrome DevTools MCP via ToolCollection.from_mcp()
- Ajout de lifespan FastAPI pour gérer le cycle de vie du client MCP
- 26 outils disponibles : navigation, input automation, debugging, etc.
- Fallback silencieux si Chrome DevTools MCP ne peut pas être chargé
```

---

## GESTION DES ERREURS

### Erreurs de démarrage

| Erreur | Cause | Solution |
|--------|-------|----------|
| `npx: command not found` | Node.js non installé | Installer Node.js 20.19+ |
| `TimeoutError` | npx trop lent au premier lancement | Augmenter timeout à 90s dans lifespan |
| `Chrome not found` | Chrome non installé | Installer Chrome stable |
| `PermissionError` | Droits insuffisants | Exécuter en admin (Windows) |

### Erreurs d'exécution

| Erreur | Cause | Solution |
|--------|-------|----------|
| `RuntimeError: Event loop is closed` | Client MCP fermé incorrectement | Vérifier lifespan |
| `ValueError: I/O operation on closed pipe` | Client MCP fermé incorrectement | Vérifier lifespan |
| `TimeoutError` | Chrome trop lent à répondre | Augmenter timeout dans navigate_page() |

---

## PROCHAINES ÉTAPES

Une fois TOOL-10 validé :
1. Mettre à jour `PROGRESS.md` avec le statut DONE
2. Mettre à jour `LEARNING.md` avec les découvertes techniques
3. Passer au MODULE 4 : Canal Nextcloud Talk
4. Implémenter les modules restants (Cron & Proactivité, Z.ai + Health Check, Identity & Persona)

---

## RÉFÉRENCES

- smolagents MCP : https://huggingface.co/docs/smolagents/tutorials/mcp
- Chrome DevTools MCP : https://github.com/ChromeDevTools/chrome-devtools-mcp
- IMPLEMENTATION-TOOLS.md : Spécifications TOOL-10
- AGENTS.md : Règles impératives pour l'IA de codage
- LEARNING.md : Découvertes my-claw
