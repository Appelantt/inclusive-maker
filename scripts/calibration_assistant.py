"""Assistant de calibration en ligne de commande.

Guide l'utilisateur pour associer ses etats mentaux aux commandes OPEN/CLOSE/IDLE.
Fonctionne sans interface graphique ni casque grace au simulateur EEG.
"""

import time
import sys

import numpy as np

from inclusive_maker.acquisition.generator import EEGGenerator
from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS


STATES = ["OPEN", "CLOSE", "IDLE"]


def clear_line():
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()


def calibrate_state(state: str, detector: MentalStateDetector) -> None:
    print(f"\n=== Calibration : {state} ===")
    if state == "OPEN":
        print("Detendez-vous, fermez les yeux, respirez lentement.")
    elif state == "CLOSE":
        print("Concentrez-vous. Imaginez que vous fermez votre main.")
    else:
        print("Restez dans un etat neutre, ni detendu ni concentre.")

    generator = EEGGenerator(state)
    detector.reset()

    print("Acquisition en cours", end="", flush=True)
    for i in range(10):
        eeg = generator.read_window(1.0)
        features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
        detector.detect(features)
        print(".", end="", flush=True)
        time.sleep(0.05)
    print(" OK")


def main(auto: bool = False):
    print("=" * 60)
    print(" Inclusive Maker - Assistant de calibration")
    print("=" * 60)
    print("\nCe tutoriel vous aide a associer vos etats mentaux")
    print("aux commandes du gant : OUVRIR, FERMER, NEUTRE.\n")

    detector = MentalStateDetector()

    for state in STATES:
        if not auto:
            input(f"Appuyez sur Entrée pour calibrer l'etat {state}...")
        else:
            print(f"Calibration automatique de l'etat {state}...")
        calibrate_state(state, detector)

    print("\n" + "=" * 60)
    print(" Calibration terminee !")
    print("=" * 60)
    print("\nTest rapide : pensez a un etat (OPEN/CLOSE/IDLE).")
    print("Appuyez sur Ctrl+C pour quitter.\n")

    try:
        for _ in range(3 if auto else 10000):
            for state in STATES:
                detector.reset()
                generator = EEGGenerator(state)
                eeg = generator.read_window(2.0)
                features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
                detected = detector.detect(features)
                clear_line()
                sys.stdout.write(f"Etat simule : {state:5} | Detecte : {detected:5}")
                sys.stdout.flush()
                time.sleep(0.5)
        if auto:
            print("\n\nMode automatique termine.")
    except KeyboardInterrupt:
        print("\n\nAu revoir !")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Assistant de calibration")
    parser.add_argument("--auto", action="store_true", help="Mode automatique sans interaction")
    args = parser.parse_args()
    main(auto=args.auto)
