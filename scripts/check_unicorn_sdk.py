#!/usr/bin/env python3
"""Vérifie si le SDK Unicorn Hybrid Black est installé et fonctionnel."""

from pathlib import Path

try:
    import gpype
except ImportError:
    gpype = None

from inclusive_maker.acquisition.unicorn_connector import UnicornConnector


def check_sdk_installation():
    print("=== Vérification SDK Unicorn Hybrid Black ===")

    paths_to_check = [
        Path.home() / "Documents" / "gtec" / "Unicorn Suite" / "Hybrid Black" / "Unicorn.exe",
        Path("C:/Program Files/gtec/Unicorn Suite/Hybrid Black/Unicorn.exe"),
        Path("C:/Program Files (x86)/gtec/Unicorn Suite/Hybrid Black/Unicorn.exe"),
    ]

    found = False
    for path in paths_to_check:
        if path.exists():
            print(f"[OK] Trouvé : {path}")
            found = True

    if not found:
        print("[INFO] Unicorn Suite non trouvé aux emplacements habituels.")

    if gpype is None:
        print("[ERREUR] gpype n'est pas installé. Lance : pip install gpype==3.0.9")
    else:
        print(f"[OK] gpype version : {gpype.__version__}")

    print("\nTest de connexion au simulateur / casque...")
    connector = UnicornConnector(use_generator=False)
    source = connector.connect()
    if connector.is_native():
        print("[OK] Connexion au casque Unicorn réussie !")
    else:
        print("[INFO] Basculement sur le générateur synthétique (casque non connecté / SDK manquant).")
    connector.disconnect()


if __name__ == "__main__":
    check_sdk_installation()
