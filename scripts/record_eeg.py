"""Script d'enregistrement EEG (à implémenter selon le matériel disponible)."""

import time
import csv
from pathlib import Path

from inclousive_maker.acquisition.unicorn_connector import UnicornConnector
from inclousive_maker.shared.constants import EEG_SAMPLING_RATE


def main() -> None:
    connector = UnicornConnector(use_generator=True)
    source = connector.connect()

    if source is None:
        print("Impossible d'initialiser la source EEG.")
        return

    output = Path("data/raw/record_demo.csv")
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Enregistrement vers {output} - appuyez sur Ctrl+C pour arrêter")

    # TODO: remplacer par un vrai pipeline g.Pype avec CsvWriter
    try:
        with open(output, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([f"ch{i}" for i in range(8)] + ["timestamp"])
            while True:
                # Ici on simule une acquisition
                time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nEnregistrement terminé.")
    finally:
        connector.disconnect()


if __name__ == "__main__":
    main()
