@echo off
REM Script d'installation automatique pour Windows
REM Usage: double-cliquez ou executez dans cmd: scripts\install.bat

echo === Installation Inclusive Maker (Windows) ===

REM Verifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Erreur : python n'est pas installe ou pas dans le PATH.
    echo Telechargez Python ici : https://www.python.org/downloads/
    echo Cochez "Add Python to PATH" lors de l'installation.
    exit /b 1
)

REM Creer l'environnement virtuel s'il n'existe pas
if not exist "venv\" (
    echo Creation de l'environnement virtuel...
    python -m venv venv
)

REM Activer l'environnement
echo Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Mettre a jour pip
echo Mise a jour de pip...
python -m pip install --upgrade pip

REM Installer les dependances
echo Installation des dependances...
pip install -r requirements.txt

REM Installer le package en mode editable
echo Installation du package en mode editable...
pip install -e .

REM Lancer les tests
echo Lancement des tests...
pytest tests/ -v

echo === Installation terminee avec succes ===
echo Pour activer l'environnement : venv\Scripts\activate.bat
