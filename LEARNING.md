# LEARNING.md — Découvertes my-claw

> Document de mémoire technique pour le développement my-claw
> À mettre à jour après chaque module/feature implémenté

---

## TOOL-1 — FileSystemTool (2025-02-19)

### Structure smolagents Tool
- Classe Tool nécessite les attributs: `name`, `description`, `inputs`, `output_type`
- La méthode `forward(*args, **kwargs)` implémente la logique
- `inputs` est un dict avec les paramètres: `{"param_name": {"type": "string", "description": "...", "nullable": True|False}}`
- Les types autorisés: "string", "integer", "boolean", "number", "array", "object", "any", "image", "audio"

### Validation Tool
- smolagents valide automatiquement que:
  - Les paramètres de `forward()` correspondent aux clés de `inputs`
  - Le type de retour correspond à `output_type`
  - `name` est un identifiant Python valide (pas de mot clé réservé)

### Imports dans forward()
- Règle AGENTS.md: imports dans `forward()` pour les librairies externes (pas stdlib)
- Pour pathlib, logging: OK au top-level car stdlib
- Pour les packages externes comme pyautogui, pyperclip: importer dans `forward()`

### Opérations implémentées
- **read**: Lecture fichier texte UTF-8
- **write**: Écriture fichier (remplace contenu, crée dossiers parents)
- **create**: Création fichier (échoue si existe déjà)
- **delete**: Suppression fichier ou dossier vide
- **list**: Listing contenu dossier
- **move**: Déplacement/renommage
- **search**: Recherche par pattern glob

### Gestion erreurs
- Exceptions capturées: FileNotFoundError, PermissionError, IsADirectoryError, NotADirectoryError, OSError
- Retour: message préfixé par "ERROR:" pour que l'agent smolagents comprenne
- Logging: logger.error() pour debug backend, message user dans return

### Test plan
Selon IMPLEMENTATION-TOOLS.md, tests à effectuer via Gradio avec modèle "reason" (glm-4.7):
1. Créer fichier: "Crée le fichier C:\tmp\myclaw_test.txt avec le contenu : Test TOOL-1 OK"
2. Lire fichier: "Lis le fichier C:\tmp\myclaw_test.txt"
3. Lister dossier: "Liste le contenu du dossier C:\tmp\"
4. Déplacer: "Déplace C:\tmp\myclaw_test.txt vers C:\tmp\myclaw_test_renamed.txt"
5. Supprimer: "Supprime C:\tmp\myclaw_test_renamed.txt"

### Résultats tests
- ✅ Tous les tests passés avec succès
- ✅ FileSystemTool fonctionne correctement sur Windows

---

## TOOL-2 — OsExecTool (2025-02-19)

### Implémentation
- Classe OsExecTool avec paramètres:
  - command (str): commande PowerShell à exécuter
  - timeout (int, optionnel): timeout en secondes, défaut 30
- Utilise subprocess.run() avec shell=False
- Lance via ["powershell", "-Command", command]
- Capture stdout et stderr en UTF-8
- Retourne un dict formaté: stdout, stderr, returncode

### Test plan
Selon IMPLEMENTATION-TOOLS.md, tests à effectuer via Gradio avec modèle "reason" (glm-4.7):
1. "Exécute la commande PowerShell : Get-Date"
2. "Liste les 5 premiers processus avec Get-Process | Select-Object -First 5"
3. "Crée le dossier C:\tmp\testdir_powershell via PowerShell"
4. "Supprime le dossier C:\tmp\testdir_powershell"

### Résultats tests
- ✅ Tous les tests passés avec succès
- ✅ OsExecTool fonctionne correctement sur Windows
- ✅ PowerShell intégré correctement

---

## TOOL-3 — ClipboardTool (2025-02-19)

### Implémentation
- Classe ClipboardTool avec paramètres:
  - operation (str): "read" ou "write"
  - content (str, optionnel): texte à écrire (requis si operation="write")
- Utilise pyperclip.copy() pour écrire
- Utilise pyperclip.paste() pour lire
- Gère l'exception si pas de gestionnaire de clipboard disponible

### Test plan
Selon IMPLEMENTATION-TOOLS.md, tests à effectuer via Gradio avec modèle "reason" (glm-4.7):
1. "Écris 'Bonjour depuis my-claw !' dans le presse-papier"
2. Vérifier manuellement avec Ctrl+V dans Notepad
3. "Lis le contenu actuel du presse-papier"

### Résultats tests
- ✅ Tous les tests passés avec succès
- ✅ ClipboardTool fonctionne correctement sur Windows
- ✅ pyperclip intégré correctement

---

## MCP Z.ai — Problèmes de compatibilité (2025-02-19)

### Découverte
Les modèles GLM-4.7 (glm-4.7 et glm-4.7-flash) génèrent du code avec des balises HTML/XML (`</code`) qui causent des erreurs de syntaxe Python dans smolagents.

