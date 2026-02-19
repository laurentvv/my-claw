# ============================================================
# setup.ps1 — Script d'initialisation automatique de l'environnement
# my-claw — Assistant personnel self-hosted, privacy-first
# ============================================================
#
# Ce script automatise l'installation et la configuration de tous les
# composants nécessaires au projet my-claw.
#
# PREREQUIS:
#   - Node.js 24+
#   - uv (gestionnaire Python)
#   - Ollama avec Qwen3:14b
#
# USAGE:
#   .\setup.ps1
#
# NOTE: Ce script N'EXÉCUTE PAS les serveurs. Il se contente d'installer
#       et de configurer l'environnement.
#
# ============================================================

# ============================================================
# CONFIGURATION DU SCRIPT
# ============================================================

# Définit le mode d'erreur : arrête le script en cas d'erreur
$ErrorActionPreference = "Stop"

# Définit le niveau de verbosité
$VerbosePreference = "Continue"

# Couleurs pour les messages de sortie
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "Cyan"
$ColorHeader = "Magenta"

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

<#
.SYNOPSIS
    Affiche un message de succès
.PARAMETER Message
    Le message à afficher
#>
function Write-Success {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor $ColorSuccess
}

<#
.SYNOPSIS
    Affiche un message d'avertissement
.PARAMETER Message
    Le message à afficher
#>
function Write-Warning {
    param([string]$Message)
    Write-Host "[⚠] $Message" -ForegroundColor $ColorWarning
}

<#
.SYNOPSIS
    Affiche un message d'erreur
.PARAMETER Message
    Le message à afficher
#>
function Write-Error {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor $ColorError
}

<#
.SYNOPSIS
    Affiche un message d'information
.PARAMETER Message
    Le message à afficher
#>
function Write-Info {
    param([string]$Message)
    Write-Host "[ℹ] $Message" -ForegroundColor $ColorInfo
}

<#
.SYNOPSIS
    Affiche un en-tête de section
.PARAMETER Title
    Le titre de la section
#>
function Write-Header {
    param([string]$Title)
    Write-Host "`n$('-' * 70)" -ForegroundColor $ColorHeader
    Write-Host "  $Title" -ForegroundColor $ColorHeader
    Write-Host "$('-' * 70)`n" -ForegroundColor $ColorHeader
}

<#
.SYNOPSIS
    Vérifie si une commande est disponible
.PARAMETER Command
    La commande à vérifier
.OUTPUTS
    Boolean - True si la commande est disponible, False sinon
