# my-claw 🦞

Un assistant personnel minimaliste, auto-hébergé et respectueux de la vie privée, conçu pour Windows.

**my-claw** est un assistant hybride puissant qui combine une interface moderne en Next.js 16 avec un "cerveau" Python propulsé par `smolagents`. Il est conçu pour fonctionner entièrement sur votre propre matériel, garantissant que vos données ne quittent jamais votre machine, sauf si vous choisissez explicitement d'utiliser des modèles cloud optionnels.

---

## ✨ Fonctionnalités Clés

- 🛡️ **Privacy-First** : Conçu pour fonctionner à 100% localement avec Ollama.
- 🪟 **Intégration Windows Profonde** : Accès complet au système de fichiers, à PowerShell, au presse-papier et à l'écran.
- 🧠 **Cerveau Hybride** : Utilise `smolagents` pour une utilisation intelligente des outils et l'exécution de code.
- 🌐 **Interface Web Moderne** : Interface propre et réactive construite avec Next.js 16 et Tailwind CSS 4.
- 🔌 **Outils Extensibles** : Supporte les outils Python personnalisés et les intégrations Model Context Protocol (MCP).
- 🤖 **Support Multi-Modèles** : Support natif pour Qwen3, Gemma3 et GLM-4.7 (via Z.ai).

---

## 🚀 Démarrage Rapide

### Prérequis

