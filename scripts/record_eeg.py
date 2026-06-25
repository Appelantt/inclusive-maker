#!/usr/bin/env python3
"""Script d'enregistrement EEG avec générateur synthétique ou casque Unicorn.

Usage:
    set PYTHONPATH=src
    python scripts\record_eeg.py --duration 30 --output data/raw/record_demo.csv

Sans matériel Unicorn, le script utilise EEGGenerator pour produire un
signal de démonstration.  Avec le casque, réglez use_unicorn=True dans
config/default.yaml ou passez --device unicorn (nécessite g.Pype / Unicorn Suite).
"""

import argparse
import csv
import time
from pathlib import Path

import numpy as np

from inclusive_maker.acquisition.generator import EEGGenerator
from inclusive_maker.acquisition.unicorn_connector import UnicornConnector
from inclusive_maker.shared.constants import EEG_CHANNEL_COUNT
from inclusive_maker.shared.utils import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Enregistrement EEG")
    parser.add_argument("--duration", type=float, default=30.0, help="Durée d'enregistrement en secondes")
    parser.add_argument("--output", type=str, default="data/raw/record_demo.csv", help="Chemin du fichier CSV")
    parser.add_argument("--device", type=str, default=None, choices=["generator", "unicorn"], help="Source EEG")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / "config" / "default.yaml"
    config = load_config(config_path)

    device = args.device or config.get("eeg", {}).get("device", "generator")
    use_unicorn = device == "unicorn"

    connector = None
    source = None
    if use_unicorn:
        connector = UnicornConnector(use_generator=False)
        source = connector.connect()
        if source is None:
            print("Impossible de se connecter au casque Unicorn.")
            print("Basculement sur le générateur synthétique.")
            use_unicorn = False
    if not use_unicorn:
        source = EEGGenerator("IDLE")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Source : {'Unicorn Hybrid Black' if use_unicorn else 'Générateur synthétique'}")
    print(f"Enregistrement vers {output} - appuyez sur Ctrl+C pour arrêter")

    header = [f"ch{i}" for i in range(EEG_CHANNEL_COUNT)] + ["timestamp", "state"]
    rows = 0
    start = time.time()

    try:
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            while True:
                elapsed = time.time() - start
                if elapsed >= args.duration:
                    break

                # Change d'état toutes les 5s pour la démo
                demo_state = ["OPEN", "CLOSE", "IDLE"][int(elapsed // 5) % 3]
                if hasattr(source, "set_state"):
                    source.set_state(demo_state)

                if use_unicorn:
                    # TODO: remplacer par source.get_data() quand g.Pype est disponible
                    chunk = np.zeros((EEG_CHANNEL_COUNT,))
                else:
                    chunk = source.read(1)[0]

                writer.writerow(list(chunk) + [time.time(), demo_state])
                rows += 1
                time.sleep(1.0 / 250)  # 250 Hz
    except KeyboardInterrupt:
        print("\nEnregistrement interrompu par l'utilisateur.")
    finally:
        if connector:
            connector.disconnect()

    print(f"\nEnregistrement terminé : {rows} échantillons sauvegardés dans {output}")


if __name__ == "__main__":
    main()
