@echo off
echo ============================================
echo  Equity Research Workflow - Live Visualizer
echo ============================================
echo.

set TICKER=%1
if "%TICKER%"=="" set TICKER=6682 HK

echo Starting workflow for: %TICKER%
echo.
echo The visualizer will open in your browser.
echo Watch the minions work!
echo.

cd /d "%~dp0"
python run_workflow_live.py --ticker "%TICKER%" --workflow equity_research_v3 --port 8765

pause
