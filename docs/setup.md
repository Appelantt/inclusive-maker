# Guide d'installation

## Prérequis

- Python 3.10 ou plus
- Windows 10/11 (pour l'acquisition directe du casque Unicorn)
- Unicorn Suite Hybrid Black installé (si acquisition réelle)

## Installation

```bash
# Cloner le repo
git clone https://github.com/<ton-compte>/inclusive-maker.git
cd inclusive-maker

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

## Vérification

```bash
python scripts/demo_alpha_command.py
```

Ce script ne nécessite pas de matériel. Il génère des signaux synthétiques.

## Connexion du casque Unicorn

1. Allumer le casque.
2. Appairer le casque en Bluetooth sous Windows.
3. Vérifier que Unicorn Suite est installé dans `Documents/gtec/Unicorn Suite/Hybrid Black`.
4. Mettre `use_generator: false` dans `config/default.yaml`.
5. Lancer `scripts/record_eeg.py`.

## Dépannage

### `UnicornPy` introuvable

Ajoute manuellement le chemin de la librairie :

```python
import sys
sys.path.insert(0, r"C:\Users\<nom>\Documents\gtec\Unicorn Suite\Hybrid Black\Unicorn Python\Lib")
```

### Pas de flux LSL découvert

Vérifie que `pylsl` est installé et qu'il n'y a pas de pare-feu bloquant.

### Erreur de port UDP

Change le port dans `config/default.yaml` si le port 56000 est déjà utilisé.
