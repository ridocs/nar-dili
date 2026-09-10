@echo off
REM Nar compiler launcher for Windows.
REM Usage:  nar.cmd run ornekler\merhaba.nar
REM NOTE: keep this file pure ASCII with CRLF line endings.
REM cmd.exe reads it in the OEM code page; non-ASCII characters break REM lines.
setlocal
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python -m narc %*
endlocal
