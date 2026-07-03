#!/usr/bin/env python3
"""Lanceur principal de l'application Inclusive Maker."""

import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def run_dashboard_app():
    from frontend.dashboard_app import main
    main()


def run_pyside_app():
    from frontend.inclusive_app import main
    main()


def run_tkinter_app():
    from frontend.inclusive_app_tk import main
    main()


def _launch():
    try:
        run_dashboard_app()
    except ImportError as e:
        print(f"Dashboard indisponible : {e}")
        try:
            import PySide6  # noqa: F401
            print("PySide6 detecte - lancement de l'interface moderne.")
            run_pyside_app()
        except ImportError:
            print("PySide6 non disponible - utilisation de Tkinter (natif).")
            run_tkinter_app()


def main():
    try:
        _launch()
    except Exception:
        # Ne jamais fermer la fenetre en silence : afficher l'erreur et attendre.
        print("\n" + "=" * 64)
        print("  L'APPLICATION A RENCONTRE UNE ERREUR")
        print("=" * 64)
        traceback.print_exc()
        print("=" * 64)
        print("  Copie ce message pour diagnostic.")
        try:
            input("  Appuie sur Entree pour fermer cette fenetre... ")
        except EOFError:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
