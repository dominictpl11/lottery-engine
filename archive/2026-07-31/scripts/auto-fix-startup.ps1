# Auto Fix Startup Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Auto Fix Startup Issues" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop existing processes
Write-Host "[Step 1] Stopping existing Java processes..." -ForegroundColor Yellow
Get-Process -Name java -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "[OK] Java processes stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Check port 8080
Write-Host "[Step 2] Checking port 8080..." -ForegroundColor Yellow
$port = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
if ($port) {
    Write-Host "[WARN] Port 8080 is still in use" -ForegroundColor Yellow
    $port | Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize
} else {
    Write-Host "[OK] Port 8080 is available" -ForegroundColor Green
}
Write-Host ""

# Step 3: Check configuration
Write-Host "[Step 3] Checking configuration..." -ForegroundColor Yellow
$configFile = "src\main\resources\application.yml"
if (Test-Path $configFile) {
    $config = Get-Content $configFile -Raw
    if ($config -match "username:\s*(\w+)") {
        $dbUser = $matches[1]
        Write-Host "  Database user: $dbUser" -ForegroundColor Gray
    }
    if ($config -match "password:[REDACTED_LOCAL_CREDENTIAL](\w+)") {
        $dbPass = $matches[1]
        Write-Host "  Database password: [hidden]" -ForegroundColor Gray
    }
    Write-Host "[OK] Configuration file exists" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Configuration file not found" -ForegroundColor Red
}
Write-Host ""

# Step 4: Start project
Write-Host "[Step 4] Starting project..." -ForegroundColor Yellow
Write-Host "  This may take 1-3 minutes for first startup" -ForegroundColor Gray
Start-Process -FilePath ".\mvnw.cmd" -ArgumentList "spring-boot:run" -NoNewWindow
Start-Sleep -Seconds 5
Write-Host "[OK] Project start command executed" -ForegroundColor Green
Write-Host ""

# Step 5: Monitor startup
Write-Host "[Step 5] Monitoring startup (waiting 90 seconds)..." -ForegroundColor Yellow
$maxWait = 90
$interval = 10
$elapsed = 0
$started = $false

while ($elapsed -lt $maxWait -and -not $started) {
    Start-Sleep -Seconds $interval
    $elapsed += $interval
    
    $port = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
    if ($port) {
        Write-Host "  [SUCCESS] Port 8080 is now listening!" -ForegroundColor Green
        $started = $true
        break
    }
    
    $java = Get-Process -Name java -ErrorAction SilentlyContinue
    if (-not $java) {
        Write-Host "  [ERROR] Java process exited, startup may have failed" -ForegroundColor Red
        Write-Host "  Please check the Maven console logs" -ForegroundColor Yellow
        break
    }
    
    Write-Host "  Waiting... ($elapsed seconds)" -ForegroundColor Gray
}

Write-Host ""

# Step 6: Final check
if ($started) {
    Write-Host "[Step 6] Testing health endpoint..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/lottery/api/lottery/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [SUCCESS] Health check passed! Response: $($response.Content)" -ForegroundColor Green
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Project started successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Access URLs:" -ForegroundColor Cyan
        Write-Host "  Health: http://localhost:8080/lottery/api/lottery/health" -ForegroundColor White
        Write-Host "  Draw:   http://localhost:8080/lottery/api/lottery/draw" -ForegroundColor White
    } catch {
        Write-Host "  [WARN] Health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "  But port 8080 is listening, service may still be initializing" -ForegroundColor Gray
    }
} else {
    Write-Host "[Step 6] Startup timeout or failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "  1. Database connection failed - Check MySQL and database setup" -ForegroundColor White
    Write-Host "  2. Redis connection failed - Check Redis service" -ForegroundColor White
    Write-Host "  3. Compilation error - Check Maven console logs" -ForegroundColor White
    Write-Host ""
    Write-Host "Please check the Maven console output for detailed error messages" -ForegroundColor Yellow
}

Write-Host ""

