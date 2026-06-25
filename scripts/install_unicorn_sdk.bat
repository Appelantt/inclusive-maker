@echo off
REM Assistant d'installation du SDK Unicorn Hybrid Black
REM Ce script ne télécharge PAS le SDK automatiquement (logiciel propriétaire g.tec).
REM Il vérifie l'environnement et guide l'utilisateur.

echo === Assistant SDK Unicorn Hybrid Black ===
echo.

REM Vérifier les droits admin
net session >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Ce script doit etre execute en tant qu'administrateur.
    echo Clic droit sur ce fichier -^> "Executer en tant qu'administrateur".
    pause
    exit /b 1
)

REM Vérifier Windows 10/11
for /f "tokens=*" %%a in ('powershell -Command "[System.Environment]::OSVersion.VersionString"') do set OS=%%a
echo Systeme : %OS%

REM Vérifier Bluetooth
powershell -Command "if ((Get-Service -Name bthserv -ErrorAction SilentlyContinue).Status -eq 'Running') { Write-Host '[OK] Service Bluetooth actif.' } else { Write-Host '[AVERTISSEMENT] Service Bluetooth non demarre.' }"

REM Vérifier Python 64 bits
python -c "import platform; print('[OK] Python', platform.python_version(), platform.architecture()[0])"

REM Vérifier si deja installe
if exist "%USERPROFILE%\Documents\gtec\Unicorn Suite\Hybrid Black\Unicorn.exe" (
    echo [OK] Unicorn Suite Hybrid Black semble deja installe.
) else (
    echo [INFO] Unicorn Suite Hybrid Black NON installe.
)

echo.
echo === Etapes manuelles a suivre ===
echo 1. Allez sur https://www.gtec.at/downloads/
echo 2. Connectez-vous ou creez un compte g.tec.
echo 3. Recherchez "Unicorn Suite Hybrid Black" ou "g.Pype SDK for Python".
echo 4. Telechargez l'installateur Windows.
echo 5. Lancez l'installateur en administrateur et suivez l'assistant.
echo 6. Redemarrez l'ordinateur.
echo 7. Revenez dans le projet et lancez :
echo    venv\Scripts\activate.bat ^&^& python scripts\check_env.py
echo.
pause
