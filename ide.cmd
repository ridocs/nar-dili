@echo off
REM Nar IDE launcher for Windows -- opens the desktop app window.
REM Usage:  ide.cmd            (desktop window)
REM         ide.cmd --tarayici (browser tab instead)
REM NOTE: keep this file pure ASCII with CRLF line endings.
setlocal
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python "%~dp0ide\masaustu.py" %*
endlocal
