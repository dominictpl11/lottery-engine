$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$healthUri = "http://localhost:8080/lottery/api/lottery/health"

Write-Host "Lottery Engine - Java status" -ForegroundColor Cyan
Write-Host "Project root: $repoRoot" -ForegroundColor DarkGray

$javaProcesses = Get-Process -Name java -ErrorAction SilentlyContinue
if ($javaProcesses) {
    $processIds = ($javaProcesses | Select-Object -ExpandProperty Id) -join ", "
    Write-Host "[OK] Java process detected. PID: $processIds" -ForegroundColor Green
} else {
    Write-Host "[INFO] No Java process detected." -ForegroundColor Yellow
}

$listeners = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $listenerIds = ($listeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
    Write-Host "[OK] Port 8080 is listening. PID: $listenerIds" -ForegroundColor Green
} else {
    Write-Host "[INFO] Port 8080 is not listening." -ForegroundColor Yellow
}

try {
    $response = Invoke-WebRequest -Uri $healthUri -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "[OK] Health check returned HTTP $($response.StatusCode): $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Health check is unavailable: $($_.Exception.Message)" -ForegroundColor Yellow
}
