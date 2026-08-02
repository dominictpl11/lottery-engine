# Maven快速安装脚本
# 需要管理员权限运行

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Maven安装脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[错误] 需要管理员权限运行此脚本" -ForegroundColor Red
    Write-Host "[提示] 右键PowerShell，选择'以管理员身份运行'" -ForegroundColor Yellow
    pause
    exit 1
}

# 检查是否已安装
$mavenPath = Get-Command mvn -ErrorAction SilentlyContinue
if ($mavenPath) {
    Write-Host "[信息] Maven已安装：" -ForegroundColor Green
    & mvn -version
    exit 0
}

Write-Host "[信息] 开始安装Maven..." -ForegroundColor Yellow
Write-Host ""

# 尝试使用winget安装
$wingetPath = Get-Command winget -ErrorAction SilentlyContinue
if ($wingetPath) {
    Write-Host "[信息] 使用winget安装Maven..." -ForegroundColor Yellow
    winget install Apache.Maven
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[成功] Maven安装完成！" -ForegroundColor Green
        Write-Host ""
        Write-Host "[提示] 请重新打开终端，然后运行: mvn spring-boot:run" -ForegroundColor Cyan
        pause
        exit 0
    }
}

# 如果winget失败，提供手动安装说明
Write-Host "[提示] 自动安装失败，请手动安装Maven：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 访问: https://maven.apache.org/download.cgi" -ForegroundColor Cyan
Write-Host "2. 下载 apache-maven-3.9.x-bin.zip" -ForegroundColor Cyan
Write-Host "3. 解压到: C:\Program Files\Apache\maven" -ForegroundColor Cyan
Write-Host "4. 添加环境变量:" -ForegroundColor Cyan
Write-Host "   MAVEN_HOME = C:\Program Files\Apache\maven" -ForegroundColor Cyan
Write-Host "   PATH += %MAVEN_HOME%\bin" -ForegroundColor Cyan
Write-Host ""
Write-Host "或者使用IDE（如IntelliJ IDEA）运行项目，IDE自带Maven" -ForegroundColor Yellow
Write-Host ""
pause

