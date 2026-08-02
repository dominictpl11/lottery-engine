# Port 8080 Diagnostic Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Port 8080 Diagnostic Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if port 8080 is already in use
Write-Host "[Step 1] Checking if port 8080 is already in use..." -ForegroundColor Yellow
$port8080 = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
if ($port8080) {
    Write-Host "  [WARNING] Port 8080 is already in use!" -ForegroundColor Red
    Write-Host "  Process ID: $($port8080.OwningProcess)" -ForegroundColor Gray
    $process = Get-Process -Id $port8080.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "  Process Name: $($process.ProcessName)" -ForegroundColor Gray
        Write-Host "  Process Path: $($process.Path)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "  Solution: Stop the process or change the port in application.yml" -ForegroundColor Yellow
} else {
    Write-Host "  [OK] Port 8080 is available" -ForegroundColor Green
}
Write-Host ""

# Step 2: Check Java processes
Write-Host "[Step 2] Checking Java processes..." -ForegroundColor Yellow
$javaProcesses = Get-Process -Name java -ErrorAction SilentlyContinue
if ($javaProcesses) {
    Write-Host "  [INFO] Found $($javaProcesses.Count) Java process(es)" -ForegroundColor Cyan
    foreach ($proc in $javaProcesses) {
        Write-Host "    PID: $($proc.Id), Start Time: $($proc.StartTime)" -ForegroundColor Gray
    }
} else {
    Write-Host "  [INFO] No Java processes running" -ForegroundColor Gray
}
Write-Host ""

# Step 3: Check application.yml configuration
Write-Host "[Step 3] Checking application.yml configuration..." -ForegroundColor Yellow
$configFile = "src\main\resources\application.yml"
if (Test-Path $configFile) {
    $configContent = Get-Content $configFile -Raw
    if ($configContent -match "port:\s*(\d+)") {
        $configuredPort = $matches[1]
        Write-Host "  [OK] Found port configuration: $configuredPort" -ForegroundColor Green
        if ($configuredPort -ne "8080") {
            Write-Host "  [INFO] Port is configured as $configuredPort, not 8080" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [WARNING] Could not find port configuration in application.yml" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [ERROR] application.yml not found at $configFile" -ForegroundColor Red
}
Write-Host ""

# Step 4: Check if project is starting
Write-Host "[Step 4] Monitoring port 8080 for 30 seconds..." -ForegroundColor Yellow
$maxWait = 30
$checkInterval = 2
$elapsed = 0
$portOpened = $false

while ($elapsed -lt $maxWait -and -not $portOpened) {
    Start-Sleep -Seconds $checkInterval
    $elapsed += $checkInterval
    $portCheck = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
    if ($portCheck) {
        Write-Host "  [SUCCESS] Port 8080 is now listening!" -ForegroundColor Green
        Write-Host "    State: $($portCheck.State)" -ForegroundColor Gray
        $portOpened = $true
    } else {
        Write-Host "  [WAIT] Still waiting... ($elapsed/$maxWait seconds)" -ForegroundColor Gray
    }
}

if (-not $portOpened) {
    Write-Host "  [TIMEOUT] Port 8080 did not open within $maxWait seconds" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Possible issues:" -ForegroundColor Yellow
    Write-Host "    1. Project is still starting (downloading dependencies)" -ForegroundColor White
    Write-Host "    2. Database connection failed" -ForegroundColor White
    Write-Host "    3. Redis connection failed" -ForegroundColor White
    Write-Host "    4. Port conflict (check with: netstat -ano | findstr :8080)" -ForegroundColor White
    Write-Host "    5. Application startup error (check console logs)" -ForegroundColor White
}

Write-Host ""

# Step 5: Test health endpoint if port is open
if ($portOpened) {
    Write-Host "[Step 5] Testing health endpoint..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/lottery/api/lottery/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [SUCCESS] Health check passed!" -ForegroundColor Green
        Write-Host "    Response: $($response.Content)" -ForegroundColor Gray
        Write-Host "    Status Code: $($response.StatusCode)" -ForegroundColor Gray
    } catch {
        Write-Host "  [WARNING] Health check failed" -ForegroundColor Yellow
        Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Gray
        if ($_.Exception.Response) {
            Write-Host "    Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Diagnostic Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

