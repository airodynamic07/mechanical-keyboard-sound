@echo off
rem Double-click this file to start mechsound. The first run sets it up.
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "..\.venv\Scripts\activate.bat" (
    call "..\.venv\Scripts\activate.bat"
) else (
    echo First run: setting up mechsound, this takes a minute...
    python -m venv .venv || goto nopython
    call ".venv\Scripts\activate.bat"
)

rem Install (or reinstall after an update) if the command is missing.
where mechsound >nul 2>nul || python -m pip install -e . || goto failed

set "HAS_SOUNDS="
for %%f in (sounds\*.wav sounds\*.mp3 sounds\*.ogg sounds\*.flac) do set "HAS_SOUNDS=1"

echo.
echo Type in any app to hear the sounds. Close this window to stop.
echo.
if defined HAS_SOUNDS (
    mechsound --sounds sounds %*
) else (
    echo No recordings in the sounds folder, using the built-in sounds.
    mechsound %*
)
pause
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
