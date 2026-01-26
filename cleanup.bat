@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Equity Minions - Project Cleanup
echo ========================================
echo.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo Project folder: %PROJECT_DIR%
echo.

:: Counter for deleted items
set /a DELETED=0
set /a FOUND=0

echo [1/5] Cleaning Windows/OS artifacts...
echo ----------------------------------------

:: Delete nul file (Windows artifact)
if exist "nul" (
    del /f "nul" 2>nul
    if not exist "nul" (
        echo   Deleted: nul
        set /a DELETED+=1
    )
)

:: Delete Thumbs.db recursively
for /r %%i in (Thumbs.db) do (
    if exist "%%i" (
        del /f "%%i" 2>nul
        echo   Deleted: %%i
        set /a DELETED+=1
    )
)

:: Delete .DS_Store recursively
for /r %%i in (.DS_Store) do (
    if exist "%%i" (
        del /f "%%i" 2>nul
        echo   Deleted: %%i
        set /a DELETED+=1
    )
)

echo.
echo [2/5] Cleaning Python bytecode...
echo ----------------------------------------

:: Delete .pyc files recursively
for /r %%i in (*.pyc) do (
    if exist "%%i" (
        del /f "%%i" 2>nul
        echo   Deleted: %%i
        set /a DELETED+=1
    )
)

:: Delete __pycache__ directories recursively
for /d /r %%i in (__pycache__) do (
    if exist "%%i" (
        rmdir /s /q "%%i" 2>nul
        echo   Deleted: %%i
        set /a DELETED+=1
    )
)

echo.
echo [3/5] Cleaning temporary files...
echo ----------------------------------------

:: Delete .tmp files
for /r %%i in (*.tmp) do (
    if exist "%%i" (
        del /f "%%i" 2>nul
        echo   Deleted: %%i
        set /a DELETED+=1
    )
)

:: Delete .temp files
for /r %%i in (*.temp) do (
    if exist "%%i" (
        del /f "%%i" 2>nul
        echo   Deleted: %%i
        set /a DELETED+=1
    )
)

:: Delete .bak files
for /r %%i in (*.bak) do (
    if exist "%%i" (
        del /f "%%i" 2>nul
        echo   Deleted: %%i
        set /a DELETED+=1
    )
)

:: Delete .log files (except in brain folder)
for %%i in (*.log) do (
    if exist "%%i" (
        del /f "%%i" 2>nul
        echo   Deleted: %%i
        set /a DELETED+=1
    )
)

echo.
echo [4/5] Checking for deprecated files (manual review)...
echo ----------------------------------------

:: Check for deprecated workflow versions
if exist "workflows\equity_research_v1.yaml" (
    echo   FOUND (deprecated): workflows\equity_research_v1.yaml
    set /a FOUND+=1
)
if exist "workflows\equity_research_v2.yaml" (
    echo   FOUND (deprecated): workflows\equity_research_v2.yaml
    set /a FOUND+=1
)
if exist "workflows\equity_research_v3.yaml" (
    echo   FOUND (deprecated): workflows\equity_research_v3.yaml
    set /a FOUND+=1
)

:: Check for old visualizer files
if exist "visualizer\Workflow Visualizer.html" (
    echo   FOUND (deprecated): visualizer\Workflow Visualizer.html
    set /a FOUND+=1
)
if exist "visualizer\agent_flowchart.html" (
    echo   FOUND (deprecated): visualizer\agent_flowchart.html
    set /a FOUND+=1
)

:: Check for files that should be in brain/
for %%i in (*.txt) do (
    if /i not "%%i"=="requirements.txt" (
        echo   FOUND (should move to brain/): %%i
        set /a FOUND+=1
    )
)

:: Check for .md files in root that aren't log.md
for %%i in (*.md) do (
    if /i not "%%i"=="log.md" (
        if /i not "%%i"=="README.md" (
            echo   FOUND (should move to brain/): %%i
            set /a FOUND+=1
        )
    )
)

echo.
echo [5/5] Checking for empty directories...
echo ----------------------------------------

:: List empty directories (but don't delete - might be intentional)
for /d /r %%i in (*) do (
    dir /b "%%i" 2>nul | findstr "^" >nul || (
        echo   FOUND (empty dir): %%i
        set /a FOUND+=1
    )
)

echo.
echo ========================================
echo   Cleanup Complete!
echo ========================================
echo   Items deleted: %DELETED%
echo   Items found for manual review: %FOUND%
echo.

if %FOUND% GTR 0 (
    echo NOTE: Some files were flagged for manual review.
    echo       See housecleaning.md in brain/ for rules.
    echo.
)

echo Press any key to exit...
pause >nul
