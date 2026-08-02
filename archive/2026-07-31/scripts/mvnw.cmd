@REM Maven Wrapper for Windows
@REM This is a simple wrapper script that checks for Maven and runs it
@echo off
setlocal

set MAVEN_HOME=
set MAVEN_CMD=mvn

REM Check if Maven is in PATH
where mvn >nul 2>&1
if %errorlevel% equ 0 (
    echo [信息] 找到Maven，使用系统Maven...
    goto :run
)

REM Check common Maven installation locations
if exist "C:\Program Files\Apache\maven\bin\mvn.cmd" (
    set "MAVEN_HOME=C:\Program Files\Apache\maven"
    set "MAVEN_CMD=%MAVEN_HOME%\bin\mvn.cmd"
    echo [信息] 找到Maven安装：%MAVEN_HOME%
    goto :run
)

if exist "C:\apache-maven\bin\mvn.cmd" (
    set "MAVEN_HOME=C:\apache-maven"
    set "MAVEN_CMD=%MAVEN_HOME%\bin\mvn.cmd"
    echo [信息] 找到Maven安装：%MAVEN_HOME%
    goto :run
)

REM Check if JAVA_HOME is set and try to use embedded Maven
if defined JAVA_HOME (
    echo [警告] 未找到Maven安装
    echo [提示] 请执行以下操作之一：
    echo   1. 安装Maven并配置环境变量
    echo   2. 使用IDE（如IntelliJ IDEA）运行项目
    echo   3. 下载Maven Wrapper：https://maven.apache.org/wrapper/
    echo.
    pause
    exit /b 1
)

:run
echo [信息] 使用Maven命令：%MAVEN_CMD%
echo.

REM Pass all arguments to Maven
%MAVEN_CMD% %*

