@echo off
rem Double-click to turn on keyboard sounds. A key icon appears next to the
rem clock: click it to turn the sound on/off, right-click for volume and quit.
rem The first run sets everything up.
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "..\.venv\Scripts\activate.bat" (
    call "..\.venv\Scripts\activate.bat"
) else (
    echo First run: setting up keyboard sounds, this takes a minute...
    python -m venv .venv || goto nopython
    call ".venv\Scripts\activate.bat"
)

rem Install, or finish installing after an update, if the tray app is missing.
where mechsound-tray >nul 2>nul || python -m pip install -e . || goto failed

start "" mechsound-tray %*
exit /b

:nopython
echo.
echo Python was not found. Install it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" on the first install screen.
pause
exit /b 1

:failed
echo.
echo Setup failed. Take a screenshot of this window and ask for help.
pause
exit /b 1
