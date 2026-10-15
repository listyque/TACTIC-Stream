@echo off
setlocal DisableDelayedExpansion
rem Thin entry point; arguments are forwarded once without CALL.
set "TACTIC_LAUNCH_ENTRY=manage"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\local\tactic_bootstrap.ps1" %*
set "RESULT=%ERRORLEVEL%"
exit /b %RESULT%
