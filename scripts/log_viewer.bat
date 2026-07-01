@echo off
chcp 65001 >nul
title Inclusive Maker - Logs temps reel
setlocal

cd /d "C:\Users\Admin\Desktop\inclusive-maker"
set PYTHONPATH=src

echo.
echo  === Terminal de logs Inclusive Maker ===
echo  Ce terminal affiche en temps reel ce qui se passe dans l'application.
echo  Gardez-le ouvert pendant que vous utilisez l'interface.
echo.

"venv\Scripts\python.exe" scripts\log_viewer.py

endlocal
pause