@echo off
setlocal
if not defined TACTIC_HANDLER_SETTINGS_DIR set "TACTIC_HANDLER_SETTINGS_DIR=%APPDATA%\TACTIC Stream\handler"
start "TACTIC Handler" "%~dp0runtime\pythonw.exe" -I -B -X utf8 "%~dp0TACTIC-Handler\launch.pyw" %*
