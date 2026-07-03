@echo off
chcp 65001 >nul
cd /d "C:\Users\Admin\Desktop\inclusive-maker"
set PYTHONPATH=src

echo.
echo  ===============================================================
echo    Inclusive Maker - Lancement
echo  ===============================================================
echo.
echo  Pour utiliser le VRAI casque Unicorn Hybrid Black :
echo    1. Allume le casque (LED).
echo    2. Ouvre l'application "Unicorn LSL" (bouton dans l'appli,
echo       ou UnicornLSL.exe dans Unicorn Suite).
echo    3. Dans Unicorn LSL : choisis le casque (UN-...),
echo       clique "Open" puis "Start".
echo.
echo  Sans cela, l'appli demarre en mode SIMULATEUR : tu pourras
echo  cliquer "Reconnecter le casque" une fois Unicorn LSL lance.
echo.
echo  ===============================================================
echo.

REM Fenetre de logs en temps reel (optionnelle : si elle ne s'ouvre pas,
REM l'application fonctionne quand meme).
start "Inclusive Maker - Logs temps reel" cmd /k "cd /d C:\Users\Admin\Desktop\inclusive-maker && set PYTHONPATH=src && venv\Scripts\python.exe scripts\log_viewer.py"

echo  Lancement de l'application graphique...
echo.
"venv\Scripts\python.exe" run_app.py

echo.
echo  === Application fermee ===
pause
