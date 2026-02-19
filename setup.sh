#!/bin/bash
# setup.sh — Initialisation du projet my-claw
# Usage : bash setup.sh

set -e

echo "🦞 my-claw — Setup"
echo "=================="

# Vérifications prérequis
echo ""
echo "→ Vérification des prérequis..."

command -v node >/dev/null 2>&1 || { echo "❌ Node.js manquant — https://nodejs.org"; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "❌ uv manquant — https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
command -v ollama >/dev/null 2>&1 || { echo "⚠️  Ollama non trouvé — https://ollama.ai (optionnel pour tester)"; }

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 22 ]; then
  echo "⚠️  Node.js $NODE_VERSION détecté — version 22+ recommandée"
fi

echo "✅ Prérequis OK"

# Variables d'env
echo ""
echo "→ Configuration des variables d'env..."
if [ ! -f .env.local ]; then
  cp .env.example .env.local
  echo "✅ .env.local créé — REMPLIR les valeurs avant de continuer"
else
  echo "✅ .env.local déjà présent"
fi

# Gateway
echo ""
echo "→ Installation gateway (Next.js)..."
if [ ! -d gateway/node_modules ]; then
  cd gateway && npm install && cd ..
  echo "✅ Dépendances Next.js installées"
else
  echo "✅ node_modules déjà présent"
fi

# Agent Python — uv
echo ""
echo "→ Installation agent (Python / uv)..."
cd agent
uv sync
cd ..
echo "✅ Environnement Python créé via uv"

# Ollama model
echo ""
echo "→ Vérification modèle Ollama..."
if command -v ollama >/dev/null 2>&1; then
  if ollama list 2>/dev/null | grep -q "qwen3"; then
    echo "✅ qwen3 disponible"
  else
    echo "⚠️  qwen3 non trouvé — lancer : ollama pull qwen3:14b (9.3GB)"
  fi
fi

echo ""
echo "🎉 Setup terminé !"
echo ""
echo "Prochaines étapes :"
echo "  1. Remplir .env.local avec vos valeurs"
echo "  2. cd gateway && npx prisma migrate dev --name init"
echo "  3. cd gateway && npm run dev                    → http://localhost:3000"
echo "  4. cd agent && uv run uvicorn main:app --reload → http://localhost:8000"
echo "  5. cd agent && uv run python gradio_app.py      → http://localhost:7860"
echo "  6. Valider le CHECKPOINT 0 dans AGENTS.md"
