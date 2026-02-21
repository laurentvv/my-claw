# Comparatif — OpenClaw vs Mon Assistant Minimaliste

> Dernière mise à jour : Février 2026  
> OpenClaw : ~200k ⭐ GitHub, racheté par OpenAI (Peter Steinberger)

---

## Vue d'ensemble

| | OpenClaw 🦞 | Mon Assistant ✅ |
|---|---|---|
| **Architecture** | Gateway Node.js persistant + daemon système | Next.js 16 tout-en-un |
| **Installation** | CLI wizard + launchd/systemd daemon | `./setup.ps1` |
| **Utilisateurs** | Mono (mais complexe multi-agent) | Mono — assumé et simplifié |
| **Vie privée** | Variable selon config | Machine dédiée, privacy-first |
| **Modèles** | Cloud-first (Claude, GPT, xAI Grok...) | Local-first (Ollama) + Z.ai opt. |
| **Complexité code** | ~200k lignes TypeScript | ~2-3k lignes cible |
| **Dépendances npm** | 100+ | < 15 |

---

## Canaux de Communication

| Canal | OpenClaw | Mon Assistant | Notes |
|---|---|---|---|
| **WebChat** | ✅ | ✅ | |
| **WhatsApp** | ✅ via Baileys (hack non-officiel) | ❌ non voulu | |
| **Telegram** | ✅ | ❌ non voulu | |
| **Nextcloud Talk** | ❌ | ✅ | Avantage privacy |
| **Discord** | ✅ | ❌ non voulu | |
| **Slack** | ✅ | ❌ non voulu | |
| **Signal** | ✅ | ❌ non voulu | |
| **iMessage** | ✅ via BlueBubbles (macOS only) | ❌ | |
| **Google Chat** | ✅ | ❌ | |
| **Microsoft Teams** | ✅ | ❌ | |
| **Matrix** | ✅ | ❌ | |
| **Voice (parole)** | ✅ ElevenLabs (macOS/iOS/Android) | ❌ hors scope | |

**Verdict canaux** : OpenClaw = 13 canaux. Mon assistant = 3 canaux choisis. C'est voulu.

---

## Modèles LLM

| Feature | OpenClaw | Mon Assistant |
|---|---|---|
| **Anthropic Claude** | ✅ (Opus 4.6, Sonnet...) | ❌ (optionnel à ajouter) |
| **OpenAI GPT** | ✅ | ❌ (optionnel à ajouter) |
| **xAI Grok** | ✅ | ❌ |
| **Z.ai GLM-4.7** | ❌ | ✅ |
| **Ollama / local** | ✅ (supporté) | ✅ **prioritaire** |
| **Failover auto** | ✅ sophistiqué | ✅ simple (Z.ai → Ollama) |
| **Routing par tâche** | Manuel / config | ✅ auto (fast/smart/code/reason) |
| **Thinking mode** | ✅ | ✅ GLM-4.7 |
| **100% offline** | ⚠️ possible mais pas défaut | ✅ **mode par défaut** |

---

## Mémoire & Contexte

| Feature | OpenClaw | Mon Assistant | Décision |
|---|---|---|---|
| **Historique conversations** | ✅ persistant | ✅ Prisma SQLite | ✅ À faire |
| **Mémoire long-terme** | ✅ Voyage AI (vectoriel) | ❌ | 🤔 Voir plus bas |
| **Résumé automatique** | ✅ | ❌ | 🟡 Simple à ajouter |
| **Sessions multi-agents** | ✅ routing sophistiqué | ❌ mono-agent | ❌ Non voulu |
| **Context glissant** | ✅ cap automatique | ✅ 20 derniers messages | ✅ À faire |
| **Identity files** | ✅ personnalité persistante | ✅ system prompt en DB | ✅ À faire |

### 🤔 Sur la mémoire vectorielle (Voyage AI)
OpenClaw utilise des embeddings pour retrouver des souvenirs pertinents dans de longues histoires de conversation. C'est puissant mais lourd (service externe ou modèle d'embedding local). 

**Pour ton cas** : commencer avec un simple historique glissant (20 messages). Si besoin de mémoire longue durée → ajouter `pgvector` + Ollama embeddings (`nomic-embed-text`) en v2.

---

## Outils & Actions (Tools)

| Outil | OpenClaw | Mon Assistant | Décision |
|---|---|---|---|
| **Recherche web** | ✅ (provider externe) | ✅ Z.ai MCP | ✅ local-first |
| **Browser control** | ✅ Puppeteer headless | ✅ Chrome DevTools | ✅ DONE (v1) |
| **Exécution de code** | ✅ sandbox | ✅ sandbox Node/Python | ⏳ **v2** |
| **Lecture de fichiers** | ✅ | ✅ dossier autorisé | ⏳ **v2** |
| **Création de fichiers** | ✅ (Word, Excel, PPT) | ✅ fichiers simples | ⏳ **v2** |
| **GitHub** | ✅ intégration | ❌ | ❌ hors scope |
| **Gmail / Calendar** | ✅ | ❌ | ❌ hors scope |
| **Spotify / Hue** | ✅ | ❌ | ❌ hors scope |
| **Twitter/X** | ✅ | ❌ | ❌ hors scope |
| **Obsidian** | ✅ | ❌ | 🟡 Voir plus bas |
| **Cron / proactivité** | ✅ heartbeats | ✅ cron DB + crontab | ✅ À faire |
| **50+ intégrations** | ✅ ClawdHub registry | ❌ | ❌ non voulu |

