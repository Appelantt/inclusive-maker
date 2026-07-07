#!/usr/bin/env python3
"""Diagnostic capteur par capteur - via pipeline gpype (comme le dashboard).

Connecte le casque via gp.HybridBlack (le meme chemin que gpype_dashboard.py),
capture le signal brut 8 canaux via un TimeSeriesScope natif, et affiche les
statistiques de chaque canal en temps reel pour identifier quels capteurs
repondent et lesquels sont deconnectes.

Usage :
    venv\\Scripts\\python.exe scripts\\diagnose_sensors.py [--serial UN-xxxx]
"""

import argparse
import os
import sys
import time
import threading
import numpy as np

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# QApplication necessaire car TimeSeriesScope est un widget Qt natif gpype
from PySide6 import QtWidgets  # noqa: E402
_qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

import gpype as gp  # noqa: E402
from gpype.backend.core.node import Node  # noqa: E402
Node._is_executed_in_ide = lambda self: True

ELECTRODES = ["Fz", "C3", "Cz", "C4", "Pz", "PO7", "PO8", "Oz"]
FS = 250.0
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"


def quality_label(rms, median_rms):
    """Retourne (label, couleur) selon le rapport RMS/mediane."""
    if rms < 1e-3:
        return "DECONNECTE", RED
    ratio = rms / max(median_rms, 1e-6)
    if ratio < 0.3:
        return "DECONNECTE", RED
    elif ratio < 0.6:
        return "MAUVAIS", RED
    elif ratio < 0.85:
        return "MEDIOCRE", YELLOW
    elif ratio < 1.2:
        return "BON", GREEN
    elif ratio < 1.5:
        return "OK", GREEN
    elif ratio < 2.0:
        return "BRUIT?", YELLOW
    elif ratio < 3.0:
        return "BRUIT", RED
    else:
        return "DECONNECTE/BRUIT", RED


def list_serials():
    """Liste les casques disponibles via UnicornPy."""
    try:
        from gpype.backend.sources.hybrid_black import _ensure_unicorn_path
        _ensure_unicorn_path()
        import UnicornPy
        return list(UnicornPy.GetAvailableDevices(True) or [])
    except Exception:
        return []


