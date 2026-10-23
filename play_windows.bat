@echo off
setlocal
cd /d "%~dp0"
rem bootstrap.py searches installed runtimes for a working pygame first.
py -3.13 -c "import sys" >nul 2>nul
if not errorlevel 1 (
  py -3.13 bootstrap.py %*
  goto done
)
py -3.12 -c "import sys" >nul 2>nul
if not errorlevel 1 (
  py -3.12 bootstrap.py %*
  goto done
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" bootstrap.py %*
  goto done
)
python bootstrap.py %*
:done
if errorlevel 1 (
  echo Launch failed. See README_KO.md.
  pause
  exit /b 1
)
exit /b 0
