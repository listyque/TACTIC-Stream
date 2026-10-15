@echo off
cd /d "%~dp0..\.."
start "" ".venv\Scripts\pythonw.exe" -B "tools\shared_ui_demo\gantt_qml.py" --language ru --mode dark
start "" "%~dp0output\gantt-report.html"
