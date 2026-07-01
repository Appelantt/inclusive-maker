@echo off
chcp 65001 >nul
setlocal

cd /d "C:\Users\Admin\Desktop\inclusive-maker"
set PYTHONPATH=src

echo.
echo  === Inclusive Maker - Lancement avec terminal de logs ===
echo.
echo  Ouverture du terminal de logs en temps reel dans une fenetre separee...
start "Inclusive Maker - Logs temps reel" cmd /k "cd /d C:\Users\Admin\Desktop\inclusive-maker && set PYTHONPATH=src && venv\Scripts\python.exe scripts\log_viewer.py"

echo  Attente du demarrage du visualiseur de logs...
timeout /t 2 /nobreak >nul

echo  Lancement de l application graphique...
echo  (Gardez la fenetre des logs ouverte pour suivre ce qui se passe)
echo.
"venv\Scripts\python.exe" run_app.py

endlocal
pause
