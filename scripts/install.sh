#!/bin/bash
# Script d'installation automatique pour les collaborateurs
# Usage: bash scripts/install.sh

set -e

echo "=== Installation Inclusive Maker ==="

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "Erreur : python3 n'est pas installé."
    exit 1
fi

# Créer l'environnement virtuel s'il n'existe pas
if [ ! -d "venv" ]; then
    echo "Creation de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement
echo "Activation de l'environnement virtuel..."
source venv/bin/activate

# Mettre à jour pip
echo "Mise a jour de pip..."
pip install --upgrade pip

# Installer les dépendances
echo "Installation des dependances..."
pip install -r requirements.txt

# Installer le package en mode editable
echo "Installation du package en mode editable..."
pip install -e .

# Lancer les tests
echo "Lancement des tests..."
pytest tests/ -v

echo "=== Installation terminee avec succes ==="
echo "Pour activer l'environnement: source venv/bin/activate"
