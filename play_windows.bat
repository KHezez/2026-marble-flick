@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if errorlevel 1 (
    python -m venv .venv
  ) else (
    py -3 -m venv .venv
  )
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -c "import pygame; assert pygame.version.ver == '2.6.1'" >nul 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 goto fail
exit /b 0
:fail
echo Please install Python 3.11-3.13 and check the error above.
pause
exit /b 1
