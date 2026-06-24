"""Démonstration : signaux synthétiques -> features alpha -> commande UDP.

Ce script simule une chaîne complète sans matériel, pour tester la structure
du projet sur n'importe quelle machine.
"""

import time
import numpy as np

from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper
from inclusive_maker.remote_command.client import CommandClient
from inclusive_maker.remote_command.protocol import CommandPacket
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS


def generate_synthetic_eeg(n_samples: int, state: str) -> np.ndarray:
    """Génère un signal EEG synthétique selon l'état cible."""
    t = np.arange(n_samples) / EEG_SAMPLING_RATE
    data = np.zeros((n_samples, 8))

    for ch in range(8):
        noise = np.random.normal(0, 1, n_samples)
        alpha = 0.0
        if state == "OPEN":
            alpha = 15 * np.sin(2 * np.pi * 10 * t)
        elif state == "CLOSE":
            alpha = 2 * np.sin(2 * np.pi * 10 * t)
            beta = 5 * np.sin(2 * np.pi * 20 * t)
            noise += beta
        else:  # IDLE
            alpha = 5 * np.sin(2 * np.pi * 10 * t)

        data[:, ch] = alpha + noise

    return data


def main() -> None:
    detector = MentalStateDetector(
        alpha_high_threshold=10.0,
        alpha_low_threshold=2.0,
        smoothing_window=3,
    )
    mapper = CommandMapper()
    client = CommandClient()

    print("Démonstration inclusive Maker - appuyez sur Ctrl+C pour arrêter")
    print("-" * 60)

    states_cycle = ["OPEN", "IDLE", "CLOSE", "IDLE"]
    try:
        while True:
            for state in states_cycle:
                eeg = generate_synthetic_eeg(EEG_SAMPLING_RATE, state)
                features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
                detected = detector.detect(features)
                command = mapper.map(detected)
                packet = CommandPacket(
                    action=command["action"],
                    value=command["value"],
                    label=command["label"],
                    timestamp=time.time(),
                )
                client.send(packet)
                print(f"[{state:5}] alpha={features['alpha']:6.2f} -> {detected:5} -> {packet.to_dict()}")
                time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nArrêt demandé.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