### 🟡 Browser Control — Intéressant ?
OpenClaw pilote un navigateur headless pour scraper, remplir des formulaires, etc. C'est lourd (Puppeteer) mais très utile pour automatiser des tâches web que l'API ne couvre pas.
→ **Décision** : hors scope v1, possible en v2 avec `chrome-devtools-mcp` en option.

### 🟡 Obsidian — Intéressant ?
OpenClaw peut lire/écrire dans un vault Obsidian (notes markdown). Parfait pour un assistant qui mémorise dans tes notes.  
→ **Décision** : très simple à implémenter (lire/écrire des `.md` dans un dossier). À évaluer selon tes besoins de prise de notes.

---

## Infrastructure & Déploiement

| Feature | OpenClaw | Mon Assistant |
|---|---|---|
| **Daemon système** | ✅ launchd/systemd auto | 🟡 pm2 (simple) |
| **Docker** | ✅ (optionnel) | ❌ pas nécessaire |
| **Nix / NixOS** | ✅ module dédié | ❌ |
| **CLI wizard** | ✅ `openclaw onboard` | ❌ setup manuel (simple) |
| **macOS app native** | ✅ | ❌ |
| **iOS / Android** | ✅ nodes | ❌ (WebChat mobile) |
| **Multi-devices** | ✅ réseau de nodes | ❌ mono-serveur |
| **Auto-update** | ✅ `openclaw update` | 🟡 git pull + restart |
| **Health check** | ✅ `openclaw doctor` | ❌ (basique à faire) |
| **Canvas / UI riche** | ✅ interface interactive | ❌ WebChat simple |

---

## Sécurité

| Feature | OpenClaw | Mon Assistant |
|---|---|---|
| **DM pairing** | ✅ code de validation | N/A (mono-user) |
| **Allowlist** | ✅ par canal | ✅ token statique |
| **Vérif signature webhook** | ✅ | ✅ HMAC-SHA256 |
| **Block high-risk tools** | ✅ gateway.tools.deny | À implémenter |
| **Prompt injection** | ✅ protections | 🟡 basique |
| **Audit log** | ✅ | 🟡 ToolLog DB |
| **Chiffrement secrets** | ✅ keychain système | .env.local |

---

## Fonctionnalités Manquantes — Analyse

Voici les features d'OpenClaw absentes de mon assistant, avec recommandation claire :

### 🔴 Non, clairement hors scope
- Telegram, Discord, Slack, Signal, iMessage, Teams, Matrix
- macOS/iOS/Android app native
- Voice (ElevenLabs)
- 50+ intégrations (GitHub, Gmail, Spotify, Twitter...)
- Multi-devices / réseau de nodes
- NixOS module
- Canvas interactif

### 🟡 Peut-être utile, à décider
| Feature | Effort | Valeur | Recommandation |
|---|---|---|---|
| Mémoire vectorielle (pgvector + embeddings) | Moyen | Haute si longues histoires | **v2** — après avoir utilisé l'outil |
| Résumé auto des conversations | Faible | Moyen | **v1.5** — simple prompt |
| Browser control (Chrome DevTools) | Moyen | Haute pour automatisation | ✅ **v1 DONE** |
| Création fichiers (Word/Excel) | Faible | Moyen | **v1.5** — lib simple |
| Lecture vault Obsidian | Très faible | Dépend de toi | **À toi de décider** |
| Health check endpoint | Très faible | Moyen | **v1** — 1 route `/api/health` |
| `pm2` pour daemon | Très faible | Haute | **v1** — juste `ecosystem.config.js` |
| Identity/persona persistante | Faible | Haute | **v1** — system prompt en DB |

### ✅ Déjà prévu dans mon design
- WebChat
- Nextcloud Talk
- Mémoire conversations (Prisma)
- Ollama multi-modèles
- Z.ai GLM-4.7
- Cron / proactivité
- SearXNG local (meilleur que la solution OpenClaw côté privacy)
- Exécution de code sandbox
- Sécurité webhooks HMAC

---

## Score Global

| Dimension | OpenClaw | Mon Assistant |
|---|---|---|
| Richesse fonctionnelle | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Simplicité / maintenabilité | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Vie privée / local-first | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Time-to-first-use | ⭐⭐ (wizard lourd) | ⭐⭐⭐⭐⭐ |
| Extensibilité future | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Coût infra | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Conclusion

OpenClaw est impressionnant mais souffre de sa propre ambition : il veut tout faire pour tout le monde. Mon assistant fait **exactement ce que j'utilise**, rien de plus.

**Points où mon assistant est objectivement meilleur que OpenClaw :**
1. **Nextcloud Talk** (inexistant dans OpenClaw)
2. **100% local par défaut** (Ollama prioritaire, pas cloud)
3. **Privacy by design** (machine dédiée, SearXNG local)
4. **Maintenabilité** (1 dev peut lire tout le code en 1h)
