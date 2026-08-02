@echo off
echo ========================================
echo 使用Java直接运行项目（无需Maven）
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

REM 设置类路径
set CLASSPATH=target\classes
for /r target\lib %%a in (*.jar) do set CLASSPATH=!CLASSPATH!;%%a

REM 检查是否已编译
if not exist "target\classes\com\seckiller\lottery\LotteryApplication.class" (
    echo [错误] 项目未编译，请先编译项目
    echo [提示] 使用IDE编译或安装Maven后执行: mvn clean compile
    pause
    exit /b 1
)

echo [信息] 找到已编译的类文件
echo [信息] 启动应用...
echo.

REM 运行主类
java -cp "%CLASSPATH%" com.seckiller.lottery.LotteryApplication

pause

