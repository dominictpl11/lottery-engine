@echo off
setlocal

pushd "%~dp0.." >nul
if errorlevel 1 (
    echo [ERROR] Unable to locate the project root.
    exit /b 1
)

where java >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Java was not found. Install JDK 8 or newer and add it to PATH.
    popd
    exit /b 1
)

where mvn >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Maven was not found. Install Maven 3.6 or newer and add it to PATH.
    popd
    exit /b 1
)

echo [INFO] Project root: %CD%
echo [INFO] Starting the Java application with Maven...
mvn spring-boot:run
set "SCRIPT_EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %SCRIPT_EXIT_CODE%
