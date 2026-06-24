#!/usr/bin/env python3
"""Lanceur principal de l'application Inclusive Maker.

Tente d'utiliser PySide6 si disponible, sinon bascule automatiquement
sur Tkinter qui est natif a Python.
"""

import sys
import os

# Ajouter src/ au PYTHONPATH pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def run_tkinter_app():
    """Lance l'interface Tkinter."""
    from frontend.inclusive_app_tk import main
    main()


def run_pyside_app():
    """Lance l'interface PySide6."""
    from frontend.inclusive_app import main
    main()


def main():
    try:
        import PySide6  # noqa: F401
        print("PySide6 detecte - lancement de l'interface moderne.")
        run_pyside_app()
    except ImportError:
        print("PySide6 non disponible - utilisation de Tkinter (natif).")
        run_tkinter_app()


if __name__ == "__main__":
    main()
