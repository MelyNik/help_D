@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM === путь к проекту ===
set APP=D:\Programs\helpD-main
cd /d "%APP%"

REM === активируем виртуалку ===
if exist "%APP%\.venv\Scripts\activate.bat" (
  call "%APP%\.venv\Scripts\activate.bat"
)

REM === запускаем (режим/ID/override придут через ENV от schtasks) ===
python .\main.py

endlocal
