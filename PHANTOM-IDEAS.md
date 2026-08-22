# Analyse de Phantom & Pistes d'Amélioration pour my-claw 🦞

Ce document résume les fonctionnalités clés du projet [ghostwright/phantom](https://github.com/ghostwright/phantom) et propose des idées concrètes pour améliorer l'architecture de **my-claw** tout en respectant sa philosophie 100% locale.

## 1. Qu'est-ce que Phantom ?

Phantom est un assistant IA (agent) conçu pour fonctionner sur **sa propre machine virtuelle dédiée** plutôt que de partager les ressources de la machine de l'utilisateur.

### Concepts Clés :
- **Self-Evolution (Auto-évolution) :** L'agent observe les conversations, critique ses propres performances, et met à jour sa propre configuration (instructions, rôles) de manière autonome après chaque session. Le "Jour 30 Phantom" est meilleur que le "Jour 1".
- **Mémoire Persistante Vectorielle :** Utilise une base vectorielle (Qdrant) avec 3 niveaux de mémoire. Ce qui est dit le lundi est retenu pour le mercredi sans avoir besoin de le répéter.
- **Dynamic Tools (Outils Dynamiques) :** L'agent peut coder et enregistrer ses propres outils (MCP tools) au moment de l'exécution, et ces outils survivent aux redémarrages.
- **Machine dédiée :** Il interagit avec le monde extérieur via un serveur MCP, permettant à d'autres agents (comme Claude Code) de s'y connecter comme à une API.

---

## 2. Pistes d'implémentation pour my-claw (Local-First)

Voici comment nous pourrions adapter ces concepts puissants à l'architecture de **my-claw**, en utilisant exclusivement nos ressources locales (Ollama, smolagents, Prisma).

### Idée A : Le moteur de "Self-Evolution" Local (Module Identité V2)
**Le concept Phantom :** L'agent modifie ses propres prompts système en fonction de ce qu'il apprend sur l'utilisateur.
**Adaptation my-claw :**
- **Implémentation :** Ajouter une étape "Post-Session Reflection". À la fin d'une conversation importante (ou via le futur Module 5 Cron), le Manager (glm-4.7 ou qwen3:14b) analyse les interactions récentes pour en extraire des "Principes" (ex: "L'utilisateur préfère le code Python commenté en français").
- **Stockage :** Ces principes sont sauvegardés dans la base SQLite via Prisma (nouvelle table `UserPreference` ou `AgentPrinciple`).
- **Utilisation :** Lors du démarrage d'une nouvelle session, ces principes sont injectés dynamiquement dans le `system_prompt` du Manager.

### Idée B : Outils générés dynamiquement (Dynamic Skills)
**Le concept Phantom :** L'agent crée ses outils MCP au vol.
**Adaptation my-claw :**
- **État actuel :** Nous avons déjà un dossier `agent/tools/` avec des outils statiques.
- **Implémentation :** Permettre à l'agent d'écrire de nouveaux scripts `.py` dans un dossier `agent/tools/dynamic/`.
- **Mécanisme :** Lors du démarrage de FastAPI (ou via un rechargement à chaud), smolagents lit ce dossier et instancie dynamiquement les nouveaux sous-classes de `Tool`. L'agent pourrait utiliser le `TOOL-1` (Fichiers) pour écrire le code de son nouvel outil, puis appeler un nouvel outil `TOOL-12 (Register Tool)` pour le charger en mémoire sans redémarrer.

### Idée C : Mémoire Vectorielle Légère (Déblocage V2-E)
**Le concept Phantom :** Utilisation de Qdrant pour la mémoire à long terme.
**Adaptation my-claw :**
- Vous avez déjà prévu ce point (V2-E : Mémoire vectorielle) avec `nomic-embed-text` sur Ollama.
- **Implémentation :** Plutôt que d'ajouter un conteneur externe lourd comme Qdrant, nous pourrions utiliser **SQLite avec l'extension `sqlite-vec`** (ou une bibliothèque Python locale comme ChromaDB/FAISS) directement intégrée dans le workflow FastAPI.
- **Flux :** Le texte de l'utilisateur est vectorisé via Ollama (`nomic-embed-text`), puis stocké. Avant chaque réponse, on fait une recherche de similarité pour retrouver le contexte des jours précédents.

### Idée D : L'Agent comme Serveur MCP
**Le concept Phantom :** L'agent lui-même est un serveur MCP auquel d'autres outils peuvent se connecter.
**Adaptation my-claw :**
- **État actuel :** my-claw consomme des serveurs MCP (via `TOOL-10 Chrome DevTools` et le futur `TOOL-6 Zread`).
- **Implémentation :** Exposer les capacités de my-claw (comme son pilotage PC `pc_control_agent`) en tant que serveur MCP. Cela permettrait à des IDE locaux (comme Cursor ou Windsurf) de demander à my-claw d'effectuer des tâches sur l'OS directement via le protocole MCP.

## 3. Recommandations pour la Roadmap

Si ces idées vous plaisent, voici comment les intégrer logiquement dans l'actuel `PLAN.md` :

1. **Court terme (Facile) :** Ajouter la "Post-Session Reflection" (Idée A) dans le **Module 7 (Identity & Persona)**. C'est facile à faire avec Prisma et ne nécessite pas de nouveaux modèles.
2. **Moyen terme (Modéré) :** Débloquer le **Module V2-E (Mémoire vectorielle)** en utilisant ChromaDB local ou sqlite-vec, combiné à Ollama `nomic-embed-text` (Idée C).
3. **Long terme (Complexe) :** Implémenter les "Dynamic Tools" (Idée B) après avoir terminé tous les modules de base, car cela nécessite des garde-fous de sécurité importants pour que l'agent ne casse pas son propre code.
