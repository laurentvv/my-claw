# Test de l'API Z.ai pour diagnostiquer le problème
# Exécutez ce script avec : .\test_zai_api.ps1

$headers = @{
    "Authorization" = "Bearer 158a69aa670c41c28d2eed264e79f239.tv9CWe5zlKtVCSDY"
    "Content-Type" = "application/json"
}

$body = @{
    model = "glm-4.7"
    messages = @(
        @{
            role = "user"
            content = "Bonjour"
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "=== Test de l'API Z.ai ===" -ForegroundColor Cyan
Write-Host "URL: https://api.z.ai/api/coding/paas/v4/chat/completions" -ForegroundColor Yellow
Write-Host "Clé: 158a69aa670c41c28d2eed264e79f239.tv9CWe5zlKtVCSDY" -ForegroundColor Yellow
Write-Host ""

try {
    Write-Host "Envoi de la requête..." -ForegroundColor Green
    $response = Invoke-RestMethod -Uri "https://api.z.ai/api/coding/paas/v4/chat/completions" -Method Post -Headers $headers -Body $body -ErrorAction Stop
    Write-Host "=== Réponse réussie ===" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "=== Erreur ===" -ForegroundColor Red
    Write-Error "Message: $($_.Exception.Message)"
    Write-Host "StatusCode: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    
    try {
        $errorStream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($errorStream)
        $errorResponse = $reader.ReadToEnd()
        Write-Host "Response: $errorResponse" -ForegroundColor Red
    } catch {
        Write-Host "Impossible de lire la réponse d'erreur" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Test terminé ===" -ForegroundColor Cyan
