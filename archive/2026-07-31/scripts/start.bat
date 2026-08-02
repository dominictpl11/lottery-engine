@echo off
echo ========================================
echo 智能营销抽奖引擎启动脚本
echo ========================================
echo.

REM 检查Java环境
java -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Java环境，请先安装JDK 1.8+
    pause
    exit /b 1
)

echo [信息] 检测到Java环境
echo.

REM 检查Maven是否可用
where mvn >nul 2>&1
if %errorlevel% equ 0 (
    echo [信息] 检测到Maven，使用Maven启动...
    echo.
    mvn spring-boot:run
) else (
    echo [警告] 未找到Maven命令
    echo [提示] 请使用以下方式之一启动项目：
    echo   1. 安装Maven后使用: mvn spring-boot:run
    echo   2. 使用IDE（如IntelliJ IDEA或Eclipse）运行LotteryApplication类
    echo   3. 先打包后运行: mvn clean package 然后 java -jar target/lottery-engine-1.0.0.jar
    echo.
    echo [提示] 项目依赖以下服务，请确保已启动：
    echo   - MySQL (localhost:3306)
    echo   - Redis (localhost:6379)
    echo   - RocketMQ (localhost:9876) - 可选
    echo   - ZooKeeper (localhost:2181) - 可选（如果使用Dubbo）
    echo.
    pause
)

