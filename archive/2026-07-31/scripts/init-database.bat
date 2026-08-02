@echo off
REM 数据库初始化脚本
REM 使用方法：双击此文件执行，或在命令行运行

echo ========================================
echo 抽奖引擎数据库初始化
echo ========================================
echo.

REM 检查MySQL是否在PATH中
where mysql >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到MySQL命令
    echo.
    echo 请使用以下方式之一：
    echo   1. 将MySQL bin目录添加到PATH环境变量
    echo   2. 在MySQL客户端中手动执行 init-database.sql
    echo   3. 使用MySQL Workbench等工具执行 init-database.sql
    echo.
    pause
    exit /b 1
)

echo [信息] 找到MySQL命令
echo.
echo 请输入MySQL root用户的密码（如果为空直接回车）：
set /p mysql_password=

if "%mysql_password%"=="" (
    echo 执行初始化脚本（无密码）...
    mysql -u root < init-database.sql
) else (
    echo 执行初始化脚本（有密码）...
    mysql -u root -p[REDACTED_LOCAL_CREDENTIAL] < init-database.sql
)

if %errorlevel% equ 0 (
    echo.
    echo [成功] 数据库初始化完成！
    echo.
    echo 验证数据：
    mysql -u root %mysql_password_opt% -e "USE lottery_db; SELECT 'Activities' as TableName, COUNT(*) as Count FROM activity UNION ALL SELECT 'Strategies', COUNT(*) FROM strategy UNION ALL SELECT 'Strategy Details', COUNT(*) FROM strategy_detail UNION ALL SELECT 'Awards', COUNT(*) FROM award;"
) else (
    echo.
    echo [错误] 数据库初始化失败
    echo 请检查：
    echo   1. MySQL服务是否运行
    echo   2. 用户名密码是否正确
    echo   3. 是否有足够的权限
    echo.
    echo 也可以手动在MySQL客户端执行 init-database.sql 文件
)

echo.
pause





