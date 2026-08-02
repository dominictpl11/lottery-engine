# 项目重启和端口检查脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "项目重启和端口检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 步骤1: 检查并停止现有进程
Write-Host "[步骤1] 检查现有Java进程..." -ForegroundColor Yellow
$javaProcesses = Get-Process -Name java -ErrorAction SilentlyContinue
if ($javaProcesses) {
    Write-Host "  发现 $($javaProcesses.Count) 个Java进程，正在停止..." -ForegroundColor Yellow
    $javaProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "  [OK] Java进程已停止" -ForegroundColor Green
} else {
    Write-Host "  [OK] 没有运行中的Java进程" -ForegroundColor Green
}

Write-Host ""

# 步骤2: 检查8080端口占用
Write-Host "[步骤2] 检查8080端口占用情况..." -ForegroundColor Yellow
$port8080 = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
if ($port8080) {
    Write-Host "  [WARN] 8080端口被占用！" -ForegroundColor Red
    Write-Host "  占用进程PID: $($port8080.OwningProcess)" -ForegroundColor Yellow
    $process = Get-Process -Id $port8080.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "  进程名称: $($process.ProcessName)" -ForegroundColor Yellow
        Write-Host "  进程路径: $($process.Path)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "  请手动关闭占用端口的程序，或修改application.yml中的端口号" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "  [OK] 8080端口未被占用，可以启动项目" -ForegroundColor Green
}

Write-Host ""

# 步骤3: 检查配置文件
Write-Host "[步骤3] 检查配置文件..." -ForegroundColor Yellow
$configFile = "src\main\resources\application.yml"
if (Test-Path $configFile) {
    $configContent = Get-Content $configFile -Raw
    if ($configContent -match "port:\s*(\d+)") {
        $configuredPort = $matches[1]
        Write-Host "  [OK] 配置文件存在" -ForegroundColor Green
        Write-Host "  配置的端口: $configuredPort" -ForegroundColor Gray
    } else {
        Write-Host "  [WARN] 未找到端口配置" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [ERROR] 配置文件不存在: $configFile" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 步骤4: 启动项目
Write-Host "[步骤4] 启动项目..." -ForegroundColor Yellow
Write-Host "  使用Maven Wrapper启动..." -ForegroundColor Gray
Write-Host "  请等待项目启动（首次启动可能需要1-3分钟）" -ForegroundColor Gray
Write-Host ""

# 启动项目（后台运行）
$process = Start-Process -FilePath ".\mvnw.cmd" -ArgumentList "spring-boot:run" -NoNewWindow -PassThru

Write-Host "  Maven进程已启动 (PID: $($process.Id))" -ForegroundColor Green
Write-Host ""

# 步骤5: 等待并检查启动状态
Write-Host "[步骤5] 等待项目启动..." -ForegroundColor Yellow
$maxWaitTime = 180  # 最多等待3分钟
$checkInterval = 5  # 每5秒检查一次
$elapsed = 0
$started = $false

while ($elapsed -lt $maxWaitTime -and -not $started) {
    Start-Sleep -Seconds $checkInterval
    $elapsed += $checkInterval
    
    # 检查8080端口
    $port8080 = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
    if ($port8080) {
        Write-Host "  [OK] 8080端口已开始监听！" -ForegroundColor Green
        Write-Host "  状态: $($port8080.State)" -ForegroundColor Gray
        $started = $true
        break
    }
    
    # 检查Java进程是否还在运行
    $javaProcess = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
    if (-not $javaProcess) {
        Write-Host "  [ERROR] Java进程已退出，项目启动可能失败" -ForegroundColor Red
        Write-Host "  请查看控制台日志了解详细错误信息" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "  等待中... ($elapsed 秒)" -ForegroundColor Gray
}

Write-Host ""

# 步骤6: 验证启动成功
if ($started) {
    Write-Host "[步骤6] 验证服务可用性..." -ForegroundColor Yellow
    
    # 等待服务完全就绪
    Start-Sleep -Seconds 3
    
    # 检查健康接口
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/lottery/api/lottery/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [OK] 健康检查通过！" -ForegroundColor Green
        Write-Host "  响应: $($response.Content)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "项目启动成功！" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "访问地址:" -ForegroundColor Cyan
        Write-Host "  健康检查: http://localhost:8080/lottery/api/lottery/health" -ForegroundColor White
        Write-Host "  抽奖接口: http://localhost:8080/lottery/api/lottery/draw" -ForegroundColor White
    } catch {
        Write-Host "  [WARN] 健康检查失败，但端口已监听" -ForegroundColor Yellow
        Write-Host "  错误: $($_.Exception.Message)" -ForegroundColor Gray
        Write-Host "  项目可能还在初始化中，请稍后再试" -ForegroundColor Yellow
    }
} else {
    Write-Host "[步骤6] 启动超时" -ForegroundColor Red
    Write-Host "  项目在 $maxWaitTime 秒内未能启动" -ForegroundColor Yellow
    Write-Host "  可能的原因:" -ForegroundColor Yellow
    Write-Host "    1. 依赖下载缓慢" -ForegroundColor White
    Write-Host "    2. 数据库连接失败" -ForegroundColor White
    Write-Host "    3. Redis连接失败" -ForegroundColor White
    Write-Host "    4. 编译错误" -ForegroundColor White
    Write-Host ""
    Write-Host "  请查看控制台日志了解详细错误信息" -ForegroundColor Yellow
}

Write-Host ""

