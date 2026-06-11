@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ================================
echo Temu 前台截图助手 v0.1
echo ================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 没找到 Python。请确认 Python 已安装并加入 PATH。
    echo 也可以手动用 C:\Users\Yunxi\AppData\Local\Programs\Python\Python311\python.exe 运行。
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [首次运行] 正在创建虚拟环境 .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败。
        pause
        exit /b 1
    )
)

echo [检查] 安装/更新依赖...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败。
    pause
    exit /b 1
)

echo.
echo [启动] 打开截图助手...
".venv\Scripts\python.exe" -m src.main

echo.
echo 程序已退出。
pause
