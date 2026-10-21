@echo off
setlocal
cd /d "%~dp0"
set SDL_VIDEODRIVER=dummy
set SDL_AUDIODRIVER=dummy
if not exist ".venv\Scripts\python.exe" (
  echo Run play_windows.bat once to install dependencies.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -s tests -v
set test_result=%errorlevel%
pause
exit /b %test_result%
