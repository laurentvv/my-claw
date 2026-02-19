# setup.ps1 — Installation complète my-claw sur Windows (PowerShell)
# Usage : .\setup.ps1
# Prérequis : Node.js 22+, uv, Ollama, Git

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "my-claw — Setup Windows" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan

# ── Vérification prérequis ──────────────────────────────────────────────────

Write-Host ""
Write-Host "Vérification des prérequis..." -ForegroundColor Yellow

$missing = @()

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    $missing += "Node.js 22+ — https://nodejs.org"
}
else {
    $nodeVersion = (node -v).TrimStart('v').Split('.')[0]
    if ([int]$nodeVersion -lt 22) {
        Write-Warning "Node.js $nodeVersion détecté — version 22+ recommandée"
    }
    else {
        Write-Host "  Node.js $(node -v)" -ForegroundColor Green
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    $missing += "uv — https://docs.astral.sh/uv/getting-started/installation/"
}
else {
    Write-Host "  uv $(uv --version)" -ForegroundColor Green
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Warning "Ollama non trouvé — https://ollama.ai (requis pour les modèles locaux)"
}
else {
    Write-Host "  Ollama disponible" -ForegroundColor Green
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Prérequis manquants :" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "  Prérequis OK" -ForegroundColor Green

# ── Variables d'environnement ───────────────────────────────────────────────

Write-Host ""
Write-Host "Configuration des variables d'env..." -ForegroundColor Yellow

if (-not (Test-Path "gateway\.env.local")) {
    Copy-Item "gateway\.env.example" "gateway\.env.local"
    Write-Host "  gateway/.env.local créé — REMPLIR avant de continuer" -ForegroundColor Yellow
}
else {
    Write-Host "  gateway/.env.local déjà présent" -ForegroundColor Green
}

if (-not (Test-Path "agent\.env")) {
    if (Test-Path "agent\.env.example") {
        Copy-Item "agent\.env.example" "agent\.env"
        Write-Host "  agent/.env créé" -ForegroundColor Green
    }
}
else {
    Write-Host "  agent/.env déjà présent" -ForegroundColor Green
}

# ── Gateway Next.js ─────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Installation gateway (Next.js)..." -ForegroundColor Yellow

Push-Location gateway
if (-not (Test-Path "node_modules")) {
    npm install
    Write-Host "  Dépendances Node.js installées" -ForegroundColor Green
}
else {
    Write-Host "  node_modules déjà présent" -ForegroundColor Green
}

# Vérifier si la migration a déjà été faite
if (-not (Test-Path "prisma\dev.db")) {
    Write-Host "  Migration Prisma..." -ForegroundColor Yellow
    npx prisma migrate dev --name init
    Write-Host "  Base de données créée" -ForegroundColor Green
}
else {
    Write-Host "  Base de données déjà présente" -ForegroundColor Green
}
Pop-Location

# ── Agent Python ────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Installation agent (Python / uv)..." -ForegroundColor Yellow

Push-Location agent
uv sync
Write-Host "  Environnement Python créé via uv" -ForegroundColor Green
Pop-Location

# ── Modèles Ollama ──────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Vérification modèles Ollama..." -ForegroundColor Yellow

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    $ollamaModels = ollama list 2>$null
    if ($ollamaModels -match "qwen3:14b") {
        Write-Host "  qwen3:14b disponible" -ForegroundColor Green
    }
    else {
        Write-Warning "  qwen3:14b non trouvé — lancer : ollama pull qwen3:14b"
    }
    if ($ollamaModels -match "qwen3:8b") {
        Write-Host "  qwen3:8b disponible" -ForegroundColor Green
    }
    if ($ollamaModels -match "qwen3:4b") {
        Write-Host "  qwen3:4b disponible" -ForegroundColor Green
    }
}

# ── Résumé ──────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Setup terminé !" -ForegroundColor Green
Write-Host ""
Write-Host "Prochaines étapes :" -ForegroundColor Cyan
Write-Host "  1. Remplir gateway\.env.local avec vos valeurs"
Write-Host "  2. Terminal 1 : cd gateway && npm run dev        -> http://localhost:3000"
Write-Host "  3. Terminal 2 : cd agent && uv run uvicorn main:app --reload  -> http://localhost:8000"
Write-Host "  4. Terminal 3 : cd agent && uv run python gradio_app.py       -> http://localhost:7860"
Write-Host "  5. Lire PROGRESS.md pour connaître le module en cours"
Write-Host ""
