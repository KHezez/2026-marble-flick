@echo off
setlocal
cd /d "%~dp0"
rem Keep any existing .venv untouched; use an explicit supported runtime.
if exist ".venv-py312\Scripts\python.exe" goto ready
py -3.12 -c "import sys,struct; sys.exit(0 if sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
if errorlevel 1 goto try_python
py -3.12 -m venv .venv-py312
if errorlevel 1 goto fail
goto ready
:try_python
python -c "import sys,struct; sys.exit(0 if sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
if errorlevel 1 goto missing_python
python -m venv .venv-py312
if errorlevel 1 goto fail
:ready
".venv-py312\Scripts\python.exe" -c "import sys,struct; sys.exit(0 if sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
if errorlevel 1 goto bad_env
".venv-py312\Scripts\python.exe" -c "import pygame; assert pygame.version.ver == '2.6.1'" >nul 2>nul
if not errorlevel 1 goto launch
".venv-py312\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto fail
:launch
".venv-py312\Scripts\python.exe" main.py %*
if errorlevel 1 goto fail
exit /b 0
:missing_python
echo Python 3.12 64-bit is required by this launcher.
echo Install it with: winget install -e --id Python.Python.3.12
echo Then reopen this launcher. Other Python versions can stay installed.
pause
exit /b 1
:bad_env
echo .venv-py312 is not a working Python 3.12 64-bit environment.
echo Rename that folder to keep a backup, then run this launcher again.
pause
exit /b 1
:fail
echo Setup or launch failed. See the error above and README_KO.md.
pause
exit /b 1
