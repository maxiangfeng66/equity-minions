@echo off
title Equity Minions - Agent Logger
cd /d "%~dp0.."
echo.
echo ================================================================================
echo                    EQUITY MINIONS - AGENT LOGGER
echo ================================================================================
echo.
echo Choose an option:
echo   1. View System Architecture
echo   2. Run Demo Session (creates sample logs)
echo   3. Open Logs Folder
echo   4. Exit
echo.
set /p choice="Enter choice (1-4): "

if "%choice%"=="1" (
    python agents/agent_logger.py
    pause
) else if "%choice%"=="2" (
    python agents/agent_logger.py --demo
    pause
) else if "%choice%"=="3" (
    start "" "agents\logs"
) else if "%choice%"=="4" (
    exit
) else (
    echo Invalid choice
    pause
)