### Tests effectués
1. **API Z.ai directe** : ✅ Fonctionne correctement avec PowerShell/curl
   - La clé API est valide
   - L'API Z.ai est accessible
   - Le modèle glm-4.7 répond correctement

2. **LiteLLM + smolagents** : ❌ Échec
   - Le modèle génère du code avec des balises `</code`
   - smolagents ne peut pas parser ce code
   - Erreur: "SyntaxError: invalid syntax (<unknown>, line X)"

3. **Configurations testées** :
   - `custom_llm_provider="openai"` : ❌ Pas de changement
   - `extra_body={"think": False}` : ❌ Pas de changement
   - `max_steps=10` : ❌ Pas de changement

### Conclusion
Les modèles GLM-4.7 ne sont pas compatibles avec smolagents dans leur configuration actuelle. Le problème vient du format de réponse des modèles qui inclut des balises HTML/XML dans le code généré.

### Actions prises
- ❌ Suppression de tous les composants MCP Z.ai
- ❌ Suppression des modèles "code" (glm-4.7-flash) et "reason" (glm-4.7)
- ❌ Suppression de la fonction load_mcp_tools()
- ❌ Suppression des variables d'environnement ZAI_API_KEY et ZAI_BASE_URL
- ✅ Conservation des modèles Ollama (fast, smart, main) qui fonctionnent correctement

### État final
- ✅ Tools locaux (FileSystemTool, OsExecTool, ClipboardTool) opérationnels
- ✅ Modèles Ollama (qwen3:4b, qwen3:8b, qwen3:14b) opérationnels
- ❌ MCP Z.ai (TOOL-4, 5, 6, 7, 10) désactivés temporairement
- 🔄 Continuation avec TOOL-8 (ScreenshotTool) et TOOL-9 (MouseKeyboardTool)

### Note pour le futur
- Réévaluer la compatibilité smolagents + GLM-4.7 lors de futures versions
- Explorer d'autres options MCP (OpenAI, Anthropic, etc.)
- Considérer l'utilisation d'autres modèles cloud compatibles avec smolagents

### Découverte technique
- pathlib.Path utilisé pour tous les chemins Windows
- encode="utf-8" par défaut pour compatibilité
- path_obj.parent.mkdir(parents=True, exist_ok=True) crée dossiers parents automatiquement
- `path_obj.touch()` crée fichier vide
- `path_obj.iterdir()` itère sur contenu dossier
- `path_obj.glob(pattern)` pour recherche glob

---

## MODULES TERMINÉS

- MODULE 0: Socle & Configuration
- MODULE 1: Cerveau Python (sans outils)
- MODULE 2: Mémoire Prisma 7 + SQLite
- MODULE 3: WebChat

---

## MODULES EN COURS

- TOOL-1: FileSystemTool ✅ implémenté, testé et validé
- TOOL-2: OsExecTool (PowerShell) ✅ implémenté, testé et validé
- TOOL-3: ClipboardTool ✅ implémenté, testé et validé
- TOOL-4: MCP Web Search Z.ai ❌ désactivé - problèmes de compatibilité
- TOOL-5: MCP Web Reader Z.ai ❌ désactivé - problèmes de compatibilité
- TOOL-6: MCP Zread GitHub ❌ désactivé - problèmes de compatibilité
- TOOL-7: MCP Vision GLM-4.6V ❌ désactivé - problèmes de compatibilité
- TOOL-8: ScreenshotTool
- TOOL-9: MouseKeyboardTool
- TOOL-10: MCP Chrome Playwright ❌ désactivé - problèmes de compatibilité

---

## DÉCISIONS TECHNIQUES

### Stack choisie
- Next.js 16 + Prisma 7 (gateway)
- Python + uv + FastAPI (agent)
- smolagents 1.9+ (CodeAgent)
- Ollama (qwen3:4b/8b/14b local)
- Z.ai GLM-4.7 (cloud, optionnel)

### Patterns établis
- Tools smolagents: sous-classe Tool, pas décorateur @tool
- Imports des librairies externes dans `forward()`
- Validation max_steps=5 pour tâches simples, 10 pour pilotage PC complexe
- Fallback silencieux sur Ollama si ZAI_API_KEY absent

### Environnement Windows
- Chemins Windows acceptés (backslashes et forward slashes)
- PowerShell pour exécution OS
- pyautogui.FAILSAFE=True pour contrôle souris/clavier
- Dossier temporaire: C:\tmp\myclawshots\ pour screenshots

---

## RÉFÉRENCES

- smolagents Tool: https://huggingface.co/docs/smolagents/tutorials/custom_tools
- smolagents MCP: https://huggingface.co/docs/smolagents/tutorials/mcp
- Prisma 7 Config: https://pris.ly/d/config-datasource
- Z.ai GLM-4.7: https://open.bigmodel.cn/dev/api