def run_diagnostic(serial, duration=30):
    """Lance un pipeline gpype avec HybridBlack et affiche les stats par canal.

    Utilise le meme chemin que gpype_dashboard.py :
      source (HybridBlack) -> TimeSeriesScope natif -> lecture _data_buffer

    Essaye tous les casques disponibles (retry) si le premier ne repond pas.
    """
    # Trouver les casques disponibles
    devices = list_serials()
    if not devices and serial is None:
        print("Aucun casque Unicorn detecte. Allume-le et appaire-le.")
        return 1

    if devices:
        print(f"Casques detectes : {devices}")

    # Construire la liste des candidats a essayer
    if serial:
        # Serial force : on l'essaie en premier, puis les autres en backup
        candidates = ([serial] if serial in devices else []) + \
                     [d for d in devices if d != serial]
        if not candidates:
            candidates = [serial]
    else:
        candidates = devices

    print(f"Candidats a tester : {candidates}")
    print("  -> Unicorn Suite / LSL / Recorder doivent etre FERMES.")
    print()

    # --- Essay chaque casque jusqu'a trouver un qui repond ---
    p = None
    scope = None
    target = None

    for sn in candidates:
        print(f"Connexion au casque {sn} via gpype...")
        try:
            p = gp.Pipeline()
            source = gp.HybridBlack(serial=sn)
            scope = gp.TimeSeriesScope(
                amplitude_limit=500,
                time_window=2,
                name="Raw EEG",
            )
            p.connect(source, scope)
            p.start()
            target = sn
            print(f"  -> Connecte a {sn} !\n")
            break
        except Exception as e:
            print(f"  -> ECHEC : {e}")
            if "couldn't connect" in str(e).lower():
                print(f"  -> {sn} ne repond pas, essai du casque suivant...\n")
                # Nettoyer le pipeline echoue
                try:
                    if p:
                        p.stop()
                except Exception:
                    pass
                p = None
                scope = None
                continue
            else:
                # Autre erreur : on arrete
                print(f"ERREUR non liee a la connexion : {e}")
                return 1

    if p is None or scope is None:
        print("=> Aucun casque n'a reponde apres avoir essaye tous les serials.")
        print("   Allume le casque, FERME Unicorn Suite/LSL/Recorder,")
        print("   et si besoin fais un cycle Bluetooth (OFF/ON) ou rallume le casque.")
        return 1

    print("Pipeline demarre ! Acquisition en cours.\n")

    # --- Attendre que le _data_buffer se remplisse ---
    print("Collecte des donnees (3 s)...", end="", flush=True)
    time.sleep(3)
    print(" OK")

    buf = scope._data_buffer
    if buf is None or buf.shape[0] < 50:
        print("ERREUR : le buffer du scope est vide ou trop petit.")
        print(f"  buffer = {buf}")
        p.stop()
        return 1

    print(f"Buffer : {buf.shape[0]} samples x {buf.shape[1]} canaux\n")

    # --- Affichage du tableau de diagnostic ---
    print("=" * 80)
    print("  TEST DES 8 CAPTEURS EEG (via gpype)")
    print("=" * 80)
    print(f"{'Canal':<6} {'Electrode':<10} {'Std (sans DC)':>14} {'Variance':>12} "
          f"{'Min':>10} {'Max':>10} {'Qualite'}")
    print("-" * 80)

    eeg = buf[:, :8]
    # IMPORTANT : on utilise np.diff() + std, pas le RMS.
    # Le signal brut EEG a une derive DC (rampe lineaire qui augmente avec
    # le temps, observee a ~36000->198000 sur le casque reel).
    # np.diff(x) = x[1:] - x[:-1] retire la rampe lineaire et l'offset constant.
    # Le std du diff reflete uniquement l'amplitude de l'activite cerebrale.
    std_vals = [float(np.std(np.diff(eeg[:, ch]))) for ch in range(8)]
    median_std = float(np.median(std_vals))
    if median_std < 1e-6:
        median_std = 1e-6

    for ch in range(8):
        sig = eeg[:, ch]
        std = std_vals[ch]
        var = float(np.var(sig))
        vmin = float(np.min(sig))
        vmax = float(np.max(sig))
        label, color = quality_label(std, median_std)
        print(f"  {ch:<4} {ELECTRODES[ch]:<10} {std:>14.4f} {var:>12.4f} "
              f"{vmin:>10.4f} {vmax:>10.4f} {color}{label}{RESET}")

    print("-" * 80)
    print(f"  Std median : {median_std:.4f}  (sans derive DC)")
    print()

    # --- Monitoring temps reel ---
    print("=" * 80)
    print("  MONITORING TEMPS REEL (Ctrl+C pour arreter)")
    print("  Chaque ligne = 1 canal. Plus de '|' = plus d'amplitude.")
    print("=" * 80)

    try:
        while True:
            time.sleep(1)  # attendre 1s de nouvelles donnees
            buf = scope._data_buffer
            if buf is None or buf.shape[0] < 50:
                continue

            eeg = buf[:, :8]
            # np.diff + std (sans DC ni rampe lineaire)
            std_vals = [float(np.std(np.diff(eeg[:, ch]))) for ch in range(8)]
            med = max(float(np.median(std_vals)), 1e-6)

            max_bar = 50
            for ch in range(8):
                ratio = std_vals[ch] / med
                bar_len = int(min(ratio, 5.0) / 5.0 * max_bar)
                label, color = quality_label(std_vals[ch], med)
                bar = "|" * max(bar_len, 1)
                print(f"  {ch:<4} {ELECTRODES[ch]:<10} {color}{label:<16}{RESET} "
                      f"{std_vals[ch]:>8.3f} {bar}")

            print(f"\n  (Std median={med:.3f}, sans DC)  [Ctrl+C pour arreter]\n")

    except KeyboardInterrupt:
        print("\nArret demande par l'utilisateur.")

    # Arret propre
    p.stop()
    print("Pipeline arrete. Casque deconnecte.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Diagnostic capteur par capteur via gpype - Unicorn Hybrid Black"
    )
    parser.add_argument("--serial", default=None,
                        help="Numero de serie du casque (defaut: 1er trouve)")
    args = parser.parse_args()

    print()
    print("  DIAGNOSTIC CAPTEURS - Unicorn Hybrid Black (via gpype)")
    print("  Teste chaque electrode individuellement")
    print()
    print("  >>> Allume le casque, FERME Unicorn Suite/LSL/Recorder <<<")
    print()

    return run_diagnostic(args.serial)


if __name__ == "__main__":
    sys.exit(main())