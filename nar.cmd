@echo off
REM Nar derleyicisi — Windows başlatıcı.
REM Kullanım:  nar run ornekler\merhaba.nar
setlocal
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python -m narc %*
endlocal
