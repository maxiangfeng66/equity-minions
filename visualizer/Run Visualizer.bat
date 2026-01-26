@echo off
title Minions Visualizer Server
cd /d "%~dp0\.."
echo Starting Minions Visualizer Server...
echo.
echo Open http://localhost:8765 in your browser
echo.
python visualizer/serve_visualizer.py 8765
pause