- **Node.js** : 25.x ou supérieur
- **uv** : [Gestionnaire de paquets Python](https://docs.astral.sh/uv/)
- **Python** : 3.14.x ou supérieur
- **Ollama** : Pour l'accélération locale des LLM
- **Windows OS** : Recommandé (pour le support natif des outils)

### Installation

Le projet inclut un script d'installation automatique pour plus de commodité :

```powershell
./setup.ps1
```

Ce script va :
1. Initialiser l'environnement de la Gateway (Next.js) et ses dépendances.
2. Configurer l'environnement de l'Agent (Python) via `uv`.
3. Configurer la base de données SQLite avec Prisma 7.4.
4. Préparer vos fichiers `.env`.

---

## 🏗️ Architecture

Le système est divisé en deux composants principaux : la **Gateway** (gestion de l'UI et de la mémoire) et l'**Agent** (gestion du raisonnement et des outils).

```mermaid
graph TD
    User([Utilisateur])
    WebChat[Next.js 16 WebChat]
    NCTalk[Nextcloud Talk]

    subgraph Gateway ["Gateway (Next.js 16)"]
        API_Chat[API /api/chat]
        API_Webhook[API /api/nc-talk]
        Prisma[Prisma 7 + SQLite]
    end

    subgraph Agent ["Agent (Python 3.14)"]
        FastAPI[Serveur FastAPI]
        Smolagents[smolagents CodeAgent]
        Tools[Outils Windows & MCP]
    end

    subgraph Local ["Services Locaux"]
        Ollama[Ollama - Qwen3/Gemma3]
    end

    subgraph Cloud ["Externe (Optionnel)"]
        ZAI[Z.ai GLM-4.7]
    end

    User --> WebChat
    User --> NCTalk
    WebChat --> API_Chat
    NCTalk --> API_Webhook
    API_Chat --> Prisma
    API_Chat --> FastAPI
    API_Webhook --> FastAPI
    FastAPI --> Smolagents
    Smolagents --> Tools
    Smolagents --> Ollama
    Smolagents --> ZAI
    Tools --> Windows[Windows OS]
    Tools --> Chrome[Chrome DevTools]
```

---

## ⚙️ Configuration des Modèles

### Modèle par Défaut

Le modèle par défaut pour le manager et tous les sous-agents est **glm-4.7 (reason)** si `ZAI_API_KEY` est configuré, sinon **qwen3:8b** (local).

Vous pouvez changer le modèle par défaut en définissant la variable d'environnement `DEFAULT_MODEL` dans `agent/.env` :

```bash
# Utiliser glm-4.7 (recommandé)
DEFAULT_MODEL=reason

# Utiliser glm-4.7-flash (plus rapide)
DEFAULT_MODEL=code

# Utiliser qwen3:8b (local, gratuit)
DEFAULT_MODEL=main
```

### Modèles Disponibles

| Catégorie | Modèle | Type | Description |
|-----------|--------|------|-------------|
| reason | glm-4.7 | Cloud | Raisonnement profond (défaut avec clé API) |
| code | glm-4.7-flash | Cloud | Codage rapide |
| main | qwen3:8b | Local | Modèle principal (défaut sans clé API) |
| vision | qwen3-vl:8b | Local | Vision locale |
| smart | qwen3:14b / 8b | Local | Assistant intelligent quotidien (14b recommandé) |
| fast | gemma3:4b / latest | Local | Réponses ultra-rapides |

### Choix Intelligent du Modèle

Le système détecte automatiquement les capacités de votre matériel. Pour un usage local :
- **Haut de gamme (16GB+ VRAM)** : Utilisez `qwen3:14b` pour les tâches `main` et `smart`.
- **Milieu de gamme (8GB VRAM)** : Utilisez `qwen3:8b` pour une expérience équilibrée.
- **Entrée de gamme / Vitesse** : Utilisez `gemma3:4b` ou `Nanbeige4.1-3B` pour des réponses quasi-instantanées.

### Configuration Z.ai (optionnel)

Pour utiliser les modèles cloud GLM-4.7, configurez votre clé API dans `agent/.env` :

```bash
ZAI_API_KEY=sk-your-api-key
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
```

Sans clé API, le système bascule automatiquement sur les modèles locaux (Qwen3).

---

## 🛠️ Capacités des Outils

Statut actuel : **10/11 outils cœurs implémentés**

| Outil | Statut | Description |
|-------|--------|-------------|
| **Système de Fichiers** | ✅ | Lire, écrire, déplacer, supprimer et rechercher des fichiers sur Windows. |
| **Exécution OS** | ✅ | Exécuter des commandes et des scripts PowerShell. |
| **Presse-papier** | ✅ | Accéder et modifier le presse-papier Windows. |
| **Recherche Web** | ✅ | Recherche web en temps réel via DuckDuckGo (illimité). |
| **Lecteur Web** | ✅ | Extraction de contenu et conversion en markdown depuis des URLs. |
| **Vision** | ✅ | Analyse d'images locale et OCR via `qwen3-vl`. |
| **Capture d'Écran** | ✅ | Capturer l'écran entier ou des régions spécifiques. |
| **Souris & Clavier** | ✅ | Contrôle direct des entrées OS via pyautogui. |
| **Grounding GUI** | ✅ | Localisation d'éléments UI avec qwen3-vl. |
| **Chrome DevTools** | ✅ | Automatisation complète du navigateur via MCP (Puppeteer). |
| **GitHub** | ⏳ | Analyse de dépôts et lecture de fichiers (Roadmap). |

---

## 📅 Roadmap

### Module 0 : Fondations ✅
- Structure du projet, Next.js 16, Python `uv`, et intégration Ollama.

### Module 1 : Cerveau Python ✅
- Intégration `smolagents`, serveur FastAPI, et interface de développement Gradio.

### Module 2 : Mémoire (Prisma 7.4) ✅
- Persistance SQLite pour les conversations et les paramètres.

### Module 3 : WebChat ✅
- Interface de streaming, SSE, et authentification sécurisée.

### Module 4 : Intégration Nextcloud Talk ✅
- Support de bot via webhooks HMAC-SHA256 pour l'interaction mobile.
- Upload WebDAV des screenshots pour affichage des images dans le chat.

### Module 5 : Tâches Proactives ⏳
- Exécution de jobs basés sur cron et notifications proactives.

### Module 6 : Identité & Persona ⏳
- Prompts système personnalisables et réglages de la personnalité de l'assistant.

---

## 📚 Documentation

Pour des informations plus détaillées, veuillez vous référer aux fichiers suivants :

- 📊 [STATUS.md](STATUS.md) — Vue d'ensemble rapide du projet.
- 📋 [PROGRESS.md](PROGRESS.md) — Points d'avancement détaillés du développement.
- 🗺️ [PLAN.md](PLAN.md) — Architecture et objectifs à long terme.
- 🏗️ [AGENTS.md](AGENTS.md) — Guide technique pour les développeurs et agents.
- 🎯 [agent/SKILLS.md](agent/SKILLS.md) — Patterns de code spécifiques à l'agent.

---

## 🛠️ Stack Technique

- **Frontend** : Next.js 16.1, React 19, Tailwind CSS 4
- **Base de Données** : SQLite avec Prisma 7.4
- **Framework Agent** : [smolagents](https://github.com/huggingface/smolagents)
- **API** : FastAPI (Python)
- **Environnement** : Node.js 25+, Python 3.14.2 (via `uv`)
- **LLM** : Ollama (Local), Z.ai (Cloud/Optionnel)

---

## 📄 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) file for details.

---

Construit avec 🦞 et 🐍 pour une meilleure expérience d'IA personnelle.
