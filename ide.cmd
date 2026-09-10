@echo off
REM Nar IDE launcher for Windows. Opens the editor in your browser.
REM Usage:  ide.cmd
REM NOTE: keep this file pure ASCII with CRLF line endings.
setlocal
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python "%~dp0ide\sunucu.py" %*
endlocal