#>
function Test-Command {
    param([string]$Command)
    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

<#
.SYNOPSIS
    Exécute une commande avec gestion d'erreurs
.PARAMETER Command
    La commande à exécuter
.PARAMETER Arguments
    Les arguments de la commande
.PARAMETER WorkingDirectory
    Le répertoire de travail
.PARAMETER Description
    Description de l'opération pour les logs
#>
function Invoke-CommandSafe {
    param(
        [string]$Command,
        [string]$Arguments = "",
        [string]$WorkingDirectory = $PSScriptRoot,
        [string]$Description = "Exécution de la commande"
    )
    
    try {
        Write-Info "$Description..."
        
        # Sauvegarder le répertoire courant
        $currentDir = Get-Location
        
        try {
            # Changer vers le répertoire de travail
            Set-Location $WorkingDirectory
            
            # Construire la commande complète
            $fullCommand = if ($Arguments) {
                "$Command $Arguments"
            }
            else {
                $Command
            }
            
            # Exécuter la commande et capturer la sortie
            $output = Invoke-Expression $fullCommand 2>&1
            $exitCode = $LASTEXITCODE
            
            # Vérifier le code de retour
            if ($exitCode -ne 0) {
                throw "La commande a échoué avec le code de sortie $exitCode. Sortie: $output"
            }
            
            Write-Success "$Description terminé avec succès"
            return $true
        }
        finally {
            # Restaurer le répertoire courant
            Set-Location $currentDir
        }
    }
    catch {
        Write-Error "$Description a échoué: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Vérifie la version minimale requise de Node.js
.PARAMETER MinVersion
    La version minimale requise
.OUTPUTS
    Boolean - True si la version est suffisante, False sinon
#>
function Test-NodeVersion {
    param([string]$MinVersion = "24.0.0")
    
    try {
        $versionOutput = node --version 2>&1
        if ($versionOutput -match 'v(\d+\.\d+\.\d+)') {
            $currentVersion = [version]$matches[1]
            $minVersionObj = [version]$MinVersion
            
            if ($currentVersion -ge $minVersionObj) {
                Write-Success "Node.js version $currentVersion détecté (min: $MinVersion)"
                return $true
            }
            else {
                Write-Error "Node.js version $currentVersion détecté mais $MinVersion ou supérieur requis"
                return $false
            }
        }
        else {
            Write-Error "Impossible de déterminer la version de Node.js"
            return $false
        }
    }
    catch {
        Write-Error "Erreur lors de la vérification de Node.js: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Vérifie si Ollama est installé et si le modèle Qwen3 est disponible
.OUTPUTS
    Boolean - True si Ollama et Qwen3 sont disponibles, False sinon
#>
function Test-Ollama {
    try {
        # Vérifier si Ollama est installé
        $ollamaVersion = ollama --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Ollama n'est pas installé ou non accessible"
            return $false
        }
        
        Write-Success "Ollama détecté: $ollamaVersion"
        
        # Vérifier si le modèle qwen3:14b est disponible
        $models = ollama list 2>&1
        if ($models -match "qwen3:14b") {
            Write-Success "Modèle qwen3:14b détecté"
            return $true
        }
        else {
            Write-Warning "Modèle qwen3:14b non détecté. Installez-le avec: ollama pull qwen3:14b"
            return $false
        }
    }
    catch {
        Write-Error "Erreur lors de la vérification d'Ollama: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Génère un token sécurisé aléatoire
.OUTPUTS
    String - Token hexadécimal de 64 caractères
#>
function New-SecureToken {
    # Utiliser .NET pour générer un token sécurisé
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $rng.Dispose()
    return [System.BitConverter]::ToString($bytes).Replace("-", "").ToLower()
}

<#
.SYNOPSIS
    Configure les fichiers d'environnement avec valeurs par défaut
.PARAMETER SourceFile
    Le fichier source (.env.example)
.PARAMETER TargetFile
    Le fichier cible (.env.local)
#>
function Set-EnvironmentFile {
    param(
        [string]$SourceFile,
        [string]$TargetFile
    )
    
    try {
        # Vérifier si le fichier source existe
        if (-not (Test-Path $SourceFile)) {
            Write-Error "Fichier source non trouvé: $SourceFile"
            return $false
        }
        
        # Vérifier si le fichier cible existe déjà
        if (Test-Path $TargetFile) {
            Write-Warning "Le fichier $TargetFile existe déjà. Préservation du fichier existant."
            return $true
        }
        
        # Lire le contenu du fichier source
        $content = Get-Content $SourceFile -Raw
        
        # Générer les tokens sécurisés pour le développement
        $webchatToken = New-SecureToken
        $cronSecret = New-SecureToken
        
        # Remplacer les valeurs vides par des valeurs par défaut pour le développement
        $content = $content -replace 'WEBCHAT_TOKEN=""', "WEBCHAT_TOKEN=`"$webchatToken`""
        $content = $content -replace 'CRON_SECRET=""', "CRON_SECRET=`"$cronSecret`""
        
        # Garder les autres valeurs par défaut (elles sont déjà dans .env.example)
        # DATABASE_URL, AGENT_URL, OLLAMA_BASE_URL, etc. ont déjà des valeurs par défaut
        
        # Écrire le fichier cible
        $content | Out-File -FilePath $TargetFile -Encoding UTF8
        
        Write-Success "Fichier $TargetFile créé avec valeurs par défaut pour le développement"
        Write-Info "Tokens générés automatiquement:"
        Write-Info "  - WEBCHAT_TOKEN: $webchatToken"
        Write-Info "  - CRON_SECRET: $cronSecret"
        
        return $true
    }
    catch {
        Write-Error "Erreur lors de la configuration de l'environnement: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Installe les dépendances npm dans un répertoire
.PARAMETER Directory
    Le répertoire contenant package.json
#>
function Install-NpmDependencies {
    param([string]$Directory)
    
    try {
        $packageJson = Join-Path $Directory "package.json"
        
        if (-not (Test-Path $packageJson)) {
            Write-Warning "Fichier package.json non trouvé dans $Directory - Installation ignorée"
            return $true
        }
        
        Write-Info "Installation des dépendances npm dans $Directory..."
        
        # Installer les dépendances
        $success = Invoke-CommandSafe -Command "npm" -Arguments "install" -WorkingDirectory $Directory -Description "npm install"
        
        if (-not $success) {
            throw "Échec de l'installation des dépendances npm"
        }
        
        return $true
    }
    catch {
        Write-Error "Erreur lors de l'installation des dépendances npm: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Exécute les migrations Prisma
.PARAMETER Directory
    Le répertoire contenant le projet Prisma
#>
function Invoke-PrismaMigrations {
    param([string]$Directory)
    
    try {
        $schemaFile = Join-Path $Directory "prisma" "schema.prisma"
        
        if (-not (Test-Path $schemaFile)) {
            Write-Warning "Fichier schema.prisma non trouvé dans $Directory - Migrations ignorées"
            return $true
        }
        
        Write-Info "Exécution des migrations Prisma dans $Directory..."
        
        # Exécuter les migrations
        $success = Invoke-CommandSafe -Command "npx" -Arguments "prisma migrate dev --name init" -WorkingDirectory $Directory -Description "Prisma migrate dev"
        
        if (-not $success) {
            throw "Échec des migrations Prisma"
        }
        
        return $true
    }
    catch {
        Write-Error "Erreur lors des migrations Prisma: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Installe les dépendances Python avec uv
.PARAMETER Directory
    Le répertoire contenant pyproject.toml
#>
function Install-UvDependencies {
    param([string]$Directory)
    
    try {
        $pyprojectToml = Join-Path $Directory "pyproject.toml"
        
        if (-not (Test-Path $pyprojectToml)) {
            Write-Warning "Fichier pyproject.toml non trouvé dans $Directory - Installation ignorée"
            return $true
        }
        
        Write-Info "Installation des dépendances Python avec uv dans $Directory..."
        
        # Installer les dépendances avec uv sync
        $success = Invoke-CommandSafe -Command "uv" -Arguments "sync" -WorkingDirectory $Directory -Description "uv sync"
        
        if (-not $success) {
            throw "Échec de l'installation des dépendances Python"
        }
        
        return $true
    }
    catch {
        Write-Error "Erreur lors de l'installation des dépendances Python: $_"
        return $false
    }
}

<#
.SYNOPSIS
    Affiche les étapes de démarrage après l'installation réussie
#>
function Show-NextSteps {
    Write-Header "ÉTAPES SUIVANTES"
    
    # Afficher les tokens générés
    Write-Host "`nTOKENS GÉNÉRÉS AUTOMATIQUEMENT:" -ForegroundColor $ColorHeader
    Write-Host "=====================================`n" -ForegroundColor $ColorHeader
    
    # Lire les tokens depuis le fichier .env.local
    $gatewayEnvFile = Join-Path $PSScriptRoot "gateway\.env.local"
    if (Test-Path $gatewayEnvFile) {
        $envContent = Get-Content $gatewayEnvFile -Raw
        if ($envContent -match 'WEBCHAT_TOKEN="([^"]+)"') {
            Write-Host "WEBCHAT_TOKEN:" -ForegroundColor $ColorInfo
            Write-Host "  $($matches[1])`n" -ForegroundColor $ColorSuccess
        }
        if ($envContent -match 'CRON_SECRET="([^"]+)"') {
            Write-Host "CRON_SECRET:" -ForegroundColor $ColorInfo
            Write-Host "  $($matches[1])`n" -ForegroundColor $ColorSuccess
        }
    }
    
    Write-Host "=====================================`n" -ForegroundColor $ColorHeader
    
    # Afficher les commandes à exécuter
    Write-Host "POUR DÉMARRER L'APPLICATION:" -ForegroundColor $ColorHeader
    Write-Host "============================`n" -ForegroundColor $ColorHeader
    
    Write-Host "1. Démarrez la Gateway (Next.js):" -ForegroundColor $ColorInfo
    Write-Host "   cd gateway" -ForegroundColor $ColorSuccess
    Write-Host "   npm run dev`n" -ForegroundColor $ColorSuccess
    
    Write-Host "2. Démarrez l'Agent (Python):" -ForegroundColor $ColorInfo
    Write-Host "   cd agent" -ForegroundColor $ColorSuccess
    Write-Host "   uv run uvicorn main:app --reload`n" -ForegroundColor $ColorSuccess
    
    Write-Host "3. (Optionnel) Démarrez l'interface Gradio:" -ForegroundColor $ColorInfo
    Write-Host "   cd agent" -ForegroundColor $ColorSuccess
    Write-Host "   uv run python gradio_app.py`n" -ForegroundColor $ColorSuccess
    
    Write-Host "============================`n" -ForegroundColor $ColorHeader
    
    Write-Host "ACCÈS WEBCHAT:" -ForegroundColor $ColorHeader
    Write-Host "==============`n" -ForegroundColor $ColorHeader
    Write-Host "URL: http://localhost:3000" -ForegroundColor $ColorSuccess
    Write-Host "Token: Utilisez le WEBCHAT_TOKEN ci-dessus`n" -ForegroundColor $ColorWarning
    
    Write-Host "Pour plus d'informations, consultez README.md`n" -ForegroundColor $ColorInfo
}

# ============================================================
# SCRIPT PRINCIPAL
# ============================================================

try {
    # Afficher l'en-tête du script
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor $ColorHeader
    Write-Host "║                                                                ║" -ForegroundColor $ColorHeader
    Write-Host "║   my-claw — Initialisation de l'environnement                  ║" -ForegroundColor $ColorHeader
    Write-Host "║   Assistant personnel self-hosted, privacy-first              ║" -ForegroundColor $ColorHeader
    Write-Host "║                                                                ║" -ForegroundColor $ColorHeader
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor $ColorHeader
    Write-Host ""
    
    # ============================================================
    # ÉTAPE 1: Vérification des prérequis
    # ============================================================
    Write-Header "ÉTAPE 1: Vérification des prérequis"
    
    $prerequisitesMet = $true
    
    # Vérifier Node.js
    if (-not (Test-Command "node")) {
        Write-Error "Node.js n'est pas installé"
        Write-Info "Téléchargez et installez Node.js 24+ depuis: https://nodejs.org/"
        $prerequisitesMet = $false
    }
    else {
        if (-not (Test-NodeVersion)) {
            $prerequisitesMet = $false
        }
    }
    
    # Vérifier npm
    if (-not (Test-Command "npm")) {
        Write-Error "npm n'est pas installé (normalement fourni avec Node.js)"
        $prerequisitesMet = $false
    }
    else {
        $npmVersion = npm --version 2>&1
        Write-Success "npm version $npmVersion détecté"
    }
    
    # Vérifier uv
    if (-not (Test-Command "uv")) {
        Write-Error "uv n'est pas installé"
        Write-Info "Installez uv depuis: https://docs.astral.sh/uv/getting-started/installation/"
        $prerequisitesMet = $false
    }
    else {
        $uvVersion = uv --version 2>&1
        Write-Success "uv version $uvVersion détecté"
    }
    
    # Vérifier Ollama (optionnel mais recommandé)
    if (-not (Test-Ollama)) {
        Write-Warning "Ollama ou le modèle qwen3:14b n'est pas disponible"
        Write-Info "Installez Ollama depuis: https://ollama.ai"
        Write-Info "Puis installez le modèle: ollama pull qwen3:14b"
        # On continue quand même, car Ollama est optionnel pour le setup
    }
    
    if (-not $prerequisitesMet) {
        Write-Error "Certains prérequis ne sont pas satisfaits. Veuillez les installer avant de continuer."
        exit 1
    }
    
    # ============================================================
    # ÉTAPE 2: Configuration de l'environnement
    # ============================================================
    Write-Header "ÉTAPE 2: Configuration de l'environnement"
    
    # Copier .env.example vers .env.local dans le répertoire gateway
    $gatewayEnvFile = Join-Path $PSScriptRoot "gateway\.env.local"
    $envFileSuccess = Set-EnvironmentFile -SourceFile ".env.example" -TargetFile $gatewayEnvFile
    
    if (-not $envFileSuccess) {
        Write-Error "Échec de la configuration de l'environnement"
        exit 1
    }
    
    # Copier .env.example vers .env dans le répertoire agent
    $agentEnvFile = Join-Path $PSScriptRoot "agent\.env"
    $agentEnvFileSuccess = Set-EnvironmentFile -SourceFile ".env.example" -TargetFile $agentEnvFile
    
    if (-not $agentEnvFileSuccess) {
        Write-Error "Échec de la configuration de l'environnement agent"
        exit 1
    }
    
    # ============================================================
    # ÉTAPE 3: Installation des dépendances Gateway (Next.js)
    # ============================================================
    Write-Header "ÉTAPE 3: Installation des dépendances Gateway (Next.js)"
    
    $gatewayDir = Join-Path $PSScriptRoot "gateway"
    
    if (-not (Test-Path $gatewayDir)) {
        Write-Error "Répertoire gateway non trouvé: $gatewayDir"
        exit 1
    }
    
    # Installer les dépendances npm
    $npmSuccess = Install-NpmDependencies -Directory $gatewayDir
    
    if (-not $npmSuccess) {
        Write-Error "Échec de l'installation des dépendances npm"
        exit 1
    }
    
    # ============================================================
    # ÉTAPE 4: Migrations Prisma
    # ============================================================
    Write-Header "ÉTAPE 4: Migrations Prisma"
    
    $prismaSuccess = Invoke-PrismaMigrations -Directory $gatewayDir
    
    if (-not $prismaSuccess) {
        Write-Error "Échec des migrations Prisma"
        exit 1
    }
    
    # ============================================================
    # ÉTAPE 4.5: Génération du client Prisma
    # ============================================================
    Write-Header "ÉTAPE 4.5: Génération du client Prisma"
    
    Write-Info "Génération du client Prisma dans $gatewayDir..."
    
    # Générer le client Prisma
    $prismaGenerateSuccess = Invoke-CommandSafe -Command "npx" -Arguments "prisma generate" -WorkingDirectory $gatewayDir -Description "Prisma generate"
    
    if (-not $prismaGenerateSuccess) {
        Write-Error "Échec de la génération du client Prisma"
        exit 1
    }
    
    # ============================================================
    # ÉTAPE 5: Installation des dépendances Agent (Python)
    # ============================================================
    Write-Header "ÉTAPE 5: Installation des dépendances Agent (Python)"
    
    $agentDir = Join-Path $PSScriptRoot "agent"
    
    if (-not (Test-Path $agentDir)) {
        Write-Error "Répertoire agent non trouvé: $agentDir"
        exit 1
    }
    
    # Installer les dépendances avec uv
    $uvSuccess = Install-UvDependencies -Directory $agentDir
    
    if (-not $uvSuccess) {
        Write-Error "Échec de l'installation des dépendances Python"
        exit 1
    }
    
    # ============================================================
    # RÉSUMÉ FINAL
    # ============================================================
    Write-Header "RÉSUMÉ DE L'INSTALLATION"
    
    Write-Success "✓ Prérequis vérifiés"
    Write-Success "✓ Configuration de l'environnement Gateway (gateway/.env.local)"
    Write-Success "✓ Configuration de l'environnement Agent (agent/.env)"
    Write-Success "✓ Dépendances Gateway (Next.js) installées"
    Write-Success "✓ Migrations Prisma exécutées"
    Write-Success "✓ Client Prisma généré"
    Write-Success "✓ Dépendances Agent (Python) installées"
    
    Write-Host "`nL'environnement a été initialisé avec succès!" -ForegroundColor $ColorSuccess
    
    # Afficher les étapes suivantes
    Show-NextSteps
    
    exit 0
}
catch {
    Write-Error "Une erreur inattendue s'est produite:"
    Write-Error $_.Exception.Message
    Write-Error "Stack trace: $($_.ScriptStackTrace)"
    exit 1
}
