@echo off
setlocal
title TACTIC Stream
pushd "%~dp0tactic_stream"
if errorlevel 1 exit /b 1

if not exist ".venv\Scripts\python.exe" (
    echo Python environment is missing. Follow tactic_stream\README.md to install it.
    goto failed
)

".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3, 14), 'Python 3.14+ is required'; import fastapi, uvicorn, dateutil"
if errorlevel 1 goto failed

".venv\Scripts\python.exe" -B -X utf8 run.py init --if-needed
if errorlevel 1 goto failed

".venv\Scripts\python.exe" -B -X utf8 run.py upgrade
if errorlevel 1 goto failed
echo Starting TACTIC Stream. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -B -X utf8 run.py serve --open-browser %*
if errorlevel 1 goto failed
popd
exit /b 0

:failed
echo TACTIC Stream could not start. See the error above.
pause
popd
exit /b 1
