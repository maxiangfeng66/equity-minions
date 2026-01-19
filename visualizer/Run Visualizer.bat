@echo off
chcp 65001 >nul
title Claude Minions - Agent Visualizer

echo.
echo  ==========================================
echo       Claude Minions - Agent Visualizer
echo  ==========================================
echo.
echo  Opening visualizer in your browser...
echo.

REM Open the HTML file directly in default browser
start "" "%~dp0Claude Minions.html"

echo  Done! The visualizer should open in your browser.
echo.
echo  To load your project:
echo    1. Click "Open Project Folder"
echo    2. Select a folder with minions.json or session_state.json
echo    3. Or click "View Demo" to see sample data
echo.
pause
