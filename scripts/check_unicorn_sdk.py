#!/usr/bin/env python3
"""Vérifie si le SDK Unicorn Hybrid Black est installé et fonctionnel."""

from pathlib import Path

try:
    import gpype
except ImportError:
    gpype = None

from inclusive_maker.acquisition.eeg_source import UnifiedEEGSource


def check_sdk_installation():
    print("=== Verification SDK Unicorn Hybrid Black ===")

    paths_to_check = [
        Path.home() / "Documents" / "gtec" / "Unicorn Suite" / "Hybrid Black" / "UnicornSuite.exe",
        Path("C:/Program Files/gtec/Unicorn Suite/Hybrid Black/UnicornSuite.exe"),
        Path.home() / "Documents" / "gtec" / "Unicorn Suite" / "Hybrid Black" / "Unicorn Recorder" / "UnicornRecorder.exe",
        Path("C:/Program Files/gtec/Unicorn Suite/Hybrid Black/Unicorn Recorder/UnicornRecorder.exe"),
    ]

    found = False
    for path in paths_to_check:
        if path.exists():
            print(f"[OK] Trouve : {path}")
            found = True

    if not found:
        print("[INFO] Unicorn Suite non trouve aux emplacements habituels.")

    if gpype is None:
        print("[ERREUR] gpype n'est pas installe. Lance : pip install gpype==3.0.9")
    else:
        print(f"[OK] gpype version : {gpype.__version__}")

    print("\nTest de connexion au simulateur / casque...")
    source = UnifiedEEGSource()
    mode = source.get_mode()
    if mode == "gpype":
        print("[OK] Connexion au casque Unicorn reussie via gpype !")
    elif mode == "lsl":
        print("[OK] Connexion au casque Unicorn reussie via LSL (Unicorn Recorder) !")
    else:
        print("[INFO] Basculement sur le generateur synthetique (casque non connecte / SDK manquant).")
    source.disconnect()


if __name__ == "__main__":
    check_sdk_installation()
